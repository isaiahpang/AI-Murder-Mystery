import streamlit as st
from groq import Groq

from config import MODEL, MAX_TURNS, AI_WRONG_GUESS_TURN, RAHIM_CADENCE
from prompts import (
    CASE_GENERATION_PROMPT,
    CLUE_EXTRACTION_PROMPT,
    AI_DETECTIVE_PROMPT,
    RAHIM_COMMENTARY_PROMPT,
    SUGGESTED_QUESTIONS_PROMPT,
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
    questions_asked = len(history) // 2

    messages = (
        [{"role": "system", "content": build_suspect_prompt(suspect, case, is_killer, questions_asked)}]
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
    """Extract only NEW clues from a response, skipping duplicates of existing clues."""
    existing = st.session_state.get("clues", [])
    existing_summary = "\n".join(f"- {c['text']}" for c in existing) or "None yet."

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": CLUE_EXTRACTION_PROMPT},
                {"role": "user", "content": (
                    f"Suspect: {suspect_name}\n"
                    f"Response: {response_text}\n\n"
                    f"Existing clues (do not duplicate):\n{existing_summary}"
                )}
            ],
            temperature=0.2,
            max_tokens=400,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("clues", []) if parsed else []
    except Exception:
        return []

def get_ai_detective_update(client: Groq, turn: int) -> dict | None:
    """Return Inspector Rahim's milestone update (wrong guess or solve), or None."""
    if turn not in [AI_WRONG_GUESS_TURN, MAX_TURNS]:
        return None

    case = st.session_state.case
    killer_name = case["suspects"][case["killer_index"]]["name"]
    transcripts = _build_transcripts(case)

    user_content = f"""
Case: {case['title']}
Setting: {case['setting']}
Victim: {case['victim']['name']}
Suspects: {', '.join(s['name'] for s in case['suspects'])}
Current turn: {turn}
{'Correct answer: ' + killer_name if turn == MAX_TURNS else 'Do NOT accuse the correct killer yet.'}

Transcripts:
{transcripts}
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

def get_rahim_commentary(client: Groq, turn: int) -> str | None:
    """Return a short Rahim comment on cadence turns, or None if not a cadence turn."""
    if turn % RAHIM_CADENCE != 0 or turn in [AI_WRONG_GUESS_TURN, MAX_TURNS] or turn == 0:
        return None

    case = st.session_state.case
    transcripts = _build_transcripts(case)

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RAHIM_COMMENTARY_PROMPT},
                {"role": "user", "content": f"""
Case: {case['title']}
Setting: {case['setting']}
Turn: {turn} of {MAX_TURNS}
Transcripts so far:
{transcripts}
"""}
            ],
            temperature=0.9,
            max_tokens=150,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("message") if parsed else None
    except Exception:
        return None

def get_suggested_questions(client: Groq, suspect_index: int) -> list[str]:
    """Generate 3 suggested questions based only on what the player currently knows."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    clues = st.session_state.get("clues", [])
    history = st.session_state.histories[suspect_index]

    known_clues = "\n".join(f"- {c['text']}" for c in clues) or "None yet."
    conversation_so_far = "\n".join(
        f"{'Player' if m['role'] == 'user' else suspect['name']}: {m['content']}"
        for m in history
    ) or "No questions asked yet."

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SUGGESTED_QUESTIONS_PROMPT},
                {"role": "user", "content": f"""
Case facts the player knows:
- Victim: {case['victim']['name']} ({case['victim']['description']})
- Location: {case['setting']}
- Cause of death: {case['cause_of_death']}
- Opening clue: {case.get('opening_clue', '')}

Suspect: {suspect['name']} — {suspect['relationship_to_victim']}
Stated alibi: {suspect['alibi']}

Clues collected:
{known_clues}

Conversation so far:
{conversation_so_far}
"""}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("questions", []) if parsed else []
    except Exception:
        return []

def _build_transcripts(case: dict) -> str:
    """Build a readable transcript of all interrogations so far."""
    transcripts = []
    for i, suspect in enumerate(case["suspects"]):
        history = st.session_state.histories[i]
        if history:
            lines = [
                f"  {'Player' if m['role'] == 'user' else suspect['name']}: {m['content']}"
                for m in history
            ]
            transcripts.append(f"Interrogation of {suspect['name']}:\n" + "\n".join(lines))
    return "\n\n".join(transcripts) if transcripts else "No interrogations yet."