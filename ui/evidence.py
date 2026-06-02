import streamlit as st

CLUE_ICONS = {
    "alibi": "📋",
    "witness": "👁️",
    "physical": "🔬",
    "contradiction": "⚠️",
    "motive": "💢",
}

def render_evidence_board():
    """Render the evidence board with clues grouped by suspect in columns."""
    clues = st.session_state.get("clues", [])
    case = st.session_state.case
    suspects = case["suspects"]

    st.markdown("### 🗂️ Evidence Board")

    # Opening scene clue — always shown
    opening = case.get("opening_clue", "")
    if opening:
        st.info(f"📍 **Scene clue:** {opening}")

    # One card per suspect
    cols = st.columns(3)
    for i, suspect in enumerate(suspects):
        suspect_clues = [c for c in clues if c.get("links_to_suspect") == suspect["name"]]
        with cols[i]:
            st.markdown(f"**🧑 {suspect['name']}**")
            if suspect_clues:
                for c in suspect_clues:
                    icon = CLUE_ICONS.get(c.get("type", ""), "🔍")
                    st.markdown(
                        f"<div style='background:#1e1e2e;border-left:3px solid #7c7cff;"
                        f"padding:6px 10px;margin:4px 0;border-radius:4px;font-size:0.85em'>"
                        f"{icon} {c['text']}</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.caption("No clues yet")

    # General clues not linked to a specific suspect
    unlinked = [c for c in clues if not c.get("links_to_suspect")]
    if unlinked:
        st.markdown("**🔎 General clues**")
        for c in unlinked:
            icon = CLUE_ICONS.get(c.get("type", ""), "🔍")
            st.markdown(
                f"<div style='background:#1e1e2e;border-left:3px solid #ffaa33;"
                f"padding:6px 10px;margin:4px 0;border-radius:4px;font-size:0.85em'>"
                f"{icon} {c['text']}</div>",
                unsafe_allow_html=True
            )

    if not clues:
        st.caption("No clues collected yet. Start interrogating suspects.")