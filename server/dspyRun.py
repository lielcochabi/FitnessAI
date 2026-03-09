import dspy
from exerciseDB import get_exercises_by_bodypart, get_exercises_by_target, get_body_parts, get_muscles  

_DSPY_CONFIGURED = False  

keyWordsForFindingExercises = [
    "give me exercises",
    "show me exercises",
    "what are some exercises for",
    "list exercises for",
    "exercises for",
    "exercises targeting",
    "exercises"
]
keyWordsForWorkoutRoutines = [
    "create a workout routine",
    "generate a workout plan",
    "workout routine for",
    "workout plan for",
    "design a workout schedule",
    "workout"
]
keyWordsForFavorites = [
    "add to favorites",
    "add to favourite",
    "save to favorites",
    "save to favourite",
    "add to favorite",
    "save to favorite",
    "favorite",
    "favourite",
]

def init_dspy():
    global _DSPY_CONFIGURED
    if _DSPY_CONFIGURED:
        return  
    dspy.configure(
        lm=dspy.LM(
            'openai/gpt-oss-120b',
            base_url="https://models.mylab.th-luebeck.dev/v1",
            api_key="anything-but-empty",
            temperature=1.0,
            max_tokens=32768,
            cache=False,
        )
    )
    _DSPY_CONFIGURED = True

def check_for_bodypart(prompt):  
    body_parts = get_body_parts() 
    for part in body_parts:
        if part.lower() in prompt.lower():
            return part
    return None


def check_for_muscle(prompt): 
    muscles = get_muscles() 
    for muscle in muscles:
        if muscle.lower() in prompt.lower():
            return muscle
    return None

def muscle_or_bodypart_in_prompt(prompt): 
    body_part = check_for_bodypart(prompt)
    muscle = check_for_muscle(prompt)
    if body_part:
        exercises = get_exercises_by_bodypart(body_part, limit=5)
        if exercises:
            return {
                "type": "exercise_list",
                "label": body_part,
                "exercises": exercises
            }
        return {"type": "text", "answer": f"Sorry, I couldn't find exercises for {body_part}."}
    if muscle:
        exercises = get_exercises_by_target(muscle, limit=5)
        if exercises:
            return {
                "type": "exercise_list",
                "label": muscle,
                "exercises": exercises
            }
        return {"type": "text", "answer": f"Sorry, I couldn't find exercises targeting {muscle}."}
    return None

def create_workout_routine(prompt):
    return


def _extract_answer(pred) -> str:
    if hasattr(pred, "answer"):
        return pred.answer or ""
    if isinstance(pred, dict):
        return pred.get("answer", "")
    return str(pred) or ""

def search_fitness_info(prompt, user):
    prompt_lower = prompt.lower()

    for keyword in keyWordsForFavorites:
        if keyword in prompt_lower:
            return {"type": "favorite_request"}
    workoutFlag = False
    flag = True
    for keyword in keyWordsForWorkoutRoutines:
        if keyword in prompt.lower():
            workoutFlag = True
            flag = False
            break

    if flag:
        for keyword in keyWordsForFindingExercises:
            if keyword in prompt.lower():
                result = muscle_or_bodypart_in_prompt(prompt)
                if result:
                    return result
                break

    search = dspy.Predict("question->answer")

    full_prompt = f"""You are an AI FITNESS COACH.
- Only answer questions about fitness, workouts, muscles, recovery, nutrition for training, or health related to exercise.
- If the user asks about anything not related to fitness, you MUST answer: "I only answer fitness-related questions."
User question: {prompt}
"""

    if workoutFlag:
        full_prompt += "\nCreate a detailed workout routine based on the user's request."
        pred = search(question=full_prompt)
        workout_text = _extract_answer(pred) 

        if not workout_text.strip():  
            workout_text = "I couldn't generate the routine. Please rephrase (e.g., 'create a chest workout plan for 3 days')."
        return (
            "Would you like to add this workout to your workoutPlans? "
            "answer with a yes or no\n\n" + workout_text
        )
    pred = search(question=full_prompt)
    return _extract_answer(pred) 
