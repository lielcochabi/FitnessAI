import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

user = st.session_state.get("user")
if not user:
    st.warning("Please log in to access this page.")
    st.stop()

st.title("Chat History")
username = user["username"]

@st.cache_data(ttl=30)
def fetch_chats(api_url: str, username: str):
    resp = requests.get(
        f"{api_url}/chats",
        params={"username": username},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("chats", [])

if st.button("Refresh"):
    fetch_chats.clear()
    st.rerun()

with st.spinner("Loading chat history..."):
    try:
        chats = fetch_chats(API_URL, username)
    except Exception as e:
        st.error(str(e))
        chats = []

if not chats:
    st.info("No chat history found.")

for chat in chats:
    title = chat.get("title", "New Chat")
    chat_id = chat.get("chat_id")

    if st.button(title, key=f"chat_{chat_id}", use_container_width=True):
        st.session_state.selected_chat_id = chat_id
        st.session_state.loaded_chat_id = None
        st.session_state.chat_messages = []
        st.switch_page("main.py")