# ── Model ────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"

# ── Tension curve — replaces difficulty presets ───────────────────────────────
#
# One fixed structure. Every game has the same three-act shape:
#
#   Act 1 — Discovery     (turns  1–5)   suspects cooperative, clues flow freely
#   Act 2 — Pressure      (turns  6–9)   Rahim makes his wrong move at turn 6,
#                                         suspects start clamming up after 4 Qs
#   Act 3 — Climax        (turns 10–15)  breaking evidence drops at turn 10,
#                                         Rahim closes in, accusation window opens
#
# The player can accuse at any point but the "deduction board" gate means
# they need to have built a case first.

TENSION_CURVE = {
    "max_turns": 15,

    # Turn at which Rahim makes his (wrong) accusation — misled by the red herring
    "rahim_wrong_turn": 6,

    # Turn at which breaking evidence (CCTV / phone record) auto-drops
    "breaking_evidence_turn": 10,

    # Turn at which Rahim correctly solves the case (player loses)
    "rahim_solves_turn": 15,

    # Questions per suspect before they become cagey / defensive
    "cagey_after": 4,

    # Every N turns Rahim drops a cadence comment (not on milestone turns)
    "rahim_cadence": 3,

    # Act labels for UI display
    "acts": {
        (1, 5):  {"label": "Act I — Discovery",  "colour": "#4a9", "icon": "🔍"},
        (6, 9):  {"label": "Act II — Pressure",  "colour": "#c84", "icon": "⚠️"},
        (10, 15): {"label": "Act III — Climax",   "colour": "#c44", "icon": "🔥"},
    },
}

def get_act(turn: int) -> dict:
    """Return the current act metadata for a given turn number."""
    for (start, end), meta in TENSION_CURVE["acts"].items():
        if start <= turn <= end:
            return meta
    return {"label": "Investigation", "colour": "#888", "icon": "🔍"}