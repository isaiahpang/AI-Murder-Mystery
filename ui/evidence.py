import streamlit as st

# ── Clue type display config ─────────────────────────────────────────────────
# Each type has a plain-English label, icon, border colour, and background colour.
# Border colour signals importance: red = most significant, muted = informational.

CLUE_CONFIG = {
    "contradiction": {
        "label": "Story doesn't add up",
        "icon": "⚠️",
        "border": "#cc4444",
        "bg": "#2a1a1a",
    },
    "motive": {
        "label": "Possible motive",
        "icon": "💢",
        "border": "#cc7722",
        "bg": "#2a1e10",
    },
    "physical": {
        "label": "Physical evidence",
        "icon": "🔬",
        "border": "#8844cc",
        "bg": "#1e1a2a",
    },
    "witness": {
        "label": "Spotted nearby",
        "icon": "👁️",
        "border": "#2288aa",
        "bg": "#0f1e24",
    },
    "alibi": {
        "label": "Alibi claim",
        "icon": "📋",
        "border": "#446688",
        "bg": "#141e28",
    },
}

DEFAULT_CONFIG = {
    "label": "General observation",
    "icon": "🔍",
    "border": "#444",
    "bg": "#1a1a1a",
}

def _clue_card_html(text: str, ctype: str, cross_ref: str, is_flagged: bool) -> str:
    """Render a single clue card as styled HTML."""
    cfg = CLUE_CONFIG.get(ctype, DEFAULT_CONFIG)
    flag = "⭐" if is_flagged else ""
    cross = (
        f"<div style='margin-top:5px;font-size:0.78em;color:#aaa'>"
        f"↔ also implicates <strong>{cross_ref}</strong></div>"
        if cross_ref else ""
    )
    return (
        f"<div style='"
        f"background:{cfg['bg']};"
        f"border-left:4px solid {cfg['border']};"
        f"border-radius:0 4px 4px 0;"
        f"padding:8px 12px;"
        f"margin:5px 0;"
        f"'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
        f"<span style='font-size:0.72em;color:{cfg['border']};text-transform:uppercase;"
        f"letter-spacing:1px;font-weight:bold'>"
        f"{cfg['icon']} {cfg['label']}</span>"
        f"<span style='font-size:0.9em'>{flag}</span>"
        f"</div>"
        f"<div style='margin-top:4px;font-size:0.88em;color:#ddd'>{text}</div>"
        f"{cross}"
        f"</div>"
    )

def render_evidence_board():
    """Render the detective's case file — clue cards grouped by suspect with cross-links."""
    clues = st.session_state.get("clues", [])
    flagged = st.session_state.setdefault("flagged_clues", set())
    case = st.session_state.case
    suspects = case["suspects"]
    suspect_names = [s["name"] for s in suspects]

    # ── Header row ────────────────────────────────────────────────────────────
    total = len(clues)
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:space-between;"
        f"margin-bottom:8px'>"
        f"<span style='font-size:1.1em;font-weight:bold;color:#c8a84b'>🗂️ Case File</span>"
        f"<span style='font-size:0.8em;color:#888'>{total} clue{'s' if total != 1 else ''} collected</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Opening scene clue
    opening = case.get("opening_clue", "")
    if opening:
        st.markdown(
            f"<div style='background:#111;border:1px dashed #c8a84b;border-radius:4px;"
            f"padding:8px 12px;margin-bottom:10px;font-size:0.88em;color:#c8a84b'>"
            f"📍 <strong>Scene clue:</strong> {opening}</div>",
            unsafe_allow_html=True
        )

    if not clues:
        st.caption("No clues collected yet. Start interrogating suspects.")
        return

    # ── Suspect columns ────────────────────────────────────────────────────────
    # Group clues: primary column = links_to_suspect, cross-ref = any other suspect mentioned
    linked = {s["name"]: [] for s in suspects}
    unlinked = []

    for ci, c in enumerate(clues):
        primary = c.get("links_to_suspect", "")
        if primary in linked:
            linked[primary].append((ci, c))
        else:
            unlinked.append((ci, c))

    # Build per-suspect cross-reference: does this clue text mention another suspect?
    def find_cross_ref(text: str, primary: str) -> str:
        for name in suspect_names:
            if name != primary and name.split()[0] in text:
                return name
        return ""

    # Column headers with clue counts
    cols = st.columns(3)
    for i, suspect in enumerate(suspects):
        count = len(linked[suspect["name"]])
        with cols[i]:
            st.markdown(
                f"<div style='text-align:center;padding:6px;background:#1a1a1a;"
                f"border-radius:4px;margin-bottom:6px'>"
                f"<div style='font-size:0.9em;font-weight:bold;color:#e0d6c8'>"
                f"{suspect['name']}</div>"
                f"<div style='font-size:0.75em;color:#888'>"
                f"{count} clue{'s' if count != 1 else ''}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    # Clue cards — sorted so contradictions and motives float to top
    TYPE_ORDER = ["contradiction", "motive", "physical", "witness", "alibi", ""]

    cols = st.columns(3)
    for i, suspect in enumerate(suspects):
        suspect_clues = sorted(
            linked[suspect["name"]],
            key=lambda x: TYPE_ORDER.index(x[1].get("type", ""))
            if x[1].get("type", "") in TYPE_ORDER else 99
        )
        with cols[i]:
            if suspect_clues:
                for ci, c in suspect_clues:
                    clue_id = f"{suspect['name']}_{ci}"
                    is_flagged = clue_id in flagged
                    cross = find_cross_ref(c.get("text", ""), suspect["name"])

                    # Render card HTML
                    st.markdown(
                        _clue_card_html(c["text"], c.get("type", ""), cross, is_flagged),
                        unsafe_allow_html=True
                    )

                    # Flag button sits below the card
                    btn_label = "★ Flagged" if is_flagged else "☆ Flag"
                    if st.button(
                        btn_label,
                        key=f"flag_{clue_id}",
                        use_container_width=True,
                        help="Mark this clue as important"
                    ):
                        if is_flagged:
                            flagged.discard(clue_id)
                        else:
                            flagged.add(clue_id)
                        st.session_state.flagged_clues = flagged
                        st.rerun()
            else:
                st.markdown(
                    "<div style='text-align:center;color:#555;font-size:0.85em;"
                    "padding:20px 0'>No clues yet</div>",
                    unsafe_allow_html=True
                )

    # ── General / unlinked clues ──────────────────────────────────────────────
    if unlinked:
        st.markdown(
            "<div style='margin-top:12px;font-size:0.85em;font-weight:bold;"
            "color:#888'>GENERAL OBSERVATIONS</div>",
            unsafe_allow_html=True
        )
        for ci, c in unlinked:
            st.markdown(
                _clue_card_html(c["text"], c.get("type", ""), "", False),
                unsafe_allow_html=True
            )

    # ── Flagged summary ───────────────────────────────────────────────────────
    if flagged:
        st.markdown(
            "<div style='margin-top:14px;font-size:0.85em;font-weight:bold;"
            "color:#c8a84b'>⭐ FLAGGED CLUES</div>",
            unsafe_allow_html=True
        )
        for ci, c in enumerate(clues):
            clue_id_check = None
            # Find which flagged id matches this clue
            for s in suspects:
                test_id = f"{s['name']}_{ci}"
                if test_id in flagged:
                    clue_id_check = test_id
                    break
            if clue_id_check:
                st.markdown(
                    _clue_card_html(c["text"], c.get("type", ""), "", True),
                    unsafe_allow_html=True
                )

    # ── Relationship map ──────────────────────────────────────────────────────
    relationships = case.get("relationships", [])
    if relationships:
        st.markdown(
            "<div style='margin-top:14px;font-size:0.85em;font-weight:bold;"
            "color:#888'>KNOWN RELATIONSHIPS</div>",
            unsafe_allow_html=True
        )
        for r in relationships:
            names = " & ".join(r.get("between", []))
            st.markdown(
                f"<div style='background:#141414;border-left:3px solid #444;"
                f"padding:6px 12px;margin:3px 0;border-radius:0 4px 4px 0;"
                f"font-size:0.85em'>"
                f"<strong style='color:#aaa'>{names}</strong> — "
                f"<span style='color:#888'>{r.get('description','')}</span></div>",
                unsafe_allow_html=True
            )