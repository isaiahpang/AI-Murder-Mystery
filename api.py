import streamlit as st
from groq import Groq

from config import TENSION_CURVE
from prompts import (
    build_case_generation_prompt,
    CLUE_EXTRACTION_PROMPT,
    build_rahim_milestone_prompt,
    RAHIM_COMMENTARY_PROMPT,
    build_rahim_interrogation_prompt,
    RAHIM_REACTION_PROMPT,
    RAHIM_WRONG_ACCUSATION_FOLLOWUP_PROMPT,
    build_suspect_prompt,
    SUGGESTED_QUESTIONS_PROMPT,
    build_breaking_evidence_prompt,
    build_deduction_evaluation_prompt,
)
from utils import safe_parse_json

# ── Helpers ──────────────────────────────────────────────────────────────────

def _tc() -> dict:
    """Return the tension curve config."""
    return TENSION_CURVE

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

def _falsely_accused_index() -> int | None:
    """Return the index of the suspect Rahim falsely accused, or None."""
    rahim_accused = st.session_state.get("rahim_accused", "")
    if not rahim_accused:
        return None
    case = st.session_state.case
    killer_index = case["killer_index"]
    for i, s in enumerate(case["suspects"]):
        if s["name"] == rahim_accused and i != killer_index:
            return i
    return None

# ── Case generation ───────────────────────────────────────────────────────────

def generate_case(client: Groq) -> dict:
    """Call Groq to generate a new Singapore murder mystery case as JSON."""
    prompt = build_case_generation_prompt()
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
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
    cagey_after = _tc()["cagey_after"]

    # Check if this suspect was falsely accused by Rahim
    falsely_accused = (_falsely_accused_index() == suspect_index)

    # Collect Rahim's prior questions to this suspect for cross-awareness
    rahim_prior = [
        entry["rahim_question"]
        for entry in st.session_state.get("rahim_interrogations", {}).get(str(suspect_index), [])
    ]

    messages = (
        [{"role": "system", "content": build_suspect_prompt(
            suspect, case, is_killer, questions_asked, cagey_after,
            falsely_accused=falsely_accused,
            rahim_prior_questions=rahim_prior,
        )}]
        + history
        + [{"role": "user", "content": question}]
    )
    try:
        response = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=messages, temperature=0.8, max_tokens=300
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
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
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
    tc = _tc()
    wrong_turn = tc["rahim_wrong_turn"]
    solves_turn = tc["rahim_solves_turn"]

    if turn not in [wrong_turn, solves_turn]:
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
{'Correct answer: ' + killer_name if turn == solves_turn else f'WRONG accusation turn — accuse {rh_suspect_name} based on the red herring. Do NOT accuse {killer_name}.'}

Player interrogation transcripts:
{_build_transcripts(case)}
"""
    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": build_rahim_milestone_prompt(wrong_turn, solves_turn)},
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
    tc = _tc()
    cadence = tc["rahim_cadence"]
    wrong_turn = tc["rahim_wrong_turn"]
    solves_turn = tc["rahim_solves_turn"]

    if turn % cadence != 0 or turn in [wrong_turn, solves_turn] or turn == 0:
        return None

    case = st.session_state.case
    rahim_history = st.session_state.get("rahim_history", [])

    messages = [{"role": "system", "content": RAHIM_COMMENTARY_PROMPT}]
    messages += rahim_history
    messages.append({"role": "user", "content": f"""
Case: {case['title']}
Setting: {case['setting']}
Turn: {turn} of {solves_turn}
Player interrogation transcripts:
{_build_transcripts(case)}
"""})

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=messages, temperature=0.9, max_tokens=150
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        msg = parsed.get("message") if parsed else None
        if msg:
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

    prior = [
        entry["rahim_question"]
        for entry in st.session_state.get("rahim_interrogations", {}).get(str(suspect_index), [])
    ]
    turn = st.session_state.get("turn", 0)

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
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
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
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
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
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

# ── Cross-examination ─────────────────────────────────────────────────────────

def cross_examine_suspect(client: Groq, suspect_index: int, claim: str) -> dict:
    """Confront a suspect with a specific claim made by someone else."""
    from prompts import CROSS_EXAMINE_PROMPT
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    history = st.session_state.histories[suspect_index]
    questions_asked = len(history) // 2
    cagey_after = _tc()["cagey_after"]

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": CROSS_EXAMINE_PROMPT},
                {"role": "user", "content": (
                    f"Suspect: {suspect['name']}\n"
                    f"Personality: {suspect['personality']}\n"
                    f"Their alibi: {suspect['alibi']}\n"
                    f"Are they guilty: {'YES' if is_killer else 'NO'}\n"
                    f"Times questioned so far: {questions_asked}\n\n"
                    f"Claim being confronted with:\n{claim}"
                )}
            ],
            temperature=0.85,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.histories[suspect_index].append({
                "role": "user",
                "content": f"[Confrontation] {claim}"
            })
            st.session_state.histories[suspect_index].append({
                "role": "assistant",
                "content": parsed.get("response", "")
            })
            new_clue_text = parsed.get("new_clue", "").strip()
            if new_clue_text:
                clues = st.session_state.setdefault("clues", [])
                clues.append({
                    "text": new_clue_text,
                    "type": "contradiction",
                    "links_to_suspect": suspect["name"],
                    "source": "confrontation",
                })
        return parsed or {}
    except Exception as e:
        return {"response": f"[Error: {e}]", "new_clue": ""}

# ── Alibi challenge ───────────────────────────────────────────────────────────

def challenge_alibi(client: Groq, suspect_index: int) -> dict:
    """Press a suspect hard on their alibi, forcing them to provide verifiable detail."""
    from prompts import ALIBI_CHALLENGE_PROMPT
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": ALIBI_CHALLENGE_PROMPT},
                {"role": "user", "content": (
                    f"Suspect: {suspect['name']}\n"
                    f"Personality: {suspect['personality']}\n"
                    f"Stated alibi: {suspect['alibi']}\n"
                    f"Are they guilty: {'YES' if is_killer else 'NO'}\n"
                    f"Alibi flaw (if guilty): {suspect.get('alibi_contradiction', 'N/A')}\n"
                    f"Setting: {case['setting']}"
                )}
            ],
            temperature=0.85,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.histories[suspect_index].append({
                "role": "user",
                "content": "[Alibi Challenge] Prove your alibi. Give me something specific — a name, a time, a receipt. Something I can verify."
            })
            st.session_state.histories[suspect_index].append({
                "role": "assistant",
                "content": parsed.get("response", "")
            })
            detail = parsed.get("detail_provided", "").strip()
            ctype = "alibi" if detail and not parsed.get("is_evasive") else "contradiction"
            clue_text = detail if detail else f"{suspect['name']} could not provide a verifiable alibi detail."
            st.session_state.setdefault("clues", []).append({
                "text": clue_text,
                "type": ctype,
                "links_to_suspect": suspect["name"],
                "source": "alibi_challenge",
            })
        return parsed or {}
    except Exception as e:
        return {"response": f"[Error: {e}]", "detail_provided": "", "is_evasive": True}

# ── Physical clue investigation ───────────────────────────────────────────────

def investigate_physical_clue(client: Groq, clue_text: str) -> dict:
    """Send a physical clue for forensic follow-up analysis."""
    from prompts import INVESTIGATE_CLUE_PROMPT
    case = st.session_state.case

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": INVESTIGATE_CLUE_PROMPT},
                {"role": "user", "content": (
                    f"Case: {case['title']}\n"
                    f"Setting: {case['setting']}\n"
                    f"Victim: {case['victim']['name']}\n"
                    f"Suspects: {', '.join(s['name'] for s in case['suspects'])}\n\n"
                    f"Physical clue to investigate:\n{clue_text}"
                )}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            suspect_link = parsed.get("points_to_suspect", "")
            st.session_state.setdefault("clues", []).append({
                "text": f"[Forensics] {parsed.get('finding', '')}",
                "type": "physical",
                "links_to_suspect": suspect_link,
                "source": "forensic",
            })
        return parsed or {}
    except Exception as e:
        return {"finding": f"[Error: {e}]", "corroborates": False, "points_to_suspect": ""}

# ── Witness call ──────────────────────────────────────────────────────────────

def call_witness(client: Groq, suspect_index: int) -> dict:
    """Call a one-time NPC witness who can confirm or contradict a suspect's alibi."""
    from prompts import WITNESS_PROMPT
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": WITNESS_PROMPT},
                {"role": "user", "content": (
                    f"Case setting: {case['setting']}\n"
                    f"Suspect: {suspect['name']}\n"
                    f"Their stated alibi: {suspect['alibi']}\n"
                    f"Should this witness CONFIRM or CONTRADICT the alibi: "
                    f"{'CONTRADICT — the suspect is the killer and the alibi is false' if is_killer else 'CONFIRM — the suspect is innocent and was where they said'}\n"
                    f"Alibi flaw if killer: {suspect.get('alibi_contradiction', '')}"
                )}
            ],
            temperature=0.9,
            max_tokens=400,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.setdefault("clues", []).append({
                "text": f"[Witness: {parsed.get('witness_name','')}] {parsed.get('new_clue','')}",
                "type": "witness",
                "links_to_suspect": parsed.get("suspect_name", suspect["name"]),
                "source": "witness",
            })
            st.session_state.witness_used = True
        return parsed or {}
    except Exception as e:
        return {"witness_name": "Unknown", "witness_statement": f"[Error: {e}]",
                "confirms_alibi": True, "suspect_name": suspect["name"], "new_clue": ""}

# ── Breaking evidence (Act III auto-drop) ─────────────────────────────────────

def trigger_breaking_evidence(client: Groq) -> dict | None:
    """
    Called at the breaking_evidence_turn. Dramatises the case's pre-generated
    breaking_evidence and adds it to the clue board.
    Only fires once per game.
    """
    if st.session_state.get("breaking_evidence_triggered"):
        return None

    case = st.session_state.case
    breaking_evidence = case.get("breaking_evidence")
    if not breaking_evidence:
        return None

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": build_breaking_evidence_prompt(breaking_evidence, case)},
                {"role": "user", "content": "Deliver the breaking evidence update."}
            ],
            temperature=0.8,
            max_tokens=250,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            # Add as a high-priority physical clue
            suspect_link = parsed.get("points_to_suspect", "")
            st.session_state.setdefault("clues", []).append({
                "text": f"[BREAKING] {breaking_evidence.get('description', '')}",
                "type": "physical",
                "links_to_suspect": suspect_link,
                "source": "breaking_evidence",
            })
            st.session_state.breaking_evidence_triggered = True
        return parsed
    except Exception:
        return None

# ── Deduction board — evaluate player's reasoning ────────────────────────────

def evaluate_deduction(client: Groq, accused_name: str, player_reasoning: str) -> dict:
    """
    Evaluate the logical strength of the player's case before they formally accuse.
    Returns verdict (solid/shaky/weak), feedback, missing pieces, and ready_to_accuse flag.
    """
    case = st.session_state.case
    clues = st.session_state.get("clues", [])

    try:
        result = client.chat.completions.create(
            model=st.session_state.get("MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {"role": "system", "content": build_deduction_evaluation_prompt(
                    case, clues, player_reasoning, accused_name
                )},
                {"role": "user", "content": "Evaluate this case."}
            ],
            temperature=0.5,
            max_tokens=400,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed or {"verdict": "weak", "feedback": "Could not evaluate.", "missing_pieces": [], "ready_to_accuse": False}
    except Exception as e:
        return {"verdict": "weak", "feedback": f"[Error: {e}]", "missing_pieces": [], "ready_to_accuse": False}