# config/settings.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
import streamlit as st

MODEL_NAME = "gemini-2.5-flash"

def init_environment():
    """Load API key and configure Streamlit & Gemini."""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not found in .env file.")
    genai.configure(api_key=api_key)
    st.set_page_config(page_title="AI Study Assistant", page_icon="📘", layout="wide")
