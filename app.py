import os
import time
import re
import pdfplumber
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai

# ===============
# 0) Setup & Config
# ===============
load_dotenv()  # load GOOGLE_API_KEY from .env
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found. Create a .env file with your key.")

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-1.5-flash"  # fast & free-tier friendly

# Streamlit page config
st.set_page_config(page_title="AI Study Assistant", page_icon="📘", layout="wide")

# Small CSS polish
st.markdown(
    """
    <style>
      .small-muted { font-size: 12px; color: #666; }
      .section { padding: 0.5rem 1rem; border-radius: 12px; background: #fafafa; border: 1px solid #eee; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ===============
# 1) Session State
# ===============
if "base_messages" not in st.session_state:  # general chat messages
    st.session_state.base_messages = []  # list of dicts: {"role": "user"|"assistant", "content": str}

if "notes_messages" not in st.session_state:  # notes Q&A messages
    st.session_state.notes_messages = []

if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""

if "last_call_time" not in st.session_state:
    st.session_state.last_call_time = 0.0

# Keep separate chat objects for base and notes
if "base_chat" not in st.session_state:
    st.session_state.base_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])

if "notes_chat" not in st.session_state:
    st.session_state.notes_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])


# ===============
# 2) Helpers
# ===============

def rate_limited_send(chat, prompt: str, stream: bool = True, min_interval: float = 2.0):
    """Simple client-side rate limiter to avoid 429s (free tier)."""
    now = time.time()
    delta = now - st.session_state.last_call_time
    if delta < min_interval:
        time.sleep(min_interval - delta)
    try:
        resp = chat.send_message(prompt, stream=stream)
        return resp
    finally:
        st.session_state.last_call_time = time.time()


def stream_and_accumulate(chat, prompt: str) -> str:
    """Stream Gemini response to UI but return one final combined string."""
    try:
        stream = rate_limited_send(chat, prompt, stream=True)
        full_text = ""
        # live display while streaming
        container = st.empty()
        for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                full_text += chunk.text
                container.markdown(full_text)
        return full_text.strip()
    except Exception as e:
        # Friendly errors
        msg = str(e)
        if "ResourceExhausted" in msg or "429" in msg:
            st.warning("⚠️ Free-tier quota hit (429). Please slow down or try again later.")
        else:
            st.error(f"Error: {e}")
        return ""


def extract_text_from_pdf(file) -> str:
    """Extract text from an uploaded PDF using pdfplumber."""
    try:
        with pdfplumber.open(file) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n\n".join(pages)
        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
        return ""


def split_into_chunks(text: str, max_chars: int = 8000, overlap: int = 300):
    """Naive text chunking by characters, with overlap to preserve context."""
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def keyword_score(chunk: str, question: str) -> int:
    """Very simple relevance score based on keyword overlap."""
    # Lowercase and split words
    words_q = re.findall(r"\w+", question.lower())
    words_c = re.findall(r"\w+", chunk.lower())
    set_q = set(words_q)
    score = sum(1 for w in words_c if w in set_q)
    return score


def pick_relevant_chunks(notes_text: str, question: str, top_k: int = 3):
    chunks = split_into_chunks(notes_text)
    if not chunks:
        return []
    ranked = sorted(chunks, key=lambda c: keyword_score(c, question), reverse=True)
    return ranked[:top_k]


def build_notes_prompt(context_chunks, question: str) -> str:
    context = "\n\n---\n\n".join(context_chunks)
    prompt = f"""
You are a helpful study assistant.
Use ONLY the context below to answer the user's question. If the answer is not in the context, say "I don't know based on the notes." Keep the explanation simple and student‑friendly.

Context:
{context}

Question: {question}

Answer:
"""
    return prompt


# ===============
# 3) Sidebar — Upload Notes
# ===============
with st.sidebar:
    st.header("📄 Study Notes")
    uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
    if uploaded is not None:
        if uploaded.type == "text/plain":
            content = uploaded.read().decode("utf-8", errors="ignore")
        else:
            content = extract_text_from_pdf(uploaded)
        st.session_state.notes_text = content or ""
        if st.session_state.notes_text:
            st.success("Notes loaded!")
            st.caption(f"Characters: {len(st.session_state.notes_text):,}")
            with st.expander("Preview (first 800 chars)"):
                st.text(st.session_state.notes_text[:800])
    if st.session_state.notes_text:
        if st.button("🗑️ Clear Notes"):
            st.session_state.notes_text = ""
            st.experimental_rerun()


# ===============
# 4) Main UI — Tabs
# ===============
st.title("📘 AI Study Assistant")

chat_tab, notes_tab, summarize_tab, quiz_tab = st.tabs([
    "💬 Chat (General)",
    "❓ Ask from Notes",
    "📝 Summarize Notes",
    "🧪 Generate MCQs",
])

# ---- 4.1 General Chat ----
with chat_tab:
    st.subheader("Chat with Gemini")

    # Show existing messages
    for msg in st.session_state.base_messages:
        with st.chat_message(msg["role"], avatar=("🧑" if msg["role"] == "user" else "🤖")):
            st.markdown(msg["content"])  # render markdown

    # Input
    user_msg = st.chat_input("Type your message…")
    if user_msg:
        # Add user message to history & display
        st.session_state.base_messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_msg)

        # Stream assistant reply and save only once
        with st.chat_message("assistant", avatar="🤖"):
            reply = stream_and_accumulate(st.session_state.base_chat, user_msg)
        if reply:
            st.session_state.base_messages.append({"role": "assistant", "content": reply})

    # Clear Chat button
    if st.session_state.base_messages:
        if st.button("🧹 Clear Chat", key="clear_base"):
            st.session_state.base_messages = []
            st.session_state.base_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])
            st.experimental_rerun()

# ---- 4.2 Ask from Notes ----
with notes_tab:
    st.subheader("Ask Questions from Your Notes")
    if not st.session_state.notes_text:
        st.info("Upload notes in the sidebar to enable this tab.")
    else:
        # Show past Q&A
        for msg in st.session_state.notes_messages:
            with st.chat_message(msg["role"], avatar=("🧑" if msg["role"] == "user" else "🤖")):
                st.markdown(msg["content"])  # render markdown

        question = st.chat_input("Ask a question from your notes…")
        if question:
            st.session_state.notes_messages.append({"role": "user", "content": question})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(question)

            # Pick relevant chunks and build prompt
            chunks = pick_relevant_chunks(st.session_state.notes_text, question, top_k=3)
            prompt = build_notes_prompt(chunks, question)

            # Stream answer
            with st.chat_message("assistant", avatar="🤖"):
                reply = stream_and_accumulate(st.session_state.notes_chat, prompt)
            if reply:
                st.session_state.notes_messages.append({"role": "assistant", "content": reply})

        # Clear Notes Chat
        if st.session_state.notes_messages:
            if st.button("🧹 Clear Notes Q&A", key="clear_notes_chat"):
                st.session_state.notes_messages = []
                st.session_state.notes_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])
                st.experimental_rerun()

# ---- 4.3 Summarize Notes ----
with summarize_tab:
    st.subheader("Summarize Your Notes")
    if not st.session_state.notes_text:
        st.info("Upload notes in the sidebar to enable this tab.")
    else:
        level = st.selectbox("Detail level", ["Very short bullets", "Short bullets", "Detailed bullets"])
        if st.button("📝 Summarize"):
            style_map = {
                "Very short bullets": "Keep it extremely concise (max 5 bullets).",
                "Short bullets": "Use up to 8 bullets with key points only.",
                "Detailed bullets": "Use up to 12 bullets, briefly explain key concepts.",
            }
            prompt = f"""
Summarize the following study notes into {style_map[level]}
Use simple language suitable for quick revision.

Notes:\n\n{st.session_state.notes_text}
"""
            with st.spinner("Summarizing…"):
                reply = stream_and_accumulate(st.session_state.base_chat, prompt)
            if reply:
                st.markdown("### Summary")
                st.markdown(reply)
                st.download_button("⬇️ Download Summary", reply, file_name="summary.txt")

# ---- 4.4 Generate MCQs ----
with quiz_tab:
    st.subheader("Create a Quiz from Your Notes")
    if not st.session_state.notes_text:
        st.info("Upload notes in the sidebar to enable this tab.")
    else:
        num_q = st.slider("Number of questions", 3, 20, 5)
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        if st.button("🧪 Generate MCQs"):
            prompt = f"""
From the notes below, generate {num_q} multiple-choice questions of {difficulty} difficulty.
For each question, provide exactly 4 options (A, B, C, D) and indicate the correct answer.
Format strictly like this:

Q1. <question text>
A) <option>
B) <option>
C) <option>
D) <option>
Answer: <A/B/C/D>

Repeat for all questions.

Notes:\n\n{st.session_state.notes_text}
"""
            with st.spinner("Generating quiz…"):
                reply = stream_and_accumulate(st.session_state.base_chat, prompt)
            if reply:
                st.markdown("### Quiz")
                st.text(reply)
                st.download_button("⬇️ Download Quiz", reply, file_name="quiz.txt")

# Footer
st.markdown("<p class='small-muted'>Tip: If you hit free-tier limits (429), slow down a bit or try later. Use the sidebar to (re)load notes.</p>", unsafe_allow_html=True)


