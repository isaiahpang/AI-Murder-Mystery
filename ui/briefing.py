import streamlit as st
from config import get_difficulty

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
    """Render the case briefing screen with newspaper dark theme."""
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)
    case = st.session_state.case
    diff_name = st.session_state.get("difficulty", "Medium")
    diff = get_difficulty(diff_name)

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
                    Difficulty: {diff_name} &nbsp;·&nbsp;
                    {diff["max_turns"]} turns &nbsp;·&nbsp;
                    Suspects go quiet after {diff["cagey_after"]} questions
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

        # Red herring callout (shown as a "tip" but is actually misleading)
        red_herring = case.get("red_herring", {})
        if red_herring:
            rh_idx = red_herring.get("points_to_suspect_index", -1)
            rh_name = case["suspects"][rh_idx]["name"] if 0 <= rh_idx < 3 else "unknown"
            st.warning(
                f"🚨 **Officer's note:** A piece of evidence at the scene appears to implicate "
                f"**{rh_name}**. {red_herring.get('description', '')}"
            )

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
        st.warning(
            f"⏱️ **Race against Inspector Rahim!** You have **{diff['max_turns']} turns**. "
            f"He makes his first move at turn {diff['wrong_guess_turn']}. "
            f"Suspects become uncooperative after {diff['cagey_after']} questions."
        )

        if st.button("Begin Interrogations →", type="primary", use_container_width=True):
            st.session_state.phase = "interrogate"
            st.rerun()