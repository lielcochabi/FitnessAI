import logging
import uuid
from fastapi import FastAPI, HTTPException, Depends, Request, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from logging_setup import configure_logging, bind_request_context, clear_context
from dataBase import (signup_user,login_user,add_workout,get_all_workouts,get_workout_by_name,
add_favorite_exercise,get_favorite_exercises,remove_favorite_exercise,delete_workout,
create_chat,list_chats,add_message,get_chat_messages,rename_chat,delete_chat,
create_session,delete_session,get_user_profile,update_user_profile,)
from dspyRun import search_fitness_info, init_dspy
from auth import get_current_user, get_session_id_from_header

configure_logging()
logger = logging.getLogger("fitnessai")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_dspy()
    yield


app = FastAPI(
    title="FitnessAI API",
    version="1.0.0",
    lifespan=lifespan,
)
limiter = Limiter(key_func=get_remote_address, strategy="moving-window")
app.state.limiter = limiter

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    bind_request_context(request_id=request_id, method=request.method, path=request.url.path)
    logger.info("request_started")
    response = await call_next(request)
    logger.info("request_finished", extra={"status_code": response.status_code})
    response.headers["X-Request-ID"] = request_id
    clear_context()
    return response


def _log_and_handle_rate_limit(request: Request, exc: RateLimitExceeded):
    logger.warning("rate_limit_exceeded", extra={"ip": get_remote_address(request)})
    return _rate_limit_exceeded_handler(request, exc)


app.add_exception_handler(RateLimitExceeded, _log_and_handle_rate_limit)

# ------------------ Health Check ------------------ #
@app.get("/health")
def health():
    """Liveness/readiness probe target for Kubernetes."""
    return {"status": "ok"}


# ------------------ DSPy Endpoint ------------------ #
class AskRequest(BaseModel):
    prompt: str


@app.post("/ask")
def ask(req: AskRequest, current_user: str = Depends(get_current_user)):
    try:
        profile = get_user_profile(current_user)
        result = search_fitness_info(req.prompt, current_user, profile)
        if isinstance(result, dict):
            return result
        return {"answer": result}
    except Exception:
        logger.exception("ask_endpoint_error")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")


# ------------------ User Authentication ------------------ #
class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    first_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    # max 72: bcrypt silently truncates past 72 bytes, so anything longer
    # would only be checked on its first 72 - reject instead of pretending
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username")
    @classmethod
    def username_must_be_simple(cls, v: str) -> str:
        v = v.strip()
        if not v.replace("_", "").isalnum():
            raise ValueError("Username may only contain letters, numbers, and underscores")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/signup")
@limiter.limit("5/minute")
def signup(request: Request, req: SignupRequest):
    try:
        user = signup_user(req.username, req.first_name, req.email, req.password)
        session_id = create_session(user["username"])
        return {"message": "User created successfully", "user": user, "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, req: LoginRequest):
    try:
        user = login_user(req.username, req.password)
        session_id = create_session(user["username"])
        return {"message": "Login successful", "user": user, "session_id": session_id}
    except ValueError as e:
        logger.warning("failed_login_attempt", extra={"attempted_username": req.username})
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/logout")
def logout(session_id: str = Depends(get_session_id_from_header)):
    delete_session(session_id)
    return {"message": "Logged out"}


# ------------------ User Profile ------------------ #
class ProfileUpdate(BaseModel):
    experience: str
    days_per_week: int
    equipment: list[str] = []
    injuries: str = ""


@app.get("/profile")
def read_profile(current_user: str = Depends(get_current_user)):
    try:
        profile = get_user_profile(current_user)
        return {"profile": profile}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/profile")
def save_profile(req: ProfileUpdate, current_user: str = Depends(get_current_user)):
    try:
        profile = update_user_profile(current_user, req.model_dump())
        return {"message": "Profile updated", "profile": profile}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ------------------ Workouts ------------------ #
class WorkoutCreate(BaseModel):
    workout_name: str
    workout_data: dict


@app.post("/workouts")
def create_workout(req: WorkoutCreate, current_user: str = Depends(get_current_user)):
    try:
        message = add_workout(req.workout_data, req.workout_name, current_user)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/workouts")
def list_workouts(
    current_user: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    try:
        workouts, total = get_all_workouts(current_user, limit=limit, skip=skip)
        return {"workouts": workouts, "total": total, "limit": limit, "skip": skip}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/workouts/{workout_name}")
def get_workout(workout_name: str, current_user: str = Depends(get_current_user)):
    try:
        workout_data = get_workout_by_name(workout_name, current_user)
        return workout_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/workouts")
def remove_workout(workout_name: str, current_user: str = Depends(get_current_user)):
    try:
        message = delete_workout(workout_name, current_user)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------ Favorites ------------------ #
class FavoriteCreate(BaseModel):
    exercise_name: str
    exercise_data: dict


@app.post("/favorites")
def add_favorite(req: FavoriteCreate, current_user: str = Depends(get_current_user)):
    try:
        message = add_favorite_exercise(current_user, req.exercise_name, req.exercise_data)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/favorites")
def list_favorites(
    current_user: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    try:
        favorites, total = get_favorite_exercises(current_user, limit=limit, skip=skip)
        return {"favorites": favorites, "total": total, "limit": limit, "skip": skip}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/favorites")
def remove_favorite(exercise_name: str, current_user: str = Depends(get_current_user)):
    try:
        message = remove_favorite_exercise(current_user, exercise_name)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------ Chat ------------------ #
class ChatCreate(BaseModel):
    title: str | None = None


class MessageCreate(BaseModel):
    chat_id: str
    sender: str
    content: str


class ChatRename(BaseModel):
    new_title: str


@app.post("/chats")
def create_new_chat(req: ChatCreate, current_user: str = Depends(get_current_user)):
    try:
        chat_id = create_chat(current_user, req.title or "")
        return {"chat_id": chat_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/chats")
def get_chats(
    current_user: str = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    try:
        chats, total = list_chats(current_user, limit=limit, skip=skip)
        return {"chats": chats, "total": total, "limit": limit, "skip": skip}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/chats/messages")
def add_chat_message(req: MessageCreate, current_user: str = Depends(get_current_user)):
    try:
        message = add_message(current_user, req.chat_id, req.sender, req.content)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/chats/{chat_id}/messages")
def get_messages(chat_id: str, current_user: str = Depends(get_current_user)):
    try:
        messages = get_chat_messages(current_user, chat_id)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/chats/{chat_id}/rename")
def rename_existing_chat(chat_id: str, req: ChatRename, current_user: str = Depends(get_current_user)):
    try:
        message = rename_chat(current_user, chat_id, req.new_title)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/chats/{chat_id}")
def delete_existing_chat(chat_id: str, current_user: str = Depends(get_current_user)):
    try:
        message = delete_chat(current_user, chat_id)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
