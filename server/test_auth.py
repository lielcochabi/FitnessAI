"""
Tests for auth.py - the auth dependency functions, called directly as plain
Python functions. FastAPI's Header(default=None) is just a default value
marker; passing `authorization=` explicitly bypasses it, so these run
without needing a real HTTP request.
"""
import pytest
from fastapi import HTTPException

from dataBase import create_session
from auth import get_current_user, get_session_id_from_header


def test_get_current_user_accepts_valid_session():
    session_id = create_session("liel")

    username = get_current_user(authorization=f"Bearer {session_id}")

    assert username == "liel"


def test_get_current_user_accepts_case_insensitive_bearer_prefix():
    session_id = create_session("liel")

    username = get_current_user(authorization=f"BEARER {session_id}")

    assert username == "liel"


def test_get_current_user_rejects_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization=None)

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="not-a-bearer-token")

    assert exc_info.value.status_code == 401


def test_get_current_user_rejects_unknown_session():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(authorization="Bearer some-fake-session-id")

    assert exc_info.value.status_code == 401


def test_get_session_id_from_header_extracts_token():
    session_id = get_session_id_from_header(authorization="Bearer abc123")

    assert session_id == "abc123"
