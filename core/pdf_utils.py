# core/pdf_utils.py
import re
import pdfplumber
import streamlit as st

def extract_text_from_pdf(file):
    """Extract and clean text from a PDF."""
    try:
        with pdfplumber.open(file) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n\n".join(pages)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
        return ""