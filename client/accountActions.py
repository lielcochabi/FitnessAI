import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TIMEOUT = 10

@st.dialog("Sign Up")
def signup_dialog():
    username = st.text_input("Username")
    first_name = st.text_input("First Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        if not username or not first_name or not email or not password:
            st.warning("Please fill in all fields.")
            return
        try:
            resp = requests.post(f"{API_URL}/signup", params={
                "username": username,
                "first_name": first_name,
                "email": email,
                "password": password
            },
            timeout=TIMEOUT,)
            resp.raise_for_status()
            data = resp.json()
            st.session_state.user = data["user"]

            st.success("Account created")
            st.rerun()

        except Exception as e:
            st.error(str(e))

@st.dialog("Log In")
def login_dialog():
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        if not username or not password:
            st.warning("Please fill in all fields.")
            return
        try:
            resp = requests.post(f"{API_URL}/login", params={
                "username": username,
                "password": password
            },
            timeout=TIMEOUT,)
            resp.raise_for_status()
            data = resp.json()
            st.session_state.user = data["user"]

            st.success("Logged in")
            st.rerun()

        except Exception as e:
            st.error(str(e))


import os
import streamlit as st
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
TIMEOUT = 10

@st.dialog("Sign Up")
def signup_dialog():
    username = st.text_input("Username")
    first_name = st.text_input("First Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        if not username or not first_name or not email or not password:
            st.warning("Please fill in all fields.")
            return

        payload = {  
            "username": username,
            "first_name": first_name,
            "email": email,
            "password": password,
        }  

        try:
            resp = requests.post(
                f"{API_URL}/signup",
                json=payload,
                timeout=TIMEOUT, 
            )
            resp.raise_for_status()
            data = resp.json()
            st.session_state.user = data["user"]

            st.success("Account created")
            st.rerun()

        except Exception as e:
            st.error(str(e))

@st.dialog("Log In")
def login_dialog():
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        if not username or not password:
            st.warning("Please fill in all fields.")
            return

        payload = { 
            "username": username,
            "password": password,
        }  

        try:
            resp = requests.post(
                f"{API_URL}/login",
                json=payload,
                timeout=TIMEOUT,   
            )
            resp.raise_for_status()
            data = resp.json()
            st.session_state.user = data["user"]

            st.success("Logged in")
            st.rerun()

        except Exception as e:
            st.error(str(e))