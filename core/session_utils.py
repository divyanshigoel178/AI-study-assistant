# core/session_utils.py
import streamlit as st
import google.generativeai as genai

def init_session_state(model_name: str):
    """Initialize all Streamlit session_state variables safely."""

    defaults = {
        "base_messages": [],
        "notes_messages": [],
        "notes_text": "",
        "last_call_time": 0.0,
        "generated_mcqs": [],
        "current_mcq_index": 0,
        "mcq_score": 0,
        "mcq_show_feedback": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Ensure chat sessions exist
    if "base_chat" not in st.session_state:
        st.session_state.base_chat = genai.GenerativeModel(model_name).start_chat(history=[])

    if "notes_chat" not in st.session_state:
        st.session_state.notes_chat = genai.GenerativeModel(model_name).start_chat(history=[])