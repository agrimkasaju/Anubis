# services/flight_poller.py

"""
Background flight price polling daemon for Anubis.
Runs continuously inside the Anubis background service.
Customized for evening availability (5:00 PM to 9:30 PM):
  - Primary poll: 5:00 PM (17:00) with automatic catch-up if computer turns on past 5:00 PM.
  - Secondary poll: 8:30 PM (20:30) for evening airline fare updates before going offline at 9:30 PM.
  - Persists polling state so restarts or wakeups never duplicate or miss checks.
"""

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sys

# Ensure project root in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from actions.flight_tracker import poll_all_active_trackers, get_active_trackers

POLL_STATE_FILE = project_root / "data" / "flight_poll_state.json"


def _load_poll_state() -> dict:
    POLL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if POLL_STATE_FILE.exists():
        try:
            return json.loads(POLL_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"date": "", "completed_slots": [], "last_poll_timestamp": None}


def _save_poll_state(state: dict):
    try:
        POLL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        POLL_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[FlightPoller] ⚠️ Error saving poll state: {e}")


class FlightPollerDaemon:
    def __init__(self, speech_callback=None):
        self.speech_callback = speech_callback
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        print("[FlightPoller] 🛫 Daemon started (Evening window: 5:00 PM to 9:30 PM with wake catch-up).")

        while self._running:
            try:
                now = datetime.now()
                today_str = now.strftime("%Y-%m-%d")

                state = _load_poll_state()
                if state.get("date") != today_str:
                    state = {
                        "date": today_str,
                        "completed_slots": [],
                        "last_poll_timestamp": state.get("last_poll_timestamp"),
                    }

                # Evaluate if a poll is due
                slot_to_run = None
                poll_reason = None

                # Check minimum interval debounce (at least 45 minutes between polls)
                last_ts = state.get("last_poll_timestamp")
                mins_since_last = 999999
                if last_ts:
                    try:
                        mins_since_last = (now - datetime.fromisoformat(last_ts)).total_seconds() / 60
                    except Exception:
                        pass

                # Check Slot 1: 5:00 PM (17:00) onwards
                if "17:00" not in state["completed_slots"] and now.hour >= 17:
                    if mins_since_last >= 45:
                        slot_to_run = "17:00"
                        if now.hour == 17 and now.minute < 10:
                            poll_reason = "5:00 PM scheduled evening poll"
                        else:
                            poll_reason = f"Missed 5:00 PM catch-up poll (computer online at {now.strftime('%I:%M %p')})"

                # Check Slot 2: 8:30 PM (20:30) onwards (before 9:30 PM)
                elif "20:30" not in state["completed_slots"] and (now.hour > 20 or (now.hour == 20 and now.minute >= 30)):
                    if mins_since_last >= 45:
                        slot_to_run = "20:30"
                        poll_reason = f"8:30 PM evening fare update poll (at {now.strftime('%I:%M %p')})"

                if slot_to_run:
                    active = get_active_trackers()
                    if active:
                        print(f"[FlightPoller] ⏰ {poll_reason} for {len(active)} active tracker(s)...")
                        loop = asyncio.get_running_loop()
                        alerts = await loop.run_in_executor(None, poll_all_active_trackers)

                        if alerts and self.speech_callback:
                            for alert in alerts:
                                try:
                                    self.speech_callback(alert.get("spoken_alert", ""))
                                except Exception as se:
                                    print(f"[FlightPoller] ⚠️ Speech alert failed: {se}")

                    # Mark slot completed
                    state["completed_slots"].append(slot_to_run)
                    state["last_poll_timestamp"] = now.isoformat()
                    # If computer first came online late (after 20:30), mark both slots completed
                    if now.hour > 20 or (now.hour == 20 and now.minute >= 30):
                        if "17:00" not in state["completed_slots"]:
                            state["completed_slots"].append("17:00")
                        if "20:30" not in state["completed_slots"]:
                            state["completed_slots"].append("20:30")
                    _save_poll_state(state)

                await asyncio.sleep(30)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[FlightPoller] ⚠️ Daemon loop error: {e}")
                await asyncio.sleep(60)

    def stop(self):
        self._running = False
        print("[FlightPoller] 🛑 Daemon stopped.")


_daemon: FlightPollerDaemon | None = None


def get_poller_daemon(speech_callback=None) -> FlightPollerDaemon:
    global _daemon
    if _daemon is None:
        _daemon = FlightPollerDaemon(speech_callback=speech_callback)
    elif speech_callback and not _daemon.speech_callback:
        _daemon.speech_callback = speech_callback
    return _daemon
