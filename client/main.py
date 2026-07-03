import streamlit as st
import requests
from accountActions import signup_dialog, login_dialog
from user_input import handle_user_input
from config import get_api_url

API_URL = get_api_url()

st.set_page_config(page_title="AI Fitness Plan Assistant", layout="wide")
st.title("AI Fitness Plan Assistant!")
st.subheader("Your personal workout & nutrition AI")

# ---- session state defaults ----
defaults = {
    "user": None,
    "session_id": None,
    "awaiting_workout_save": False,
    "awaiting_favorite_selection": False,
    "pending_workout": "",
    "pending_exercises": [],
    "submitted_text": "",
    "user_input": "",
    "awaiting_name": False,
    "pending_workout_name": "",
    "selected_chat_id": None,
    "found_exercises": [],
    "chat_messages": [],
    "loaded_chat_id": None,
}

for k, v in defaults.items():
    st.session_state.setdefault(k, v)


def auth_headers():
    token = st.session_state.get("session_id")
    return {"Authorization": f"Bearer {token}"} if token else {}


EQUIPMENT_OPTIONS = [
    "Bodyweight only", "Dumbbells", "Barbell", "Kettlebells",
    "Resistance bands", "Cables", "Machines", "Pull-up bar",
]
EXPERIENCE_LEVELS = ["Beginner", "Intermediate", "Advanced"]


def render_profile_sidebar(api_url: str):
    profile = st.session_state.user.get("profile", {})
    with st.sidebar:
        st.header("Personalize your plan")
        experience = st.selectbox(
            "Experience level",
            EXPERIENCE_LEVELS,
            index=EXPERIENCE_LEVELS.index(profile.get("experience", "Beginner")),
        )
        days_per_week = st.slider(
            "Training days per week", 1, 7, profile.get("days_per_week", 3)
        )
        equipment = st.multiselect(
            "Available equipment",
            EQUIPMENT_OPTIONS,
            default=[e for e in profile.get("equipment", []) if e in EQUIPMENT_OPTIONS],
        )
        injuries = st.text_input(
            "Injuries or limitations (optional)", value=profile.get("injuries", "")
        )

        if st.button("Save profile"):
            try:
                resp = requests.put(
                    f"{api_url}/profile",
                    json={
                        "experience": experience,
                        "days_per_week": days_per_week,
                        "equipment": equipment,
                        "injuries": injuries,
                    },
                    headers=auth_headers(),
                    timeout=10,
                )
                if not resp.ok:
                    st.error(resp.json().get("detail", "Failed to save profile."))
                else:
                    st.session_state.user["profile"] = resp.json()["profile"]
                    st.success("Profile saved!")
            except Exception as e:
                st.error(str(e))


def fetch_chat_messages(api_url: str, chat_id: str):
    resp = requests.get(
        f"{api_url}/chats/{chat_id}/messages",
        headers=auth_headers(),
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("messages", [])


def create_chat(api_url: str, first_message: str):
    title = first_message.strip()[:40] if first_message.strip() else "New Chat"

    resp = requests.post(
        f"{api_url}/chats",
        json={"title": title},
        headers=auth_headers(),
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("chat_id")


def save_message(api_url: str, chat_id: str, sender: str, content: str):
    resp = requests.post(
        f"{api_url}/chats/messages",
        json={
            "chat_id": chat_id,
            "sender": sender,
            "content": content
        },
        headers=auth_headers(),
        timeout=10
    )
    resp.raise_for_status()


def load_selected_chat():
    user = st.session_state.get("user")
    chat_id = st.session_state.get("selected_chat_id")

    if not user or not chat_id:
        st.session_state.chat_messages = []
        st.session_state.loaded_chat_id = None
        return

    try:
        messages = fetch_chat_messages(API_URL, chat_id)
        st.session_state.chat_messages = [
            {
                "role": msg.get("role", "user"),
                "content": msg.get("message", "")
            }
            for msg in messages
        ]
        st.session_state.loaded_chat_id = chat_id
    except Exception as e:
        st.error(f"Failed to load chat: {e}")
        st.session_state.chat_messages = []
        st.session_state.loaded_chat_id = None

if (
    st.session_state.get("user") is not None
    and st.session_state.get("selected_chat_id") != st.session_state.get("loaded_chat_id")
):
    load_selected_chat()

# ---- auth UI ----
if st.session_state.user is None:
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Sign Up"):
            signup_dialog()
    with c2:
        if st.button("Log In"):
            login_dialog()
else:
    st.write(f"Logged in as: **{st.session_state.user['username']}**")
    render_profile_sidebar(API_URL)

    if st.button("Log Out"):
        try:
            requests.post(f"{API_URL}/logout", headers=auth_headers(), timeout=5)
        except Exception:
            pass
        for k, v in defaults.items():
            st.session_state[k] = v
        st.rerun()

st.divider()

st.markdown(
    """
Welcome!
This app helps you:
- Generate customized workout plans
- Build meal plans with calories & macros
- Track your progress
- Adapt and improve weekly with AI
"""
)

for msg in st.session_state.chat_messages:
    role = msg.get("role", "user")
    content = msg.get("content", "")

    with st.chat_message("user" if role == "user" else "assistant"):
        st.markdown(content)

# ----------------- chat input ----------------- #
if st.session_state.user is not None:
    user_input = st.chat_input("Send a message")

    if user_input:
        try:
            if not st.session_state.selected_chat_id:
                new_chat_id = create_chat(API_URL, user_input)
                st.session_state.selected_chat_id = new_chat_id
                st.session_state.loaded_chat_id = new_chat_id
            chat_id = st.session_state.selected_chat_id
            save_message(API_URL, chat_id, "user", user_input)
            st.session_state.submitted_text = user_input
            st.session_state.chat_messages.append({
                "role": "user",
                "content": user_input
            })
            answer = handle_user_input(API_URL)
            if answer:
                save_message(API_URL, chat_id, "assistant", answer)
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": answer
                })
            st.rerun()
        except Exception as e:
            st.error(str(e))
