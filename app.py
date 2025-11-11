import streamlit as st
from config.settings import init_environment, MODEL_NAME
from core.session_utils import init_session_state
from core.gemini_utils import ensure_chat_sessions
from core.pdf_utils import extract_text_from_pdf
from core.file_utils import load_last_notes, save_notes
from features.chat_general import general_chat_tab
from features.chat_notes import notes_qa_tab
from features.summarize_notes import summarize_tab
from features.quiz_generator import quiz_tab
from features.sidebar_stats import sidebar_stats


# ==========================================================
# 0️⃣ INITIAL SETUP
# ==========================================================
init_environment()
init_session_state(MODEL_NAME)
ensure_chat_sessions(MODEL_NAME)

# Set Streamlit page configuration
st.set_page_config(page_title="📘 AI Study Assistant", page_icon="📚", layout="wide")

# Load custom CSS for styling (UTF-8 to prevent emoji decode errors)
with open("assets/styles.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📘 AI Study Assistant")


# ==========================================================
# 1️⃣ LOAD PREVIOUSLY SAVED NOTES (IF AVAILABLE)
# ==========================================================
if not st.session_state.get("notes_text"):
    last_notes = load_last_notes()
    if last_notes:
        st.session_state.notes_text = last_notes
        st.toast("📄 Loaded your last saved notes automatically!")


# ==========================================================
# 2️⃣ SIDEBAR – STRUCTURED & POLISHED
# ==========================================================
with st.sidebar:
    # --- Study Notes Upload Section ---
    st.markdown("<div class='sidebar-section'>", unsafe_allow_html=True)
    st.header("📄 Study Notes")
    
    uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])

    if uploaded:
        # Handle text and PDF uploads
        if uploaded.type == "text/plain":
            text = uploaded.read().decode("utf-8", errors="ignore")
        else:
            text = extract_text_from_pdf(uploaded)

        if text:
            st.session_state.notes_text = text
            save_notes(text)
            st.success("✅ Notes loaded and saved successfully!")
            st.caption(f"Characters: {len(text):,}")
            with st.expander("📘 Preview (first 800 chars)"):
                st.text(text[:800])

    # ✅ Clear Notes Button (unique key)
    if st.session_state.get("notes_text"):
        if st.button("🗑️ Clear Notes", key='clear_notes_sidebar'):
            st.session_state.notes_text = ""
            st.experimental_rerun()

    # Close Study Notes section
    st.markdown("</div>", unsafe_allow_html=True)


    # --- Quick Stats Section ---
    st.markdown("<div id='quick-stats-card'>", unsafe_allow_html=True)
    st.markdown("### 📊 Quick Stats")
    sidebar_stats()
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
# 3️⃣ MAIN APP TABS
# ==========================================================
chat_tab, notes_tab, summarize_tab_section, quiz_tab_section = st.tabs([
    "💬 Chat (General)",
    "❓ Ask from Notes",
    "📝 Summarize Notes",
    "🧪 Generate MCQs"
])

# --- General Chat ---
with chat_tab:
    general_chat_tab()

# --- Ask from Notes ---
with notes_tab:
    notes_qa_tab()

# --- Summarize Notes ---
with summarize_tab_section:
    summarize_tab()

# --- MCQ Generator ---
with quiz_tab_section:
    quiz_tab()


# ==========================================================
# 4️⃣ FOOTER
# ==========================================================
st.markdown(
    """
    <div class='small-muted'>
        💡 Tip: If you hit free-tier limits (429), wait a few seconds or try again later.<br>
        Use the sidebar to upload, view, or clear your notes anytime.
    </div>
    """,
    unsafe_allow_html=True
)
