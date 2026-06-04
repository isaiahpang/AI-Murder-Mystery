import streamlit as st
from groq import Groq

from config import get_difficulty
from api import (
    interrogate_suspect, extract_clues,
    get_ai_detective_update, get_rahim_commentary,
    get_rahim_interrogation, get_suggested_questions,
)
from ui.evidence import render_evidence_board

# ── Transition CSS ────────────────────────────────────────────────────────────
TRANSITION_CSS = """
<style>
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in {
    animation: fadeSlideIn 0.4s ease forwards;
}
</style>
<div class="fade-in" style="display:none"></div>
"""

def _refresh_suggested_questions(client: Groq, idx: int):
    """Fetch fresh suggested questions for the active suspect."""
    st.session_state.suggested_questions = get_suggested_questions(client, idx)

def show_interrogation():
    """Render the full interrogation screen."""
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)

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

        # Notes panel with autosave indicator
        st.markdown("### 📓 Your Notes")
        notes_val = st.session_state.get("player_notes", "")
        new_notes = st.text_area(
            label="notes",
            value=notes_val,
            height=160,
            placeholder="Write your suspicions here...",
            label_visibility="collapsed",
            key="notes_input"
        )
        if new_notes != notes_val:
            st.session_state.player_notes = new_notes
            st.session_state.notes_saved_flash = True
        if st.session_state.pop("notes_saved_flash", False):
            st.caption("✓ Notes saved")

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

        # Active suspect header
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

        # Player conversation history
        for msg in st.session_state.histories[idx]:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.write(msg["content"])

        # Rahim's interrogations of this suspect — shows ALL visits, newest first
        rahim_all = st.session_state.get("rahim_interrogations", {}).get(str(idx), [])
        if rahim_all:
            with st.expander(
                f"🚔 Inspector Rahim questioned {suspect['name']} "
                f"({len(rahim_all)} time{'s' if len(rahim_all) > 1 else ''})",
                expanded=False
            ):
                for i, entry in enumerate(reversed(rahim_all)):
                    if len(rahim_all) > 1:
                        st.caption(f"Visit {len(rahim_all) - i}")
                    st.markdown(
                        f"<div style='background:#1a1a2e;border-left:3px solid #c8a84b;"
                        f"padding:10px 14px;border-radius:4px;margin:4px 0'>"
                        f"<strong>Rahim:</strong> {entry.get('rahim_question','')}</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f"<div style='background:#1a1a1a;border-left:3px solid #555;"
                        f"padding:10px 14px;border-radius:4px;margin:4px 0'>"
                        f"<strong>{suspect['name']}:</strong> {entry.get('suspect_reply','')}</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f"<div style='background:#111;border-left:3px solid #444;"
                        f"padding:8px 14px;border-radius:4px;margin:4px 0;font-style:italic;"
                        f"color:#888'>"
                        f"Rahim thinks: {entry.get('rahim_reaction','')}</div>",
                        unsafe_allow_html=True
                    )
                    if i < len(rahim_all) - 1:
                        st.markdown("---")

        # Scroll anchor so chat input stays visible after rerun
        st.markdown("<div id='chat-anchor'></div>", unsafe_allow_html=True)

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

            # Extract clues (dedup handled in api.py)
            new_clues = extract_clues(client, suspect["name"], reply)
            if "clues" not in st.session_state:
                st.session_state.clues = []
            st.session_state.clues.extend(new_clues)

            # Generate fresh Rahim interrogation after each player turn
            get_rahim_interrogation(client, idx)

            # Invalidate question cache
            st.session_state.pop("sq_key", None)
            st.session_state.pop("suggested_questions", None)

            # Advance turn
            st.session_state.turn = turn + 1
            new_turn = st.session_state.turn

            # Milestone check first, then cadence commentary
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