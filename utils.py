import os
import json
import streamlit as st

def get_api_key() -> str:
    """Get Groq API key from Streamlit secrets (Cloud) or .env (local)."""
    if "GROQ_API_KEY" in st.secrets:
        return st.secrets["GROQ_API_KEY"]
    key = os.getenv("GROQ_API_KEY")
    if not key:
        st.error("GROQ_API_KEY not found. Add it to .env locally or Streamlit secrets on Cloud.")
        st.stop()
    return key

def safe_parse_json(raw: str) -> dict | list | None:
    """Strip markdown fences if present, then parse JSON. Returns None on failure."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None