import streamlit as st
from groq import Groq

from utils import get_api_key
from api import generate_case
from ui.briefing import show_briefing
from ui.interrogation import show_interrogation
from ui.reveal import show_reveal

# ── Global CSS — dark mystery theme ─────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* Dark background */
.stApp { background-color: #0d0d0d; color: #e0d6c8; }

/* Sidebar */
[data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #2a2a2a; }

/* Buttons */
.stButton > button {
    background-color: #1a1a2e;
    color: #c8a84b;
    border: 1px solid #c8a84b;
    border-radius: 4px;
    font-size: 0.85em;
}
.stButton > button:hover {
    background-color: #c8a84b;
    color: #0d0d0d;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background-color: #c8a84b;
    color: #0d0d0d;
    font-weight: bold;
    border: none;
}
.stButton > button[kind="primary"]:hover {
    background-color: #e0c870;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background-color: #141414;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    margin: 4px 0;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: #141414;
    border: 1px solid #2a2a2a;
    border-radius: 4px;
}

/* Headings */
h1, h2, h3 { color: #c8a84b !important; font-family: Georgia, serif; }

/* Info/warning/success boxes */
[data-testid="stAlert"] { border-radius: 4px; }

/* Divider */
hr { border-color: #2a2a2a; }

/* Caption */
.stCaption { color: #888 !important; }
</style>
"""

def main():
    """App entry point — injects theme, initialises state, routes between phases."""
    st.set_page_config(
        page_title="Singapore Murder Mystery",
        page_icon="🔍",
        layout="wide"
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    if "client" not in st.session_state:
        st.session_state.client = Groq(api_key=get_api_key())

    if "case" not in st.session_state:
        _, col, _ = st.columns([1, 6, 1])
        with col:
            st.markdown(
                "<div style='text-align:center;font-size:3em;margin-bottom:0'>🔍</div>",
                unsafe_allow_html=True
            )
            st.title("Singapore Murder Mystery")
            st.markdown(
                "<div style='text-align:center;color:#999;margin-bottom:24px'>"
                "A fully AI-generated mystery set in Singapore. No two cases are the same.<br>"
                "Race against <strong style='color:#c8a84b'>Inspector Rahim</strong> "
                "to solve the case before he does."
                "</div>",
                unsafe_allow_html=True
            )
            st.divider()
            if st.button("Generate New Case", type="primary", use_container_width=True):
                with st.spinner("Generating your mystery..."):
                    case = generate_case(st.session_state.client)
                    st.session_state.case = case
                    st.session_state.phase = "briefing"
                    st.session_state.histories = [[] for _ in case["suspects"]]
                    st.session_state.active_suspect = 0
                    st.session_state.clues = []
                    st.session_state.flagged_clues = set()
                    st.session_state.turn = 0
                    st.session_state.rahim_messages = []
                st.rerun()
        return

    phase = st.session_state.get("phase", "briefing")
    if phase == "briefing":
        show_briefing()
    elif phase == "interrogate":
        show_interrogation()
    elif phase == "reveal":
        show_reveal()

if __name__ == "__main__":
    main()