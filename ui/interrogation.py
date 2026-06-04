import streamlit as st
from groq import Groq

from config import TENSION_CURVE, get_act
from api import (
    interrogate_suspect, extract_clues,
    get_ai_detective_update, get_rahim_commentary,
    get_rahim_interrogation, get_suggested_questions,
    cross_examine_suspect, challenge_alibi,
    investigate_physical_clue, call_witness,
    trigger_breaking_evidence,
)
from ui.evidence import render_evidence_board
from ui.deduction import show_deduction_board

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

def _refresh_suggested_questions(client: Groq, idx: int):
    st.session_state.suggested_questions = get_suggested_questions(client, idx)

def _advance_turn(client: Groq):
    """
    Increment turn counter and trigger all turn-based events:
    - Rahim's milestone actions (wrong guess at turn 6, solve at turn 15)
    - Rahim's cadence commentary
    - Breaking evidence drop at turn 10
    """
    tc = TENSION_CURVE
    st.session_state.turn = st.session_state.get("turn", 0) + 1
    new_turn = st.session_state.turn

    # ── Breaking evidence (Act III trigger) ─────────────────────────────────
    if new_turn == tc["breaking_evidence_turn"]:
        breaking = trigger_breaking_evidence(client)
        if breaking and breaking.get("message"):
            st.session_state.rahim_messages.append(
                f"🔬 **BREAKING EVIDENCE** — {breaking['message']}"
            )

    # ── Rahim milestone ──────────────────────────────────────────────────────
    rahim = get_ai_detective_update(client, new_turn)
    if rahim:
        st.session_state.rahim_messages.append(rahim["message"])
        if rahim.get("accusation"):
            st.session_state.rahim_accused = rahim["accusation"]

            # ── NEW: Rahim's wrong accusation has consequences ────────────────
            # The falsely accused suspect's defensiveness is now driven by
            # build_suspect_prompt(falsely_accused=True) — see api.py.
            # We surface a notice so the player understands what changed.
            case = st.session_state.case
            accused_name = rahim["accusation"]
            killer_name = case["suspects"][case["killer_index"]]["name"]
            if accused_name != killer_name:
                # Rahim accused an innocent — flag it visibly
                st.session_state.rahim_false_accusation_notice = (
                    f"Rahim just publicly accused **{accused_name}**. "
                    f"They are furious and may refuse to cooperate. "
                    f"Other suspects may also reference Rahim's mistake."
                )

        if new_turn >= tc["rahim_solves_turn"]:
            st.session_state.rahim_solved = True
            st.session_state.accusation = None
            st.session_state.phase = "reveal"
    else:
        # ── Cadence commentary ───────────────────────────────────────────────
        commentary = get_rahim_commentary(client, new_turn)
        if commentary:
            st.session_state.rahim_messages.append(commentary)

def _handle_pending_actions(client: Groq):
    """Process any pending confront/investigate/alibi/witness actions before rendering."""
    case = st.session_state.case

    # ── Pending confrontation ─────────────────────────────────────────────────
    confront = st.session_state.pop("pending_confront", None)
    if confront:
        suspect_idx = confront["suspect_index"]
        suspect = case["suspects"][suspect_idx]
        claim = confront["claim"]
        source = confront["source_suspect"]

        with st.spinner(f"Confronting {suspect['name']}..."):
            result = cross_examine_suspect(client, suspect_idx, claim)

        if result.get("response"):
            st.session_state.active_suspect = suspect_idx
            st.success(f"⚡ **Confronted {suspect['name']}** with claim from {source}")
            st.info(f"**{suspect['name']}:** {result['response']}")
            if result.get("new_clue"):
                st.warning(f"🔍 New clue surfaced: *{result['new_clue']}*")
            st.session_state.pop("sq_key", None)
            _advance_turn(client)

    # ── Pending forensic investigation ───────────────────────────────────────
    investigate = st.session_state.pop("pending_investigate", None)
    if investigate:
        clue_text = investigate["clue_text"]
        clue_id = investigate["clue_id"]
        with st.spinner("Sending to forensics..."):
            result = investigate_physical_clue(client, clue_text)
        if result.get("finding"):
            st.session_state[f"investigated_{clue_id}"] = True
            verdict = "✅ Corroborated" if result.get("corroborates") else "❓ Complicated"
            st.info(
                f"🔬 **Forensic Report** ({verdict})\n\n"
                f"{result['finding']}"
            )
            if result.get("points_to_suspect"):
                st.warning(f"👤 Finding implicates: **{result['points_to_suspect']}**")
            _advance_turn(client)

def _render_act_indicator(turn: int):
    """Show a subtle act indicator below the title."""
    tc = TENSION_CURVE
    act = get_act(turn)
    turns_left = tc["max_turns"] - turn
    progress = turn / tc["max_turns"]

    # Act colour for the progress bar background
    colour = act["colour"]

    st.markdown(
        f"<div style='background:#111;border:1px solid #2a2a2a;border-radius:6px;"
        f"padding:10px 16px;margin-bottom:12px;display:flex;align-items:center;"
        f"justify-content:space-between'>"
        f"<span style='color:{colour};font-weight:bold;font-size:0.9em'>"
        f"{act['icon']} {act['label']}</span>"
        f"<span style='color:#888;font-size:0.85em'>Turn {turn} / {tc['max_turns']} "
        f"· {turns_left} left</span>"
        f"</div>",
        unsafe_allow_html=True
    )
    st.progress(progress)

def show_interrogation():
    """Render the full interrogation screen with all verification mechanics."""
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)

    client: Groq = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]
    turn = st.session_state.get("turn", 0)
    idx = st.session_state.get("active_suspect", 0)
    tc = TENSION_CURVE
    max_turns = tc["max_turns"]
    cagey_after = tc["cagey_after"]
    witness_used = st.session_state.get("witness_used", False)
    deduction_mode = st.session_state.get("deduction_mode", False)

    # Handle any pending actions from evidence board buttons
    _handle_pending_actions(client)

    # Refresh suggested questions when suspect/conversation changes
    sq_key = f"sq_{idx}_{len(st.session_state.histories[idx])}"
    if st.session_state.get("sq_key") != sq_key:
        _refresh_suggested_questions(client, idx)
        st.session_state.sq_key = sq_key

    # Generate Rahim's parallel interrogation for active suspect
    get_rahim_interrogation(client, idx)

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        turns_left = max_turns - turn
        act = get_act(turn)

        # Act header in sidebar
        st.markdown(
            f"<div style='background:#111;border-left:4px solid {act['colour']};"
            f"padding:8px 12px;border-radius:4px;margin-bottom:8px'>"
            f"<div style='color:{act['colour']};font-weight:bold;font-size:0.9em'>"
            f"{act['icon']} {act['label']}</div>"
            f"<div style='color:#888;font-size:0.8em'>Turn {turn} · {turns_left} left</div>"
            f"</div>",
            unsafe_allow_html=True
        )
        st.progress(turn / max_turns)

        if turns_left <= 3:
            st.error("Inspector Rahim is about to crack it!")
        elif turn >= tc["breaking_evidence_turn"]:
            st.warning("Breaking evidence is in. Make your case.")
        elif turn >= tc["rahim_wrong_turn"]:
            st.warning("Inspector Rahim has made his move.")
        else:
            st.success("You have time. Choose wisely.")

        st.divider()
        st.markdown("### 👤 Suspects")

        falsely_accused_idx = None
        rahim_accused = st.session_state.get("rahim_accused", "")
        if rahim_accused:
            killer_idx = case["killer_index"]
            for i, s in enumerate(suspects):
                if s["name"] == rahim_accused and i != killer_idx:
                    falsely_accused_idx = i
                    break

        for i, s in enumerate(suspects):
            q_count = len(st.session_state.histories[i]) // 2
            is_cagey = q_count >= cagey_after
            is_falsely_accused = (i == falsely_accused_idx)

            prefix = ""
            if is_falsely_accused:
                prefix = "🚨 "  # Rahim accused this innocent — they're in defensive mode
            elif is_cagey:
                prefix = "🔴 "

            label = f"{prefix}{s['name']} ({q_count} Qs)"
            if st.button(label, key=f"sel_{i}", use_container_width=True):
                st.session_state.active_suspect = i
                st.session_state.deduction_mode = False
                st.session_state.pop("sq_key", None)
                st.session_state.pop("suggested_questions", None)
                st.rerun()

        st.divider()

        # Notes panel
        st.markdown("### 📓 Your Notes")
        notes_val = st.session_state.get("player_notes", "")
        new_notes = st.text_area(
            label="notes", value=notes_val, height=160,
            placeholder="Write your suspicions here...",
            label_visibility="collapsed", key="notes_input"
        )
        if new_notes != notes_val:
            st.session_state.player_notes = new_notes
            st.session_state.notes_saved_flash = True
        if st.session_state.pop("notes_saved_flash", False):
            st.caption("✓ Notes saved")

        st.divider()

        # Deduction board entry point — replaces the raw Accuse buttons
        st.markdown("### ⚖️ Make Your Case")
        st.caption("Don't just guess — build a case first.")
        if st.button("📋 Open Deduction Board", use_container_width=True, type="primary",
                     key="open_deduction"):
            st.session_state.deduction_mode = True
            st.rerun()

    # ── Main layout ───────────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title("🔍 Interrogation Room")

        # ── Act indicator ─────────────────────────────────────────────────────
        _render_act_indicator(turn)

        # ── Rahim messages ────────────────────────────────────────────────────
        if "rahim_messages" not in st.session_state:
            st.session_state.rahim_messages = []

        # Show false accusation notice prominently if it just fired
        false_acc_notice = st.session_state.pop("rahim_false_accusation_notice", None)
        if false_acc_notice:
            st.error(f"🚨 **Rahim's wrong move:** {false_acc_notice}")

        for msg in st.session_state.rahim_messages:
            # Breaking evidence gets special styling
            if msg.startswith("🔬 **BREAKING EVIDENCE**"):
                st.error(msg)
            else:
                st.info(f"🚔 **Inspector Rahim:** {msg}")

        # ── Deduction board (replaces interrogation when active) ──────────────
        if deduction_mode:
            st.divider()
            accused_idx, confirmed = show_deduction_board()
            if confirmed and accused_idx is not None:
                st.session_state.accusation = accused_idx
                st.session_state.deduction_mode = False
                st.session_state.phase = "reveal"
                st.rerun()
            elif accused_idx is None and not confirmed:
                # Player hit Back
                st.session_state.deduction_mode = False
                st.rerun()
            return  # Don't render the interrogation room when deduction board is open

        # ── Evidence board ────────────────────────────────────────────────────
        render_evidence_board()
        st.divider()

        # ── Active suspect header ─────────────────────────────────────────────
        suspect = suspects[idx]
        q_count = len(st.session_state.histories[idx]) // 2
        is_cagey = q_count >= cagey_after
        is_falsely_accused = (idx == falsely_accused_idx) if falsely_accused_idx is not None else False

        # Suspect header + action buttons on the same row
        h_col, btn_col1, btn_col2 = st.columns([3, 1, 1])
        with h_col:
            suspect_label = suspect['name']
            if is_falsely_accused:
                suspect_label += " 🚨"
            st.subheader(f"Interrogating: {suspect_label}")
            st.caption(f"{suspect['relationship_to_victim']} · Alibi: {suspect['alibi']}")

            # Show special notice for falsely accused suspect
            if is_falsely_accused:
                st.markdown(
                    "<div style='background:#2a1a1a;border-left:4px solid #cc4444;"
                    "padding:8px 12px;border-radius:4px;margin:4px 0;font-size:0.85em'>"
                    "🚨 <strong>Rahim publicly accused this suspect.</strong> "
                    "They are hostile and lawyering up.</div>",
                    unsafe_allow_html=True
                )

        with btn_col1:
            # Challenge Alibi button
            alibi_key = f"alibi_challenged_{idx}"
            if not st.session_state.get(alibi_key):
                if st.button("🔎 Challenge Alibi", key=f"ch_alibi_{idx}",
                             use_container_width=True,
                             help="Press them for a specific verifiable alibi detail"):
                    with st.spinner(f"Pressing {suspect['name']} on their alibi..."):
                        result = challenge_alibi(client, idx)
                    st.session_state[alibi_key] = True
                    if result.get("response"):
                        evasive = result.get("is_evasive", False)
                        verdict = "⚠️ Evasive answer" if evasive else "📋 Detail provided"
                        st.warning(f"{verdict}: *{result['response']}*")
                    st.session_state.pop("sq_key", None)
                    _advance_turn(client)
                    st.rerun()
            else:
                st.caption("✓ Alibi challenged")

        with btn_col2:
            # Call Witness button — one use per game
            if not witness_used:
                if st.button("📢 Call Witness", key=f"witness_{idx}",
                             use_container_width=True,
                             help="Call a local witness who may have seen this suspect"):
                    with st.spinner("Locating a witness..."):
                        result = call_witness(client, idx)
                    if result.get("witness_statement"):
                        confirms = result.get("confirms_alibi", True)
                        verdict = "✅ Confirms alibi" if confirms else "❌ Contradicts alibi"
                        st.info(
                            f"📢 **{result['witness_name']}** ({verdict})\n\n"
                            f"*\"{result['witness_statement']}\"*"
                        )
                    _advance_turn(client)
                    st.rerun()
            else:
                st.caption("📢 Witness called")

        if is_cagey and not is_falsely_accused:
            st.warning(
                f"⚠️ {suspect['name']} has been questioned {q_count} times and is becoming "
                f"uncooperative. Consider switching suspects."
            )

        # ── Suggested questions ───────────────────────────────────────────────
        questions = st.session_state.get("suggested_questions", [])
        if questions:
            st.caption("💡 Suggested questions:")
            sq_cols = st.columns(len(questions))
            for j, q in enumerate(questions):
                with sq_cols[j]:
                    if st.button(q, key=f"sq_{idx}_{j}_{q[:15]}", use_container_width=True):
                        st.session_state.pending_question = q
                        st.rerun()

        st.markdown("")

        # ── Conversation history ──────────────────────────────────────────────
        for msg in st.session_state.histories[idx]:
            role = msg["role"]
            label = "user" if role == "user" else "assistant"
            with st.chat_message(label):
                content = msg["content"]
                if content.startswith("[Confrontation]"):
                    st.markdown(f"⚡ *{content.replace('[Confrontation] ', '')}*")
                elif content.startswith("[Alibi Challenge]"):
                    st.markdown(f"🔎 *Alibi challenge issued*")
                else:
                    st.write(content)

        # ── Rahim's interrogations of this suspect ────────────────────────────
        rahim_all = st.session_state.get("rahim_interrogations", {}).get(str(idx), [])
        if rahim_all:
            with st.expander(
                f"🚔 Rahim questioned {suspect['name']} "
                f"({len(rahim_all)} time{'s' if len(rahim_all) > 1 else ''})",
                expanded=False
            ):
                for v_num, entry in enumerate(reversed(rahim_all), 1):
                    if len(rahim_all) > 1:
                        st.caption(f"Visit {len(rahim_all) - v_num + 1}")
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
                        f"<div style='background:#111;border-left:3px solid #333;"
                        f"padding:8px 14px;border-radius:4px;margin:4px 0;"
                        f"font-style:italic;color:#777'>"
                        f"Rahim thinks: {entry.get('rahim_reaction','')}</div>",
                        unsafe_allow_html=True
                    )
                    if v_num < len(rahim_all):
                        st.markdown("---")

        # ── Scroll anchor ─────────────────────────────────────────────────────
        st.markdown("<div id='chat-anchor'></div>", unsafe_allow_html=True)

        # ── Chat input ────────────────────────────────────────────────────────
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
            st.session_state.setdefault("clues", []).extend(new_clues)
            get_rahim_interrogation(client, idx)
            st.session_state.pop("sq_key", None)
            st.session_state.pop("suggested_questions", None)
            _advance_turn(client)
            st.rerun()