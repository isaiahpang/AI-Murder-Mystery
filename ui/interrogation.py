import streamlit as st
from groq import Groq

from config import MAX_TURNS
from api import interrogate_suspect, extract_clues, get_ai_detective_update, get_suggested_questions
from ui.evidence import render_evidence_board

def _refresh_suggested_questions(client: Groq, idx: int):
    """Fetch fresh suggested questions for the active suspect and cache in session state."""
    questions = get_suggested_questions(client, idx)
    st.session_state.suggested_questions = questions

def show_interrogation():
    """Render the interrogation screen with evidence board and AI detective."""
    client: Groq = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]
    turn = st.session_state.get("turn", 0)
    idx = st.session_state.get("active_suspect", 0)

    # Generate suggested questions on first load or when suspect changes
    sq_key = f"sq_generated_{idx}_{len(st.session_state.histories[idx])}"
    if st.session_state.get("sq_key") != sq_key:
        _refresh_suggested_questions(client, idx)
        st.session_state.sq_key = sq_key

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
            if st.button(f"{s['name']} ({q_count} Qs)", key=f"sel_{i}", use_container_width=True):
                st.session_state.active_suspect = i
                # Clear cached questions so they regenerate for the new suspect
                st.session_state.pop("sq_key", None)
                st.session_state.pop("suggested_questions", None)
                st.rerun()

        st.divider()
        st.markdown("### ⚖️ Accuse")
        for i, s in enumerate(suspects):
            if st.button(f"Accuse {s['name']}", key=f"acc_{i}", use_container_width=True):
                st.session_state.accusation = i
                st.session_state.phase = "reveal"
                st.rerun()

    # ── Centred main layout ───────────────────────────────────────────────────
    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title("🔍 Interrogation Room")

        # Inspector Rahim messages
        if "rahim_messages" not in st.session_state:
            st.session_state.rahim_messages = []
        for msg in st.session_state.rahim_messages:
            st.info(f"🚔 **Inspector Rahim:** {msg}")

        # Evidence board — always visible
        render_evidence_board()
        st.divider()

        # Active suspect header
        suspect = suspects[idx]
        st.subheader(f"Interrogating: {suspect['name']}")
        st.caption(f"{suspect['relationship_to_victim']} · Alibi: {suspect['alibi']}")

        # Suggested questions — based only on known info, refreshed after each answer
        questions = st.session_state.get("suggested_questions", [])
        if questions:
            st.caption("💡 Suggested questions — based on what you know so far:")
            sq_cols = st.columns(len(questions))
            for j, q in enumerate(questions):
                with sq_cols[j]:
                    if st.button(q, key=f"sq_{idx}_{j}_{q[:15]}", use_container_width=True):
                        st.session_state.pending_question = q
                        st.rerun()

        st.markdown("")

        # Conversation history
        for msg in st.session_state.histories[idx]:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.write(msg["content"])

        # Chat input
        prefill = st.session_state.pop("pending_question", None)
        question = st.chat_input(f"Ask {suspect['name']} a question...") or prefill

        if question:
            with st.chat_message("user"):
                st.write(question)
            with st.chat_message("assistant"):
                with st.spinner(f"{suspect['name']} is thinking..."):
                    reply = interrogate_suspect(client, idx, question)
                st.write(reply)

            # Extract clues from response
            new_clues = extract_clues(client, suspect["name"], reply)
            if "clues" not in st.session_state:
                st.session_state.clues = []
            st.session_state.clues.extend(new_clues)

            # Invalidate cached questions so they regenerate next render
            st.session_state.pop("sq_key", None)
            st.session_state.pop("suggested_questions", None)

            # Advance turn and check Inspector Rahim
            st.session_state.turn = turn + 1
            rahim = get_ai_detective_update(client, st.session_state.turn)
            if rahim:
                st.session_state.rahim_messages.append(rahim["message"])
                if st.session_state.turn >= MAX_TURNS:
                    st.session_state.rahim_solved = True
                    st.session_state.accusation = None
                    st.session_state.phase = "reveal"

            st.rerun()