import streamlit as st
from groq import Groq

from config import MODEL, MAX_TURNS, AI_WRONG_GUESS_TURN
from prompts import (
    CASE_GENERATION_PROMPT,
    CLUE_EXTRACTION_PROMPT,
    AI_DETECTIVE_PROMPT,
    build_suspect_prompt,
)
from utils import safe_parse_json

def generate_case(client: Groq) -> dict:
    """Call Groq to generate a new Singapore murder mystery case as JSON."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": CASE_GENERATION_PROMPT},
                    {"role": "user", "content": "Generate a new Singapore murder mystery case."}
                ],
                temperature=1.0,
                max_tokens=2000,
            )
            parsed = safe_parse_json(response.choices[0].message.content)
            if parsed:
                return parsed
        except Exception:
            pass

        if attempt == 2:
            st.error("Failed to generate a valid case after 3 attempts. Please try again.")
            st.stop()
    return {}

def interrogate_suspect(client: Groq, suspect_index: int, question: str) -> str:
    """Send a question to a suspect and return their in-character response."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    history = st.session_state.histories[suspect_index]

    messages = (
        [{"role": "system", "content": build_suspect_prompt(suspect, case, is_killer)}]
        + history
        + [{"role": "user", "content": question}]
    )

    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.8, max_tokens=300
        )
        reply = response.choices[0].message.content.strip()
        st.session_state.histories[suspect_index].append({"role": "user", "content": question})
        st.session_state.histories[suspect_index].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"[Error reaching suspect: {e}]"

def extract_clues(client: Groq, suspect_name: str, response_text: str) -> list:
    """Extract clues from a suspect's response. Returns empty list on any failure."""
    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": CLUE_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Suspect: {suspect_name}\nResponse: {response_text}"}
            ],
            temperature=0.2,
            max_tokens=400,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("clues", []) if parsed else []
    except Exception:
        return []

def get_ai_detective_update(client: Groq, turn: int) -> dict | None:
    """Return Inspector Rahim's update at milestone turns, or None otherwise."""
    if turn not in [AI_WRONG_GUESS_TURN, MAX_TURNS]:
        return None

    case = st.session_state.case
    killer_name = case["suspects"][case["killer_index"]]["name"]

    # Build transcript summary for Rahim to reason over
    transcripts = []
    for i, suspect in enumerate(case["suspects"]):
        history = st.session_state.histories[i]
        if history:
            lines = [
                f"  {'Player' if m['role'] == 'user' else suspect['name']}: {m['content']}"
                for m in history
            ]
            transcripts.append(f"Interrogation of {suspect['name']}:\n" + "\n".join(lines))

    user_content = f"""
Case: {case['title']}
Setting: {case['setting']}
Victim: {case['victim']['name']}
Suspects: {', '.join(s['name'] for s in case['suspects'])}
Current turn: {turn}
{'Correct answer (for turn ' + str(MAX_TURNS) + ' only): ' + killer_name if turn == MAX_TURNS else 'Do NOT accuse the correct killer yet.'}

Transcripts so far:
{''.join(transcripts) if transcripts else 'No interrogations yet.'}
"""

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": AI_DETECTIVE_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        return safe_parse_json(result.choices[0].message.content)
    except Exception:
        return None