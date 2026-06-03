# ── Model ────────────────────────────────────────────────────────────────────
MODEL = "llama-3.3-70b-versatile"

# ── Difficulty presets ───────────────────────────────────────────────────────
DIFFICULTIES = {
    "Easy": {
        "max_turns": 15,
        "wrong_guess_turn": 8,
        "cagey_after": 5,
        "rahim_cadence": 4,
        "description": "More turns, obvious clues, Rahim starts late.",
    },
    "Medium": {
        "max_turns": 12,
        "wrong_guess_turn": 6,
        "cagey_after": 4,
        "rahim_cadence": 3,
        "description": "Balanced. Rahim makes his move at the halfway point.",
    },
    "Hard": {
        "max_turns": 8,
        "wrong_guess_turn": 3,
        "cagey_after": 3,
        "rahim_cadence": 2,
        "description": "Tight turn limit. Rahim is aggressive. Suspects clam up fast.",
    },
}

def get_difficulty(name: str) -> dict:
    """Return difficulty config by name, defaulting to Medium."""
    return DIFFICULTIES.get(name, DIFFICULTIES["Medium"])