import streamlit as st
from groq import Groq

from utils import get_api_key
from api import generate_case
from ui.briefing import show_briefing
from ui.interrogation import show_interrogation
from ui.reveal import show_reveal

def main():
    """App entry point — initialises state and routes between game phases."""
    st.set_page_config(
        page_title="Singapore Murder Mystery",
        page_icon="🔍",
        layout="wide"
    )

    # Initialise Groq client once per session
    if "client" not in st.session_state:
        st.session_state.client = Groq(api_key=get_api_key())

    # Landing screen
    if "case" not in st.session_state:
        _, col, _ = st.columns([1, 6, 1])
        with col:
            st.title("🔍 Singapore Murder Mystery")
            st.markdown(
                "A fully AI-generated mystery set in Singapore. "
                "No two cases are the same."
            )
            st.markdown("Race against **Inspector Rahim** to solve the case before he does.")
            st.divider()
            if st.button("Generate New Case", type="primary", use_container_width=True):
                with st.spinner("Generating your mystery..."):
                    case = generate_case(st.session_state.client)
                    st.session_state.case = case
                    st.session_state.phase = "briefing"
                    st.session_state.histories = [[] for _ in case["suspects"]]
                    st.session_state.active_suspect = 0
                    st.session_state.clues = []
                    st.session_state.turn = 0
                    st.session_state.rahim_messages = []
                st.rerun()
        return

    # Route to current phase
    phase = st.session_state.get("phase", "briefing")
    if phase == "briefing":
        show_briefing()
    elif phase == "interrogate":
        show_interrogation()
    elif phase == "reveal":
        show_reveal()

if __name__ == "__main__":
    main()