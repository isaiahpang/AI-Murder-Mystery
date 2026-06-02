import streamlit as st

CLUE_ICONS = {
    "alibi": "📋",
    "witness": "👁️",
    "physical": "🔬",
    "contradiction": "⚠️",
    "motive": "💢",
}

CLUE_COLOURS = {
    "alibi": "#3a3a6e",
    "witness": "#3a5a3a",
    "physical": "#5a3a6e",
    "contradiction": "#6e3a3a",
    "motive": "#6e5a3a",
}

def render_evidence_board():
    """Render the evidence board with flaggable clue cards grouped by suspect."""
    clues = st.session_state.get("clues", [])
    flagged = st.session_state.setdefault("flagged_clues", set())
    case = st.session_state.case
    suspects = case["suspects"]

    st.markdown("### 🗂️ Evidence Board")

    opening = case.get("opening_clue", "")
    if opening:
        st.info(f"📍 **Scene clue:** {opening}")

    # Relationship map
    relationships = case.get("relationships", [])
    if relationships:
        with st.expander("🔗 Suspect Relationships", expanded=False):
            for r in relationships:
                names = " & ".join(r.get("between", []))
                st.markdown(f"**{names}** — {r.get('description', '')}")

    if not clues:
        st.caption("No clues collected yet. Start interrogating suspects.")
        return

    cols = st.columns(3)
    for i, suspect in enumerate(suspects):
        suspect_clues = [c for c in clues if c.get("links_to_suspect") == suspect["name"]]
        with cols[i]:
            st.markdown(f"**🧑 {suspect['name']}**")
            if suspect_clues:
                for ci, c in enumerate(suspect_clues):
                    clue_id = f"{suspect['name']}_{ci}"
                    icon = CLUE_ICONS.get(c.get("type", ""), "🔍")
                    colour = CLUE_COLOURS.get(c.get("type", ""), "#2a2a2a")
                    is_flagged = clue_id in flagged
                    flag_icon = "⭐" if is_flagged else "☆"

                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(
                            f"<div style='background:{colour};border-radius:4px;"
                            f"padding:6px 10px;margin:3px 0;font-size:0.85em'>"
                            f"{icon} {c['text']}</div>",
                            unsafe_allow_html=True
                        )
                    with c2:
                        if st.button(flag_icon, key=f"flag_{clue_id}", help="Flag as important"):
                            if is_flagged:
                                flagged.discard(clue_id)
                            else:
                                flagged.add(clue_id)
                            st.session_state.flagged_clues = flagged
                            st.rerun()
            else:
                st.caption("No clues yet")

    unlinked = [c for c in clues if not c.get("links_to_suspect")]
    if unlinked:
        st.markdown("---")
        st.markdown("**🔎 General clues**")
        for ci, c in enumerate(unlinked):
            icon = CLUE_ICONS.get(c.get("type", ""), "🔍")
            st.markdown(
                f"<div style='background:#2a3a4a;border-left:3px solid #ffaa33;"
                f"padding:6px 10px;margin:3px 0;border-radius:4px;font-size:0.85em'>"
                f"{icon} {c['text']}</div>",
                unsafe_allow_html=True
            )