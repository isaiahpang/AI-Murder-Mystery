import streamlit as st
from groq import Groq

from config import MAX_TURNS, CAGEY_AFTER, ACT2_START, ACT3_START
from api import (
    interrogate_suspect, extract_clues,
    get_ai_detective_update, get_rahim_commentary,
    get_rahim_interrogation, get_suggested_questions,
    cross_examine_suspect, challenge_alibi,
    investigate_physical_clue, call_witness,
    generate_breaking_evidence,
)
from ui.evidence import render_evidence_board

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

def _get_act(turn: int) -> int:
    """Return current act number based on turn."""
    if turn >= ACT3_START:
        return 3
    elif turn >= ACT2_START:
        return 2
    return 1

def _get_effective_cagey(act: int) -> int:
    """Cagey threshold tightens in act 3."""
    return max(2, CAGEY_AFTER - 1) if act == 3 else CAGEY_AFTER

def _suspect_contradiction_count(suspect_name: str) -> int:
    """Count contradiction-type clues linked to a suspect."""
    return sum(
        1 for c in st.session_state.get("clues", [])
        if c.get("type") == "contradiction" and c.get("links_to_suspect") == suspect_name
    )

def _refresh_suggested_questions(client: Groq, idx: int):
    """Fetch fresh suggested questions for the active suspect."""
    st.session_state.suggested_questions = get_suggested_questions(client, idx)

def _maybe_refresh_rahim_interrogation(client: Groq, idx: int):
    """Generate a Rahim interrogation only when suspect changes or after a player turn."""
    rahim_key = f"rahim_int_rendered_{idx}_{len(st.session_state.histories[idx])}"
    if st.session_state.get("rahim_int_key") != rahim_key:
        get_rahim_interrogation(client, idx)
        st.session_state.rahim_int_key = rahim_key

def _advance_turn(client: Groq):
    """Increment turn, trigger Rahim updates, and fire act 3 breaking evidence if due."""
    turn = st.session_state.get("turn", 0) + 1
    st.session_state.turn = turn

    # Act 3 entry — drop breaking evidence once
    if turn == ACT3_START and not st.session_state.get("breaking_evidence_dropped"):
        with st.spinner("🚨 Breaking evidence coming in..."):
            result = generate_breaking_evidence(client)
        if result:
            st.session_state.breaking_evidence = result
        st.session_state.breaking_evidence_dropped = True

    # Rahim milestone first, then cadence
    rahim = get_ai_detective_update(client, turn)
    if rahim:
        st.session_state.setdefault("rahim_messages", []).append(rahim["message"])
        if rahim.get("accusation"):
            st.session_state.rahim_accused = rahim["accusation"]
        if turn >= MAX_TURNS:
            st.session_state.rahim_solved = True
            st.session_state.accusation = None
            st.session_state.phase = "reveal"
    else:
        commentary = get_rahim_commentary(client, turn)
        if commentary:
            st.session_state.setdefault("rahim_messages", []).append(commentary)

def _handle_pending_actions(client: Groq):
    """Process confront/investigate actions triggered from evidence board buttons."""
    case = st.session_state.case

    confront = st.session_state.pop("pending_confront", None)
    if confront:
        suspect_idx = confront["suspect_index"]
        suspect = case["suspects"][suspect_idx]
        with st.spinner(f"Confronting {suspect['name']}..."):
            result = cross_examine_suspect(client, suspect_idx, confront["claim"])
        if result.get("response"):
            st.session_state.active_suspect = suspect_idx
            st.session_state.pop("sq_key", None)
            st.session_state.pop("rahim_int_key", None)
            _advance_turn(client)
        return True

    investigate = st.session_state.pop("pending_investigate", None)
    if investigate:
        with st.spinner("Sending to forensics..."):
            result = investigate_physical_clue(client, investigate["clue_text"])
        if result.get("finding"):
            st.session_state[f"investigated_{investigate['clue_id']}"] = True
            st.session_state.forensic_flash = {
                "finding": result["finding"],
                "corroborates": result.get("corroborates", False),
                "suspect": result.get("points_to_suspect", ""),
            }
            _advance_turn(client)
        return True

    return False

def show_interrogation():
    """Render the full interrogation screen."""
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)

    client: Groq = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]
    turn = st.session_state.get("turn", 0)
    idx = st.session_state.get("active_suspect", 0)
    act = _get_act(turn)
    cagey_after = _get_effective_cagey(act)
    witness_used = st.session_state.get("witness_used", False)

    # Handle evidence board actions before anything else
    if _handle_pending_actions(client):
        st.rerun()

    # Cache-gated API calls — only fire when inputs change
    sq_key = f"sq_{idx}_{len(st.session_state.histories[idx])}"
    if st.session_state.get("sq_key") != sq_key:
        _refresh_suggested_questions(client, idx)
        st.session_state.sq_key = sq_key

    _maybe_refresh_rahim_interrogation(client, idx)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        turns_left = MAX_TURNS - turn
        st.markdown(f"### ⏱️ Turns Left: {turns_left}/{MAX_TURNS}")
        st.progress(turn / MAX_TURNS)

        # Act indicator
        act_labels = {
            1: ("🟢 Act 1 — Exploration", "success"),
            2: ("🟡 Act 2 — Pressure", "warning"),
            3: ("🔴 Act 3 — Crisis", "error"),
        }
        act_label, act_style = act_labels[act]
        getattr(st, act_style)(act_label)

        st.divider()
        st.markdown("### 👤 Suspects")
        for i, s in enumerate(suspects):
            q_count = len(st.session_state.histories[i]) // 2
            contradiction_count = _suspect_contradiction_count(s["name"])
            is_cagey = q_count >= cagey_after
            rahim_visited = i in st.session_state.get("rahim_visited_suspects", set())

            # Build label with visual weight indicators
            indicators = []
            if is_cagey:
                indicators.append("🔴")
            if contradiction_count >= 2:
                indicators.append("⚠️" * min(contradiction_count, 3))
            if rahim_visited:
                indicators.append("🚔")
            prefix = " ".join(indicators) + " " if indicators else ""
            label = f"{prefix}{s['name']} ({q_count}Q · {contradiction_count}⚠️)"

            if st.button(label, key=f"sel_{i}", use_container_width=True):
                st.session_state.active_suspect = i
                st.session_state.pop("sq_key", None)
                st.session_state.pop("rahim_int_key", None)
                st.session_state.pop("suggested_questions", None)
                st.rerun()

        st.divider()

        # Notes panel — no rerun on keystroke
        st.markdown("### 📓 Your Notes")
        new_notes = st.text_area(
            label="notes",
            value=st.session_state.get("player_notes", ""),
            height=160,
            placeholder="Write your suspicions here...",
            label_visibility="collapsed",
            key="notes_input",
            on_change=lambda: st.session_state.update({
                "player_notes": st.session_state.notes_input,
                "notes_saved_flash": True,
            })
        )
        if st.session_state.pop("notes_saved_flash", False):
            st.caption("✓ Saved")

        st.divider()
        st.markdown("### ⚖️ Accuse")
        for i, s in enumerate(suspects):
            if st.button(f"Accuse {s['name']}", key=f"acc_{i}", use_container_width=True):
                st.session_state.deduction_suspect_index = i
                st.session_state.phase = "deduction"
                st.rerun()

    # ── Main layout ───────────────────────────────────────────────────────────
    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title("🔍 Interrogation Room")

        # Breaking evidence flash
        breaking = st.session_state.pop("breaking_evidence", None)
        if breaking:
            st.error(
                f"🚨 **BREAKING: {breaking.get('headline', 'New evidence')}**\n\n"
                f"{breaking.get('detail', '')}"
            )

        # Forensic result flash
        forensic = st.session_state.pop("forensic_flash", None)
        if forensic:
            verdict = "✅ Corroborated" if forensic["corroborates"] else "❓ Complicated"
            st.info(
                f"🔬 **Forensic Report ({verdict}):** {forensic['finding']}"
                + (f"\n👤 Implicates: **{forensic['suspect']}**" if forensic["suspect"] else "")
            )

        # Rahim messages
        for msg in st.session_state.get("rahim_messages", []):
            st.info(f"🚔 **Inspector Rahim:** {msg}")

        render_evidence_board()
        st.divider()

        # Active suspect header with weight indicators
        suspect = suspects[idx]
        q_count = len(st.session_state.histories[idx]) // 2
        is_cagey = q_count >= cagey_after
        contradiction_count = _suspect_contradiction_count(suspect["name"])
        rahim_visited = idx in st.session_state.get("rahim_visited_suspects", set())

        h_col, btn_col1, btn_col2 = st.columns([3, 1, 1])
        with h_col:
            # Suspect name with contradiction heat indicator
            heat = ""
            if contradiction_count >= 3:
                heat = " 🔥🔥🔥"
            elif contradiction_count == 2:
                heat = " 🔥🔥"
            elif contradiction_count == 1:
                heat = " 🔥"
            st.subheader(f"Interrogating: {suspect['name']}{heat}")

            caption_parts = [
                suspect["relationship_to_victim"],
                f"Alibi: {suspect['alibi']}",
            ]
            if rahim_visited:
                caption_parts.append("🚔 Rahim has questioned this suspect")
            if is_cagey:
                caption_parts.append(f"🔴 Uncooperative ({q_count} Qs)")
            if contradiction_count > 0:
                caption_parts.append(f"⚠️ {contradiction_count} contradiction{'s' if contradiction_count > 1 else ''} on file")
            st.caption(" · ".join(caption_parts))

        with btn_col1:
            alibi_key = f"alibi_challenged_{idx}"
            if not st.session_state.get(alibi_key):
                if st.button("🔎 Challenge Alibi", key=f"ch_{idx}",
                             use_container_width=True):
                    with st.spinner("Pressing for details..."):
                        challenge_alibi(client, idx)
                    st.session_state[alibi_key] = True
                    st.session_state.pop("sq_key", None)
                    _advance_turn(client)
                    st.rerun()
            else:
                st.caption("✓ Alibi challenged")

        with btn_col2:
            if not witness_used:
                if st.button("📢 Witness", key=f"wit_{idx}",
                             use_container_width=True):
                    with st.spinner("Locating witness..."):
                        result = call_witness(client, idx)
                    if result.get("witness_statement"):
                        confirms = result.get("confirms_alibi", True)
                        verdict = "✅ Confirms" if confirms else "❌ Contradicts"
                        st.info(
                            f"📢 **{result['witness_name']}** ({verdict})\n\n"
                            f"*\"{result['witness_statement']}\"*"
                        )
                    _advance_turn(client)
                    st.rerun()
            else:
                st.caption("📢 Witness called")

        if is_cagey:
            st.warning(f"⚠️ {suspect['name']} is becoming uncooperative. Consider switching suspects.")

        # Act 3 urgency banner
        if act == 3:
            st.error("🔴 **Act 3 — Crisis:** Inspector Rahim is closing in. Make your move.")

        # Suggested questions
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

        # Conversation history
        for msg in st.session_state.histories[idx]:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                content = msg["content"]
                if content.startswith("[Confrontation]"):
                    st.markdown(f"⚡ *{content.replace('[Confrontation] ', '')}*")
                elif content.startswith("[Alibi Challenge]"):
                    st.markdown("🔎 *Alibi challenged — demanding verifiable detail*")
                else:
                    st.write(content)

        # Rahim's interrogation panel
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

            new_clues = extract_clues(client, suspect["name"], reply)
            st.session_state.setdefault("clues", []).extend(new_clues)

            # Invalidate caches so next render refreshes properly
            st.session_state.pop("sq_key", None)
            st.session_state.pop("rahim_int_key", None)
            st.session_state.pop("suggested_questions", None)

            _advance_turn(client)
            st.rerun()