from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dataBase import (signup_user,login_user,add_workout,get_all_workouts,get_workout_by_name,
add_favorite_exercise,get_favorite_exercises,remove_favorite_exercise,delete_workout,
create_chat,list_chats,add_message,get_chat_messages,rename_chat,delete_chat,)
from dspyRun import search_fitness_info, init_dspy

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
    user: dict | None = None


@app.post("/ask")
def ask(req: AskRequest):
    try:
        result = search_fitness_info(req.prompt, req.user)
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
        return {"message": "User created successfully", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/login")
def login(req: LoginRequest):
    try:
        user = login_user(req.username, req.password)
        return {"message": "Login successful", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ------------------ Workouts ------------------ #
class WorkoutCreate(BaseModel):
    workout_name: str
    username: str
    workout_data: dict


@app.post("/workouts")
def create_workout(req: WorkoutCreate):
    try:
        message = add_workout(req.workout_data, req.workout_name, req.username)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/workouts")
def list_workouts(username: str):
    try:
        workouts = get_all_workouts(username)
        return {"workouts": workouts}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/workouts/{workout_name}")
def get_workout(workout_name: str, username: str):
    try:
        workout_data = get_workout_by_name(workout_name, username)
        return workout_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/workouts")
def remove_workout(username: str, workout_name: str):
    try:
        message = delete_workout(workout_name, username)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------ Favorites ------------------ #
class FavoriteCreate(BaseModel):
    username: str
    exercise_name: str
    exercise_data: dict


@app.post("/favorites")
def add_favorite(req: FavoriteCreate):
    try:
        message = add_favorite_exercise(req.username, req.exercise_name, req.exercise_data)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/favorites")
def list_favorites(username: str):
    try:
        favorites = get_favorite_exercises(username)
        return {"favorites": favorites}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/favorites")
def remove_favorite(username: str, exercise_name: str):
    try:
        message = remove_favorite_exercise(username, exercise_name)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------ Chat ------------------ #
class ChatCreate(BaseModel):
    username: str
    title: str | None = None


class MessageCreate(BaseModel):
    username: str
    chat_id: str
    sender: str
    content: str


class ChatRename(BaseModel):
    username: str
    new_title: str


@app.post("/chats")
def create_new_chat(req: ChatCreate):
    try:
        chat_id = create_chat(req.username, req.title or "")
        return {"chat_id": chat_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/chats")
def get_chats(username: str):
    try:
        chats = list_chats(username)
        return {"chats": chats}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/chats/messages")
def add_chat_message(req: MessageCreate):
    try:
        message = add_message(req.username, req.chat_id, req.sender, req.content)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/chats/{chat_id}/messages")
def get_messages(username: str, chat_id: str):
    try:
        messages = get_chat_messages(username, chat_id)
        return {"messages": messages}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/chats/{chat_id}/rename")
def rename_existing_chat(chat_id: str, req: ChatRename):
    try:
        message = rename_chat(req.username, chat_id, req.new_title)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/chats/{chat_id}")
def delete_existing_chat(username: str, chat_id: str):
    try:
        message = delete_chat(username, chat_id)
        return {"message": message}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))