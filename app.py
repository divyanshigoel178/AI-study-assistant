# streamlit_app.py
import streamlit as st
from config.settings import init_environment, MODEL_NAME
from core.session_utils import init_session_state
from core.gemini_utils import ensure_chat_sessions
from core.pdf_utils import extract_text_from_pdf
from features.chat_general import general_chat_tab
from features.chat_notes import notes_qa_tab
from features.summarize_notes import summarize_tab
from features.quiz_generator import quiz_tab

# ===== 0. Setup =====
init_environment()
init_session_state(MODEL_NAME)
ensure_chat_sessions(MODEL_NAME)

# ===== 1. Sidebar =====
with st.sidebar:
    st.header("📄 Study Notes")
    uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
    if uploaded:
        text = uploaded.read().decode("utf-8") if uploaded.type == "text/plain" else extract_text_from_pdf(uploaded)
        st.session_state.notes_text = text
        if text:
            st.success("Notes loaded!")
            st.caption(f"Characters: {len(text):,}")
            with st.expander("Preview"):
                st.text(text[:800])
    if st.session_state.get("notes_text"):
        if st.button("🗑 Clear Notes"):
            st.session_state.notes_text = ""
            st.experimental_rerun()

# ===== 2. Tabs =====
st.title("📘 AI Study Assistant")
tabs = st.tabs(["💬 Chat", "❓ Ask from Notes", "📝 Summarize", "🧪 MCQs"])
with tabs[0]:
    general_chat_tab()
with tabs[1]:
    notes_qa_tab()
with tabs[2]:
    summarize_tab()
with tabs[3]:
    quiz_tab()

st.markdown("<p class='small-muted'>⚠ Slow down if you hit rate limits.</p>", unsafe_allow_html=True)