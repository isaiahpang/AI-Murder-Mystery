import streamlit as st

# ── Clue type display config ──────────────────────────────────────────────────
CLUE_CONFIG = {
    "contradiction": {"label": "Story doesn't add up", "icon": "⚠️", "border": "#cc4444", "bg": "#2a1a1a"},
    "motive":        {"label": "Possible motive",       "icon": "💢", "border": "#cc7722", "bg": "#2a1e10"},
    "physical":      {"label": "Physical evidence",     "icon": "🔬", "border": "#8844cc", "bg": "#1e1a2a"},
    "witness":       {"label": "Spotted nearby",        "icon": "👁️", "border": "#2288aa", "bg": "#0f1e24"},
    "alibi":         {"label": "Alibi claim",           "icon": "📋", "border": "#446688", "bg": "#141e28"},
}
DEFAULT_CONFIG = {"label": "General observation", "icon": "🔍", "border": "#444", "bg": "#1a1a1a"}
TYPE_ORDER = ["contradiction", "motive", "physical", "witness", "alibi"]

def _clue_card_html(text: str, ctype: str, cross_ref: str, is_flagged: bool) -> str:
    """Render a single clue card as styled HTML."""
    cfg = CLUE_CONFIG.get(ctype, DEFAULT_CONFIG)
    flag = "⭐ " if is_flagged else ""
    cross = (
        f"<div style='margin-top:5px;font-size:0.78em;color:#aaa'>"
        f"↔ also implicates <strong>{cross_ref}</strong></div>"
        if cross_ref else ""
    )
    return (
        f"<div style='background:{cfg['bg']};border-left:4px solid {cfg['border']};"
        f"border-radius:0 4px 4px 0;padding:8px 12px;margin:5px 0'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start'>"
        f"<span style='font-size:0.72em;color:{cfg['border']};text-transform:uppercase;"
        f"letter-spacing:1px;font-weight:bold'>{cfg['icon']} {cfg['label']}</span>"
        f"<span style='font-size:0.9em'>{flag}</span>"
        f"</div>"
        f"<div style='margin-top:4px;font-size:0.88em;color:#ddd'>{text}</div>"
        f"{cross}"
        f"</div>"
    )

def render_evidence_board():
    """Render the detective's case file with verification actions on each clue."""
    clues = st.session_state.get("clues", [])
    flagged = st.session_state.setdefault("flagged_clues", set())
    case = st.session_state.case
    suspects = case["suspects"]
    suspect_names = [s["name"] for s in suspects]

    # ── Header ────────────────────────────────────────────────────────────────
    total = len(clues)
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:space-between;"
        f"margin-bottom:8px'>"
        f"<span style='font-size:1.1em;font-weight:bold;color:#c8a84b'>🗂️ Case File</span>"
        f"<span style='font-size:0.8em;color:#888'>{total} clue{'s' if total != 1 else ''} collected</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Opening clue
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
        _render_relationships(case)
        return

    # ── Group clues ───────────────────────────────────────────────────────────
    linked = {s["name"]: [] for s in suspects}
    unlinked = []
    for ci, c in enumerate(clues):
        primary = c.get("links_to_suspect", "")
        if primary in linked:
            linked[primary].append((ci, c))
        else:
            unlinked.append((ci, c))

    def find_cross_ref(text: str, primary: str) -> str:
        for name in suspect_names:
            if name != primary and name.split()[0] in text:
                return name
        return ""

    # ── Column headers ────────────────────────────────────────────────────────
    cols = st.columns(3)
    for i, suspect in enumerate(suspects):
        count = len(linked[suspect["name"]])
        with cols[i]:
            st.markdown(
                f"<div style='text-align:center;padding:6px;background:#1a1a1a;"
                f"border-radius:4px;margin-bottom:6px'>"
                f"<div style='font-size:0.9em;font-weight:bold;color:#e0d6c8'>{suspect['name']}</div>"
                f"<div style='font-size:0.75em;color:#888'>{count} clue{'s' if count != 1 else ''}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    # ── Clue cards per suspect ────────────────────────────────────────────────
    cols = st.columns(3)
    for i, suspect in enumerate(suspects):
        sorted_clues = sorted(
            linked[suspect["name"]],
            key=lambda x: TYPE_ORDER.index(x[1].get("type", "alibi"))
            if x[1].get("type", "") in TYPE_ORDER else 99
        )
        with cols[i]:
            if sorted_clues:
                for ci, c in sorted_clues:
                    clue_id = f"{suspect['name']}_{ci}"
                    is_flagged = clue_id in flagged
                    cross = find_cross_ref(c.get("text", ""), suspect["name"])
                    ctype = c.get("type", "")

                    st.markdown(
                        _clue_card_html(c["text"], ctype, cross, is_flagged),
                        unsafe_allow_html=True
                    )

                    # Action buttons — laid out compactly below each card
                    source = c.get("source", "")
                    btn_cols = st.columns([1, 1, 1])

                    # Flag toggle
                    with btn_cols[0]:
                        flag_label = "★ Flagged" if is_flagged else "☆ Flag"
                        if st.button(flag_label, key=f"flag_{clue_id}", use_container_width=True):
                            flagged.discard(clue_id) if is_flagged else flagged.add(clue_id)
                            st.session_state.flagged_clues = flagged
                            st.rerun()

                    # Confront button — if clue mentions another suspect
                    with btn_cols[1]:
                        if cross and source not in ("confrontation", "alibi_challenge", "forensic", "witness"):
                            cross_idx = next(
                                (j for j, s in enumerate(suspects) if s["name"] == cross), None
                            )
                            if cross_idx is not None:
                                if st.button("⚡ Confront", key=f"confront_{clue_id}", use_container_width=True,
                                             help=f"Confront {cross} with this claim"):
                                    st.session_state.pending_confront = {
                                        "suspect_index": cross_idx,
                                        "claim": c["text"],
                                        "source_suspect": suspect["name"],
                                    }
                                    st.rerun()

                    # Investigate button — physical clues only, not already investigated
                    with btn_cols[2]:
                        if ctype == "physical" and source != "forensic":
                            invest_key = f"investigated_{clue_id}"
                            if not st.session_state.get(invest_key):
                                if st.button("🔬 Investigate", key=f"invest_{clue_id}",
                                             use_container_width=True,
                                             help="Send to forensics for analysis"):
                                    st.session_state.pending_investigate = {
                                        "clue_text": c["text"],
                                        "clue_id": clue_id,
                                    }
                                    st.rerun()
                            else:
                                st.caption("✓ Analysed")
            else:
                st.markdown(
                    "<div style='text-align:center;color:#555;font-size:0.85em;"
                    "padding:20px 0'>No clues yet</div>",
                    unsafe_allow_html=True
                )

    # ── Unlinked clues ────────────────────────────────────────────────────────
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
            for s in suspects:
                test_id = f"{s['name']}_{ci}"
                if test_id in flagged:
                    st.markdown(
                        _clue_card_html(c["text"], c.get("type", ""), "", True),
                        unsafe_allow_html=True
                    )
                    break

    _render_relationships(case)

def _render_relationships(case: dict):
    """Render the suspect relationship map at the bottom of the board."""
    relationships = case.get("relationships", [])
    if not relationships:
        return
    st.markdown(
        "<div style='margin-top:14px;font-size:0.85em;font-weight:bold;"
        "color:#888'>KNOWN RELATIONSHIPS</div>",
        unsafe_allow_html=True
    )
    for r in relationships:
        names = " & ".join(r.get("between", []))
        st.markdown(
            f"<div style='background:#141414;border-left:3px solid #444;"
            f"padding:6px 12px;margin:3px 0;border-radius:0 4px 4px 0;font-size:0.85em'>"
            f"<strong style='color:#aaa'>{names}</strong> — "
            f"<span style='color:#888'>{r.get('description','')}</span></div>",
            unsafe_allow_html=True
        )