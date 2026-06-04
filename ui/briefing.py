import streamlit as st

TRANSITION_CSS = """
<style>
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeSlideIn 0.4s ease forwards; }
</style>
<div class="fade-in" style="display:none"></div>
"""

def show_briefing():
    """
    Render the case briefing screen.
    
    Key change: the red herring is NOT shown here at all.
    It surfaces naturally through interrogation, just like a real investigation.
    The 'Officer's note' callout that used to hint at the red herring is gone.
    """
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)
    case = st.session_state.case
    tc = TENSION_CURVE

    _, col, _ = st.columns([1, 6, 1])
    with col:
        # Newspaper header
        st.markdown(
            f"""
            <div style='border:2px solid #c8a84b;border-radius:4px;
                padding:24px 32px;margin-bottom:24px;background:#111'>
                <div style='text-align:center;font-size:0.75em;letter-spacing:4px;
                    color:#c8a84b;text-transform:uppercase;margin-bottom:8px'>
                    Singapore Criminal Investigation Department
                </div>
                <div style='text-align:center;font-size:2em;font-weight:900;
                    color:#f0e6cc;letter-spacing:2px;line-height:1.2;font-family:Georgia,serif'>
                    {case["title"]}
                </div>
                <div style='text-align:center;font-size:0.85em;color:#999;
                    margin-top:8px;letter-spacing:1px'>
                    📍 {case["setting"]}
                </div>
                <div style='text-align:center;font-size:0.75em;color:#666;margin-top:6px'>
                    {tc["max_turns"]} turns &nbsp;·&nbsp;
                    Suspects go quiet after {tc["cagey_after"]} questions &nbsp;·&nbsp;
                    Breaking evidence at turn {tc["breaking_evidence_turn"]}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Victim
        st.markdown("### 💀 The Victim")
        st.markdown(
            f"<div style='background:#1a1a1a;border-left:4px solid #c8a84b;"
            f"padding:12px 16px;border-radius:4px;margin-bottom:16px'>"
            f"<strong>{case['victim']['name']}</strong> — {case['victim']['description']}<br>"
            f"<span style='color:#aaa'>Cause of death: {case['cause_of_death']}</span></div>",
            unsafe_allow_html=True
        )
        st.info(f"🔎 **Opening clue found at scene:** {case.get('opening_clue', '')}")

        # NOTE: The red herring callout that was here has been deliberately removed.
        # The player should discover misleading evidence through interrogation,
        # not have it handed to them upfront. Showing it here was spoiling the game
        # by telling the player who NOT to suspect.

        st.divider()

        # Suspects
        st.markdown("### 🕵️ Suspects")
        for s in case["suspects"]:
            with st.expander(f"{s['name']} — {s['relationship_to_victim']}"):
                st.write(f"**Alibi:** {s['alibi']}")

        # Relationships
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

        # Tension curve overview — replaces difficulty warning
        st.markdown(
            f"<div style='background:#1a1a2e;border:1px solid #2a2a4a;border-radius:6px;"
            f"padding:14px 18px;margin-bottom:16px'>"
            f"<div style='color:#c8a84b;font-weight:bold;margin-bottom:8px'>⏱️ How this case unfolds</div>"
            f"<div style='font-size:0.88em;color:#aaa;line-height:1.7'>"
            f"🔍 <strong>Turns 1–5:</strong> Discovery — suspects are cooperative<br>"
            f"⚠️ <strong>Turn {tc['rahim_wrong_turn']}:</strong> Inspector Rahim makes his move<br>"
            f"🔥 <strong>Turn {tc['breaking_evidence_turn']}:</strong> Breaking evidence surfaces<br>"
            f"☠️ <strong>Turn {tc['rahim_solves_turn']}:</strong> Rahim closes the case — you lose"
            f"</div></div>",
            unsafe_allow_html=True
        )

        st.warning(
            f"⚠️ Build your case carefully. Use the **Deduction Board** before accusing — "
            f"a wrong accusation ends the game. Inspector Rahim is running his own investigation in parallel."
        )

        if st.button("Begin Interrogations →", type="primary", use_container_width=True):
            st.session_state.phase = "interrogate"
            st.rerun()