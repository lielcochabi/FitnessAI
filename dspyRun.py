import dspy


def run_dspy():
    dspy.configure(lm=dspy.LM('openai/gpt-oss-120b',                    
        base_url="https://models.mylab.th-luebeck.dev/v1",
        temperature=1.0, 
        max_tokens=32768,
        api_key="anything-but-empty",
        cache=False # Otherwise, generated responses are cached and repeated executions of DSPy calls always produce the same result
    ))
