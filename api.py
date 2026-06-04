import streamlit as st
from groq import Groq

from config import MODEL, get_difficulty
from prompts import (
    build_case_generation_prompt,
    CLUE_EXTRACTION_PROMPT,
    build_rahim_milestone_prompt,
    RAHIM_COMMENTARY_PROMPT,
    build_rahim_interrogation_prompt,
    RAHIM_REACTION_PROMPT,
    build_suspect_prompt,
    SUGGESTED_QUESTIONS_PROMPT,
)
from utils import safe_parse_json

# ── Helpers ──────────────────────────────────────────────────────────────────

def _diff() -> dict:
    """Return the current difficulty config from session state."""
    return get_difficulty(st.session_state.get("difficulty", "Medium"))

def _build_transcripts(case: dict) -> str:
    """Build a readable transcript of all player interrogations so far."""
    parts = []
    for i, suspect in enumerate(case["suspects"]):
        history = st.session_state.histories[i]
        if history:
            lines = [
                f"  {'Player' if m['role'] == 'user' else suspect['name']}: {m['content']}"
                for m in history
            ]
            parts.append(f"Interrogation of {suspect['name']}:\n" + "\n".join(lines))
    return "\n\n".join(parts) if parts else "No interrogations yet."

# ── Case generation ───────────────────────────────────────────────────────────

def generate_case(client: Groq, difficulty: str) -> dict:
    """Call Groq to generate a new Singapore murder mystery case as JSON."""
    prompt = build_case_generation_prompt(difficulty)
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt},
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

# ── Suspect interrogation ────────────────────────────────────────────────────

def interrogate_suspect(client: Groq, suspect_index: int, question: str) -> str:
    """Send a player question to a suspect and return their in-character response."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    history = st.session_state.histories[suspect_index]
    questions_asked = len(history) // 2
    cagey_after = _diff()["cagey_after"]

    messages = (
        [{"role": "system", "content": build_suspect_prompt(
            suspect, case, is_killer, questions_asked, cagey_after
        )}]
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

# ── Clue extraction ──────────────────────────────────────────────────────────

def extract_clues(client: Groq, suspect_name: str, response_text: str) -> list:
    """Extract only NEW clues from a response, skipping existing ones."""
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

# ── Inspector Rahim — milestone (wrong guess / solve) ────────────────────────

def get_ai_detective_update(client: Groq, turn: int) -> dict | None:
    """Return Rahim's milestone update at wrong-guess or solve turns, else None."""
    diff = _diff()
    wrong_turn = diff["wrong_guess_turn"]
    max_turns = diff["max_turns"]

    if turn not in [wrong_turn, max_turns]:
        return None

    case = st.session_state.case
    killer_name = case["suspects"][case["killer_index"]]["name"]
    red_herring = case.get("red_herring", {})
    rh_suspect_idx = red_herring.get("points_to_suspect_index", -1)
    rh_suspect_name = case["suspects"][rh_suspect_idx]["name"] if 0 <= rh_suspect_idx < 3 else ""

    user_content = f"""
Case: {case['title']}
Setting: {case['setting']}
Victim: {case['victim']['name']}
Suspects: {', '.join(s['name'] for s in case['suspects'])}
Red herring points to: {rh_suspect_name} ({red_herring.get('description', '')})
Current turn: {turn}
{'Correct answer: ' + killer_name if turn == max_turns else f'WRONG accusation turn — accuse {rh_suspect_name} based on the red herring. Do NOT accuse {killer_name}.'}

Player interrogation transcripts:
{_build_transcripts(case)}
"""
    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": build_rahim_milestone_prompt(wrong_turn, max_turns)},
                {"role": "user", "content": user_content}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        return safe_parse_json(result.choices[0].message.content)
    except Exception:
        return None

# ── Inspector Rahim — cadence commentary ─────────────────────────────────────

def get_rahim_commentary(client: Groq, turn: int) -> str | None:
    """Return a short Rahim comment on cadence turns, or None."""
    diff = _diff()
    cadence = diff["rahim_cadence"]
    wrong_turn = diff["wrong_guess_turn"]
    max_turns = diff["max_turns"]

    if turn % cadence != 0 or turn in [wrong_turn, max_turns] or turn == 0:
        return None

    case = st.session_state.case
    # Build Rahim's history for stateful commentary
    rahim_history = st.session_state.get("rahim_history", [])

    messages = [{"role": "system", "content": RAHIM_COMMENTARY_PROMPT}]
    messages += rahim_history
    messages.append({"role": "user", "content": f"""
Case: {case['title']}
Setting: {case['setting']}
Turn: {turn} of {max_turns}
Player interrogation transcripts:
{_build_transcripts(case)}
"""})

    try:
        result = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.9, max_tokens=150
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        msg = parsed.get("message") if parsed else None
        if msg:
            # Save to Rahim's own history for next call
            rahim_history.append({"role": "assistant", "content": msg})
            st.session_state.rahim_history = rahim_history
        return msg
    except Exception:
        return None

# ── Inspector Rahim — his own interrogation of a suspect ─────────────────────

def get_rahim_interrogation(client: Groq, suspect_index: int) -> dict | None:
    """Generate a fresh Rahim interrogation that evolves with each visit, never repeating questions."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    red_herring = case.get("red_herring", {})
    rh_idx = red_herring.get("points_to_suspect_index", -1)
    focus = (
        "This suspect is your PRIMARY focus — the red herring evidence points strongly to them."
        if suspect_index == rh_idx
        else "You are questioning this suspect as routine due diligence."
    )

    # Collect prior questions asked to this suspect to avoid repetition
    prior = [
        entry["rahim_question"]
        for entry in st.session_state.get("rahim_interrogations", {}).get(str(suspect_index), [])
    ]
    turn = st.session_state.get("turn", 0)

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": build_rahim_interrogation_prompt(prior)},
                {"role": "user", "content": f"""
Case: {case['title']}
Setting: {case['setting']}
Suspect: {suspect['name']} — {suspect['relationship_to_victim']}
Personality: {suspect['personality']}
Alibi: {suspect['alibi']}
Red herring: {red_herring.get('description', '')}
Investigation turn: {turn}
{focus}
{'This suspect is INNOCENT.' if not is_killer else 'This suspect is the KILLER — Rahim does not know this yet.'}
Player has asked this suspect {len(st.session_state.histories[suspect_index]) // 2} questions so far.
"""}
            ],
            temperature=0.9,
            max_tokens=350,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        # Append to list of all Rahim interrogations for this suspect
        if parsed:
            key = str(suspect_index)
            rahim_ints = st.session_state.setdefault("rahim_interrogations", {})
            rahim_ints.setdefault(key, []).append(parsed)
            st.session_state.rahim_interrogations = rahim_ints
        return parsed
    except Exception:
        return None

# ── Inspector Rahim — reacts to player accusation ────────────────────────────

def get_rahim_reaction(client: Groq, accused_index: int, player_correct: bool) -> str:
    """Get Rahim's in-character reaction to the player's accusation."""
    case = st.session_state.case
    accused = case["suspects"][accused_index]
    killer = case["suspects"][case["killer_index"]]
    rahim_accused = st.session_state.get("rahim_accused", "")
    rahim_was_correct = (rahim_accused == killer["name"])

    context = f"""
Player accused: {accused['name']} ({'CORRECT' if player_correct else 'WRONG'})
Actual killer: {killer['name']}
Rahim previously accused: {rahim_accused if rahim_accused else 'No accusation yet'}
Rahim was: {'correct' if rahim_was_correct else 'wrong'}
"""
    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RAHIM_REACTION_PROMPT},
                {"role": "user", "content": context}
            ],
            temperature=0.85,
            max_tokens=250,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("message", "") if parsed else ""
    except Exception:
        return ""

# ── Suggested questions ──────────────────────────────────────────────────────

def get_suggested_questions(client: Groq, suspect_index: int) -> list[str]:
    """Generate 3 suggested questions based only on what the player currently knows."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    clues = st.session_state.get("clues", [])
    history = st.session_state.histories[suspect_index]

    known_clues = "\n".join(f"- {c['text']}" for c in clues) or "None yet."
    conversation = "\n".join(
        f"{'Player' if m['role'] == 'user' else suspect['name']}: {m['content']}"
        for m in history
    ) or "No questions asked yet."

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SUGGESTED_QUESTIONS_PROMPT},
                {"role": "user", "content": f"""
Case facts:
- Victim: {case['victim']['name']} ({case['victim']['description']})
- Location: {case['setting']}
- Cause of death: {case['cause_of_death']}
- Opening clue: {case.get('opening_clue', '')}

Suspect: {suspect['name']} — {suspect['relationship_to_victim']}
Alibi: {suspect['alibi']}

Clues collected:
{known_clues}

Conversation so far:
{conversation}
"""}
            ],
            temperature=0.7,
            max_tokens=200,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("questions", []) if parsed else []
    except Exception:
        return []