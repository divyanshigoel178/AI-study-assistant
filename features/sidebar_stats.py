import streamlit as st

def sidebar_stats():
    """Display note statistics and session insights in sidebar."""
    st.markdown("### 📊 Quick Stats")

    notes_text = st.session_state.get("notes_text", "")
    note_length = len(notes_text)
    word_count = len(notes_text.split()) if notes_text else 0

    num_questions = len(st.session_state.get("notes_messages", []))
    mcq_score = st.session_state.get("mcq_score", 0)
    total_mcq = len(st.session_state.get("generated_mcqs", []))

    st.info(f"📝 **Notes Length:** {word_count:,} words ({note_length:,} chars)")
    st.info(f"❓ **Questions Asked:** {num_questions}")
    st.info(f"🧩 **Quiz Score:** {mcq_score}/{total_mcq}" if total_mcq > 0 else "🧩 No quiz taken yet.")
