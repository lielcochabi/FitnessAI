import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

user = st.session_state.get("user")
if not user:
    st.warning("Please log in to access this page.")
    st.stop()

st.title("Workout Plans")
st.subheader("Here you will see your workout plans.")


def _auth_headers():
    token = st.session_state.get("session_id")
    return {"Authorization": f"Bearer {token}"} if token else {}


# ------------------ Fetch Workouts ------------------ #
@st.cache_data(ttl=30)
def fetch_workouts(api_url: str, token: str):
    resp = requests.get(
        f"{api_url}/workouts",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json().get("workouts", [])

# ------------------ Delete Workout ------------------ #
def remove_workout(workout_name):
    try:
        resp = requests.delete(
            f"{API_URL}/workouts",
            params={"workout_name": workout_name},
            headers=_auth_headers(),
            timeout=10
        )
        resp.raise_for_status()
        return resp.json().get("message", "Workout deleted successfully")
    except Exception as e:
        return str(e)

if st.button("Refresh"):
    fetch_workouts.clear()
    st.rerun()

with st.spinner("Loading workout plans..."):
    try:
        workouts = fetch_workouts(API_URL, st.session_state.get("session_id") or "")
    except Exception as e:
        st.error(str(e))
        workouts = []

if not workouts:
    st.info("No workout plans found. Create one to get started!")
else:
    for workout in workouts:
        name = workout.get("workout_name", "Unnamed")
        data = workout.get("workout_data", {})

        col1, col2 = st.columns([8, 1])

        with col1:
            st.markdown(f"### {name}")

        with col2:
            if st.button("delete", key=f"delete_workout_{name}"):
                message = remove_workout(name)
                st.success(message)
                fetch_workouts.clear()
                st.rerun()

        with st.expander(name):
            st.json(data)
