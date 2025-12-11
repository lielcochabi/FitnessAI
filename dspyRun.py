# dspy_config.py
import dspy
from exerciseDB import get_body_parts, get_muscles

_DSPY_CONFIGURED = False   # <- global flag, lives for the whole Python process

def init_dspy():
    global _DSPY_CONFIGURED
    if _DSPY_CONFIGURED:
        return  # already configured once in this process, do nothing

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

def search_fitness_info(prompt):
    search=dspy.Predict("question->answer")
    full_prompt = f"""You are an AI FITNESS COACH.
                    - Only answer questions about fitness, workouts, muscles, recovery, nutrition for training, or health related to exercise.
                    - If the user asks about anything not related to fitness, you MUST answer:"I only answer fitness-related questions."
                    User question: {prompt}"""
    result=search(question=full_prompt)
    return result['answer']
