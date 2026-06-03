import streamlit as st
from groq import Groq

from config import get_difficulty
from api import (
    interrogate_suspect, extract_clues,
    get_ai_detective_update, get_rahim_commentary,
    get_rahim_interrogation, get_suggested_questions,
)
from ui.evidence import render_evidence_board

def _refresh_suggested_questions(client: Groq, idx: int):
    """Fetch fresh suggested questions for the active suspect."""
    st.session_state.suggested_questions = get_suggested_questions(client, idx)

def _generate_rahim_interrogation(client: Groq, suspect_index: int):
    """Generate and cache Rahim's parallel interrogation of a suspect."""
    key = f"rahim_int_{suspect_index}"
    if key not in st.session_state.rahim_interrogations:
        result = get_rahim_interrogation(client, suspect_index)
        if result:
            st.session_state.rahim_interrogations[key] = result

def show_interrogation():
    """Render the full interrogation screen."""
    client: Groq = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]
    turn = st.session_state.get("turn", 0)
    idx = st.session_state.get("active_suspect", 0)
    diff = get_difficulty(st.session_state.get("difficulty", "Medium"))
    max_turns = diff["max_turns"]
    cagey_after = diff["cagey_after"]

    # Refresh suggested questions when suspect or conversation changes
    sq_key = f"sq_{idx}_{len(st.session_state.histories[idx])}"
    if st.session_state.get("sq_key") != sq_key:
        _refresh_suggested_questions(client, idx)
        st.session_state.sq_key = sq_key

    # Generate Rahim's interrogation of active suspect in background
    _generate_rahim_interrogation(client, idx)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        turns_left = max_turns - turn
        st.markdown(f"### ⏱️ Turns Left: {turns_left}/{max_turns}")
        st.progress(turn / max_turns)
        if turns_left <= 3:
            st.error("Inspector Rahim is about to crack it!")
        elif turns_left <= max_turns // 2:
            st.warning("Inspector Rahim is gaining on you...")
        else:
            st.success("You have time. Choose wisely.")

        st.divider()
        st.markdown("### 👤 Suspects")
        for i, s in enumerate(suspects):
            q_count = len(st.session_state.histories[i]) // 2
            is_cagey = q_count >= cagey_after
            label = f"{'🔴 ' if is_cagey else ''}{s['name']} ({q_count} Qs)"
            if st.button(label, key=f"sel_{i}", use_container_width=True):
                st.session_state.active_suspect = i
                st.session_state.pop("sq_key", None)
                st.session_state.pop("suggested_questions", None)
                st.rerun()

        st.divider()

        # Player notes panel
        st.markdown("### 📓 Your Notes")
        notes = st.text_area(
            label="notes",
            value=st.session_state.get("player_notes", ""),
            height=180,
            placeholder="Write your thoughts, suspicions, and observations here...",
            label_visibility="collapsed",
            key="notes_input"
        )
        if notes != st.session_state.get("player_notes", ""):
            st.session_state.player_notes = notes

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

        # Rahim messages
        if "rahim_messages" not in st.session_state:
            st.session_state.rahim_messages = []
        for msg in st.session_state.rahim_messages:
            st.info(f"🚔 **Inspector Rahim:** {msg}")

        render_evidence_board()
        st.divider()

        # Active suspect
        suspect = suspects[idx]
        q_count = len(st.session_state.histories[idx]) // 2
        is_cagey = q_count >= cagey_after

        st.subheader(f"Interrogating: {suspect['name']}")
        st.caption(f"{suspect['relationship_to_victim']} · Alibi: {suspect['alibi']}")

        if is_cagey:
            st.warning(
                f"⚠️ {suspect['name']} has been questioned {q_count} times and is becoming "
                f"uncooperative. Consider switching suspects."
            )

        # Suggested questions
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

        # Conversation history — player's interrogation
        for msg in st.session_state.histories[idx]:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.write(msg["content"])

        # Rahim's parallel interrogation of this suspect (collapsible)
        rahim_int = st.session_state.rahim_interrogations.get(f"rahim_int_{idx}")
        if rahim_int:
            with st.expander(f"🚔 Inspector Rahim also questioned {suspect['name']}", expanded=False):
                st.markdown(
                    f"<div style='background:#1a1a2e;border-left:3px solid #c8a84b;"
                    f"padding:10px 14px;border-radius:4px;margin:4px 0'>"
                    f"<strong>Rahim:</strong> {rahim_int.get('rahim_question','')}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div style='background:#1a1a1a;border-left:3px solid #555;"
                    f"padding:10px 14px;border-radius:4px;margin:4px 0'>"
                    f"<strong>{suspect['name']}:</strong> {rahim_int.get('suspect_reply','')}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<div style='background:#1a1a2e;border-left:3px solid #888;"
                    f"padding:10px 14px;border-radius:4px;margin:4px 0'>"
                    f"<em>Rahim thinks: {rahim_int.get('rahim_reaction','')}</em></div>",
                    unsafe_allow_html=True
                )

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

            new_clues = extract_clues(client, suspect["name"], reply)
            if "clues" not in st.session_state:
                st.session_state.clues = []
            st.session_state.clues.extend(new_clues)

            st.session_state.pop("sq_key", None)
            st.session_state.pop("suggested_questions", None)

            st.session_state.turn = turn + 1
            new_turn = st.session_state.turn

            # Milestone check first, then cadence
            rahim = get_ai_detective_update(client, new_turn)
            if rahim:
                st.session_state.rahim_messages.append(rahim["message"])
                if rahim.get("accusation"):
                    st.session_state.rahim_accused = rahim["accusation"]
                if new_turn >= max_turns:
                    st.session_state.rahim_solved = True
                    st.session_state.accusation = None
                    st.session_state.phase = "reveal"
            else:
                commentary = get_rahim_commentary(client, new_turn)
                if commentary:
                    st.session_state.rahim_messages.append(commentary)

            st.rerun()