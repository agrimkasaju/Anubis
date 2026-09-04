# 🤖 O.R.I.O.N MARK I
### The Ultimate AI Job Search & Personal Assistant

O.R.I.O.N MARK I is a revamped real-time AI assistant optimized for autonomous job application workflows and system control. It automatically fetches job listings, generates tailored resumes/cover letters, and manages the submission process with human-in-the-loop confirmation.

---

## 🚀 Key Features

- **💼 Job Pipeline** — Automatically fetches jobs from GitHub repositories or URLs. Generates professional PDFs (Resume/Cover Letter) tailored to each role.
- **🎙️ Real-time Voice** — Low-latency interaction using Gemini Live for natural conversation.
- **🖥️ System Control** — Full control over apps, files, browser, and desktop settings.
- **👁️ Visual Awareness** — Real-time screen analysis and webcam vision.
- **🧠 Persistent Memory** — Deeply remembers your projects, preferences, and career goals.
- **🛡️ Live Response Guard** — Robust handling of malformed AI responses to ensure zero-crash sessions.

---

## 🛠️ Setup

1. **Clone the repo:**
   ```bash
   git clone https://github.com/agrimkasaju/Anubis.git
   cd Anubis
   ```

2. **Create a Python 3.10 virtual environment and install dependencies:**

   Linux/WSL:
   ```bash
   sudo apt-get install libportaudio2
   uv venv --python 3.10
   source .venv/bin/activate
   uv pip install -r requirements.txt
   playwright install
   ```

   Windows PowerShell:
   ```powershell
   uv venv --python 3.10
   .venv\Scripts\Activate.ps1
   uv pip install -r requirements.txt
   playwright install
   ```

3. **Configure API Keys:**
   Add your keys to `config/api_keys.json`:
   ```json
   {
     "gemini_api_key": "YOUR_GEMINI_KEY",
     "groq_api_key": "YOUR_GROQ_KEY"
   }
   ```

4. **Authenticate Codex and choose its workspace:**
   ```bash
   codex login
   export ANUBIS_CODE_WORKSPACE="$HOME/Desktop/JarvisProjects"
   ```
   Coding requests are restricted to this directory. Review and explanation
   requests are read-only; edits and builds use workspace-write access with
   permission escalation disabled.

---

## ⚡ Workflow

1. **Start the Assistant:**
   ```bash
   python main.py
   ```
2. **Job Application:**
   - The pipeline fetches jobs and places them in the queue.
   - Orion (the assistant) will automatically wake up and announce: *"Sir, a new job for [Role] at [Company] is ready."*
   - You can say: *"Yes, show it to me"* or *"Submit it"*.
   - Orion opens the application page, your generated PDFs, and helps you finish the form.

---

## 🧪 Testing

Run the automated capability test to verify the job bridge and response guard:
```bash
# Test the live response guard
pytest tests/test_live_response_guard.py

# Test the job pipeline capability
python tests/agent_capability_test.py
```

---

## 👤 Connect
Engineered by **agrimkasaju**.
