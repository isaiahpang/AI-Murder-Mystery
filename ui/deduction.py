import streamlit as st
from groq import Groq
from api import validate_deduction

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

def show_deduction():
    """Render the deduction board — player must build a case before accusing."""
    st.markdown(TRANSITION_CSS, unsafe_allow_html=True)

    client: Groq = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]
    accused_index = st.session_state.get("deduction_suspect_index", 0)
    accused = suspects[accused_index]
    clues = st.session_state.get("clues", [])

    _, col, _ = st.columns([1, 6, 1])
    with col:
        st.title("⚖️ Build Your Case")
        st.markdown(
            f"<div style='background:#1a1a1a;border-left:4px solid #c8a84b;"
            f"padding:12px 16px;border-radius:4px;margin-bottom:20px'>"
            f"You are about to formally accuse <strong style='color:#c8a84b'>"
            f"{accused['name']}</strong>. Before you can proceed, you must provide "
            f"evidence for each of the three pillars of your case.</div>",
            unsafe_allow_html=True
        )

        # Show collected clues as reference
        with st.expander("📋 Your collected clues (for reference)", expanded=False):
            if clues:
                for c in clues:
                    st.markdown(f"- {c['text']}")
            else:
                st.caption("No clues collected yet.")

        st.divider()

        # Three input fields — motive, alibi flaw, evidence
        st.markdown("### 1. Motive")
        st.caption("Why would this suspect want the victim dead?")
        motive = st.text_area(
            "motive", label_visibility="collapsed",
            placeholder="e.g. The victim was blackmailing them over a gambling debt...",
            height=80, key="deduction_motive"
        )

        st.markdown("### 2. Alibi Flaw")
        st.caption("What is wrong with their alibi? What specific contradiction did you find?")
        alibi_flaw = st.text_area(
            "alibi_flaw", label_visibility="collapsed",
            placeholder="e.g. They said they were at Bedok 85 but the EZ-Link record shows...",
            height=80, key="deduction_alibi"
        )

        st.markdown("### 3. Supporting Evidence")
        st.caption("What physical evidence, witness statement, or clue links them to the crime?")
        evidence = st.text_area(
            "evidence", label_visibility="collapsed",
            placeholder="e.g. The forensic report on the broken keychain matched...",
            height=80, key="deduction_evidence"
        )

        st.divider()

        # Feedback from previous validation attempt
        feedback = st.session_state.get("deduction_feedback")
        if feedback:
            strength = feedback.get("strength", "weak")
            colour = {"strong": "#2a6e2a", "reasonable": "#6e5a1a", "weak": "#6e1a1a"}.get(strength, "#333")
            st.markdown(
                f"<div style='background:{colour};border-radius:4px;"
                f"padding:12px 16px;margin-bottom:12px'>"
                f"<strong>Assessment ({strength.title()}):</strong> {feedback.get('feedback','')}</div>",
                unsafe_allow_html=True
            )

        col_validate, col_back = st.columns([1, 1])

        with col_validate:
            all_filled = all([motive.strip(), alibi_flaw.strip(), evidence.strip()])
            if st.button(
                "🔍 Validate Deduction",
                type="primary",
                use_container_width=True,
                disabled=not all_filled
            ):
                with st.spinner("Senior officer reviewing your case..."):
                    result = validate_deduction(
                        client, accused_index,
                        motive.strip(), alibi_flaw.strip(), evidence.strip()
                    )
                st.session_state.deduction_feedback = result

                if result.get("valid") and result.get("strength") in ("strong", "reasonable"):
                    # Deduction accepted — proceed to accusation
                    st.session_state.accusation = accused_index
                    st.session_state.deduction_feedback = None
                    st.session_state.phase = "reveal"
                    st.rerun()
                else:
                    st.rerun()

        with col_back:
            if st.button("← Back to Investigation", use_container_width=True):
                st.session_state.deduction_feedback = None
                st.session_state.phase = "interrogate"
                st.rerun()