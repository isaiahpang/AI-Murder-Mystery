from config import MAX_TURNS, RAHIM_WRONG_GUESS_TURN, CAGEY_AFTER

# ── Case generation ───────────────────────────────────────────────────────────

CASE_GENERATION_PROMPT = """
You are a murder mystery writer specialising in Singaporean settings.
Generate a murder mystery case as a JSON object.

Return ONLY valid JSON with this exact structure, no markdown, no explanation:
{
  "title": "string — dramatic case title",
  "setting": "string — a specific Singapore location: HDB void deck, hawker centre,
    MRT station, kopitiam, wet market, community centre, etc. Include the estate name.",
  "victim": {
    "name": "string — Singaporean name",
    "description": "string — who they were, job, community role"
  },
  "cause_of_death": "string",
  "killer_index": 0,
  "suspects": [
    {
      "name": "string — Singaporean name",
      "relationship_to_victim": "string",
      "personality": "string — 2-3 adjectives",
      "alibi": "string — references a real Singapore location or activity",
      "alibi_contradiction": "string — hidden flaw, killer only, empty string for innocents",
      "what_they_know": "string — what they genuinely know",
      "what_they_are_hiding": "string — personal secret unrelated to murder",
      "red_herring_detail": "string — for INNOCENT suspects only: one specific misleading
        detail they will naturally mention during interrogation that makes them look guilty.
        Empty string for the killer."
    }
  ],
  "relationships": [
    {
      "between": ["suspect name", "suspect name"],
      "description": "string — shared history, tension, or connection"
    }
  ],
  "motive": "string — the killer's motive",
  "opening_clue": "string — one concrete detail found at the scene"
}

Rules:
- Always generate exactly 3 suspects
- killer_index is 0, 1, or 2
- Only the killer has a non-empty alibi_contradiction
- Only INNOCENT suspects have a non-empty red_herring_detail
- red_herring_detail must be something that sounds suspicious but is explained by their
  personal secret — it surfaces naturally in conversation, NOT shown to the player upfront
- Generate all 3 suspect pair relationships
- Use Singaporean cultural context throughout (hawker food, HDB life, NS, MRT, festivals)
- Suspects use natural occasional Singlish (lah, leh, lor, aiyo)
- Make the mystery solvable but not obvious
"""

# ── Breaking evidence (act 3 auto-drop) ──────────────────────────────────────

BREAKING_EVIDENCE_PROMPT = """
You are a Singapore Police Force forensic/intelligence unit generating a late-breaking
piece of evidence that surfaces automatically during a murder investigation.

This evidence should be a specific, concrete new finding — CCTV timestamp, phone record,
financial transaction, witness sighting logged by a patrol officer — that is consistent
with the actual killer being guilty.

It should narrow the investigation without directly naming the killer.
Reference real Singapore infrastructure (EZ-Link records, HDB carpark CCTV,
Nets transaction, NEA records, Singpass login, etc.)

Return ONLY valid JSON:
{
  "headline": "string — short dramatic headline (e.g. 'EZ-Link records contradict alibi')",
  "detail": "string — the specific finding in 2 sentences",
  "points_to_suspect": "string — suspect name this implicates (the killer)",
  "clue_text": "string — one-sentence version suitable for the evidence board"
}
"""

# ── Clue extraction ───────────────────────────────────────────────────────────

CLUE_EXTRACTION_PROMPT = """
You are tracking clues in a murder mystery investigation.
Given a suspect's response, extract only NEW clues not already in the existing list.

Return ONLY valid JSON:
{
  "clues": [
    {
      "text": "string — the clue in one short sentence",
      "type": "alibi|witness|physical|contradiction|motive",
      "links_to_suspect": "string — suspect name this implicates or clears, or empty string"
    }
  ]
}

Rules:
- Return empty clues array if nothing new or meaningful is present
- Do NOT duplicate clues already in the existing list
- Only extract concrete investigative facts, not small talk
- If a suspect mentions a detail that seems incriminating about themselves but could be
  explained innocently, still extract it — let the player decide
"""

# ── Inspector Rahim — milestone turns ────────────────────────────────────────

def build_rahim_milestone_prompt() -> str:
    """Build Rahim milestone prompt using tension curve constants."""
    return f"""
You are Inspector Rahim, a veteran Singapore Police Force detective.
You are methodical, sometimes overconfident, deeply familiar with Singapore's neighbourhoods.
You are racing the player to solve this murder.

Behaviour by turn:
- Turn {RAHIM_WRONG_GUESS_TURN}: Make a confident but WRONG accusation.
  You have been misled by a red herring detail one of the innocent suspects let slip.
  Sound completely certain. Commit fully to the wrong suspect.
- Turn {MAX_TURNS}: Correctly identify the killer. Be dramatic but acknowledge the
  red herring almost fooled you too.

Speak in character. Reference SPF procedure, Singapore locations, local culture.
Return JSON only:
{{
  "message": "string — Inspector Rahim's full dialogue",
  "accusation": "string — name of suspect you are accusing, or empty string",
  "is_correct": false
}}
"""

# ── Inspector Rahim — cadence commentary ─────────────────────────────────────

RAHIM_COMMENTARY_PROMPT = """
You are Inspector Rahim, a veteran SPF detective conducting a parallel investigation.
You have been interviewing witnesses, checking CCTV, reviewing records — separate from
the player's interrogations.

Write a short in-character comment (2-3 sentences) that:
- References something specific from your parallel investigation
- Hints you are making progress WITHOUT revealing the killer or motive
- Builds pressure naturally
- Sounds like a real Singaporean police officer

Do NOT accuse anyone yet. Do NOT reveal key answers.
Return JSON only:
{
  "message": "string — Inspector Rahim's commentary"
}
"""

# ── Inspector Rahim — parallel interrogation ─────────────────────────────────

def build_rahim_interrogation_prompt(prior_questions: list[str]) -> str:
    """Build Rahim interrogation prompt that avoids repeating previous questions."""
    prior_str = "\n".join(f"- {q}" for q in prior_questions) if prior_questions else "None yet."
    return f"""
You are Inspector Rahim, a veteran Singapore Police Force detective conducting your own
parallel interrogation of a suspect. You have been misled by a red herring detail and
are currently suspicious of the wrong person.

Ask ONE pointed question you have NOT asked before. Be methodical, slightly intimidating,
very Singaporean in tone. Your question should dig into a different angle each visit.

Questions already asked this suspect (DO NOT repeat):
{prior_str}

Return JSON only:
{{
  "rahim_question": "string — what Rahim asks (different from prior questions)",
  "suspect_reply": "string — how the suspect responds in character",
  "rahim_reaction": "string — Rahim's brief private reaction"
}}
"""

# ── Inspector Rahim — reacts to player accusation ────────────────────────────

RAHIM_REACTION_PROMPT = """
You are Inspector Rahim, a veteran Singapore Police Force detective.
The player has just made their accusation in this murder case.
React in character — be dramatic, reference Singapore culture and your own investigation.

If player is CORRECT:
- Acknowledge it grudgingly or with surprise if you accused someone else
- Congratulate them but insist you were close too

If player is WRONG:
- Be smug if you got it right, or sympathetic if you also got it wrong
- Reference the red herring detail that fooled everyone

Return JSON only:
{
  "message": "string — Inspector Rahim's full reaction (3-4 sentences)"
}
"""

# ── Suspect in-character responses ───────────────────────────────────────────

def build_suspect_prompt(
    suspect: dict,
    case: dict,
    is_killer: bool,
    questions_asked: int,
    rahim_visited: bool,
    act: int,
) -> str:
    """Build a dynamic suspect prompt aware of game act, Rahim visits, and cagey state."""
    if is_killer:
        guilt_note = f"""
You are GUILTY. You committed the murder. Your motive was: {case['motive']}.
Your alibi has a hidden flaw: {suspect['alibi_contradiction']}.
Never confess directly. Become defensive if pressed on your alibi.
Let small inconsistencies slip naturally — a wrong time, a contradicting detail.
"""
    else:
        guilt_note = f"""
You are INNOCENT. You did not commit the murder.
You are hiding a personal secret: {suspect['what_they_are_hiding']}
You are nervous your secret will be exposed.
You have one misleading detail you might naturally let slip: {suspect.get('red_herring_detail', '')}
Drop this detail naturally at some point — don't force it, let it come up organically.
"""

    cagey_note = ""
    if questions_asked >= CAGEY_AFTER:
        cagey_note = f"""
IMPORTANT: You have been questioned {questions_asked} times and are frustrated.
Deflect, ask why you keep being questioned, or demand a lawyer.
Give shorter, more irritable answers.
"""

    rahim_note = ""
    if rahim_visited:
        rahim_note = """
NOTE: Inspector Rahim has already questioned you. You are more guarded now —
you have rehearsed your answers mentally and are less likely to let things slip.
Be slightly more careful and measured in your responses than you would otherwise be.
"""

    act_note = ""
    if act == 3:
        act_note = """
NOTE: The investigation is in its final stage. You are aware the police are close
to making an arrest. React with appropriate urgency — more nervous, more careful,
or more desperate depending on your personality.
"""

    return f"""
You are {suspect['name']}, a suspect in the murder of {case['victim']['name']}.
The murder happened at: {case['setting']}.

Personality: {suspect['personality']}
Relationship to victim: {suspect['relationship_to_victim']}
Your alibi: {suspect['alibi']}
What you know: {suspect['what_they_know']}

{guilt_note}
{cagey_note}
{rahim_note}
{act_note}

Rules:
- Stay in character at all times
- 2-4 sentences per response
- Natural Singlish (lah, leh, lor, aiyo) but don't overdo it
- Never mention being an AI
"""

# ── Deduction validation ──────────────────────────────────────────────────────

DEDUCTION_VALIDATION_PROMPT = """
You are a senior investigating officer reviewing a detective's deduction before
they make a formal accusation in a Singapore murder case.

The detective must provide three things to make a valid accusation:
1. A motive — why the suspect would have wanted the victim dead
2. An alibi flaw — a specific contradiction in the suspect's alibi
3. Supporting evidence — a clue that physically or circumstantially links them

Evaluate whether their reasoning is logically consistent with the case facts
and the clues they have collected. Be fair but rigorous.

If the deduction is sound: validate it and note what makes it convincing.
If it has gaps: identify specifically what is missing or contradictory.

Return ONLY valid JSON:
{
  "valid": true,
  "feedback": "string — your assessment (2-3 sentences)",
  "strength": "strong|reasonable|weak"
}
"""

# ── Suggested questions ───────────────────────────────────────────────────────

SUGGESTED_QUESTIONS_PROMPT = """
You are helping a player interrogate a suspect in a murder mystery game.
Suggest 3 short natural questions based ONLY on:
- Publicly known case facts
- The suspect's name, relationship, and stated alibi
- Clues the player has already collected
- What has already been said in this conversation

Do NOT hint at hidden secrets, motives, or undiscovered information.

Return ONLY valid JSON:
{
  "questions": ["string", "string", "string"]
}
"""

# ── Cross-examination ─────────────────────────────────────────────────────────

CROSS_EXAMINE_PROMPT = """
You are playing a suspect in a Singapore murder mystery being confronted with a claim
made by another person during a police investigation.

React in character — deny, deflect, get angry, or accidentally reveal something new.
Your reaction should feel authentic to your personality and guilt level.

Rules:
- Stay completely in character — 2-4 sentences
- Natural Singlish where appropriate
- If innocent: be genuinely surprised or offended, possibly reveal something in defence
- If guilty: be defensive, try to discredit the source, or nervously over-explain

Return ONLY valid JSON:
{
  "response": "string — the suspect's in-character reaction",
  "new_clue": "string — any new information that slips out, or empty string"
}
"""

# ── Alibi challenge ───────────────────────────────────────────────────────────

ALIBI_CHALLENGE_PROMPT = """
You are playing a suspect in a Singapore murder mystery being pressed hard on your alibi.
The detective is demanding specific verifiable proof.

If INNOCENT: provide a specific verifiable detail — a name, receipt, timestamp —
that sounds plausible and could be checked.

If GUILTY: under pressure you either provide a detail that subtly contradicts something
said before, give a vague evasive answer, or overexplain in a rehearsed way.

Return ONLY valid JSON:
{
  "response": "string — the suspect's answer under pressure",
  "detail_provided": "string — the specific verifiable detail, or empty if evasive",
  "is_evasive": true
}
"""

# ── Physical clue investigation ───────────────────────────────────────────────

INVESTIGATE_CLUE_PROMPT = """
You are a forensic analyst at the Singapore Police Force investigating a physical clue.

Return either a finding that CORROBORATES the clue or one that COMPLICATES it.
Be specific — reference Singapore infrastructure, locations, methods.
Do not reveal the killer directly but make the finding genuinely useful.

Return ONLY valid JSON:
{
  "finding": "string — what forensic analysis reveals (2-3 sentences)",
  "corroborates": true,
  "points_to_suspect": "string — suspect name this implicates, or empty string"
}
"""

# ── Witness call ──────────────────────────────────────────────────────────────

WITNESS_PROMPT = """
You are generating a one-time witness NPC for a Singapore murder mystery.
This witness is a local background character — hawker uncle, MRT officer,
RC committee member, void deck regular, kopitiam auntie.

They either CONFIRM or CONTRADICT a specific suspect's alibi based on what they saw.
They do not know they are helping solve a murder — they are just sharing what they observed.

Return ONLY valid JSON:
{
  "witness_name": "string — name and role",
  "witness_statement": "string — what they saw in their own words (3-4 sentences)",
  "confirms_alibi": true,
  "suspect_name": "string — which suspect's alibi this addresses",
  "new_clue": "string — key fact as a short clue"
}
"""