import streamlit as st
from dspyRun import init_dspy, search_fitness_info


init_dspy()


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

UserInput = st.text_input("What would you like to know about fitness today?")
if UserInput:
    st.write(search_fitness_info(UserInput))

