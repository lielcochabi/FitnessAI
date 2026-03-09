import os
import requests
import urllib.parse
from dotenv import load_dotenv
import time
import random
from collections import OrderedDict, deque
from threading import Lock

load_dotenv()

headers = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", ""),
    "x-rapidapi-host": "exercisedb.p.rapidapi.com"
}

EXERCISE_CACHE_TTL_SECONDS = int(os.getenv("EXERCISE_CACHE_TTL_SECONDS", str(7 * 24 * 60 * 60)))
EXERCISE_CACHE_MAX_KEYS = int(os.getenv("EXERCISE_CACHE_MAX_KEYS", "40"))
EXERCISE_BAG_TTL_SECONDS = int(os.getenv("EXERCISE_BAG_TTL_SECONDS", str(24 * 60 * 60)))  

_cache_lock = Lock()
_exercise_cache: "OrderedDict[str, tuple[float, list[dict]]]" = OrderedDict()
_bag_lock = Lock()
_user_bags: dict[str, dict[str, tuple[float, deque]]] = {}
_user_lookup: dict[str, dict[str, dict[str, dict]]] = {}

body_parts = [
    "back", "cardio", "chest", "lower arms", "lower legs",
    "neck", "shoulders", "upper arms", "upper legs", "waist"
]

muscles = [
    "abductors", "abs", "adductors", "biceps", "calves",
    "cardiovascular system", "delts", "forearms", "glutes",
    "hamstrings", "lats", "levator scapulae", "pectorals",
    "quads", "serratus anterior", "spine", "traps",
    "triceps", "upper back"
]

def get_body_parts():
    return body_parts

def get_muscles():
    return muscles


def format_exercise(ex: dict) -> str:
    lines = []

    name = ex.get("name")
    body_part = ex.get("bodyPart")
    target = ex.get("target")
    equipment = ex.get("equipment")

    sentence_parts = []

    if name:
        sentence_parts.append(name)
    if body_part:
        sentence_parts.append(f"is an exercise for {body_part}")
    if target:
        sentence_parts.append(f"that targets the {target}")
    if equipment:
        sentence_parts.append(f"using {equipment}")

    if sentence_parts:
        lines.append(" ".join(sentence_parts) + ".")

    secondary = ex.get("secondaryMuscles")
    if secondary:
        lines.append(f"Secondary Muscles: {', '.join(secondary)}")

    instructions = ex.get("instructions")
    if instructions:
        lines.append("")
        lines.append("Instructions:")
        for i, step in enumerate(instructions, 1):
            lines.append(f"  {i}. {step}")

    gif = ex.get("gifUrl")
    if gif:
        lines.append("")
        lines.append(f"GIF URL: {gif}")

    return "\n".join(lines)


def format_exercise_list(exercises: list, limit: int = 5) -> str:
    if not exercises:
        return "No exercises found."

    blocks = []
    for i, ex in enumerate(exercises[:limit], 1):
        blocks.append(f"--- Exercise {i} ---\n{format_exercise(ex)}")

    return "\n\n".join(blocks)


def _fetch_exercises(url: str):
    if not headers["x-rapidapi-key"]:
        raise RuntimeError("RAPIDAPI_KEY is missing on the server.")

    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status()
    data = response.json()

    if not isinstance(data, list):
        raise RuntimeError("ExerciseDB API returned unexpected data format.")

    return data

def _cache_get(key: str):
    now = time.time()
    with _cache_lock:
        item = _exercise_cache.get(key)
        if not item:
            return None

        expires_at, data = item
        if expires_at <= now:
            _exercise_cache.pop(key, None)
            return None

        _exercise_cache.move_to_end(key, last=True)
        return data

def _cache_set(key: str, data: list[dict]):
    expires_at = time.time() + EXERCISE_CACHE_TTL_SECONDS
    with _cache_lock:
        _exercise_cache[key] = (expires_at, data)
        _exercise_cache.move_to_end(key, last=True)

        while len(_exercise_cache) > EXERCISE_CACHE_MAX_KEYS:
            _exercise_cache.popitem(last=False)

def cache_stats():
    now = time.time()
    with _cache_lock:
        valid = sum(1 for exp, _ in _exercise_cache.values() if exp > now)
        return {
            "ttl_seconds": EXERCISE_CACHE_TTL_SECONDS,
            "max_keys": EXERCISE_CACHE_MAX_KEYS,
            "stored_keys": len(_exercise_cache),
            "valid_keys": valid,
            "bag_ttl_seconds": EXERCISE_BAG_TTL_SECONDS,
        }


def _exercise_uid(ex: dict) -> str:
    """
    Stable ID for an exercise:
    - prefer 'id' if exists
    - otherwise fall back to composite key
    """
    ex_id = ex.get("id")
    if ex_id is not None:
        return str(ex_id)

    name = (ex.get("name") or "").strip().lower()
    bp = (ex.get("bodyPart") or "").strip().lower()
    target = (ex.get("target") or "").strip().lower()
    eq = (ex.get("equipment") or "").strip().lower()
    return f"fallback:{name}|{bp}|{target}|{eq}"


def _cleanup_expired_bags():
    now = time.time()
    with _bag_lock:
        for user in list(_user_bags.keys()):
            per_key = _user_bags.get(user, {})
            for key in list(per_key.keys()):
                exp, _dq = per_key[key]
                if exp <= now:
                    per_key.pop(key, None)
                    if user in _user_lookup:
                        _user_lookup[user].pop(key, None)

            if not per_key:
                _user_bags.pop(user, None)
                _user_lookup.pop(user, None)


def _get_from_bag(user: str, key: str, full_data: list[dict], limit: int) -> list[dict]:
    _cleanup_expired_bags()
    user = (user or "anonymous").strip().lower()
    limit = max(1, int(limit))

    uid_map: dict[str, dict] = {}
    uids: list[str] = []
    for ex in full_data:
        uid = _exercise_uid(ex)
        if uid not in uid_map:
            uid_map[uid] = ex
            uids.append(uid)

    if not uids:
        return []

    now = time.time()
    with _bag_lock:
        if user not in _user_bags:
            _user_bags[user] = {}
        if user not in _user_lookup:
            _user_lookup[user] = {}

        entry = _user_bags[user].get(key)

        needs_rebuild = True
        if entry is not None:
            exp, dq = entry
            if exp > now and len(dq) > 0:
                needs_rebuild = False

        if needs_rebuild:
            shuffled = list(uids)
            random.shuffle(shuffled)
            dq = deque(shuffled)
            exp = now + EXERCISE_BAG_TTL_SECONDS
            _user_bags[user][key] = (exp, dq)
            _user_lookup[user][key] = uid_map
        else:
            _user_lookup[user][key] = uid_map

        out: list[dict] = []
        for _ in range(min(limit, len(dq))):
            uid = dq.popleft()
            ex = _user_lookup[user][key].get(uid)
            if ex is not None:
                out.append(ex)

        if len(out) < limit:
            shuffled = list(uids)
            random.shuffle(shuffled)
            dq2 = deque(shuffled)
            exp2 = now + EXERCISE_BAG_TTL_SECONDS
            _user_bags[user][key] = (exp2, dq2)
            _user_lookup[user][key] = uid_map

            while len(out) < limit and len(dq2) > 0:
                uid = dq2.popleft()
                ex = uid_map.get(uid)
                if ex is not None:
                    out.append(ex)

        return out


# ------------------ BODY PART ------------------
def get_exercises_by_bodypart(bodypart: str, limit: int = 5, user: str = "anonymous"):
    bodypart_clean = urllib.parse.quote(bodypart.lower())
    url = f"https://exercisedb.p.rapidapi.com/exercises/bodyPart/{bodypart_clean}"

    cache_key = f"bodyPart:{bodypart_clean}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return _get_from_bag(user, cache_key, cached, limit)

    try:
        data = _fetch_exercises(url)
        _cache_set(cache_key, data)
        return _get_from_bag(user, cache_key, data, limit)

    except Exception as e:
        print(f"Error fetching exercises for body part '{bodypart}':", e)
        return []


# ------------------ TARGET / MUSCLE ------------------
def get_exercises_by_target(muscle: str, limit: int = 5, user: str = "anonymous"):
    muscle_clean = urllib.parse.quote(muscle.lower())
    url = f"https://exercisedb.p.rapidapi.com/exercises/target/{muscle_clean}"

    cache_key = f"target:{muscle_clean}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return _get_from_bag(user, cache_key, cached, limit)

    try:
        data = _fetch_exercises(url)

        _cache_set(cache_key, data)
        return _get_from_bag(user, cache_key, data, limit)

    except Exception as e:
        print(f"Error fetching exercises for target '{muscle}':", e)
        return []