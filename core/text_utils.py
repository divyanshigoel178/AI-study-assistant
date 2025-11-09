# core/text_utils.py
import re

def split_into_chunks(text, max_chars=8000, overlap=300):
    text = text.strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text): break
        start = max(0, end - overlap)
    return chunks

def keyword_score(chunk, question):
    words_q = re.findall(r"\w+", question.lower())
    words_c = re.findall(r"\w+", chunk.lower())
    return sum(1 for w in words_c if w in set(words_q))

def pick_relevant_chunks(notes_text, question, top_k=3):
    chunks = split_into_chunks(notes_text)
    if not chunks:
        return []
    ranked = sorted(chunks, key=lambda c: keyword_score(c, question), reverse=True)
    return ranked[:top_k]

def build_notes_prompt(context_chunks, question):
    context = "\n\n---\n\n".join(context_chunks)
    return f"""
You are a helpful study assistant.
Use ONLY the context below to answer the user's question. If the answer is not in the context, say "I don't know based on the notes."

Context:
{context}

Question: {question}

Answer:
"""

def parse_mcq_text(mcq_text):
    questions = []
    q_blocks = re.split(r"\nQ\d+\.", mcq_text)
    for block in q_blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        question_text = lines[0].strip()
        options, answer = [], None
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