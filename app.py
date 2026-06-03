import streamlit as st
from groq import Groq

from config import DIFFICULTIES
from utils import get_api_key
from api import generate_case
from ui.briefing import show_briefing
from ui.interrogation import show_interrogation
from ui.reveal import show_reveal

GLOBAL_CSS = """
<style>
.stApp { background-color: #0d0d0d; color: #e0d6c8; }
[data-testid="stSidebar"] { background-color: #111111; border-right: 1px solid #2a2a2a; }
.stButton > button {
    background-color: #1a1a2e; color: #c8a84b;
    border: 1px solid #c8a84b; border-radius: 4px; font-size: 0.85em;
}
.stButton > button:hover { background-color: #c8a84b; color: #0d0d0d; }
.stButton > button[kind="primary"] {
    background-color: #c8a84b; color: #0d0d0d; font-weight: bold; border: none;
}
.stButton > button[kind="primary"]:hover { background-color: #e0c870; }
[data-testid="stChatMessage"] {
    background-color: #141414; border: 1px solid #2a2a2a; border-radius: 8px; margin: 4px 0;
}
[data-testid="stExpander"] { background-color: #141414; border: 1px solid #2a2a2a; border-radius: 4px; }
h1, h2, h3 { color: #c8a84b !important; font-family: Georgia, serif; }
hr { border-color: #2a2a2a; }
.stCaption { color: #888 !important; }
</style>
"""

def main():
    """App entry point — injects theme, handles difficulty selection, routes phases."""
    st.set_page_config(page_title="Singapore Murder Mystery", page_icon="🔍", layout="wide")
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    if "client" not in st.session_state:
        st.session_state.client = Groq(api_key=get_api_key())

    if "case" not in st.session_state:
        _, col, _ = st.columns([1, 6, 1])
        with col:
            st.markdown("<div style='text-align:center;font-size:3em'>🔍</div>", unsafe_allow_html=True)
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

            # Difficulty selector
            st.markdown("### Select Difficulty")
            diff_cols = st.columns(3)
            for i, (name, cfg) in enumerate(DIFFICULTIES.items()):
                with diff_cols[i]:
                    selected = st.session_state.get("difficulty", "Medium") == name
                    border = "#c8a84b" if selected else "#333"
                    st.markdown(
                        f"<div style='border:2px solid {border};border-radius:6px;"
                        f"padding:12px;text-align:center;margin-bottom:8px'>"
                        f"<strong style='color:#c8a84b'>{name}</strong><br>"
                        f"<span style='font-size:0.8em;color:#999'>{cfg['description']}</span></div>",
                        unsafe_allow_html=True
                    )
                    if st.button(f"Select {name}", key=f"diff_{name}", use_container_width=True):
                        st.session_state.difficulty = name
                        st.rerun()

            st.markdown("")
            chosen = st.session_state.get("difficulty", "Medium")
            st.info(f"Selected: **{chosen}** — {DIFFICULTIES[chosen]['description']}")

            if st.button("Generate New Case", type="primary", use_container_width=True):
                with st.spinner("Generating your mystery..."):
                    case = generate_case(st.session_state.client, chosen)
                    st.session_state.case = case
                    st.session_state.phase = "briefing"
                    st.session_state.histories = [[] for _ in case["suspects"]]
                    st.session_state.active_suspect = 0
                    st.session_state.clues = []
                    st.session_state.flagged_clues = set()
                    st.session_state.turn = 0
                    st.session_state.rahim_messages = []
                    st.session_state.rahim_history = []
                    st.session_state.rahim_accused = ""
                    st.session_state.rahim_interrogations = {}
                    st.session_state.player_notes = ""
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