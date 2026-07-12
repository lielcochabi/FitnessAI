"""
Tests for main.py - the HTTP API, exercised through FastAPI's TestClient.
No real server process and no real network calls; TestClient runs the ASGI
app in-process. Used as a context manager so the app's lifespan (init_dspy)
actually runs, matching what happens when the real server starts.
"""
from fastapi.testclient import TestClient

from main import app


def _signup_and_login(client, username="liel", password="hunter2"):
    client.post("/signup", json={
        "username": username,
        "first_name": "Liel",
        "email": f"{username}@example.com",
        "password": password,
    })
    resp = client.post("/login", json={"username": username, "password": password})
    return resp.json()["session_id"]


def test_health_check():
    with TestClient(app) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_signup_then_login_returns_session():
    with TestClient(app) as client:
        signup_resp = client.post("/signup", json={
            "username": "liel",
            "first_name": "Liel",
            "email": "liel@example.com",
            "password": "hunter2",
        })
        login_resp = client.post("/login", json={
            "username": "liel",
            "password": "hunter2",
        })

    assert signup_resp.status_code == 200
    assert login_resp.status_code == 200
    assert "session_id" in login_resp.json()


def test_protected_route_rejects_missing_auth():
    with TestClient(app) as client:
        resp = client.get("/profile")

    assert resp.status_code == 401


def test_login_rate_limited_after_too_many_attempts():
    # /login allows 5 requests/minute per IP (see main.py). Wrong-password
    # attempts still count against the limit - that's the point, it's brute
    # force protection - so 6 bad attempts in a row should get a real 401
    # for the first 5 and a 429 (not a 401) for the 6th.
    with TestClient(app) as client:
        client.post("/signup", json={
            "username": "liel",
            "first_name": "Liel",
            "email": "liel@example.com",
            "password": "hunter2",
        })

        responses = [
            client.post("/login", json={"username": "liel", "password": "wrong"})
            for _ in range(6)
        ]

    assert [r.status_code for r in responses[:5]] == [401] * 5
    assert responses[5].status_code == 429


def test_workout_full_crud_flow():
    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        create_resp = client.post(
            "/workouts",
            json={"workout_name": "Leg Day", "workout_data": {"exercises": ["squat"]}},
            headers=headers,
        )
        list_resp = client.get("/workouts", headers=headers)
        delete_resp = client.delete(
            "/workouts", params={"workout_name": "Leg Day"}, headers=headers
        )

    assert create_resp.status_code == 200
    assert len(list_resp.json()["workouts"]) == 1
    assert delete_resp.status_code == 200


def test_logout_invalidates_session():
    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        client.post("/logout", headers=headers)
        resp = client.get("/profile", headers=headers)

    assert resp.status_code == 401


def test_favorites_full_crud_flow():
    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        create_resp = client.post(
            "/favorites",
            json={
                "exercise_name": "Push Up",
                "exercise_data": {"id": "ex-1", "name": "Push Up"},
            },
            headers=headers,
        )
        list_resp = client.get("/favorites", headers=headers)
        delete_resp = client.delete(
            "/favorites", params={"exercise_name": "Push Up"}, headers=headers
        )

    assert create_resp.status_code == 200
    assert len(list_resp.json()["favorites"]) == 1
    assert delete_resp.status_code == 200


def test_profile_get_and_update():
    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        get_resp = client.get("/profile", headers=headers)
        update_resp = client.put(
            "/profile",
            json={
                "experience": "Advanced",
                "days_per_week": 5,
                "equipment": ["barbell"],
                "injuries": "",
            },
            headers=headers,
        )

    assert get_resp.status_code == 200
    assert update_resp.status_code == 200
    assert update_resp.json()["profile"]["experience"] == "Advanced"


def test_chat_full_flow():
    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        create_resp = client.post("/chats", json={"title": "Leg Day Qs"}, headers=headers)
        chat_id = create_resp.json()["chat_id"]

        message_resp = client.post(
            "/chats/messages",
            json={"chat_id": chat_id, "sender": "user", "content": "hello"},
            headers=headers,
        )
        messages_resp = client.get(f"/chats/{chat_id}/messages", headers=headers)
        rename_resp = client.put(
            f"/chats/{chat_id}/rename", json={"new_title": "Renamed"}, headers=headers
        )
        delete_resp = client.delete(f"/chats/{chat_id}", headers=headers)

    assert create_resp.status_code == 200
    assert message_resp.status_code == 200
    assert len(messages_resp.json()["messages"]) == 1
    assert rename_resp.status_code == 200
    assert delete_resp.status_code == 200


def test_ask_endpoint_logs_and_hides_internal_error(monkeypatch, caplog):
    import main as main_module

    def failing_search(prompt, user, profile):
        raise RuntimeError("leaked internal detail")

    monkeypatch.setattr(main_module, "search_fitness_info", failing_search)

    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        resp = client.post(
            "/ask", json={"prompt": "give me leg exercises"}, headers=headers
        )

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Something went wrong. Please try again."
    assert "leaked internal detail" not in resp.text
    assert any(r.getMessage() == "ask_endpoint_error" for r in caplog.records)


def test_failed_login_is_logged(caplog):
    with TestClient(app) as client:
        client.post("/signup", json={
            "username": "liel",
            "first_name": "Liel",
            "email": "liel@example.com",
            "password": "hunter2",
        })
        client.post("/login", json={"username": "liel", "password": "wrong"})

    matching = [r for r in caplog.records if r.getMessage() == "failed_login_attempt"]
    assert len(matching) == 1
    assert matching[0].attempted_username == "liel"


def test_rate_limit_block_is_logged(caplog):
    with TestClient(app) as client:
        client.post("/signup", json={
            "username": "liel",
            "first_name": "Liel",
            "email": "liel@example.com",
            "password": "hunter2",
        })
        for _ in range(6):
            client.post("/login", json={"username": "liel", "password": "wrong"})

    matching = [r for r in caplog.records if r.getMessage() == "rate_limit_exceeded"]
    assert len(matching) == 1
    assert matching[0].ip is not None


def test_request_id_present_in_response_and_logs(caplog):
    import logging as logging_module
    caplog.set_level(logging_module.INFO)

    with TestClient(app) as client:
        resp = client.get("/health")

    request_id = resp.headers.get("X-Request-ID")
    assert request_id

    matching = [
        r for r in caplog.records
        if r.getMessage() == "request_finished" and getattr(r, "request_id", None) == request_id
    ]
    assert len(matching) == 1
    assert matching[0].status_code == 200


def test_json_formatter_produces_valid_json_with_expected_fields():
    import io
    import json
    import logging as logging_module
    from logging_setup import _JSONFormatter, _ContextFilter, bind_request_context, clear_context

    stream = io.StringIO()
    handler = logging_module.StreamHandler(stream)
    handler.setFormatter(_JSONFormatter())
    handler.addFilter(_ContextFilter())

    test_logger = logging_module.getLogger("fitnessai.unittest")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging_module.INFO)
    test_logger.propagate = False

    try:
        bind_request_context(request_id="test-req-1", method="GET", path="/health")
        test_logger.info("unit_test_event", extra={"custom_field": "abc"})
    finally:
        clear_context()
        test_logger.removeHandler(handler)

    payload = json.loads(stream.getvalue())
    assert payload["message"] == "unit_test_event"
    assert payload["request_id"] == "test-req-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["custom_field"] == "abc"
    assert "username" not in payload


def test_ask_endpoint_uses_fitness_search(monkeypatch):
    # /ask calls out to a real LLM through dspy - mock the function main.py
    # actually calls so the test is fast, deterministic, and never makes a
    # network call. Patched on the `main` module (not `dspyRun`), because
    # `from dspyRun import search_fitness_info` already bound the name into
    # main's own namespace - patching dspyRun after that wouldn't affect it.
    import main as main_module

    def fake_search(prompt, user, profile):
        return {"answer": "fake response"}

    monkeypatch.setattr(main_module, "search_fitness_info", fake_search)

    with TestClient(app) as client:
        session_id = _signup_and_login(client)
        headers = {"Authorization": f"Bearer {session_id}"}

        resp = client.post(
            "/ask", json={"prompt": "give me leg exercises"}, headers=headers
        )

    assert resp.status_code == 200
    assert resp.json() == {"answer": "fake response"}
