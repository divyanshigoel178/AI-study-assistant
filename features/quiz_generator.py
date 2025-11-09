# features/quiz_generator.py
import streamlit as st
from core.gemini_utils import stream_and_accumulate
from core.text_utils import parse_mcq_text

def quiz_tab():
    st.subheader("🧪 Generate MCQs")
    if not st.session_state.get("notes_text"):
        st.info("Upload notes in the sidebar to enable this tab.")
        return

    num_q = st.slider("Number of questions", 3, 20, 5)
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])

    if st.button("🎯 Create Quiz"):
        prompt = f"""
From the notes below, generate {num_q} multiple-choice questions of {difficulty} difficulty.
Provide 4 options (A, B, C, D) and mark the correct one.

Q1. <question text>
A) <option>
B) <option>
C) <option>
D) <option>
Answer: <A/B/C/D>

Notes:
{st.session_state.notes_text}
"""
        with st.spinner("Generating questions…"):
            raw_mcqs = stream_and_accumulate(st.session_state.base_chat, prompt)

        questions = parse_mcq_text(raw_mcqs)
        if not questions:
            st.error("Failed to parse MCQs.")
            return

        st.session_state.generated_mcqs = questions
        st.session_state.current_mcq_index = 0
        st.session_state.mcq_score = 0
        st.session_state.mcq_show_feedback = False

    # quiz rendering
    if st.session_state.get("generated_mcqs"):
        q_idx = st.session_state.current_mcq_index
        q = st.session_state.generated_mcqs[q_idx]
        st.markdown(f"### Question {q_idx + 1} of {len(st.session_state.generated_mcqs)}")
        st.write(q["question"])
        choice = st.radio("Choose:", q["options"], key=f"q{q_idx}")
        if not st.session_state.mcq_show_feedback:
            if st.button("Submit Answer"):
                st.session_state.mcq_show_feedback = True
                if choice == q["answer"]:
                    st.session_state.mcq_score += 1
        else:
            if choice == q["answer"]:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect! Correct: {q['answer']}")
            if st.button("Next"):
                st.session_state.current_mcq_index += 1
                st.session_state.mcq_show_feedback = False
                if st.session_state.current_mcq_index >= len(st.session_state.generated_mcqs):
                    st.success(f"Quiz complete! Score: {st.session_state.mcq_score}/{len(st.session_state.generated_mcqs)}")
                    if st.button("Restart Quiz"):
                        st.session_state.generated_mcqs = []