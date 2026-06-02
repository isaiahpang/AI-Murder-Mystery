import streamlit as st
import json
import os
from groq import Groq

# ── API key: works both locally (.env) and on Streamlit Cloud (secrets) ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not needed on Streamlit Cloud

def get_api_key():
    """Get Groq API key from Streamlit secrets or environment variable."""
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    key = os.getenv("GROQ_API_KEY")
    if not key:
        st.error("GROQ_API_KEY not found. Add it to .env locally or Streamlit secrets on Cloud.")
        st.stop()
    return key

# ── System prompts ──────────────────────────────────────────────────────────

CASE_GENERATION_PROMPT = """
You are a murder mystery writer. Generate a murder mystery case as a JSON object.

Return ONLY valid JSON with this exact structure, no markdown, no explanation:
{
  "title": "string — dramatic case title",
  "setting": "string — location and time period",
  "victim": {
    "name": "string",
    "description": "string — who they were"
  },
  "cause_of_death": "string",
  "killer_index": 0,
  "suspects": [
    {
      "name": "string",
      "relationship_to_victim": "string",
      "personality": "string — 2-3 adjectives",
      "alibi": "string — where they claim to have been",
      "alibi_contradiction": "string — the hidden flaw in their alibi (only for killer, leave empty string for innocents)",
      "what_they_know": "string — what they genuinely know about the case",
      "what_they_are_hiding": "string — their secret (not necessarily the murder)"
    }
  ],
  "motive": "string — the killer's motive"
}

Rules:
- Always generate exactly 3 suspects
- killer_index is 0, 1, or 2 (which suspect is guilty)
- Only the killer's alibi_contradiction should be non-empty
- Make the mystery solvable but not obvious
- Each suspect should have something suspicious to keep the player guessing
"""

def build_suspect_prompt(suspect: dict, case: dict, is_killer: bool) -> str:
    """Build a system prompt for a suspect from generated case data."""
    guilt_note = ""
    if is_killer:
        guilt_note = f"""
You are GUILTY. You committed the murder. Your motive was: {case['motive']}.
Your alibi has a hidden flaw: {suspect['alibi_contradiction']}.
Never confess. If pressed hard on your alibi, become defensive or change the subject.
Occasionally let small inconsistencies slip — a wrong time, a detail that doesn't add up.
"""
    else:
        guilt_note = """
You are INNOCENT. You did not commit the murder.
You are hiding something (your secret below) but it is unrelated to the killing.
You are genuinely nervous because you fear your secret will come out.
"""

    return f"""
You are {suspect['name']}, a suspect in the murder of {case['victim']['name']}.

Your personality: {suspect['personality']}
Your relationship to the victim: {suspect['relationship_to_victim']}
Your alibi: {suspect['alibi']}
What you know about the case: {suspect['what_they_know']}
Your secret (unrelated to murder, but you don't want it revealed): {suspect['what_they_are_hiding']}

{guilt_note}

Behaviour rules:
- Stay completely in character at all times
- Respond in 2-4 sentences — be natural, not robotic
- Show your personality through your tone
- Never break the fourth wall or mention being an AI
- If asked something you wouldn't know, say so in character
"""

# ── Groq API calls ──────────────────────────────────────────────────────────

def generate_case(client: Groq) -> dict:
    """Call Groq to generate a new murder mystery case as JSON."""
    for attempt in range(3):  # retry up to 3 times if JSON is malformed
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CASE_GENERATION_PROMPT},
                    {"role": "user", "content": "Generate a new murder mystery case."}
                ],
                temperature=1.0,
                max_tokens=1500,
            )
            raw = response.choices[0].message.content.strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt == 2:
                st.error("Failed to generate a valid case after 3 attempts. Please try again.")
                st.stop()
    return {}

def interrogate_suspect(client: Groq, suspect_index: int, question: str) -> str:
    """Send a question to a suspect and return their response."""
    case = st.session_state.case
    suspect = case["suspects"][suspect_index]
    is_killer = (suspect_index == case["killer_index"])

    system_prompt = build_suspect_prompt(suspect, case, is_killer)

    # Build conversation history for this suspect
    history = st.session_state.histories[suspect_index]
    messages = [{"role": "system", "content": system_prompt}] + history + [
        {"role": "user", "content": question}
    ]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.8,
            max_tokens=300,
        )
        reply = response.choices[0].message.content.strip()

        # Save to history
        st.session_state.histories[suspect_index].append({"role": "user", "content": question})
        st.session_state.histories[suspect_index].append({"role": "assistant", "content": reply})

        return reply
    except Exception as e:
        return f"[Error reaching suspect: {e}]"

# ── UI ──────────────────────────────────────────────────────────────────────

def show_briefing():
    """Render the case briefing screen."""
    case = st.session_state.case
    st.title(f"🔍 {case['title']}")
    st.caption(case["setting"])

    st.markdown("### 💀 The Victim")
    st.write(f"**{case['victim']['name']}** — {case['victim']['description']}")
    st.write(f"**Cause of death:** {case['cause_of_death']}")

    st.markdown("### 🕵️ Your Suspects")
    for i, s in enumerate(case["suspects"]):
        with st.expander(f"{s['name']} — {s['relationship_to_victim']}"):
            st.write(f"**Alibi:** {s['alibi']}")

    if st.button("Begin Interrogations →", type="primary"):
        st.session_state.phase = "interrogate"
        st.rerun()

def show_interrogation():
    """Render the interrogation screen."""
    client = st.session_state.client
    case = st.session_state.case
    suspects = case["suspects"]

    st.title("🔍 Interrogation Room")

    # Sidebar — suspect selector + accusation
    with st.sidebar:
        st.markdown("### Suspects")
        for i, s in enumerate(suspects):
            if st.button(s["name"], key=f"sel_{i}", use_container_width=True):
                st.session_state.active_suspect = i
                st.rerun()

        st.divider()
        st.markdown("### Make Accusation")
        for i, s in enumerate(suspects):
            if st.button(f"Accuse {s['name']}", key=f"acc_{i}", use_container_width=True):
                st.session_state.accusation = i
                st.session_state.phase = "reveal"
                st.rerun()

    # Main area — chat with active suspect
    idx = st.session_state.active_suspect
    suspect = suspects[idx]
    st.subheader(f"Interrogating: {suspect['name']}")
    st.caption(f"{suspect['relationship_to_victim']} · Alibi: {suspect['alibi']}")

    # Show conversation history
    for msg in st.session_state.histories[idx]:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["content"])

    # Input
    question = st.chat_input(f"Ask {suspect['name']} a question...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner(f"{suspect['name']} is thinking..."):
                reply = interrogate_suspect(client, idx, question)
            st.write(reply)

def show_reveal():
    """Render the accusation reveal screen."""
    case = st.session_state.case
    accused_index = st.session_state.accusation
    killer_index = case["killer_index"]
    accused = case["suspects"][accused_index]
    killer = case["suspects"][killer_index]

    st.title("⚖️ The Verdict")

    if accused_index == killer_index:
        st.success(f"✅ Correct! **{accused['name']}** is the killer.")
        st.markdown(f"**Motive:** {case['motive']}")
        st.markdown(f"**The flaw in their alibi:** {killer['alibi_contradiction']}")
    else:
        st.error(f"❌ Wrong. You accused **{accused['name']}**, but they were innocent.")
        st.markdown(f"The real killer was **{killer['name']}**.")
        st.markdown(f"**Motive:** {case['motive']}")
        st.markdown(f"**The alibi flaw you missed:** {killer['alibi_contradiction']}")

    if st.button("🔄 Play Again", type="primary"):
        for key in ["case", "phase", "histories", "active_suspect", "accusation"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ── App entry point ─────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="AI Murder Mystery", page_icon="🔍", layout="wide")

    # Initialise client once
    if "client" not in st.session_state:
        st.session_state.client = Groq(api_key=get_api_key())

    # Generate case if starting fresh
    if "case" not in st.session_state:
        st.title("🔍 AI Murder Mystery")
        st.write("A new mystery is generated every time. No two cases are the same.")
        if st.button("Generate New Case", type="primary"):
            with st.spinner("Generating your mystery..."):
                case = generate_case(st.session_state.client)
                st.session_state.case = case
                st.session_state.phase = "briefing"
                st.session_state.histories = [[] for _ in case["suspects"]]
                st.session_state.active_suspect = 0
            st.rerun()
        return

    # Route to correct phase
    phase = st.session_state.get("phase", "briefing")
    if phase == "briefing":
        show_briefing()
    elif phase == "interrogate":
        show_interrogation()
    elif phase == "reveal":
        show_reveal()

if __name__ == "__main__":
    main()
