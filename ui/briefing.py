import streamlit as st
from config import MAX_TURNS, AI_WRONG_GUESS_TURN

def show_briefing():
    """Render the case briefing screen with newspaper dark theme."""
    case = st.session_state.case

    _, col, _ = st.columns([1, 6, 1])
    with col:
        # Newspaper-style header
        st.markdown(
            f"""
            <div style='
                border:2px solid #c8a84b;
                border-radius:4px;
                padding:24px 32px;
                margin-bottom:24px;
                background:#111;
            '>
                <div style='
                    text-align:center;
                    font-size:0.75em;
                    letter-spacing:4px;
                    color:#c8a84b;
                    text-transform:uppercase;
                    margin-bottom:8px;
                '>Singapore Criminal Investigation Department</div>
                <div style='
                    text-align:center;
                    font-size:2em;
                    font-weight:900;
                    color:#f0e6cc;
                    letter-spacing:2px;
                    line-height:1.2;
                    font-family:Georgia,serif;
                '>{case["title"]}</div>
                <div style='
                    text-align:center;
                    font-size:0.85em;
                    color:#999;
                    margin-top:8px;
                    letter-spacing:1px;
                '>📍 {case["setting"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Victim block
        st.markdown("### 💀 The Victim")
        st.markdown(
            f"<div style='background:#1a1a1a;border-left:4px solid #c8a84b;"
            f"padding:12px 16px;border-radius:4px;margin-bottom:16px'>"
            f"<strong>{case['victim']['name']}</strong> — {case['victim']['description']}<br>"
            f"<span style='color:#aaa'>Cause of death: {case['cause_of_death']}</span></div>",
            unsafe_allow_html=True
        )
        st.info(f"🔎 **Opening clue found at scene:** {case.get('opening_clue', '')}")

        st.divider()

        # Suspects
        st.markdown("### 🕵️ Suspects")
        for s in case["suspects"]:
            with st.expander(f"{s['name']} — {s['relationship_to_victim']}"):
                st.write(f"**Alibi:** {s['alibi']}")

        # Relationship map
        relationships = case.get("relationships", [])
        if relationships:
            st.markdown("### 🔗 Known Relationships")
            for r in relationships:
                names = " & ".join(r.get("between", []))
                st.markdown(
                    f"<div style='background:#1a1a1a;border-left:3px solid #555;"
                    f"padding:8px 12px;border-radius:4px;margin:4px 0;font-size:0.9em'>"
                    f"<strong>{names}</strong> — {r.get('description','')}</div>",
                    unsafe_allow_html=True
                )

        st.divider()
        st.warning(
            f"⏱️ **Race against Inspector Rahim!** You have **{MAX_TURNS} turns** before he cracks "
            f"the case. He'll make his first move at turn {AI_WRONG_GUESS_TURN}. "
            f"Suspects get uncooperative if questioned too many times — spread your interrogations."
        )

        if st.button("Begin Interrogations →", type="primary", use_container_width=True):
            st.session_state.phase = "interrogate"
            st.rerun()