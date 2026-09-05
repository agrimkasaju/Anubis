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

2. **Install uv:**

   Windows PowerShell:

   ```powershell
   winget install --id=astral-sh.uv -e
   ```

   WSL/Linux:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc
   ```

3. **Create a clean Python 3.10 virtual environment:**

   If an old environment is active, run `deactivate` first. Then remove only
   the `.venv` folder in this repository.

   Windows PowerShell:

   ```powershell
   if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }
   uv venv --python 3.10
   .venv\Scripts\Activate.ps1
   ```

   WSL/Linux:

   ```bash
   rm -rf .venv
   sudo apt update
   sudo apt install -y portaudio19-dev
   uv venv --python 3.10
   source .venv/bin/activate
   ```

   The PortAudio development package is required to build `pyaudio` on
   WSL/Linux. Windows normally installs its prebuilt wheel.

4. **Install dependencies:**

   ```bash
   python setup.py
   ```

   `setup.py` requires the active `.venv`, installs `requirements.txt`
   with uv for that exact Python interpreter, and installs only the Playwright
   Chromium browser. To install manually instead:

   ```bash
   uv pip install -r requirements.txt
   python -m playwright install chromium
   ```

5. **Configure API Keys:**
   Add your keys to `config/api_keys.json`:
   ```json
   {
     "gemini_api_key": "YOUR_GEMINI_KEY",
     "openrouter_api_key": "YOUR_OPENROUTER_KEY"
   }
   ```

6. **Optional Codex coding tool:**

   Set a dedicated folder that Codex is allowed to use. Review and explanation
   requests are read-only; edit and build requests can write only in this
   folder.

   WSL/Linux:

   ```bash
   export ANUBIS_CODE_WORKSPACE="$HOME/JarvisProjects"
   mkdir -p "$ANUBIS_CODE_WORKSPACE"
   ```

   Windows PowerShell:

   ```powershell
   $env:ANUBIS_CODE_WORKSPACE = "$HOME\JarvisProjects"
   New-Item -ItemType Directory -Force $env:ANUBIS_CODE_WORKSPACE
   ```

   The Codex SDK reuses an existing Codex login. Only use a company-managed
   Codex account if your organization's policy permits this repository and
   data.

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
