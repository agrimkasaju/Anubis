# services/flight_poller.py

"""
Background flight price polling daemon for Anubis.
Runs continuously inside the Anubis background service, triggering headless checks
at 8:30 AM and 6:30 PM daily for all active flight trackers.
"""

import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Ensure project root in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from actions.flight_tracker import poll_all_active_trackers, get_active_trackers


class FlightPollerDaemon:
    def __init__(self, target_times: tuple[str, ...] = ("08:30", "18:30"), speech_callback=None):
        self.target_times = target_times
        self.speech_callback = speech_callback
        self._last_polled_minute: str | None = None
        self._running = False

    async def start(self):
        if self._running:
            return
        self._running = True
        print(f"[FlightPoller] 🛫 Daemon started (Scheduled checks at: {', '.join(self.target_times)} local time).")

        while self._running:
            try:
                now = datetime.now()
                current_time = now.strftime("%H:%M")

                if current_time in self.target_times and current_time != self._last_polled_minute:
                    active = get_active_trackers()
                    if active:
                        print(f"[FlightPoller] ⏰ Scheduled poll triggered at {current_time} for {len(active)} tracker(s).")
                        self._last_polled_minute = current_time

                        loop = asyncio.get_running_loop()
                        alerts = await loop.run_in_executor(None, poll_all_active_trackers)

                        if alerts and self.speech_callback:
                            for alert in alerts:
                                try:
                                    self.speech_callback(alert.get("spoken_alert", ""))
                                except Exception as se:
                                    print(f"[FlightPoller] ⚠️ Speech alert failed: {se}")
                    else:
                        self._last_polled_minute = current_time

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
