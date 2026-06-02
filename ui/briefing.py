import streamlit as st
from config import MAX_TURNS, AI_WRONG_GUESS_TURN

def show_briefing():
    """Render the case briefing screen."""
    case = st.session_state.case

    st.title(f"🔍 {case['title']}")
    st.caption(f"📍 {case['setting']}")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 💀 The Victim")
        st.write(f"**{case['victim']['name']}** — {case['victim']['description']}")
        st.write(f"**Cause of death:** {case['cause_of_death']}")
        st.info(f"🔎 **Opening clue found at scene:** {case.get('opening_clue', '')}")

    with col2:
        st.markdown("### 🕵️ Suspects")
        for s in case["suspects"]:
            with st.expander(f"{s['name']} — {s['relationship_to_victim']}"):
                st.write(f"**Alibi:** {s['alibi']}")

    st.divider()
    st.warning(
        f"⏱️ **Race against Inspector Rahim!** You have {MAX_TURNS} turns before he cracks the case. "
        f"He'll make his first move at turn {AI_WRONG_GUESS_TURN}."
    )

    if st.button("Begin Interrogations →", type="primary"):
        st.session_state.phase = "interrogate"
        st.rerun()