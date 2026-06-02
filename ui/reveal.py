import streamlit as st
from config import MAX_TURNS

def show_reveal():
    """Render the final case reveal screen, centred."""
    case = st.session_state.case
    killer_index = case["killer_index"]
    killer = case["suspects"][killer_index]
    rahim_solved = st.session_state.get("rahim_solved", False)
    accused_index = st.session_state.get("accusation")

    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title("⚖️ Case Closed")

        if rahim_solved:
            st.error("🚔 Inspector Rahim cracked the case before you!")
            st.markdown(f"The killer was **{killer['name']}**. Better luck next time, lah.")
        elif accused_index == killer_index:
            st.success(f"✅ Correct! **{killer['name']}** is the killer. You beat Inspector Rahim!")
            st.balloons()
        else:
            accused = case["suspects"][accused_index]
            st.error(f"❌ Wrong. You accused **{accused['name']}**, but they were innocent.")
            st.markdown(f"The real killer was **{killer['name']}**.")

        st.divider()
        st.markdown(f"**Motive:** {case['motive']}")
        st.markdown(f"**The alibi flaw:** {killer['alibi_contradiction']}")
        st.markdown(f"**Turns used:** {st.session_state.get('turn', 0)} / {MAX_TURNS}")

        if st.button("🔄 New Case", type="primary", use_container_width=True):
            keys_to_clear = [
                "case", "phase", "histories", "active_suspect", "accusation",
                "clues", "turn", "rahim_messages", "rahim_solved", "pending_question"
            ]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
            st.rerun()