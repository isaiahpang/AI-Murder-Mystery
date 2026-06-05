import streamlit as st
from groq import Groq

from config import (
    MODEL, MAX_TURNS, CAGEY_AFTER, RAHIM_CADENCE,
    ACT2_START, ACT3_START, RAHIM_WRONG_GUESS_TURN, BREAKING_EVIDENCE_TURN,
)
from prompts import (
    CASE_GENERATION_PROMPT,
    BREAKING_EVIDENCE_PROMPT,
    CLUE_EXTRACTION_PROMPT,
    build_rahim_milestone_prompt,
    RAHIM_COMMENTARY_PROMPT,
    build_rahim_interrogation_prompt,
    RAHIM_REACTION_PROMPT,
    build_suspect_prompt,
    DEDUCTION_VALIDATION_PROMPT,
    SUGGESTED_QUESTIONS_PROMPT,
    CROSS_EXAMINE_PROMPT,
    ALIBI_CHALLENGE_PROMPT,
    INVESTIGATE_CLUE_PROMPT,
    WITNESS_PROMPT,
)
from utils import safe_parse_json

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_act() -> int:
    """Return current act (1, 2, or 3) based on turn count."""
    turn = st.session_state.get("turn", 0)
    if turn >= ACT3_START:
        return 3
    elif turn >= ACT2_START:
        return 2
    return 1


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


def _find_red_herring_suspect_name(case: dict) -> str:
    """
    Return the name of the red herring suspect (innocent with a red_herring_detail).
    Uses explicit index comparison to avoid O(n²) .index() calls.
    Falls back to the first non-killer suspect if none is flagged.
    """
    killer_index = case["killer_index"]
    for i, s in enumerate(case["suspects"]):
        if i != killer_index and s.get("red_herring_detail"):
            return s["name"]
    # Fallback: first innocent suspect
    for i, s in enumerate(case["suspects"]):
        if i != killer_index:
            return s["name"]
    return case["suspects"][0]["name"]


# ── Case generation ───────────────────────────────────────────────────────────

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
        except Exception as e:
            if attempt == 2:
                st.error(f"Failed to generate a valid case after 3 attempts: {e}")
                st.stop()
    return {}


# ── Breaking evidence (act 3 auto-drop) ──────────────────────────────────────

def generate_breaking_evidence(client: Groq) -> dict | None:
    """Generate a late-breaking piece of evidence that drops automatically in act 3."""
    case = st.session_state.case
    killer = case["suspects"][case["killer_index"]]
    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": BREAKING_EVIDENCE_PROMPT},
                {"role": "user", "content": (
                    f"Case: {case['title']}\n"
                    f"Setting: {case['setting']}\n"
                    f"Victim: {case['victim']['name']}\n"
                    f"Killer: {killer['name']} (alibi flaw: {killer['alibi_contradiction']})\n"
                    f"Suspects: {', '.join(s['name'] for s in case['suspects'])}"
                )}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.setdefault("clues", []).append({
                "text": f"[BREAKING] {parsed.get('clue_text', '')}",
                "type": "physical",
                "links_to_suspect": parsed.get("points_to_suspect", ""),
                "source": "breaking",
            })
        return parsed
    except Exception:
        return None


# ── Suspect interrogation ─────────────────────────────────────────────────────

def interrogate_suspect(client: Groq, suspect_index: int, question: str) -> str:
    """Send a player question to a suspect and return their in-character response."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    history = st.session_state.histories[suspect_index]
    questions_asked = len(history) // 2
    rahim_visited = suspect_index in st.session_state.get("rahim_visited_suspects", set())
    act = _get_act()

    messages = (
        [{"role": "system", "content": build_suspect_prompt(
            suspect, case, is_killer, questions_asked, rahim_visited, act
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


# ── Clue extraction ───────────────────────────────────────────────────────────

def extract_clues(client: Groq, suspect_name: str, response_text: str) -> list:
    """Extract only NEW clues, skipping duplicates of existing ones."""
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


# ── Inspector Rahim — milestone ───────────────────────────────────────────────

def get_ai_detective_update(client: Groq, turn: int) -> dict | None:
    """Return Rahim's milestone update at wrong-guess or solve turns, else None."""
    if turn not in [RAHIM_WRONG_GUESS_TURN, MAX_TURNS]:
        return None

    case = st.session_state.case
    killer_name = case["suspects"][case["killer_index"]]["name"]
    rh_suspect_name = _find_red_herring_suspect_name(case)

    user_content = f"""
Case: {case['title']}
Setting: {case['setting']}
Victim: {case['victim']['name']}
Suspects: {', '.join(s['name'] for s in case['suspects'])}
Red herring suspect (innocent but looks guilty): {rh_suspect_name}
Current turn: {turn}
{'Correct answer: ' + killer_name if turn == MAX_TURNS else
 f'WRONG accusation turn — accuse {rh_suspect_name} based on the red herring. Do NOT accuse {killer_name}.'}

Player interrogation transcripts:
{_build_transcripts(case)}
"""
    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": build_rahim_milestone_prompt()},
                {"role": "user", "content": user_content}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed and parsed.get("accusation"):
            st.session_state.rahim_accused = parsed["accusation"]
            for i, s in enumerate(case["suspects"]):
                if s["name"] == parsed["accusation"]:
                    st.session_state.setdefault("rahim_visited_suspects", set()).add(i)
        return parsed
    except Exception:
        return None


# ── Inspector Rahim — cadence commentary ─────────────────────────────────────

def get_rahim_commentary(client: Groq, turn: int) -> str | None:
    """Return a Rahim comment on cadence turns between milestones, or None."""
    if (turn % RAHIM_CADENCE != 0
            or turn in [RAHIM_WRONG_GUESS_TURN, MAX_TURNS]
            or turn < ACT2_START):
        return None

    case = st.session_state.case
    rahim_history = st.session_state.get("rahim_history", [])

    messages = [{"role": "system", "content": RAHIM_COMMENTARY_PROMPT}]
    messages += rahim_history
    messages.append({"role": "user", "content": f"""
Case: {case['title']}
Setting: {case['setting']}
Turn: {turn} of {MAX_TURNS}
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
            rahim_history.append({"role": "assistant", "content": msg})
            st.session_state.rahim_history = rahim_history
        return msg
    except Exception:
        return None


# ── Inspector Rahim — parallel interrogation ─────────────────────────────────

def get_rahim_interrogation(client: Groq, suspect_index: int) -> dict | None:
    """Generate a fresh Rahim interrogation that evolves with each visit."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    rh_suspect_name = _find_red_herring_suspect_name(case)

    focus = (
        "This suspect is your PRIMARY focus — they let slip a detail that makes them look guilty."
        if suspect["name"] == rh_suspect_name
        else "You are questioning this suspect as routine due diligence."
    )

    prior = [
        entry["rahim_question"]
        for entry in st.session_state.get("rahim_interrogations", {}).get(str(suspect_index), [])
    ]

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
Turn: {st.session_state.get('turn', 0)}
{focus}
{'This suspect is INNOCENT.' if not is_killer else 'This suspect is the KILLER — Rahim does not know this yet.'}
Player has asked {len(st.session_state.histories[suspect_index]) // 2} questions so far.
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
            st.session_state.setdefault("rahim_visited_suspects", set()).add(suspect_index)
        return parsed
    except Exception:
        return None


# ── Inspector Rahim — reaction to player accusation ──────────────────────────

def get_rahim_reaction(client: Groq, accused_index: int, player_correct: bool) -> str:
    """Get Rahim's in-character reaction to the player's accusation."""
    case = st.session_state.case
    accused = case["suspects"][accused_index]
    killer = case["suspects"][case["killer_index"]]
    rahim_accused = st.session_state.get("rahim_accused", "")
    rahim_was_correct = (rahim_accused == killer["name"])

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": RAHIM_REACTION_PROMPT},
                {"role": "user", "content": (
                    f"Player accused: {accused['name']} "
                    f"({'CORRECT' if player_correct else 'WRONG'})\n"
                    f"Actual killer: {killer['name']}\n"
                    f"Rahim previously accused: {rahim_accused or 'No accusation yet'}\n"
                    f"Rahim was: {'correct' if rahim_was_correct else 'wrong'}"
                )}
            ],
            temperature=0.85,
            max_tokens=250,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed.get("message", "") if parsed else ""
    except Exception:
        return ""


# ── Deduction validation ──────────────────────────────────────────────────────

def validate_deduction(
    client: Groq,
    suspect_index: int,
    motive: str,
    alibi_flaw: str,
    evidence: str,
) -> dict:
    """Validate the player's deduction before allowing a formal accusation."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    clues = st.session_state.get("clues", [])
    clue_summary = "\n".join(f"- {c['text']}" for c in clues) or "No clues collected."

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": DEDUCTION_VALIDATION_PROMPT},
                {"role": "user", "content": (
                    f"Case: {case['title']}\n"
                    f"Suspect accused: {suspect['name']}\n"
                    f"Victim: {case['victim']['name']}\n\n"
                    f"Player's deduction:\n"
                    f"- Motive: {motive}\n"
                    f"- Alibi flaw: {alibi_flaw}\n"
                    f"- Supporting evidence: {evidence}\n\n"
                    f"Clues collected so far:\n{clue_summary}"
                )}
            ],
            temperature=0.4,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        return parsed or {"valid": False, "feedback": "Could not evaluate deduction.", "strength": "weak"}
    except Exception as e:
        return {"valid": False, "feedback": f"Error: {e}", "strength": "weak"}


# ── Suggested questions ───────────────────────────────────────────────────────

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
                {"role": "user", "content": (
                    f"Case facts:\n"
                    f"- Victim: {case['victim']['name']} ({case['victim']['description']})\n"
                    f"- Location: {case['setting']}\n"
                    f"- Cause of death: {case['cause_of_death']}\n"
                    f"- Opening clue: {case.get('opening_clue', '')}\n\n"
                    f"Suspect: {suspect['name']} — {suspect['relationship_to_victim']}\n"
                    f"Alibi: {suspect['alibi']}\n\n"
                    f"Clues collected:\n{known_clues}\n\n"
                    f"Conversation so far:\n{conversation}"
                )}
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
    """Confront a suspect with a claim made by someone else."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])
    questions_asked = len(st.session_state.histories[suspect_index]) // 2

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": CROSS_EXAMINE_PROMPT},
                {"role": "user", "content": (
                    f"Suspect: {suspect['name']}\n"
                    f"Personality: {suspect['personality']}\n"
                    f"Alibi: {suspect['alibi']}\n"
                    f"Guilty: {'YES' if is_killer else 'NO'}\n"
                    f"Times questioned: {questions_asked}\n\n"
                    f"Claim to confront with:\n{claim}"
                )}
            ],
            temperature=0.85,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.histories[suspect_index].append(
                {"role": "user", "content": f"[Confrontation] {claim}"}
            )
            st.session_state.histories[suspect_index].append(
                {"role": "assistant", "content": parsed.get("response", "")}
            )
            new_clue_text = parsed.get("new_clue", "").strip()
            if new_clue_text:
                st.session_state.setdefault("clues", []).append({
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
    """Press a suspect for a specific verifiable alibi detail."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ALIBI_CHALLENGE_PROMPT},
                {"role": "user", "content": (
                    f"Suspect: {suspect['name']}\n"
                    f"Personality: {suspect['personality']}\n"
                    f"Stated alibi: {suspect['alibi']}\n"
                    f"Guilty: {'YES' if is_killer else 'NO'}\n"
                    f"Alibi flaw: {suspect.get('alibi_contradiction', 'N/A')}\n"
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
                "content": "[Alibi Challenge] Prove your alibi. Give me something specific I can verify."
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
    """Send a physical clue for forensic follow-up."""
    case = st.session_state.case
    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": INVESTIGATE_CLUE_PROMPT},
                {"role": "user", "content": (
                    f"Case: {case['title']}\n"
                    f"Setting: {case['setting']}\n"
                    f"Victim: {case['victim']['name']}\n"
                    f"Suspects: {', '.join(s['name'] for s in case['suspects'])}\n\n"
                    f"Physical clue:\n{clue_text}"
                )}
            ],
            temperature=0.8,
            max_tokens=300,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.setdefault("clues", []).append({
                "text": f"[Forensics] {parsed.get('finding', '')}",
                "type": "physical",
                "links_to_suspect": parsed.get("points_to_suspect", ""),
                "source": "forensic",
            })
        return parsed or {}
    except Exception as e:
        return {"finding": f"[Error: {e}]", "corroborates": False, "points_to_suspect": ""}


# ── Witness call ──────────────────────────────────────────────────────────────

def call_witness(client: Groq, suspect_index: int) -> dict:
    """Call a one-time NPC witness who confirms or contradicts a suspect's alibi."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])

    try:
        result = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": WITNESS_PROMPT},
                {"role": "user", "content": (
                    f"Setting: {case['setting']}\n"
                    f"Suspect: {suspect['name']}\n"
                    f"Alibi: {suspect['alibi']}\n"
                    f"Should witness CONFIRM or CONTRADICT: "
                    f"{'CONTRADICT — killer, alibi is false' if is_killer else 'CONFIRM — innocent'}\n"
                    f"Alibi flaw: {suspect.get('alibi_contradiction', '')}"
                )}
            ],
            temperature=0.9,
            max_tokens=400,
        )
        parsed = safe_parse_json(result.choices[0].message.content)
        if parsed:
            st.session_state.setdefault("clues", []).append({
                "text": f"[Witness: {parsed.get('witness_name', '')}] {parsed.get('new_clue', '')}",
                "type": "witness",
                "links_to_suspect": parsed.get("suspect_name", suspect["name"]),
                "source": "witness",
            })
            st.session_state.witness_used = True
        return parsed or {}
    except Exception as e:
        return {
            "witness_name": "Unknown",
            "witness_statement": f"[Error: {e}]",
            "confirms_alibi": True,
            "suspect_name": suspect["name"],
            "new_clue": "",
        }