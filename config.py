# ── Game configuration ───────────────────────────────────────────────────────
# Change these to tune difficulty and model behaviour

MODEL = "llama-3.3-70b-versatile"

MAX_TURNS = 12             # Inspector Rahim solves the case at this turn
AI_WRONG_GUESS_TURN = 6    # Inspector Rahim makes a wrong accusation at this turn
RAHIM_CADENCE = 3          # Inspector Rahim comments every N turns (between milestones)
CAGEY_AFTER = 4            # Suspect becomes evasive after this many questions