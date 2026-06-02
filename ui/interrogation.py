import streamlit as st
from groq import Groq

from config import MAX_TURNS
from api import interrogate_suspect, extract_clues, get_ai_detective_update
from ui.evidence import render_evidence_board

def show_interrogation():
    """Render the interrogation screen with evidence board and AI detective."""
    client: Groq = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]
    turn = st.session_state.get("turn", 0)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        turns_left = MAX_TURNS - turn
        st.markdown(f"### ⏱️ Turns Left: {turns_left}/{MAX_TURNS}")
        if turns_left <= 3:
            st.error("Inspector Rahim is close to solving it!")
        elif turns_left <= 6:
            st.warning("Inspector Rahim is on your heels...")
        else:
            st.success("You have time. Interrogate carefully.")

        st.divider()

        st.markdown("### 👤 Suspects")
        for i, s in enumerate(suspects):
            q_count = len(st.session_state.histories[i]) // 2
            label = f"{s['name']} ({q_count} Qs)"
            if st.button(label, key=f"sel_{i}", use_container_width=True):
                st.session_state.active_suspect = i
                st.rerun()

        st.divider()

        st.markdown("### ⚖️ Make Accusation")
        for i, s in enumerate(suspects):
            if st.button(f"Accuse {s['name']}", key=f"acc_{i}", use_container_width=True):
                st.session_state.accusation = i
                st.session_state.phase = "reveal"
                st.rerun()

    # ── Main area ─────────────────────────────────────────────────────────────
    st.title("🔍 Interrogation Room")

    # Inspector Rahim messages
    if "rahim_messages" not in st.session_state:
        st.session_state.rahim_messages = []
    for msg in st.session_state.rahim_messages:
        st.info(f"🚔 **Inspector Rahim:** {msg}")

    # Evidence board (collapsible)
    with st.expander("📋 Evidence Board", expanded=False):
        render_evidence_board()

    st.divider()

    # Active suspect
    idx = st.session_state.get("active_suspect", 0)
    suspect = suspects[idx]

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"Interrogating: {suspect['name']}")
        st.caption(f"{suspect['relationship_to_victim']} · Alibi: {suspect['alibi']}")
    with col2:
        st.caption("💡 Suggested questions:")
        for q in suspect.get("suggested_questions", []):
            if st.button(q, key=f"sq_{idx}_{q[:20]}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()

    # Conversation history
    for msg in st.session_state.histories[idx]:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.write(msg["content"])

    # Chat input — also accepts pre-filled question from suggested button
    prefill = st.session_state.pop("pending_question", None)
    question = st.chat_input(f"Ask {suspect['name']} a question...") or prefill

    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner(f"{suspect['name']} is thinking..."):
                reply = interrogate_suspect(client, idx, question)
            st.write(reply)

        # Extract and store clues from response
        new_clues = extract_clues(client, suspect["name"], reply)
        if "clues" not in st.session_state:
            st.session_state.clues = []
        st.session_state.clues.extend(new_clues)

        # Advance turn counter and check for Inspector Rahim's move
        st.session_state.turn = turn + 1
        rahim = get_ai_detective_update(client, st.session_state.turn)
        if rahim:
            st.session_state.rahim_messages.append(rahim["message"])
            if st.session_state.turn >= MAX_TURNS:
                st.session_state.rahim_solved = True
                st.session_state.accusation = None
                st.session_state.phase = "reveal"

        st.rerun()