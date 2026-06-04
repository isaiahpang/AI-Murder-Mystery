"""
ui/deduction.py — The Deduction Board

Replaces the raw sidebar "Accuse X" buttons with a structured reasoning gate.
The player must:
  1. Select a suspect
  2. Provide reasoning (free text, with flagged clues pre-populated)
  3. Request an evaluation from the AI (optional but encouraged)
  4. Formally accuse

This turns the accusation from a guess into a conclusion.
"""

import streamlit as st
from api import evaluate_deduction

# Verdict styling
VERDICT_CONFIG = {
    "solid":  {"colour": "#2a7a2a", "border": "#4caf50", "icon": "✅", "label": "Case is solid"},
    "shaky":  {"colour": "#7a5a00", "border": "#c8a84b", "icon": "⚠️", "label": "Case is shaky"},
    "weak":   {"colour": "#7a1a1a", "border": "#cc4444", "icon": "❌", "label": "Case is weak"},
}

def show_deduction_board():
    """
    Render the deduction board in the main column.
    Called from interrogation.py when the player clicks "Build My Case".
    Returns (accused_index, confirmed) — confirmed=True means player hit "Formally Accuse".
    Returns (None, False) if player cancels or hasn't committed yet.
    """
    case = st.session_state.case
    suspects = case["suspects"]
    clues = st.session_state.get("clues", [])
    flagged = st.session_state.get("flagged_clues", set())

    st.markdown(
        "<div style='background:#1a1a2e;border:2px solid #c8a84b;border-radius:8px;"
        "padding:20px 24px;margin-bottom:16px'>"
        "<div style='font-size:1.4em;font-weight:bold;color:#c8a84b;margin-bottom:4px'>"
        "⚖️ Deduction Board</div>"
        "<div style='color:#999;font-size:0.9em'>"
        "Before you make a formal accusation, build your case. "
        "Select a suspect, state your reasoning, and optionally get it evaluated."
        "</div></div>",
        unsafe_allow_html=True
    )

    # ── Step 1: Select the suspect ────────────────────────────────────────────
    st.markdown("#### Step 1 — Select your suspect")
    suspect_names = [s["name"] for s in suspects]

    # Pre-select whoever the player last hovered (active suspect) or first suspect
    default_idx = st.session_state.get("deduction_suspect_idx",
                                       st.session_state.get("active_suspect", 0))
    chosen_name = st.radio(
        "Who did it?",
        suspect_names,
        index=default_idx,
        horizontal=True,
        key="deduction_suspect_radio",
        label_visibility="collapsed",
    )
    chosen_idx = suspect_names.index(chosen_name)
    st.session_state.deduction_suspect_idx = chosen_idx

    chosen_suspect = suspects[chosen_idx]
    st.caption(
        f"{chosen_suspect['relationship_to_victim']} · "
        f"Alibi: {chosen_suspect['alibi']} · "
        f"Questioned {len(st.session_state.histories[chosen_idx]) // 2} times"
    )

    # ── Step 2: Show relevant evidence ───────────────────────────────────────
    st.markdown("#### Step 2 — Evidence against this suspect")

    suspect_clues = [c for c in clues if c.get("links_to_suspect") == chosen_name]
    flagged_clues = []

    if suspect_clues:
        for ci, c in enumerate(suspect_clues):
            clue_id = f"{chosen_name}_{clues.index(c)}"
            is_flagged = clue_id in flagged
            flag_star = "⭐ " if is_flagged else "   "
            ctype = c.get("type", "")
            type_colours = {
                "contradiction": "#cc4444",
                "motive": "#cc7722",
                "physical": "#8844cc",
                "witness": "#2288aa",
                "alibi": "#446688",
            }
            colour = type_colours.get(ctype, "#666")
            st.markdown(
                f"<div style='background:#141414;border-left:4px solid {colour};"
                f"padding:8px 12px;border-radius:0 4px 4px 0;margin:4px 0;"
                f"font-size:0.88em;color:#ddd'>"
                f"{flag_star}<strong style='color:{colour};font-size:0.8em'>[{ctype}]</strong> "
                f"{c['text']}</div>",
                unsafe_allow_html=True
            )
            if is_flagged:
                flagged_clues.append(c["text"])
    else:
        st.markdown(
            "<div style='color:#666;font-style:italic;padding:8px 0'>"
            "No clues collected specifically against this suspect yet. "
            "Interrogate them more before accusing.</div>",
            unsafe_allow_html=True
        )

    # ── Step 3: Player's reasoning ────────────────────────────────────────────
    st.markdown("#### Step 3 — State your reasoning")

    # Pre-populate with flagged clues to give the player a head start
    prefill = ""
    if flagged_clues:
        prefill = "Key evidence:\n" + "\n".join(f"- {t}" for t in flagged_clues) + "\n\nBecause: "

    reasoning = st.text_area(
        "Why do you believe this suspect is guilty?",
        value=st.session_state.get("deduction_reasoning", prefill),
        height=120,
        placeholder=(
            f"e.g. {chosen_name}'s alibi doesn't hold up because...\n"
            "The evidence shows...\nThey had motive because..."
        ),
        key="deduction_reasoning_input",
    )
    st.session_state.deduction_reasoning = reasoning

    # ── Step 4: Evaluate (optional) ───────────────────────────────────────────
    st.markdown("#### Step 4 — Evaluate your case (optional)")

    eval_col, _ = st.columns([2, 3])
    with eval_col:
        if st.button("🔍 Evaluate My Case", use_container_width=True,
                     help="Get an assessment of how solid your reasoning is before accusing"):
            if not reasoning.strip():
                st.warning("Write your reasoning first before requesting an evaluation.")
            else:
                with st.spinner("Reviewing your case file..."):
                    evaluation = evaluate_deduction(
                        st.session_state.client, chosen_name, reasoning
                    )
                st.session_state.deduction_evaluation = evaluation

    # Show evaluation if one exists for current suspect
    evaluation = st.session_state.get("deduction_evaluation")
    # Clear evaluation if suspect changed
    if st.session_state.get("last_evaluated_suspect") != chosen_name:
        evaluation = None
        st.session_state.pop("deduction_evaluation", None)

    if evaluation:
        st.session_state.last_evaluated_suspect = chosen_name
        verdict = evaluation.get("verdict", "weak")
        vcfg = VERDICT_CONFIG.get(verdict, VERDICT_CONFIG["weak"])
        ready = evaluation.get("ready_to_accuse", False)

        v_colour = vcfg["colour"]
        v_border = vcfg["border"]
        v_icon = vcfg["icon"]
        v_label = vcfg["label"].upper()
        v_feedback = evaluation.get("feedback", "")
        st.markdown(
            f"<div style='background:{v_colour}22;border:2px solid {v_border};"
            f"border-radius:8px;padding:14px 18px;margin:12px 0'>"
            f"<div style='font-size:1.1em;font-weight:bold;color:{v_border}'>"
            f"{v_icon} {v_label}</div>"
            f"<div style='margin-top:8px;color:#ddd;font-size:0.9em'>"
            f"{v_feedback}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

        missing = evaluation.get("missing_pieces", [])
        if missing:
            st.markdown(
                "<div style='background:#1a1a1a;border-left:3px solid #555;"
                "padding:10px 14px;border-radius:4px;margin:8px 0'>"
                "<div style='font-size:0.8em;color:#888;font-weight:bold;margin-bottom:6px'>"
                "GAPS IN YOUR CASE</div>" +
                "".join(
                    f"<div style='font-size:0.88em;color:#bbb;margin:3px 0'>• {p}</div>"
                    for p in missing
                ) +
                "</div>",
                unsafe_allow_html=True
            )
    else:
        ready = False  # Can still accuse, but without the green light

    # ── Step 5: Formal accusation ─────────────────────────────────────────────
    st.markdown("#### Step 5 — Formal accusation")

    if evaluation and ready:
        st.success("Your case is solid. You're ready to make a formal accusation.")
    elif evaluation and not ready:
        st.warning("Your case has gaps. You *can* still accuse, but you may be wrong.")
    else:
        st.caption("You can accuse without evaluating — but you're taking a risk.")

    acc_col1, acc_col2 = st.columns([2, 1])
    with acc_col1:
        if st.button(
            f"⚖️ Formally Accuse {chosen_name}",
            type="primary",
            use_container_width=True,
            key="formal_accuse_btn",
        ):
            # Clear deduction state
            st.session_state.pop("deduction_evaluation", None)
            st.session_state.pop("last_evaluated_suspect", None)
            return chosen_idx, True

    with acc_col2:
        if st.button("← Back to interrogation", use_container_width=True, key="deduction_back_btn"):
            return None, False

    return None, False