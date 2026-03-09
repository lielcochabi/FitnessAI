import streamlit as st
import requests

# ------------------- Constants ------------------ #
SAVE_PHRASE = "Would you like to add this workout to your workoutPlans"
FAVORITE_SELECTION_MESSAGE = (
    "Type a number (1-5) to add a specific exercise to favorites, "
    "or type 'all' to add all of them. You can also do comma-separated like: 1,3,5"
)

def submit():
    st.session_state.submitted_text = st.session_state.user_input
    st.session_state.user_input = ""

def _format_exercise_list(label, exercises):  
    lines = [f"Here are some exercises for **{label}**:"]
    for i, ex in enumerate(exercises, start=1):
        name = ex.get("name", "Exercise")
        body_part = ex.get("bodyPart", "Unknown")
        target = ex.get("target", "Unknown")
        equipment = ex.get("equipment", "Unknown")

        lines.append(
            f"{i}. **{name}**\n"
            f"   - Body part: {body_part}\n"
            f"   - Target: {target}\n"
            f"   - Equipment: {equipment}"
        )

    lines.append("\nIf you want to save some, type: **add to favorites**.")
    return "\n\n".join(lines)


def handle_user_input(url):
    user_text = st.session_state.submitted_text
    if not user_text:
        return None

    st.session_state.submitted_text = ""
    user_text_lower = user_text.lower().strip()

    if st.session_state.get("user") is None:
        st.session_state.awaiting_name = False
        st.session_state.awaiting_workout_save = False
        st.session_state.awaiting_favorite_selection = False
        st.session_state.pending_exercises = []

    # ------------------- Selecting favorites flow ------------------ #
    if st.session_state.get("awaiting_favorite_selection"):
        if st.session_state.get("user") is None:
            st.session_state.awaiting_favorite_selection = False
            st.session_state.pending_exercises = []
            return "Please log in to save favorites."  

        exercises = st.session_state.get("pending_exercises", [])
        if not exercises:
            st.session_state.awaiting_favorite_selection = False
            return "No pending exercises to save."  

        if user_text_lower == "all":
            selected = exercises
        else:
            try:
                idxs = [int(x.strip()) - 1 for x in user_text.split(",")]
                selected = [exercises[i] for i in idxs if 0 <= i < len(exercises)]
                if not selected:
                    raise ValueError
            except Exception:
                return "Invalid selection. Use 1-5, 1,3,5 or 'all'." 
        saved = 0
        already_exists = 0  
        errors = [] 

        for ex in selected:
            try:
                resp = requests.post(
                    f"{url}/favorites",
                    json={
                        "username": st.session_state.user["username"],
                        "exercise_name": ex.get("name", "Exercise"),
                        "exercise_data": ex,
                    },
                    timeout=20,
                )

                if resp.ok:
                    saved += 1
                else:
                    try:
                        detail = resp.json().get("detail", "")
                    except Exception:
                        detail = ""

                    if "already in favorites" in detail.lower():
                        already_exists += 1
                    else:
                        errors.append(detail or "Failed to save one exercise.")

            except Exception as e:
                errors.append(str(e)) 

        st.session_state.awaiting_favorite_selection = False
        st.session_state.pending_exercises = []

        parts = []
        if saved:
            parts.append(f"Added {saved} exercise(s) to favorites.")
        if already_exists:
            parts.append(f"{already_exists} exercise(s) were already in favorites.")
        if errors:
            parts.append("Some exercises could not be saved.")

        return " ".join(parts) if parts else "No exercises were saved."  

    # ------------------ user is giving workout name ------------------ #
    if st.session_state.awaiting_name:
        if st.session_state.get("user") is None:
            st.session_state.awaiting_name = False
            return "Please log in to save workout plans."  

        workout_name = user_text.strip()
        if not workout_name:
            return "Workout name cannot be empty. Please type a name."  
        try:
            response = requests.post(
                f"{url}/workouts",
                json={
                    "username": st.session_state.user["username"],
                    "workout_name": workout_name,
                    "workout_data": {"text": st.session_state.pending_workout},
                },
                timeout=20,
            )

            if not response.ok:
                try:
                    message = response.json().get("detail", "Failed to save workout.")  
                except Exception:
                    message = "Failed to save workout."
            else:
                message = f"Workout plan **{workout_name}** saved to your account!"  

        except Exception as e:
            message = str(e)  

        st.session_state.awaiting_name = False
        st.session_state.pending_workout_name = ""
        st.session_state.pending_workout = ""
        return message  

    # ------------------ user answers yes/no to saving ------------------ #
    if st.session_state.awaiting_workout_save:
        if user_text_lower in ("yes", "y"):
            if st.session_state.get("user") is None:
                st.session_state.awaiting_workout_save = False
                st.session_state.pending_workout = ""
                return "Please log in to save workout plans."  

            st.session_state.awaiting_workout_save = False
            st.session_state.awaiting_name = True
            return "Please provide a name for your workout plan."  

        elif user_text_lower in ("no", "n"):
            st.session_state.awaiting_workout_save = False
            st.session_state.pending_workout = ""
            return "Workout plan was not saved."  

        else:
            return "Please answer with 'yes' or 'no'. Would you like to save the workout plan?" 

    # ------------------ Normal ask flow ------------------ #
    try:
        resp = requests.post(
            f"{url}/ask",
            json={"prompt": user_text, "user": st.session_state.get("user")},
            timeout=60,
        )

        if not resp.ok:
            try:
                return resp.json().get("detail", "Request failed.")  
            except Exception:
                return "Request failed."

        payload = resp.json()

        if payload.get("type") == "favorite_request":
            if st.session_state.get("user") is None:
                return "Please log in to save favorites."  

            if not st.session_state.get("pending_exercises"):
                return "Ask for exercises first, for example: 'give me exercises for chest', then say 'add to favorites'."  

            st.session_state.awaiting_favorite_selection = True
            return FAVORITE_SELECTION_MESSAGE  

        if payload.get("type") == "exercise_list":
            exercises = payload.get("exercises", [])
            label = payload.get("label", "")

            if not exercises:
                return "No exercises found."  

            st.session_state.pending_exercises = exercises
            return _format_exercise_list(label, exercises) 

        answer = payload.get("answer", "")
        if not answer:
            return "No answer was returned." 

        if SAVE_PHRASE in answer:
            parts = answer.split("\n\n", 1)
            st.session_state.pending_workout = parts[1] if len(parts) > 1 else answer
            st.session_state.awaiting_workout_save = True

        return answer  

    except Exception as e:
        return str(e)  