import pymongo
import os
import bcrypt
import secrets
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv
from datetime import datetime,timezone,timedelta
from bson import ObjectId

SESSION_TTL_DAYS = int(os.getenv("SESSION_TTL_DAYS", "7"))

load_dotenv()

DB_URI = os.getenv("MONGODB_URI", "")

if not DB_URI:
    raise RuntimeError("MONGODB_URI environment variable is not set")

fitnessAI_client = pymongo.MongoClient(
    DB_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000,
    tz_aware=True,
)

try:
    fitnessAI_client.admin.command("ping")
except Exception as e:
    raise RuntimeError(f"Failed to connect to MongoDB: {e}")

fitnessAI_db = fitnessAI_client["FitnessAI"]

#collections
users_collection = fitnessAI_db["users"]
workouts_collection = fitnessAI_db["workouts"]
favorites_collection = fitnessAI_db["favorites"]
chat_history_collection = fitnessAI_db["chat_history"]
messages_per_chat_collection = fitnessAI_db["messages"]
sessions_collection = fitnessAI_db["sessions"]

# Ensure uniqueness
users_collection.create_index("username", unique=True)
users_collection.create_index("email", unique=True)
workouts_collection.create_index([("username", 1), ("workout_name", 1)], unique=True)
favorites_collection.create_index([("username", 1), ("exercise_id", 1)], unique=True)

chat_history_collection.create_index([("username", 1), ("updated_at", -1)])
messages_per_chat_collection.create_index([("username", 1), ("chat_id", 1), ("created_at", 1)])

sessions_collection.create_index("session_id", unique=True)
sessions_collection.create_index("expires_at", expireAfterSeconds=0)


# -------- SIGNUP FUNCTION --------
def signup_user(username, first_name, email, password):
    username = username.strip()
    first_name = first_name.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        raise ValueError("Missing required fields")

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    user = {
        "username": username,
        "first_name": first_name,
        "email": email,
        "password_hash": password_hash,
    }

    try:
        users_collection.insert_one(user)
    except DuplicateKeyError:
        raise ValueError("Username or email already exists")

    return {
        "username": user["username"],
        "first_name": user["first_name"],
        "email": user["email"],
    }

# -------- LOGIN FUNCTION--------
def login_user(username, password):
    username = username.strip()

    user = users_collection.find_one({"username": username})
    if not user:
        raise ValueError("Invalid username or password")

    if not bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    ):
        raise ValueError("Invalid username or password")

    return {
        "username": user["username"],
        "first_name": user["first_name"],
        "email": user["email"],
    }


# ------------------ WORKOUTS ------------------
def add_workout(workout_data, workout_name, username):
    workout_name = workout_name.strip()
    username = username.strip()

    try:
        workouts_collection.insert_one({
            "workout_name": workout_name,
            "workout_data": workout_data,
            "username": username
        })
    except DuplicateKeyError:
        raise ValueError("Workout already exists")

    return "Workout " + workout_name + " added successfully"


def get_workout_by_name(workout_name, username):
    workout_name = workout_name.strip()
    username = username.strip()

    workout = workouts_collection.find_one(
        {"workout_name": workout_name, "username": username},
        {"_id": 0, "workout_name": 1, "workout_data": 1}
    )
    if not workout:
        raise ValueError("Workout not found")
    return workout


def get_all_workouts(username):
    username = username.strip()
    workouts = workouts_collection.find(
        {"username": username},
        {"_id": 0, "workout_name": 1, "workout_data": 1}
    )
    return list(workouts)


def delete_workout(workout_name, username):
    workout_name = workout_name.strip()
    username = username.strip()

    result = workouts_collection.delete_one(
        {"workout_name": workout_name, "username": username}
    )
    if result.deleted_count == 0:
        raise ValueError("Workout not found")
    return "Workout deleted successfully"


# ------------------ Favorites ------------------
def add_favorite_exercise(username, exercise_name, exercise_data):
    username = username.strip()
    exercise_name = exercise_name.strip()

    exercise_id = exercise_data.get("id")
    if exercise_id is None:
        raise ValueError("Exercise is missing id")

    try:
        favorites_collection.insert_one({
            "username": username,
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "exercise_data": exercise_data
        })
    except DuplicateKeyError:
        raise ValueError("Exercise already in favorites")

    return "Exercise " + exercise_name + " added to favorites successfully"


def get_favorite_exercises(username):
    username = username.strip()
    favorites = favorites_collection.find(
        {"username": username},
        {"_id": 0, "exercise_id": 1, "exercise_name": 1, "exercise_data": 1}
    )
    return list(favorites)


def remove_favorite_exercise(username, exercise_name):
    username = username.strip()
    result = favorites_collection.delete_one(
        {"username": username, "exercise_name": exercise_name}
    )
    if result.deleted_count == 0:
        raise ValueError("Exercise not found in favorites")
    return "Exercise removed from favorites successfully"


# ------------------ Chat History ------------------ #
def _now():
    return datetime.now(timezone.utc)

def create_chat(username: str, title: str = ""):
    username = username.strip()
    title = (title or "").strip()
    doc = {
        "username": username,
        "title": title if title else "New Chat",
        "created_at": _now(),
        "updated_at": _now(),
    }
    res = chat_history_collection.insert_one(doc)
    return str(res.inserted_id)

def list_chats(username: str):
    username = username.strip()
    chats = chat_history_collection.find(
        {"username": username},
        {"title": 1, "created_at": 1, "updated_at": 1}
    ).sort("updated_at", -1)

    out = []
    for c in chats:
        out.append({
            "chat_id": str(c["_id"]),
            "title": c.get("title", "New Chat"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
        })
    return out


def add_message(username: str, chat_id: str, role: str, message: str):
    username = username.strip()
    role = role.strip()
    message = (message or "").strip()

    if role not in ("user", "assistant"):
        raise ValueError("Invalid role")

    if not message:
        raise ValueError("Message is empty")

    try:
        chat_obj_id = ObjectId(chat_id)
    except Exception:
        raise ValueError("Invalid chat_id")

    chat = chat_history_collection.find_one({"_id": chat_obj_id, "username": username})
    if not chat:
        raise ValueError("Chat not found")

    messages_per_chat_collection.insert_one({
        "username": username,
        "chat_id": chat_obj_id,
        "role": role,
        "message": message,
        "created_at": _now()
    })

    chat_history_collection.update_one(
        {"_id": chat_obj_id, "username": username},
        {"$set": {"updated_at": _now()}}
    )

    return "Message added"


def get_chat_messages(username: str, chat_id: str):
    """
    Returns all messages in a chat ordered by created_at asc.
    """
    username = username.strip()

    try:
        chat_obj_id = ObjectId(chat_id)
    except Exception:
        raise ValueError("Invalid chat_id")

    chat = chat_history_collection.find_one({"_id": chat_obj_id, "username": username})
    if not chat:
        raise ValueError("Chat not found")

    msgs = messages_per_chat_collection.find(
        {"username": username, "chat_id": chat_obj_id},
        {"_id": 0, "role": 1, "message": 1, "created_at": 1}
    ).sort("created_at", 1)

    return list(msgs)


def rename_chat(username: str, chat_id: str, new_title: str):
    username = username.strip()
    new_title = (new_title or "").strip()

    if not new_title:
        raise ValueError("Title is empty")

    try:
        chat_obj_id = ObjectId(chat_id)
    except Exception:
        raise ValueError("Invalid chat_id")

    res = chat_history_collection.update_one(
        {"_id": chat_obj_id, "username": username},
        {"$set": {"title": new_title, "updated_at": _now()}}
    )

    if res.matched_count == 0:
        raise ValueError("Chat not found")

    return "Chat renamed"


def delete_chat(username: str, chat_id: str):
    """
    Deletes the chat and all its messages.
    """
    username = username.strip()

    try:
        chat_obj_id = ObjectId(chat_id)
    except Exception:
        raise ValueError("Invalid chat_id")

    res = chat_history_collection.delete_one({"_id": chat_obj_id, "username": username})
    if res.deleted_count == 0:
        raise ValueError("Chat not found")

    messages_per_chat_collection.delete_many({"username": username, "chat_id": chat_obj_id})
    return "Chat deleted"


# ------------------ Sessions ------------------ #
def create_session(username: str) -> str:
    username = username.strip()
    session_id = secrets.token_urlsafe(32)
    sessions_collection.insert_one({
        "session_id": session_id,
        "username": username,
        "created_at": _now(),
        "expires_at": _now() + timedelta(days=SESSION_TTL_DAYS),
    })
    return session_id


def get_session_user(session_id: str):
    if not session_id:
        return None
    doc = sessions_collection.find_one({"session_id": session_id})
    if not doc:
        return None
    expires_at = doc.get("expires_at")
    if expires_at and expires_at < _now():
        sessions_collection.delete_one({"_id": doc["_id"]})
        return None
    return doc.get("username")


def delete_session(session_id: str) -> None:
    if not session_id:
        return
    sessions_collection.delete_one({"session_id": session_id})
