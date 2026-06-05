import os
import json
import re
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
    """
    Robustly parse a JSON response from the LLM.

    Handles:
    - Bare JSON
    - ```json ... ``` fences
    - ``` ... ``` fences (no language tag)
    - Leading/trailing whitespace and stray text before/after the JSON block

    Returns None on any parse failure rather than raising.
    """
    if not raw:
        return None

    text = raw.strip()

    # Strip markdown fences (handles ```json, ```JSON, ``` etc.)
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # If there's still no leading { or [, try to find the first JSON object/array
    if text and text[0] not in ("{", "["):
        json_start = re.search(r"[{\[]", text)
        if json_start:
            text = text[json_start.start():]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: find the outermost balanced brace/bracket pair
        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = text.find(start_char)
            if start == -1:
                continue
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
        return None