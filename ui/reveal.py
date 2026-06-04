import streamlit as st

from api import get_rahim_reaction

TRANSITION_CSS = """
<style>
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeSlideIn 0.5s ease forwards; }
</style>
<div class="fade-in" style="display:none"></div>
"""

def _calculate_score(turn: int, max_turns: int, player_correct: bool, rahim_solved: bool) -> tuple[int, str]:
    """Calculate score and rank based on performance."""
    if not player_correct or rahim_solved:
        return 0, "Case Unsolved"
    turns_left = max_turns - turn
    if turns_left >= max_turns * 0.6:
        return 3, "Master Detective"
    elif turns_left >= max_turns * 0.3:
        return 2, "Good Work, Officer"
    else:
        return 1, "Close Call, Inspector"

def _build_full_transcript(case: dict) -> str:
    """Build the full player interrogation transcript."""
    parts = []
    for i, suspect in enumerate(case["suspects"]):
        history = st.session_state.histories[i]
        if history:
            parts.append(f"### {suspect['name']}")
            for msg in history:
                speaker = "🕵️ **You**" if msg["role"] == "user" else f"👤 **{suspect['name']}**"
                parts.append(f"{speaker}: {msg['content']}")
    return "\n\n".join(parts) if parts else "No interrogations recorded."

def show_reveal():
    """Render the final case reveal with scoring, Rahim reaction, and full replay."""
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)

    case = st.session_state.case
    killer_index = case["killer_index"]
    killer = case["suspects"][killer_index]
    rahim_solved = st.session_state.get("rahim_solved", False)
    accused_index = st.session_state.get("accusation")
    client = st.session_state.client
    diff = get_difficulty(st.session_state.get("difficulty", "Medium"))
    turn = st.session_state.get("turn", 0)

    player_correct = (not rahim_solved) and (accused_index == killer_index)
    score, rank = _calculate_score(turn, diff["max_turns"], player_correct, rahim_solved)

    # Fetch Rahim's reaction once and cache it
    if "rahim_reaction_msg" not in st.session_state and accused_index is not None:
        with st.spinner("Inspector Rahim is weighing in..."):
            st.session_state.rahim_reaction_msg = get_rahim_reaction(
                client, accused_index, player_correct
            )

    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title("⚖️ Case Closed")

        # Outcome
        if rahim_solved:
            st.error("🚔 Inspector Rahim cracked the case before you!")
            st.markdown(f"The killer was **{killer['name']}**. Better luck next time, lah.")
        elif player_correct:
            st.success(f"{'⭐' * score} **{rank}** — You beat Inspector Rahim!")
            st.balloons()
        else:
            accused = case["suspects"][accused_index]
            st.error(f"❌ Wrong. You accused **{accused['name']}**, but they were innocent.")
            st.markdown(f"The real killer was **{killer['name']}**.")

        # Score card
        if player_correct and not rahim_solved:
            st.markdown(
                f"<div style='background:#1a1a1a;border:2px solid #c8a84b;border-radius:8px;"
                f"padding:16px;text-align:center;margin:16px 0'>"
                f"<div style='font-size:2em'>{'⭐' * score}</div>"
                f"<div style='color:#c8a84b;font-size:1.3em;font-weight:bold'>{rank}</div>"
                f"<div style='color:#888;font-size:0.9em'>"
                f"Solved in {turn} / {diff['max_turns']} turns</div></div>",
                unsafe_allow_html=True
            )

        # Rahim reaction
        rahim_msg = st.session_state.get("rahim_reaction_msg", "")
        if rahim_msg:
            st.info(f"🚔 **Inspector Rahim:** {rahim_msg}")

        st.divider()

        # Case truth breakdown
        st.markdown("### 🔍 The Truth")
        st.markdown(f"**Killer:** {killer['name']}")
        st.markdown(f"**Motive:** {case['motive']}")
        st.markdown(f"**Alibi flaw:** {killer['alibi_contradiction']}")

        red_herring = case.get("red_herring", {})
        if red_herring:
            rh_idx = red_herring.get("points_to_suspect_index", -1)
            rh_name = case["suspects"][rh_idx]["name"] if 0 <= rh_idx < 3 else "?"
            st.markdown(
                f"<div style='background:#2a1a1a;border-left:4px solid #aa4444;"
                f"padding:10px 14px;border-radius:4px;margin:8px 0'>"
                f"🪤 <strong>Red herring:</strong> The evidence pointing to {rh_name} "
                f"was a deliberate misdirection. {red_herring.get('description','')}</div>",
                unsafe_allow_html=True
            )

        # Player notes
        notes = st.session_state.get("player_notes", "").strip()
        if notes:
            with st.expander("📓 Your Investigation Notes", expanded=False):
                st.markdown(notes)

        # Full transcript — player + all Rahim visits
        with st.expander("📜 Full Case Transcript", expanded=False):
            st.markdown(_build_full_transcript(case))

            rahim_ints = st.session_state.get("rahim_interrogations", {})
            if rahim_ints:
                st.markdown("---")
                st.markdown("### 🚔 Inspector Rahim's Interrogations")
                for i, suspect in enumerate(case["suspects"]):
                    visits = rahim_ints.get(str(i), [])
                    if visits:
                        st.markdown(f"**{suspect['name']}** ({len(visits)} visit{'s' if len(visits) > 1 else ''})")
                        for v_num, entry in enumerate(visits, 1):
                            st.markdown(f"*Visit {v_num}*")
                            st.markdown(f"- Rahim asked: *{entry.get('rahim_question','')}*")
                            st.markdown(f"- {suspect['name']} replied: *{entry.get('suspect_reply','')}*")
                            st.markdown(f"- Rahim thought: *{entry.get('rahim_reaction','')}*")

        st.divider()
        if st.button("🔄 New Case", type="primary", use_container_width=True):
            keys_to_clear = [
                "case", "phase", "histories", "active_suspect", "accusation",
                "clues", "flagged_clues", "turn", "rahim_messages", "rahim_history",
                "rahim_solved", "rahim_accused", "rahim_interrogations",
                "rahim_reaction_msg", "pending_question", "sq_key",
                "suggested_questions", "player_notes", "notes_saved_flash",
                "witness_used", "breaking_evidence_dropped",
                "rahim_visited_suspects", "rahim_int_key", "deduction_feedback",
                "deduction_suspect_index", "forensic_flash", "breaking_evidence",
            ]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
            st.rerun()