from pathlib import Path
import shutil
import subprocess
import sys


if sys.prefix == sys.base_prefix:
    raise SystemExit("Activate .venv first, then run: python setup.py")

uv = shutil.which("uv")
if not uv:
    raise SystemExit("uv is not installed. See https://docs.astral.sh/uv/getting-started/installation/")

root = Path(__file__).resolve().parent

print("Installing requirements into the active virtual environment...")
subprocess.run(
    [uv, "pip", "install", "--python", sys.executable, "-r", str(root / "requirements.txt")],
    check=True,
)

print("Installing the Playwright Chromium browser...")
subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

print("Setup complete. Run 'python main.py' to start O.R.I.O.N.")
