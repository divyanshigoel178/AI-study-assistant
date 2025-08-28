import os
import time
import re
import pdfplumber
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import json

# ===============
# 0) Setup & Config
# ===============
load_dotenv()  # load GOOGLE_API_KEY from .env
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not found. Create a .env file with your key.")

genai.configure(api_key=API_KEY)
MODEL_NAME = "gemini-1.5-flash"  # fast & free-tier friendly

st.set_page_config(page_title="AI Study Assistant", page_icon="📘", layout="wide")

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
# 1) Session State Initialization
# ===============
if "base_messages" not in st.session_state:
    st.session_state.base_messages = []

if "notes_messages" not in st.session_state:
    st.session_state.notes_messages = []

if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""

if "last_call_time" not in st.session_state:
    st.session_state.last_call_time = 0.0

if "base_chat" not in st.session_state:
    st.session_state.base_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])

if "notes_chat" not in st.session_state:
    st.session_state.notes_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])

# MCQ quiz states
if "generated_mcqs" not in st.session_state:
    st.session_state.generated_mcqs = []
if "current_mcq_index" not in st.session_state:
    st.session_state.current_mcq_index = 0
if "mcq_score" not in st.session_state:
    st.session_state.mcq_score = 0
if "mcq_show_feedback" not in st.session_state:
    st.session_state.mcq_show_feedback = False

# ===============
# 2) Helper Functions
# ===============

def rate_limited_send(chat, prompt: str, stream: bool = True, min_interval: float = 2.0):
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
    try:
        stream = rate_limited_send(chat, prompt, stream=True)
        full_text = ""
        container = st.empty()
        for chunk in stream:
            if hasattr(chunk, "text") and chunk.text:
                full_text += chunk.text
                container.markdown(full_text)
        return full_text.strip()
    except Exception as e:
        msg = str(e)
        if "ResourceExhausted" in msg or "429" in msg:
            st.warning("⚠️ Free-tier quota hit (429). Please slow down or try again later.")
        else:
            st.error(f"Error: {e}")
        return ""

def extract_text_from_pdf(file) -> str:
    try:
        with pdfplumber.open(file) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n\n".join(pages)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
    except Exception as e:
        st.error(f"Failed to read PDF: {e}")
        return ""

def split_into_chunks(text: str, max_chars: int = 8000, overlap: int = 300):
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

def parse_mcq_text(mcq_text):
    questions = []
    q_blocks = re.split(r"\nQ\d+\.", mcq_text)
    for block in q_blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        question_text = lines[0].strip()
        options = []
        answer = None
        for line in lines[1:]:
            line = line.strip()
            if re.match(r"[ABCD]\)", line):
                options.append(line[3:].strip())
            elif line.startswith("Answer:"):
                ans_letter = line.split("Answer:")[1].strip()
                letter_to_index = {"A":0, "B":1, "C":2, "D":3}
                answer = options[letter_to_index.get(ans_letter, 0)]
        questions.append({"question": question_text, "options": options, "answer": answer})
    return questions

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

    for msg in st.session_state.base_messages:
        with st.chat_message(msg["role"], avatar=("🧑" if msg["role"] == "user" else "🤖")):
            st.markdown(msg["content"])

    user_msg = st.chat_input("Type your message…")
    if user_msg:
        st.session_state.base_messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_msg)

        with st.chat_message("assistant", avatar="🤖"):
            reply = stream_and_accumulate(st.session_state.base_chat, user_msg)
        if reply:
            st.session_state.base_messages.append({"role": "assistant", "content": reply})

    if st.session_state.base_messages:
        if st.button("🧹 Clear Chat", key="clear_base"):
            st.session_state.base_messages = []
            st.session_state.base_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])
            st.experimental_rerun()

    if st.session_state.base_messages:
        base_chat_json = json.dumps(st.session_state.base_messages, indent=2)
        st.download_button(
            label="💾 Save General Chat as JSON",
            data=base_chat_json,
            file_name="general_chat_history.json",
            mime="application/json"
        )
    uploaded_base_chat_file = st.file_uploader("📂 Load General Chat JSON", type="json", key="load_base_chat")
    if uploaded_base_chat_file is not None:
        try:
            loaded_base_messages = json.load(uploaded_base_chat_file)
            st.session_state.base_messages = loaded_base_messages
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to load General Chat: {e}")

# ---- 4.2 Ask from Notes ----
with notes_tab:
    st.subheader("Ask Questions from Your Notes")
    if not st.session_state.notes_text:
        st.info("Upload notes in the sidebar to enable this tab.")
    else:
        for msg in st.session_state.notes_messages:
            with st.chat_message(msg["role"], avatar=("🧑" if msg["role"] == "user" else "🤖")):
                st.markdown(msg["content"])

        question = st.chat_input("Ask a question from your notes…")
        if question:
            st.session_state.notes_messages.append({"role": "user", "content": question})
            with st.chat_message("user", avatar="🧑"):
                st.markdown(question)

            chunks = pick_relevant_chunks(st.session_state.notes_text, question, top_k=3)
            prompt = build_notes_prompt(chunks, question)

            with st.chat_message("assistant", avatar="🤖"):
                reply = stream_and_accumulate(st.session_state.notes_chat, prompt)
            if reply:
                st.session_state.notes_messages.append({"role": "assistant", "content": reply})

        if st.session_state.notes_messages:
            if st.button("🧹 Clear Notes Q&A", key="clear_notes_chat"):
                st.session_state.notes_messages = []
                st.session_state.notes_chat = genai.GenerativeModel(MODEL_NAME).start_chat(history=[])
                st.experimental_rerun()

        if st.session_state.notes_messages:
            notes_chat_json = json.dumps(st.session_state.notes_messages, indent=2)
            st.download_button(
                label="💾 Save Notes Q&A Chat as JSON",
                data=notes_chat_json,
                file_name="notes_qa_chat_history.json",
                mime="application/json"
            )
        uploaded_notes_chat_file = st.file_uploader("📂 Load Notes Q&A Chat JSON", type="json", key="load_notes_chat")
        if uploaded_notes_chat_file is not None:
            try:
                loaded_notes_messages = json.load(uploaded_notes_chat_file)
                st.session_state.notes_messages = loaded_notes_messages
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to load Notes Q&A Chat: {e}")

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

Notes:
{st.session_state.notes_text}
"""
            with st.spinner("Generating quiz…"):
                raw_mcqs = stream_and_accumulate(st.session_state.base_chat, prompt)

            questions = parse_mcq_text(raw_mcqs)
            if not questions:
                st.error("Failed to parse MCQs. Please try again.")
            else:
                st.session_state.generated_mcqs = questions
                st.session_state.current_mcq_index = 0
                st.session_state.mcq_score = 0
                st.session_state.mcq_show_feedback = False

        if st.session_state.generated_mcqs:
            q_idx = st.session_state.current_mcq_index
            q = st.session_state.generated_mcqs[q_idx]

            st.markdown(f"### Question {q_idx + 1} of {len(st.session_state.generated_mcqs)}")
            st.write(q["question"])

            user_choice = st.radio("Choose an answer:", q["options"], key=f"mcq_radio_{q_idx}")

            if not st.session_state.mcq_show_feedback:
                if st.button("Submit Answer"):
                    st.session_state.mcq_show_feedback = True
                    if user_choice == q["answer"]:
                        st.session_state.mcq_score += 1
            else:
                if user_choice == q["answer"]:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect! The correct answer is: {q['answer']}")
                if st.button("Next Question"):
                    st.session_state.current_mcq_index += 1
                    st.session_state.mcq_show_feedback = False
                    if st.session_state.current_mcq_index >= len(st.session_state.generated_mcqs):
                        st.success(f"Quiz completed! Your score is {st.session_state.mcq_score} / {len(st.session_state.generated_mcqs)}")
                        if st.button("Restart Quiz"):
                            st.session_state.generated_mcqs = []
                            st.session_state.current_mcq_index = 0
                            st.session_state.mcq_score = 0
                            st.session_state.mcq_show_feedback = False

# Footer
st.markdown(
    "<p class='small-muted'>Tip: If you hit free-tier limits (429), slow down a bit or try later. Use the sidebar to (re)load notes.</p>",
    unsafe_allow_html=True,
)
