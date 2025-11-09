# core/gemini_utils.py
import time
import streamlit as st
import google.generativeai as genai

def ensure_chat_sessions(model_name):
    """Initialize chat sessions for general and notes chat."""
    if "base_chat" not in st.session_state:
        st.session_state.base_chat = genai.GenerativeModel(model_name).start_chat(history=[])
    if "notes_chat" not in st.session_state:
        st.session_state.notes_chat = genai.GenerativeModel(model_name).start_chat(history=[])

def rate_limited_send(chat, prompt: str, stream=True, min_interval=2.0):
    now = time.time()
    delta = now - st.session_state.get("last_call_time", 0.0)
    if delta < min_interval:
        time.sleep(min_interval - delta)
    try:
        resp = chat.send_message(prompt, stream=stream)
        return resp
    finally:
        st.session_state["last_call_time"] = time.time()

def stream_and_accumulate(chat, prompt: str):
    """Stream the Gemini model's response live to Streamlit."""
    try:
        stream = rate_limited_send(chat, prompt, stream=True)
        full_text = ""
        container = st.empty()
        for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                full_text += chunk.text
                container.markdown(full_text)
        return full_text.strip()
    except Exception as e:
        msg = str(e)
        if "429" in msg:
            st.warning("⚠ Free-tier limit reached. Try again later.")
        else:
            st.error(f"Error: {e}")
        return ""