import streamlit as st
from config import MAX_TURNS, AI_WRONG_GUESS_TURN

def show_briefing():
    """Render the case briefing screen, centred."""
    case = st.session_state.case

    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title(f"🔍 {case['title']}")
        st.caption(f"📍 {case['setting']}")
        st.divider()

        # Victim block
        st.markdown("### 💀 The Victim")
        st.markdown(f"**{case['victim']['name']}** — {case['victim']['description']}")
        st.markdown(f"**Cause of death:** {case['cause_of_death']}")
        st.info(f"🔎 **Opening clue found at scene:** {case.get('opening_clue', '')}")

        st.divider()

        # Suspects
        st.markdown("### 🕵️ Suspects")
        for s in case["suspects"]:
            with st.expander(f"{s['name']} — {s['relationship_to_victim']}"):
                st.write(f"**Alibi:** {s['alibi']}")

        st.divider()

        st.warning(
            f"⏱️ **Race against Inspector Rahim!** You have **{MAX_TURNS} turns** before he cracks "
            f"the case. He'll make his first move at turn {AI_WRONG_GUESS_TURN}."
        )

        if st.button("Begin Interrogations →", type="primary", use_container_width=True):
            st.session_state.phase = "interrogate"
            st.rerun()