import streamlit as st

# Icons for each clue type
CLUE_ICONS = {
    "alibi": "📋",
    "witness": "👁️",
    "physical": "🔬",
    "contradiction": "⚠️",
    "motive": "💢",
}

def render_evidence_board():
    """Render a visual evidence board with clues grouped by suspect."""
    clues = st.session_state.get("clues", [])
    case = st.session_state.case
    suspects = case["suspects"]

    st.markdown("### 🗂️ Evidence Board")

    # Opening clue always shown
    opening = case.get("opening_clue", "")
    if opening:
        st.info(f"📍 **Scene clue:** {opening}")

    if not clues:
        st.caption("No clues collected yet. Start interrogating suspects.")
        return

    # Split clues into suspect-linked and general
    linked = {
        s["name"]: [c for c in clues if c.get("links_to_suspect") == s["name"]]
        for s in suspects
    }
    unlinked = [c for c in clues if not c.get("links_to_suspect")]

    # One column per suspect
    cols = st.columns(len(suspects))
    for i, suspect in enumerate(suspects):
        with cols[i]:
            st.markdown(f"**{suspect['name']}**")
            suspect_clues = linked.get(suspect["name"], [])
            if suspect_clues:
                for c in suspect_clues:
                    icon = CLUE_ICONS.get(c.get("type", ""), "🔍")
                    st.markdown(f"{icon} {c['text']}")
            else:
                st.caption("No clues yet")

    # General / unlinked clues below
    if unlinked:
        st.markdown("---")
        st.markdown("**General clues**")
        for c in unlinked:
            icon = CLUE_ICONS.get(c.get("type", ""), "🔍")
            st.markdown(f"{icon} {c['text']}")