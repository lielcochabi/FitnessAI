"""
Shared pytest fixtures for the server test suite.

Tests run against a real MongoDB rather than a mock, and this fixture wipes
every collection the app touches before each test. That keeps tests
independent of each other and of whatever ran before them, which matters
here because dataBase.py enforces unique indexes (username, email, workout
name per user, favorite exercise per user) that would otherwise make tests
fail depending on execution order.

Because this wipes real data, MONGODB_URI must point at a throwaway
database - never the one the app actually uses:
  - In CI, the workflow sets MONGODB_URI directly to its own ephemeral
    mongo service container (see .github/workflows/ci.yml). Nothing below
    is needed there.
  - Locally, MONGODB_URI is normally NOT set in the shell, and dataBase.py
    would otherwise fall back to whatever real MONGODB_URI is in .env - the
    same database the app itself uses. To prevent that, this file loads
    server/.env.test (copy server/.env.test.example to get started) BEFORE
    dataBase.py runs its own load_dotenv(), and refuses to run at all if
    neither MONGODB_URI nor .env.test is present.
"""
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

if not os.getenv("MONGODB_URI"):
    env_test_path = Path(__file__).parent / ".env.test"
    if not env_test_path.exists():
        raise RuntimeError(
            "MONGODB_URI is not set and server/.env.test does not exist. "
            "Tests must not run against the real database. Copy "
            "server/.env.test.example to server/.env.test (pointing at a "
            "local/disposable MongoDB, e.g. `docker run -d -p 27017:27017 "
            "mongo:7`) before running pytest."
        )
    # override=True: win even if a real MONGODB_URI is already exported in
    # the shell. dataBase.py's own load_dotenv() call defaults to
    # override=False, so once this sets MONGODB_URI, dataBase.py's load of
    # the real .env will NOT clobber it - the test value sticks.
    load_dotenv(env_test_path, override=True)

from dataBase import (
    users_collection,
    workouts_collection,
    favorites_collection,
    chat_history_collection,
    messages_per_chat_collection,
    sessions_collection,
)
from main import limiter


@pytest.fixture(autouse=True)
def clean_collections():
    for collection in (
        users_collection,
        workouts_collection,
        favorites_collection,
        chat_history_collection,
        messages_per_chat_collection,
        sessions_collection,
    ):
        collection.delete_many({})


@pytest.fixture(autouse=True)
def reset_rate_limits():
    # /login and /signup are rate-limited (see main.py). slowapi's default
    # in-memory storage is keyed by client IP and persists for the life of
    # the process - since every test shares the same `app` object and
    # TestClient reports the same fake IP for all of them, without this,
    # tests later in the run would start getting real 429s from earlier
    # tests' login/signup calls instead of the response they expect.
    limiter.reset()
