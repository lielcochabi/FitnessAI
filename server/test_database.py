"""
Tests for dataBase.py - the data layer, tested directly (no HTTP involved).

These hit a real MongoDB (see conftest.py), so behavior like unique indexes
and DuplicateKeyError is exercised for real instead of being simulated.
"""
from datetime import timedelta

import pytest
from bson import ObjectId

from dataBase import (
    DEFAULT_PROFILE,
    signup_user,
    login_user,
    get_user_profile,
    update_user_profile,
    add_workout,
    get_all_workouts,
    get_workout_by_name,
    delete_workout,
    add_favorite_exercise,
    remove_favorite_exercise,
    create_chat,
    list_chats,
    add_message,
    get_chat_messages,
    rename_chat,
    delete_chat,
    create_session,
    get_session_user,
    delete_session,
    sessions_collection,
    messages_per_chat_collection,
    _now,
)


# -------- signup / login --------

def test_signup_creates_user_with_hashed_password():
    user = signup_user("liel", "Liel", "liel@example.com", "hunter2")

    assert user["username"] == "liel"
    assert user["email"] == "liel@example.com"
    # the raw password (and its hash) must never come back in the response
    assert "hunter2" not in str(user)
    assert "password_hash" not in user


def test_signup_rejects_duplicate_username():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        signup_user("liel", "Someone Else", "other@example.com", "different-pw")


def test_login_succeeds_with_correct_password():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    user = login_user("liel", "hunter2")

    assert user["username"] == "liel"


def test_login_rejects_wrong_password():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        login_user("liel", "wrong-password")


def test_signup_rejects_duplicate_email():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        signup_user("someone_else", "Someone", "liel@example.com", "another-pw")


def test_signup_rejects_missing_password():
    with pytest.raises(ValueError):
        signup_user("liel", "Liel", "liel@example.com", "")


# -------- profile --------

def test_get_user_profile_returns_default_for_new_user():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    assert get_user_profile("liel") == DEFAULT_PROFILE


def test_get_user_profile_raises_for_unknown_user():
    with pytest.raises(ValueError):
        get_user_profile("ghost")


def test_update_user_profile_persists_valid_update():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    updated = update_user_profile("liel", {
        "experience": "Advanced",
        "days_per_week": 5,
        "equipment": ["barbell", "dumbbell"],
        "injuries": "knee",
    })

    assert updated["experience"] == "Advanced"
    assert get_user_profile("liel")["experience"] == "Advanced"


def test_update_user_profile_rejects_invalid_experience():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        update_user_profile("liel", {"experience": "Expert", "days_per_week": 3})


def test_update_user_profile_rejects_invalid_days_per_week():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        update_user_profile("liel", {"experience": "Beginner", "days_per_week": 10})


def test_update_user_profile_raises_for_unknown_user():
    with pytest.raises(ValueError):
        update_user_profile("ghost", {"experience": "Beginner", "days_per_week": 3})


# -------- workouts --------

def test_add_and_list_workout():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    add_workout({"exercises": ["squat", "bench"]}, "Leg Day", "liel")
    workouts = get_all_workouts("liel")

    assert len(workouts) == 1
    assert workouts[0]["workout_name"] == "Leg Day"


def test_delete_missing_workout_raises():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        delete_workout("Does Not Exist", "liel")


def test_get_workout_by_name_found():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")
    add_workout({"exercises": ["squat"]}, "Leg Day", "liel")

    workout = get_workout_by_name("Leg Day", "liel")

    assert workout["workout_name"] == "Leg Day"


def test_get_workout_by_name_not_found():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        get_workout_by_name("Does Not Exist", "liel")


# -------- favorites --------

def test_add_favorite_rejects_duplicate():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")
    exercise = {"id": "ex-1", "name": "Push Up"}

    add_favorite_exercise("liel", "Push Up", exercise)

    with pytest.raises(ValueError):
        add_favorite_exercise("liel", "Push Up", exercise)


def test_add_favorite_rejects_missing_id():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        add_favorite_exercise("liel", "Push Up", {"name": "Push Up"})


def test_remove_favorite_raises_when_not_found():
    signup_user("liel", "Liel", "liel@example.com", "hunter2")

    with pytest.raises(ValueError):
        remove_favorite_exercise("liel", "Does Not Exist")


# -------- chat history --------

def test_create_chat_appears_in_list_chats():
    create_chat("liel", "Leg Day Questions")

    chats = list_chats("liel")

    assert len(chats) == 1
    assert chats[0]["title"] == "Leg Day Questions"


def test_add_message_rejects_invalid_role():
    chat_id = create_chat("liel")

    with pytest.raises(ValueError):
        add_message("liel", chat_id, "system", "hello")


def test_add_message_rejects_empty_message():
    chat_id = create_chat("liel")

    with pytest.raises(ValueError):
        add_message("liel", chat_id, "user", "   ")


def test_add_message_raises_for_wrong_chat_owner():
    chat_id = create_chat("liel")

    with pytest.raises(ValueError):
        add_message("someone_else", chat_id, "user", "hello")


def test_get_chat_messages_returns_in_order():
    chat_id = create_chat("liel")
    add_message("liel", chat_id, "user", "first")
    add_message("liel", chat_id, "assistant", "second")

    messages = get_chat_messages("liel", chat_id)

    assert [m["message"] for m in messages] == ["first", "second"]


def test_rename_chat_updates_title():
    chat_id = create_chat("liel", "Old Title")

    rename_chat("liel", chat_id, "New Title")

    assert list_chats("liel")[0]["title"] == "New Title"


def test_rename_chat_raises_for_missing_chat():
    fake_id = str(ObjectId())

    with pytest.raises(ValueError):
        rename_chat("liel", fake_id, "New Title")


def test_delete_chat_also_deletes_its_messages():
    chat_id = create_chat("liel")
    add_message("liel", chat_id, "user", "hello")

    delete_chat("liel", chat_id)

    assert messages_per_chat_collection.count_documents(
        {"chat_id": ObjectId(chat_id)}
    ) == 0


# -------- sessions --------

def test_session_round_trip():
    session_id = create_session("liel")

    assert get_session_user(session_id) == "liel"

    delete_session(session_id)

    assert get_session_user(session_id) is None


def test_unknown_session_returns_none():
    assert get_session_user("not-a-real-session-id") is None


def test_expired_session_returns_none_and_is_deleted():
    sessions_collection.insert_one({
        "session_id": "expired-session",
        "username": "liel",
        "created_at": _now() - timedelta(days=10),
        "expires_at": _now() - timedelta(days=3),
    })

    assert get_session_user("expired-session") is None
    assert sessions_collection.find_one({"session_id": "expired-session"}) is None
