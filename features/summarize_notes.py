# features/summarize_notes.py
import streamlit as st
from core.gemini_utils import stream_and_accumulate

def summarize_tab():
    st.subheader("📝 Summarize Notes")
    if not st.session_state.get("notes_text"):
        st.info("Upload notes in the sidebar to enable this tab.")
        return

    level = st.selectbox("Detail level", ["Very short bullets", "Short bullets", "Detailed bullets"])
    if st.button("🧾 Generate Summary"):
        style_map = {
            "Very short bullets": "Keep it extremely concise (max 5 bullets).",
            "Short bullets": "Use up to 8 bullets with key points.",
            "Detailed bullets": "Use up to 12 bullets, with brief explanations."
        }
        prompt = f"""
Summarize the following study notes into {style_map[level]}
Use simple language for quick revision.

Notes:\n\n{st.session_state.notes_text}
"""
        with st.spinner("Summarizing…"):
            reply = stream_and_accumulate(st.session_state.base_chat, prompt)
        if reply:
            st.markdown("### Summary")
            st.markdown(reply)
            st.download_button("⬇ Download Summary", reply, "summary.txt")