import streamlit as st
from exerciseDB import targets
from dspyRun import run_dspy


if "initDspy" not in st.session_state:
    st.session_state.initDspy = True
    run_dspy()


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
