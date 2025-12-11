import streamlit as st
from exerciseDB import targets
import dspy



dspy.configure(lm=dspy.LM('openai/gpt-oss-120b',                    
    base_url="https://models.mylab.th-luebeck.dev/v1",
    temperature=1.0, 
    max_tokens=32768,
    api_key="anything-but-empty",
    cache=False # Otherwise, generated responses are cached and repeated executions of DSPy calls always produce the same result
))







st.set_page_config(
    page_title="AI Fitness Plan Assistant",layout="wide")


st.title("AI Fitness Plan Assistant!")
st.subheader("Your personal workout & nutrition AI")

st.markdown("""
Welcome!  
This app helps you:
- Generate customized workout plans  
- Build meal plans with calories & macros  
- Track your progress  
- Adapt and improve weekly with AI  
""")

st.divider()

st.button("Get Started")
