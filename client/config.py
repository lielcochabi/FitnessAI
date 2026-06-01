"""Central place to resolve the backend API URL.

Resolution order (first hit wins):
  1. Streamlit Cloud secret  -> st.secrets["API_URL"]      (online deployment)
  2. Environment variable     -> os.getenv("API_URL")        (Docker / Kubernetes)
  3. Local default            -> http://127.0.0.1:8000        (running on your PC)

This lets the exact same client code run unchanged locally, in Docker/k8s,
and on Streamlit Community Cloud.
"""
import os

_LOCAL_DEFAULT = "http://127.0.0.1:8000"


def get_api_url() -> str:
    # 1. Streamlit Cloud secrets (only available when running inside Streamlit).
    try:
        import streamlit as st

        if "API_URL" in st.secrets:
            return str(st.secrets["API_URL"]).rstrip("/")
    except Exception:
        # st.secrets raises if no secrets file exists; ignore and fall through.
        pass

    # 2. Environment variable (Docker Compose / Kubernetes set this).
    # 3. Local default.
    return os.getenv("API_URL", _LOCAL_DEFAULT).rstrip("/")
