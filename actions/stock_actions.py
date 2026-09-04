import os
import shutil
import subprocess
import webbrowser
import requests

def open_dashboard():
    """Reliably opens the stock dashboard on Linux (Pop!_OS) desktop."""
    url = "http://localhost:8000"
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

def get_stock_analysis(symbol: str) -> str:
    """
    Calls the Docker microservice, launches the web dashboard, 
    and returns the spoken analysis back to Orion.
    """
    ticker = symbol.upper().strip()

    # 1. Trigger the dashboard popup using xdg-open
    open_dashboard()

    # 2. Query the Docker microservice
    try:
        response = requests.get(f"http://localhost:8000/analyze/{ticker}", timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            return (
                f"=== Technical Analysis for {data['ticker']} ===\n"
                f"Current Price: ${data['current_price']:.2f}\n"
                f"2-Week Range: ${data['two_week_low']:.2f} - ${data['two_week_high']:.2f}\n"
                f"-----------------------------------\n"
                f"{data['analysis']}"
            )
        else:
            return f"Sir, the stock analyzer returned an error: {response.text}"
            
        
    except requests.exceptions.Timeout:
        return "Sir, the quantitative reasoning model timed out while evaluating the chart."
    except requests.exceptions.ConnectionError:
        return "Sir, the stock analyzer Docker container is offline. Please make sure the container is running."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"