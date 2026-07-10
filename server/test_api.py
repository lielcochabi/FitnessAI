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
