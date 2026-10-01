import json
import os
import subprocess
import urllib.request
import webbrowser
from config import get_config

_cfg = get_config()
_PORT = int(os.getenv("DASHBOARD_PORT") or _cfg.get("dashboard_port") or 8088)
_HOST = os.getenv("DASHBOARD_HOST") or _cfg.get("dashboard_host") or "127.0.0.1"
if _HOST == "0.0.0.0":
    _HOST = "127.0.0.1"

AUTH_TOKEN = os.getenv("DASHBOARD_TOKEN") or _cfg.get("dashboard_token", "")
DASHBOARD_BASE_URL = f"http://{_HOST}:{_PORT}/"
DASHBOARD_OPEN_URL = f"{DASHBOARD_BASE_URL}?token={AUTH_TOKEN}" if AUTH_TOKEN else DASHBOARD_BASE_URL


def is_dashboard_online() -> bool:
    try:
        with urllib.request.urlopen(DASHBOARD_BASE_URL, timeout=1) as res:
            return res.status == 200
    except Exception:
        return False


def ensure_dashboard_running() -> None:
    if not is_dashboard_online():
        try:
            subprocess.run(["systemctl", "--user", "start", "orion-dashboard.service"], check=False)
        except Exception:
            pass


import shutil
import time

_last_opened_timestamp = 0.0


def open_dashboard() -> bool:
    """Pulls up the AI Job Search Companion Dashboard in the default browser (debounced)."""
    global _last_opened_timestamp
    now = time.time()
    if now - _last_opened_timestamp < 4.0:
        return True
    _last_opened_timestamp = now

    ensure_dashboard_running()
    try:
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", DASHBOARD_OPEN_URL], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            webbrowser.open(DASHBOARD_OPEN_URL)
        return True
    except Exception as e:
        print(f"[AIJobSearch] ❌ Failed to open browser: {e}")
        return False


def ai_job_search_action(parameters: dict = None, player=None, speak=None) -> str:
    parameters = parameters or {}
    action = parameters.get("action", "").lower().strip()
    url = parameters.get("url", "").strip()
    company = parameters.get("company", "").strip()
    title = parameters.get("title", "").strip()

    if player and hasattr(player, "write_log"):
        player.write_log("[AI Job Search] Pulling up browser dashboard...")

    # If the user passed a specific URL or requested an auto-scrape session
    if url or action in ("manual", "scrape"):
        ensure_dashboard_running()
        mode = "manual" if url or action == "manual" else "scrape"
        payload = {"mode": mode}
        if url:
            payload["url"] = url
        if company:
            payload["company"] = company
        if title:
            payload["title"] = title

        try:
            headers = {"Content-Type": "application/json"}
            if AUTH_TOKEN:
                headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
            req = urllib.request.Request(
                f"{DASHBOARD_BASE_URL}api/job/start",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3) as res:
                pass
        except Exception as e:
            print(f"[AIJobSearch] Warning: Could not auto-trigger pipeline via API: {e}")

    success = open_dashboard()
    if success:
        if url:
            return "I've started tailoring your application and opened the dashboard in your browser, sir."
        return "I've opened the AI Job Search dashboard in your browser, sir."
    else:
        return "Sir, I was unable to open the browser dashboard."
