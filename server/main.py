from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dataBase import (signup_user,login_user,add_workout,get_all_workouts,get_workout_by_name,
add_favorite_exercise,get_favorite_exercises,remove_favorite_exercise,delete_workout,
create_chat,list_chats,add_message,get_chat_messages,rename_chat,delete_chat,
create_session,delete_session,)
from dspyRun import search_fitness_info, init_dspy
from auth import get_current_user, get_session_id_from_header

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_dspy()
    yield


app = FastAPI(
    title="FitnessAI API",
    version="1.0.0",
    lifespan=lifespan,
)

# ------------------ DSPy Endpoint ------------------ #
class AskRequest(BaseModel):
    prompt: str


@app.post("/ask")
def ask(req: AskRequest, current_user: str = Depends(get_current_user)):
    try:
        result = search_fitness_info(req.prompt, current_user)
        if isinstance(result, dict):
            return result
        return {"answer": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------ User Authentication ------------------ #
class SignupRequest(BaseModel):
    username: str
    first_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/signup")
def signup(req: SignupRequest):
    try:
        user = signup_user(req.username, req.first_name, req.email, req.password)
        session_id = create_session(user["username"])
        return {"message": "User created successfully", "user": user, "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
def login(req: LoginRequest):
    try:
        user = login_user(req.username, req.password)
        session_id = create_session(user["username"])
        return {"message": "Login successful", "user": user, "session_id": session_id}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/logout")
def logout(session_id: str = Depends(get_session_id_from_header)):
    delete_session(session_id)
    return {"message": "Logged out"}


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
def list_workouts(current_user: str = Depends(get_current_user)):
    try:
        workouts = get_all_workouts(current_user)
        return {"workouts": workouts}
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
def list_favorites(current_user: str = Depends(get_current_user)):
    try:
        favorites = get_favorite_exercises(current_user)
        return {"favorites": favorites}
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
def get_chats(current_user: str = Depends(get_current_user)):
    try:
        chats = list_chats(current_user)
        return {"chats": chats}
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
