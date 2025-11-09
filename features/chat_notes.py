# features/chat_notes.py
import json
import streamlit as st
import google.generativeai as genai
from core.text_utils import pick_relevant_chunks, build_notes_prompt
from core.gemini_utils import stream_and_accumulate
from config.settings import MODEL_NAME

def notes_qa_tab():
    st.subheader("❓ Ask Questions from Notes")

    if not st.session_state.get("notes_text"):
        st.info("Upload notes in the sidebar to enable this tab.")
        return

    for msg in st.session_state.get("notes_messages", []):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    question = st.chat_input("Ask a question from your notes…")
    if question:
        st.session_state.notes_messages.append({"role": "user", "content": question})
        chunks = pick_relevant_chunks(st.session_state.notes_text, question)
        prompt = build_notes_prompt(chunks, question)
        with st.chat_message("assistant", avatar="🤖"):
            reply = stream_and_accumulate(st.session_state.notes_chat, prompt)
        if reply:
            st.session_state.notes_messages.append({"role": "assistant", "content": reply})

    if st.session_state.get("notes_messages"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧹 Clear Notes Q&A"):
                st.session_state.notes_messages = []
                st.session_state.notes_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])
                st.experimental_rerun()
        with col2:
            notes_json = json.dumps(st.session_state.notes_messages, indent=2)
            st.download_button("💾 Save Notes Chat", notes_json, "notes_chat.json", "application/json")

    file = st.file_uploader("📂 Load Notes Chat", type="json")
    if file:
        st.session_state.notes_messages = json.load(file)
        st.experimental_rerun()