# ── Model ────────────────────────────────────────────────────────────────────
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ── Core game constants ───────────────────────────────────────────────────────
MAX_TURNS = 12          # Total turns before Rahim solves it
CAGEY_AFTER = 4         # Questions before a suspect gets uncooperative
RAHIM_CADENCE = 3       # Rahim comments every N turns between milestones

# ── Tension curve thresholds ──────────────────────────────────────────────────
# The game has three acts driven by turn count, not a difficulty selector.
# Act 1 (exploration)  : turns 1  – ACT2_START-1  → free play, Rahim is quiet
# Act 2 (pressure)     : turns ACT2_START – ACT3_START-1 → Rahim interferes,
#                        suspects who Rahim visited become more guarded
# Act 3 (crisis)       : turns ACT3_START – MAX_TURNS    → breaking evidence
#                        drops automatically, Rahim makes his wrong accusation,
#                        cagey threshold tightens

ACT2_START = 4          # Turn at which Rahim starts commenting
ACT3_START = 8          # Turn at which breaking evidence drops + Rahim wrong guess
RAHIM_WRONG_GUESS_TURN = ACT3_START   # Rahim's wrong accusation fires at act 3 start
BREAKING_EVIDENCE_TURN = ACT3_START   # Auto evidence drop fires same turn