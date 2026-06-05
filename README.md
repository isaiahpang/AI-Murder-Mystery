# Singapore Murder Mystery

An AI-generated murder mystery game set in Singapore where you interrogate suspects, gather evidence, test your theories, and race Inspector Rahim to identify the killer before the investigation reaches its conclusion. Every case is generated dynamically using the Groq API and a structured case-generation pipeline, creating unique suspects, motives, evidence trails, and red herrings for every playthrough.

The project explores how multiple AI-driven roles can interact within a single game system, creating an investigation experience where suspects, witnesses, forensic analysts, and a rival detective all contribute to an evolving narrative rather than functioning as isolated chatbots.

---

## Problem Statement

Most AI-powered games use a single language model as a conversation partner. This project explores a different approach: treating the AI as an entire investigative ecosystem.

Instead of interacting with one chatbot, players engage with multiple AI personas that each possess different information, objectives, and perspectives. Suspects protect themselves, forensic analysts interpret evidence, witnesses provide testimony, and Inspector Rahim conducts his own parallel investigation — forming wrong conclusions based on red herring details before eventually closing in on the truth.

The goal was to create an experience where the player's decisions affect the broader investigation rather than simply producing individual responses. Information surfaces over time, suspects become more guarded as pressure increases, and competing deductions create tension throughout the case.

---

## Technology Stack

- **Language:** Python 3.11
- **UI Framework:** Streamlit
- **AI API:** Groq API (`llama-3.3-70b-versatile`)
- **Libraries:** `groq`, `python-dotenv`
- **Deployment:** Streamlit Community Cloud

---

## Architecture

The game uses eight distinct AI roles, all sharing state through Streamlit's session state:

| Role                        | Function                                                 |
| --------------------------- | -------------------------------------------------------- |
| Case Generator              | Produces the full mystery as structured JSON in one shot |
| Suspect Personas            | Independent conversation agents with hidden knowledge    |
| Clue Extractor              | Parses suspect responses for investigative facts         |
| Rahim Parallel Investigator | Runs a separate investigation, chases the wrong suspect  |
| Rahim Cadence Commentary    | Periodic pressure messages between milestones            |
| Deduction Validator         | Reviews the player's case before allowing an accusation  |
| Forensic Analyst            | Processes physical clues for follow-up findings          |
| Witness NPC                 | One-time alibi confirmation or contradiction             |

None of these roles share a conversation history. Each API call is constructed fresh with the relevant context injected at call time.

---

## Core Features

### AI-Generated Cases

Every new game generates a complete case in a single structured prompt:

- A unique victim with background and community role
- Three suspects with distinct personalities and relationships to the victim
- Distinct motives, alibis, and alibi flaws
- Evidence chains and a physical opening clue
- One innocent suspect with a `red_herring_detail` — a misleading detail that surfaces naturally during interrogation and is explained by their personal secret, not the murder

No case content is hardcoded, ensuring high replayability.

### Dynamic Suspect Interrogation

Players question suspects through natural language conversations. Suspects:

- Respond in character with natural Singlish
- React to accusations and pressure
- Become more guarded after Inspector Rahim visits them
- Become increasingly uncooperative after repeated questioning (cagey threshold)
- May let inconsistencies slip naturally under scrutiny

### Tension Curve System

Every investigation follows a three-act narrative progression driven by turn count rather than a static difficulty setting:

**Act 1 — Exploration (turns 1–3)**
Suspects are cooperative. Players gather foundational information and form early theories.

**Act 2 — Pressure (turns 4–7)**
Inspector Rahim begins commenting on his parallel investigation. Suspects Rahim has visited become more careful and measured.

**Act 3 — Crisis (turns 8–12)**
Breaking evidence surfaces automatically — CCTV timestamps, EZ-Link records, Nets transactions referencing real Singapore infrastructure. Rahim makes a confident but wrong accusation based on the red herring. The cagey threshold tightens. Players must commit before the case closes.

### Inspector Rahim

Rahim acts as a rival investigator rather than a passive narrative device. He:

- Conducts his own interrogations of suspects (stored separately per suspect, per visit)
- Builds commentary based on transcripts of the player's interrogations
- Is deliberately misled by the innocent suspect's red herring detail
- Makes a wrong accusation at turn 8, then corrects himself at turn 12
- Reacts in character to whatever accusation the player makes

### Deduction Board

Before making a formal accusation, players must submit three arguments: motive, alibi flaw, and supporting evidence. A senior-officer AI persona evaluates the quality of the reasoning and either validates it or identifies specific gaps. Weak deductions are rejected — the player must strengthen their case before proceeding.

### Evidence Board

Clues are organised by suspect with colour-coded type indicators (contradiction, motive, physical, witness, alibi). From the board players can:

- Flag key clues for quick reference
- Confront a second suspect with a claim made by a first
- Send physical clues to forensic analysis (costs a turn)

### Special Investigation Tools

Each tool costs a turn and is available once per game or per suspect:

- **Challenge Alibi** — demands a specific verifiable detail from a suspect
- **Call Witness** — surfaces an NPC who confirms or contradicts a suspect's alibi
- **Forensic Analysis** — sends a physical clue for laboratory follow-up

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/singapore-murder-mystery.git
cd singapore-murder-mystery
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
```

Add your Groq API key to `.env`:

```env
GROQ_API_KEY=your_api_key_here
```

Obtain a key at: https://console.groq.com

### 4. Run the Application

```bash
streamlit run app.py
```

The application will launch at `http://localhost:8501`.

### Deployment

The project is deployed on Streamlit Community Cloud:

```
https://ai-murder-mystery.streamlit.app
```

Add `GROQ_API_KEY` to the app's Secrets in the Streamlit Cloud dashboard.

---

## Project Structure

```
├── app.py                  # Entry point, theme injection, phase routing
├── api.py                  # All Groq API calls
├── config.py               # Game constants and tension curve thresholds
├── prompts.py              # All LLM prompt strings and builders
├── utils.py                # API key loading, robust JSON parser
├── requirements.txt
├── .env.example
└── ui/
    ├── briefing.py         # Case briefing screen
    ├── interrogation.py    # Main interrogation screen
    ├── evidence.py         # Evidence board component
    ├── deduction.py        # Deduction board and accusation flow
    └── reveal.py           # Case resolution and scoring
```

---

## Usage Examples

### Interrogating a Suspect

> **Player:** Where were you on the night of the murder?
>
> **Mdm Chua Bee Leng:** I already told the other officer lah — I was at my sister's place in Tampines. We were watching drama together until past midnight. Ask her if you don't believe me.

Responses remain contextual throughout the investigation and shift depending on prior conversations, how many times the suspect has been questioned, and whether Rahim has already visited them.

### Using the Deduction Board

> **Motive:** Rajan owed the victim a significant sum and stood to benefit from the debt disappearing.
>
> **Alibi flaw:** He said he was at Bedok MRT, but EZ-Link records place a card registered to his address at Woodlands at 10:45pm.
>
> **Evidence:** The kopitiam uncle at the scene identified someone matching Rajan's description.
>
> **Assessment (Reasonable):** The transport record is compelling but you have not established a direct link between the debt and the victim's schedule. Consider pressing Rajan on how he knew about the meeting.

---

## Known Limitations

### JSON Reliability

The application relies on structured JSON responses from the language model. The JSON parser handles fenced responses, preamble text, and recovers from minor malformation, but repeated failures on case generation can occasionally require a retry.

### Long-Term Consistency

Suspect details may occasionally drift during unusually long interrogation sessions despite memory and context safeguards, due to the probabilistic nature of language model generation.

### Evidence Quality Variance

Generated red herrings and evidence chains vary in quality between cases. Some investigations naturally produce stronger misdirection than others.

---

## Future Improvements

1. **Enhanced suspect memory** — stronger long-term consistency across lengthy interrogations
2. **Smarter Inspector Rahim** — dynamic theory-building rather than predefined milestones
3. **Expanded evidence systems** — digital forensics, financial records, social connections
4. **Visual relationship mapping** — evidence linking and contradiction tracking on the deduction board
5. **Discoverable witnesses** — witnesses that surface naturally through investigation rather than as a one-time tool
6. **Additional mystery archetypes** — accomplice murders, framed suspects, corporate conspiracies, cold-case connections
7. **Persistent progression** — investigation history, player profiles, leaderboards
8. **Case quality analytics** — internal tooling to measure clue balance and solution difficulty
