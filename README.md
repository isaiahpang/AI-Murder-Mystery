# Singapore Murder Mystery

An AI-generated murder mystery game set in Singapore where you interrogate suspects, gather clues, and race Inspector Rahim to identify the killer before he does. Every case is procedurally generated — no two games are the same.

Intended for players who enjoy deduction games, and for developers or students exploring conversational AI and multi-agent game design.

---

## Problem Statement

Most AI-powered games use the model as a single chatbot. This project explores what happens when multiple AI personas — suspects, a rival detective, a forensic analyst, a witness — run in parallel and react to each other's actions. The result is a game where the AI opposition has genuine consequences: Inspector Rahim's wrong accusation changes how suspects behave, and breaking evidence surfaces on a dramatic timer rather than on demand. The goal was to make AI feel like a world, not a window.

---

## Technology Stack

- **Language:** Python 3.11
- **UI framework:** Streamlit
- **AI API:** Groq API (`llama-3.3-70b-versatile`)
- **Libraries:** `groq`, `python-dotenv`
- **Hosting:** Streamlit Community Cloud (or local)

---

## Setup Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/singapore-murder-mystery.git
   cd singapore-murder-mystery
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example environment file and add your Groq API key:

   ```bash
   cp .env.example .env
   ```

   Open `.env` and replace `your_groq_api_key_here` with your key from [console.groq.com](https://console.groq.com).

4. Run the application:
   ```bash
   streamlit run app.py
   ```
   The app opens at `http://localhost:8501`.

**Streamlit Cloud deployment:** Accessable at ai-murder-mystery.streamlit.app

---

## Usage Examples

### Example 1 — Interrogating a suspect

The player selects a suspect and types a question into the chat input:

> **Player:** Where were you on the night of the murder?
>
> **Mdm Chua Bee Leng:** I already told the other officer lah — I was at my sister's place in Tampines. We were watching drama together until past midnight. Ask her if you don't believe me, her name is Linda, same block as me.

The response is generated in-character. If the suspect is guilty, small inconsistencies slip in under pressure. If Inspector Rahim already asked them the same question, they may reference it: _"That other detective also kept asking about this — what exactly are you all implying, hah?"_

---

### Example 2 — Using the Deduction Board

After collecting clues, the player opens the Deduction Board, selects a suspect, and writes their reasoning:

> **Player's reasoning:** Rajan's alibi places him at Bedok MRT but the CCTV clue shows someone matching his description at the void deck at 10:45pm. He was evasive when I challenged his alibi and couldn't name a single person who saw him there.

The player clicks **Evaluate My Case**. The AI case reviewer responds:

> **Verdict: Shaky**
> The CCTV finding is your strongest piece, but it hasn't been formally linked to Rajan by name — only by description. You haven't addressed his stated motive or the relationship with the victim. Consider pressing him on why he knew the victim's schedule.
>
> **Gaps:** No motive established · CCTV link is circumstantial · Alibi witness unchecked

The player can still accuse, but now knows what the weak points are.

---

## Known Limitations

**JSON reliability.** The game depends entirely on the LLM returning valid JSON on every call. A `safe_parse_json` utility handles malformed responses, but if the model returns invalid JSON three times in a row during case generation, the app surfaces an error and asks the player to retry. Under load or with certain prompt combinations this happens occasionally.

**Red herring strength is inconsistent.** The red herring is generated alongside the case and is supposed to be convincing enough to mislead a careful player. In practice the model sometimes generates a weak red herring — one that a player can dismiss after a single question — which removes the intended tension in Act II. The `surface_trigger` field in the schema nudges the model toward delayed revelation, but it does not fully solve the problem.

---

## Future Improvements

**Witness system redesign.** The current one-use witness button is a power-up, not a mechanic. A better version would surface named witnesses through suspect testimony — a suspect mentions "the auntie at the kopitiam saw me" — and the player actively chooses whether to track that lead down. This turns witness-calling into a skill and makes the clue graph richer.

**Structural case variety.** Every case currently follows the same shape: one killer, one red herring, three suspects. Adding structural variants — an accomplice who provided a false alibi, a planted opening clue the killer left deliberately, a suspect hiding two separate secrets — would significantly extend replayability once the core loop is solid.
