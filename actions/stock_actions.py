import os
import re
import shutil
import subprocess
import time
import webbrowser
import requests

def open_dashboard():
    """Reliably opens the stock dashboard on Linux (Pop!_OS) desktop."""
    url = STOCK_SERVER_URL
    try:
        # Check if running in Linux with xdg-open available
        if shutil.which("xdg-open"):
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp  # Detach process so it doesn't block Orion
            )
        else:
            webbrowser.open(url)
    except Exception as e:
        print(f"[StockAction] ⚠️ Failed to auto-launch browser: {e}")

import time

def is_llm_alive(url: str, timeout: float = 1.5) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return False

from config import get_config

_cfg = get_config()
REMOTE_LLM_HOST = str(os.getenv("REMOTE_LLM_HOST") or _cfg.get("remote_llm_host") or "").strip()
REMOTE_LLM_USER = str(os.getenv("REMOTE_LLM_USER") or _cfg.get("remote_llm_user") or os.getenv("USER") or "root").strip()
STOCK_SERVER_URL = os.getenv("STOCK_SERVER_HOST") or "http://localhost:8000"


def ensure_llm_connected() -> bool:
    """
    Automates connect-llm: bridges local 127.0.0.1:8080 to configured remote LLM server.
    If the remote server is down or not configured, skips gracefully.
    """
    if is_llm_alive("http://127.0.0.1:8080/v1/models"):
        return True

    if not REMOTE_LLM_HOST:
        return False

    remote_url = f"http://{REMOTE_LLM_HOST}/v1/models"
    if not is_llm_alive(remote_url, timeout=1.5):
        print(f"[StockAction] ⚠️ Remote LLM at {REMOTE_LLM_HOST} is offline. Skipping LLM connect.")
        return False

    print(f"[StockAction] 🔗 Automating connect-llm: bridging 127.0.0.1:8080 to {REMOTE_LLM_HOST}...")
    remote_ip, remote_port = REMOTE_LLM_HOST.split(":") if ":" in REMOTE_LLM_HOST else (REMOTE_LLM_HOST, "8080")
    try:
        if shutil.which("socat"):
            subprocess.Popen(
                ["socat", "TCP-LISTEN:8080,fork,reuseaddr,bind=127.0.0.1", f"TCP:{REMOTE_LLM_HOST}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp
            )
        else:
            subprocess.Popen(
                ["ssh", "-f", "-N", "-L", f"8080:127.0.0.1:{remote_port}", f"{REMOTE_LLM_USER}@{remote_ip}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp
            )

        for _ in range(10):
            time.sleep(0.2)
            if is_llm_alive("http://127.0.0.1:8080/v1/models"):
                print("[StockAction] ✅ Local-LLM connection established on 127.0.0.1:8080.")
                return True
    except Exception as e:
        print(f"[StockAction] ⚠️ Failed to auto-connect LLM tunnel: {e}")
    return False

def get_stock_analysis(symbol: str) -> str:
    """
    Calls the Docker microservice, launches the web dashboard, 
    and returns the spoken analysis back to Orion.
    """
    ticker = symbol.upper().strip()
    # Auto-correct common ticker typos
    ticker = {"APPL": "AAPL", "FB": "META"}.get(ticker, ticker)

    # 1. Automate connect-llm to link stock analyzer to local-LLM
    ensure_llm_connected()

    # 2. Trigger the dashboard popup using xdg-open
    open_dashboard()

    # 3. Query the Docker microservice
    try:
        response = requests.get(f"{STOCK_SERVER_URL}/analyze/{ticker}", timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            analysis_text = data.get("analysis", "")

            # Extract Final Operational Stance
            m = re.search(
                r"(?:Final Operational Stance|FINAL OPERATIONAL VERDICT|Operational Stance|Stance)\s*[:\*]+\s*\*?([A-Za-z -]+)",
                analysis_text,
                re.IGNORECASE
            )
            if m:
                raw_stance = m.group(1).strip().upper()
                final_stance = raw_stance.split()[0] if raw_stance else "NEUTRAL"
            elif "BULLISH" in analysis_text.upper():
                final_stance = "BULLISH"
            elif "BEARISH" in analysis_text.upper():
                final_stance = "BEARISH"
            else:
                final_stance = "NEUTRAL"

            local_summary = (data.get("news_summary") or "").strip()
            stance_line = ""
            lines = [l.strip() for l in local_summary.splitlines() if l.strip()]
            for idx, line in enumerate(lines):
                if "Directional Stance" in line:
                    if (line.endswith(":") or line.endswith(":-")) and idx + 1 < len(lines):
                        stance_line = f"{line} {lines[idx+1]}"
                    else:
                        stance_line = line
                    break
                elif "UP (" in line or "DOWN (" in line or "NEUTRAL" in line:
                    stance_line = line
                    break
            if not stance_line and lines:
                stance_line = lines[-1]

            news_source_label = data.get("news_source", "LOCAL MODEL").upper()
            return (
                f"=== Stock Analysis for {data['ticker']} ===\n"
                f"Current Price: ${data['current_price']:.2f} (2-Week Range: ${data['two_week_low']:.2f} - ${data['two_week_high']:.2f})\n"
                f"FINAL OPERATIONAL VERDICT: {final_stance}\n"
                f"{news_source_label} NEWS CALL: {stance_line or 'Neutral / No news'}\n"
                f"NOTICE FOR ORION: Your final spoken recommendation MUST be '{final_stance}'. Do NOT recommend buying if the final stance is BEARISH or WAIT.\n"
                f"-----------------------------------\n"
                f"{analysis_text}"
            )
        else:
            if "currentTradingPeriod" in response.text or "not found" in response.text.lower():
                return f"Ticker '{ticker}' was not found or has no active trading data on Yahoo Finance. Please check the spelling (e.g. AAPL for Apple)."
            return f"Sir, the stock analyzer returned an error: {response.text}"
            
        
    except requests.exceptions.Timeout:
        return "Sir, the quantitative reasoning model timed out while evaluating the chart."
    except requests.exceptions.ConnectionError:
        return "Sir, the stock analyzer Docker container is offline. Please make sure the container is running."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"