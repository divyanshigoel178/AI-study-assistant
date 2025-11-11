import os
import streamlit as st

NOTES_DIR = "notes"

def ensure_notes_dir():
    """Create notes directory if it doesn't exist."""
    if not os.path.exists(NOTES_DIR):
        os.makedirs(NOTES_DIR)

def save_notes(content: str, filename: str = "latest_notes.txt"):
    """Save uploaded notes text locally."""
    ensure_notes_dir()
    path = os.path.join(NOTES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    st.session_state["last_saved_file"] = path
    return path

def load_last_notes():
    """Load last saved notes file if exists."""
    path = os.path.join(NOTES_DIR, "latest_notes.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""
