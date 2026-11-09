# Anubis // O.R.I.O.N. Mark I
### Real-Time Voice Intelligence, Quantitative Market Evaluation & Application Optimization

---

## About

Anubis was built to solve a modern productivity paradox: despite having powerful AI tools, workflows remain scattered across dozens of browser tabs, manual financial screeners, and repetitive application forms. Asking generic web chatbots to analyze charts or adjust resumes often results in hallucinated claims and disconnected context.

Anubis unifies these processes under a single, voice-driven command center named **Orion**. Operating locally with remote headless compute support, Orion handles quantitative stock evaluations, refines existing career experience against specific job descriptions, and executes desktop system commands—always keeping human verification at the core of every decision.

---

## Core Systems

### 1. Quantitative Market Intelligence
A hybrid evaluation pipeline designed to eliminate emotional bias from trading decisions:

* **Technical Chart Analysis:** Evaluates 14-day price structure, volume confirmation, moving average alignment, support/resistance levels, and pattern exhaustion (e.g., blow-off tops, false breakouts).
* **Catalyst & Sentiment Evaluation:** A dedicated local model scans recent news articles and filings to determine an initial directional stance (UP, DOWN, or NEUTRAL).
* **Unified Operational Stance:** Synthesizes technical price action against news sentiment into a strict operational verdict (BULLISH, BEARISH, or WAIT). Orion verbally briefs the analysis and projects live charts to the desktop and mobile companion dashboards.

### 2. Career Experience & Application Refinement
An automated optimization pipeline that treats your verified experience as ground truth:

* **Master Profile Grounding:** Rather than generating generic or fabricated resumes, the system strictly anchors to your pre-existing accomplishments, projects, and metrics in your master profile.
* **Targeted Refinement:** Analyzes the target job posting and sharpens your existing bullet points and cover letter narratives to directly highlight the qualifications and technologies requested by the employer.
* **Human-in-the-Loop Review:** Once documents are tailored, Orion announces the match via voice and stages the refined PDF outputs in the Companion Dashboard for your inspection and approval.

### 3. Voice Interaction & System Control
* **Low-Latency Dialogue:** Powered by Gemini Live for natural, interruption-aware voice conversations.
* **Desktop & Workspace Management:** Execute file operations, window controls, application launches, and system configurations hands-free.
* **Companion Dashboard:** A responsive web application accessible locally and remotely via Tailscale for monitoring pipelines, reviewing documents, and viewing market charts from any device.

---

## Architecture

```text
               +--------------------------------------+
               |          User Voice / UI             |
               +-------------------+------------------+
                                   |
                                   v
               +--------------------------------------+
               |          ORION Voice Core            |
               |      (Gemini Live + Local Logic)     |
               +---------+------------------+---------+
                         |                  |
           +-------------+                  +-------------+
           v                                              v
+------------------------+                     +------------------------+
|   Market Intelligence  |                     | Application Refinement |
| - Local Sentiment LLM  |                     | - Master Profile Base  |
| - Technical Vision     |                     | - Job Spec Alignment   |
| - Operational Stance   |                     | - PDF Staging Bridge   |
+-----------+------------+                     +-----------+------------+
            |                                              |
            +----------------------+-----------------------+
                                   |
                                   v
               +--------------------------------------+
               |      Orion Companion Dashboard       |
               |  (Tailscale Mesh / Mobile & Desktop) |
               +--------------------------------------+
```

---

## Setup & Installation

### 1. Environment Preparation
Ensure Python 3.11+ and virtual environment tools are installed:

```bash
git clone https://github.com/agrimkasaju/Anubis.git
cd Anubis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
```

### 2. Configuration
Create `config/api_keys.json` with your credentials:

```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "groq_api_key": "YOUR_GROQ_API_KEY",
  "dashboard_token": "YOUR_RANDOM_SECRET_TOKEN",
  "dashboard_port": 8088,
  "tailscale_ip": "YOUR_TAILSCALE_IP",
  "remote_llm_host": "YOUR_SERVER_IP:8080"
}
```

### 3. Running Orion
Start the primary voice assistant:

```bash
python main.py
```

To run the companion dashboard independently as a background service:

```bash
python orion_dashboard.py
```

---

## Engineering & Maintenance
Maintained by **agrimkasaju**.
