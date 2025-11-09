# features/chat_general.py
import json
import streamlit as st
import google.generativeai as genai
from core.gemini_utils import stream_and_accumulate
from config.settings import MODEL_NAME

def general_chat_tab():
    st.subheader("💬 Chat with Gemini")

    for msg in st.session_state.get("base_messages", []):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    user_msg = st.chat_input("Type your message…")
    if user_msg:
        st.session_state.base_messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"): st.markdown(user_msg)
        with st.chat_message("assistant"):
            reply = stream_and_accumulate(st.session_state.base_chat, user_msg)
        if reply:
            st.session_state.base_messages.append({"role": "assistant", "content": reply})

    if st.session_state.get("base_messages"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Clear Chat"):
                st.session_state.base_messages = []
                st.session_state.base_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])
                st.experimental_rerun()
        with col2:
            chat_json = json.dumps(st.session_state.base_messages, indent=2)
            st.download_button("💾 Save Chat", chat_json, "general_chat.json", "application/json")

    file = st.file_uploader("📂 Load Chat", type="json")
    if file:
        st.session_state.base_messages = json.load(file)
        st.experimental_rerun()