# Singapore Murder Mystery

An AI-generated murder mystery game set in Singapore where you interrogate suspects, gather evidence, test your theories, and race Inspector Rahim to identify the killer before the investigation reaches its conclusion. Every case is generated dynamically using Groq's LLM and a structured case-generation pipeline, creating unique suspects, motives, evidence trails, and red herrings for every playthrough.

The project explores how multiple AI-driven roles can interact within a single game system, creating an investigation experience where suspects, witnesses, forensic analysts, and rival detectives all contribute to an evolving narrative rather than functioning as isolated chatbots.

---

## Problem Statement

Most AI-powered games use a single language model as a conversation partner. This project explores a different approach: treating the AI as an entire investigative ecosystem.

Instead of interacting with one chatbot, players engage with multiple AI personas that each possess different information, objectives, and perspectives. Suspects protect themselves, forensic analysts interpret evidence, witnesses provide testimony, and Inspector Rahim conducts his own parallel investigation.

The goal was to create an experience where the player's decisions affect the broader investigation rather than simply producing individual responses. Information surfaces over time, suspects become more guarded as pressure increases, and competing deductions create tension throughout the case.

---

## Technology Stack

- **Language:** Python 3.11
- **UI Framework:** Streamlit
- **AI API:** Groq API (`llama-3.3-70b-versatile`)
- **Libraries:** `groq`, `python-dotenv`
- **Deployment:** Streamlit Community Cloud

---

## Core Features

### AI-Generated Cases

Every new game generates:

- A unique victim
- Multiple suspects
- Distinct motives
- Evidence chains
- False leads and red herrings
- Hidden culprit relationships

No case content is hardcoded, ensuring high replayability.

### Dynamic Suspect Interrogation

Players can freely question suspects through natural language conversations.

Suspects:

- Respond in character
- Maintain awareness of previously discussed topics
- React to accusations and pressure
- Become increasingly guarded later in the investigation
- May accidentally reveal inconsistencies under scrutiny

### Deduction Board

Players can build theories and submit reasoning before making a formal accusation.

The AI evaluates:

- Evidence quality
- Logical consistency
- Missing investigative gaps
- Strength of motive
- Reliability of conclusions

This allows players to test theories before committing to an arrest.

### Inspector Rahim

Rahim acts as a rival investigator rather than a passive narrative device.

Throughout the case he:

- Conducts his own investigation
- Forms independent conclusions
- Makes deductions based on available evidence
- Creates time pressure for the player

His progress serves as both narrative tension and a soft investigation timer.

### Tension Curve System

The game no longer uses traditional difficulty modes.

Instead, every investigation follows a structured narrative progression:

#### Act I — Investigation

- Suspects are relatively cooperative
- Players gather foundational information
- Early theories begin forming

#### Act II — Escalation

- Suspects become more defensive
- New evidence surfaces
- Contradictions become more apparent
- Pressure on both investigators increases

#### Act III — Resolution

- Critical evidence emerges
- Rahim approaches his conclusion
- Players must commit to a final theory before the investigation ends

This creates a more consistent dramatic experience than static difficulty settings.

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

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key:

```env
GROQ_API_KEY=your_api_key_here
```

Obtain an API key from:

https://console.groq.com

### 4. Run the Application

```bash
streamlit run app.py
```

The application will launch at:

```text
http://localhost:8501
```

### Deployment

The project is deployed on Streamlit Community Cloud:

```text
https://ai-murder-mystery.streamlit.app
```

---

## Usage Examples

### Example 1 — Interrogating a Suspect

The player questions a suspect:

> **Player:** Where were you on the night of the murder?
>
> **Mdm Chua Bee Leng:** I already told the other officer lah — I was at my sister's place in Tampines. We were watching drama together until past midnight. Ask her if you don't believe me.

Responses remain contextual throughout the investigation and may change depending on prior conversations and investigation progress.

---

### Example 2 — Using the Deduction Board

The player submits a theory:

> Rajan's alibi places him at Bedok MRT, but CCTV evidence places someone matching his description near the victim's block at 10:45pm. He was evasive when challenged and failed to provide corroborating witnesses.

The AI evaluates the case:

> **Verdict: Shaky**
>
> The CCTV evidence is compelling but remains circumstantial. You have not established a clear motive or connected Rajan directly to the victim's schedule. Consider investigating their prior relationship.

This provides guidance without revealing the true solution.

---

## Known Limitations

### JSON Reliability

The application relies heavily on structured JSON responses from the language model.

While utility functions attempt to repair malformed responses automatically, repeated failures can occasionally interrupt case generation or evidence creation.

### Long-Term Consistency

Because suspect responses are generated dynamically, details may occasionally drift during unusually long interrogation sessions despite memory and context safeguards.

### Evidence Quality Variance

Generated red herrings and evidence chains vary in quality between cases. Some investigations naturally produce stronger misdirection than others due to the probabilistic nature of language model generation.

---

## Future Improvements

### 1. Enhanced Suspect Memory

Introduce stronger long-term conversational memory to improve consistency across lengthy interrogations.

### 2. Smarter Inspector Rahim

Allow Rahim to build and revise theories dynamically rather than following predefined investigation milestones.

### 3. Expanded Evidence Systems

Add digital forensics, financial records, mobile device data, surveillance footage, and social connections as investigative tools.

### 4. Advanced Deduction Board

Support evidence linking, contradiction tracking, and visual relationship mapping between suspects, motives, and clues.

### 5. Witness Discovery System

Replace the current witness mechanic with discoverable witnesses that emerge naturally through investigation and evidence gathering.

### 6. Additional Mystery Archetypes

Introduce new case structures such as:

- Accomplice murders
- Multiple independent secrets
- Framed suspects
- Corporate conspiracies
- Family inheritance disputes
- Cold-case connections

### 7. Persistent Progression

Implement investigation history, player profiles, scoring persistence, and leaderboards to encourage long-term replayability.

### 8. Analytics and Evaluation

Develop internal tools for measuring case quality, clue balance, and solution difficulty to improve generation reliability over time.
