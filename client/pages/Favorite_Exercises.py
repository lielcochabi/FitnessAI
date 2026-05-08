import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

user = st.session_state.get("user")
if not user:
    st.warning("Please log in to access this page.")
    st.stop()

st.title("Favorite Exercises")


def _auth_headers():
    token = st.session_state.get("session_id")
    return {"Authorization": f"Bearer {token}"} if token else {}


@st.cache_data(ttl=30)
def fetch_favorites(api_url, token):
    resp = requests.get(
        f"{api_url}/favorites",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("favorites", [])

if st.button("Refresh"):
    fetch_favorites.clear()
    st.rerun()

with st.spinner("Loading favorite exercises..."):
    try:
        favorites = fetch_favorites(API_URL, st.session_state.get("session_id") or "")
    except Exception as e:
        st.error(str(e))
        favorites = []

def remove_exercise_from_favorites(exercise_name):
    try:
        resp = requests.delete(
            f"{API_URL}/favorites",
            params={"exercise_name": exercise_name},
            headers=_auth_headers(),
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("message", "Exercise removed from favorites successfully")
    except Exception as e:
        return str(e)


if not favorites:
    st.info("No favorite exercises found.")
else:
    for fav in favorites:
        name = fav.get("exercise_name", "Unnamed")
        data = fav.get("exercise_data", {})

        col1, col2 = st.columns([8,1])
        with col1:
            st.markdown(f"### {name}")
        with col2:
            if st.button("delete", key=f"delete_{name}"):
                message = remove_exercise_from_favorites(name)
                st.success(message)
                fetch_favorites.clear()
                st.rerun()
        with st.expander(name):
            st.json(data)
