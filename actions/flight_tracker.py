# actions/flight_tracker.py

"""
Autonomous flight price tracking and polling engine for Anubis.
Monitors flight fares across user-defined date windows with exact baggage allowance filters,
running quiet headless checks twice daily (8:30 AM & 6:30 PM) and alerting on price drops.
"""

import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Ensure project root in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from actions.flight_finder import (
    _parse_date,
    scrape_flights_headless,
)

TRACKERS_FILE = project_root / "data" / "flight_trackers.json"


def _ensure_data_dir():
    TRACKERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not TRACKERS_FILE.exists():
        TRACKERS_FILE.write_text(json.dumps({"trackers": []}, indent=2), encoding="utf-8")


def _load_data() -> dict:
    _ensure_data_dir()
    try:
        return json.loads(TRACKERS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[FlightTracker] ⚠️ Error loading tracker data: {e}")
        return {"trackers": []}


def _save_data(data: dict):
    _ensure_data_dir()
    TRACKERS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _price_to_int(price_val: str | int | float) -> int:
    digits = re.sub(r"[^\d]", "", str(price_val or ""))
    return int(digits) if digits else 999999


def _send_desktop_notification(title: str, message: str):
    """Dispatches a native Linux notification with audio chime."""
    safe_title = title.replace('"', '\\"').replace("'", "'\\''")
    safe_msg = message.replace('"', '\\"').replace("'", "'\\''")
    cmd = (
        f'paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null; '
        f'gdbus call --session --dest org.freedesktop.Notifications '
        f'--object-path /org/freedesktop/Notifications '
        f'--method org.freedesktop.Notifications.Notify '
        f'"Anubis" 0 "airplane" "{safe_title}" "{safe_msg}" [] "{{\}}" 10000 >/dev/null 2>&1'
    )
    try:
        subprocess.Popen(["/bin/bash", "-c", cmd])
    except Exception as e:
        print(f"[FlightTracker] ⚠️ Notification failed: {e}")


def add_flight_tracker(
    origin:       str,
    destination:  str,
    date:         str,
    return_date:  Optional[str] = None,
    end_date:     Optional[str] = None,
    carry_on:     int           = 0,
    checked_bags: int           = 0,
    airline:      Optional[str] = None,
    cabin:        str           = "economy",
    passengers:   int           = 1,
) -> dict:
    """
    Creates and persists a new flight tracking job.
    Runs an initial baseline headless scrape to anchor the starting price.
    """
    data = _load_data()
    now = datetime.now()

    dep_date = _parse_date(date)
    ret_date = _parse_date(return_date) if return_date else None

    # Handle cross-year rollover for round-trip return date
    if ret_date and dep_date:
        try:
            d_dt = datetime.strptime(dep_date, "%Y-%m-%d")
            r_dt = datetime.strptime(ret_date, "%Y-%m-%d")
            if r_dt < d_dt:
                r_dt = r_dt.replace(year=d_dt.year + 1)
                ret_date = r_dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    # Parse tracker end / expiration date (e.g. "next Saturday" or default to dep_date)
    if end_date:
        parsed_end = _parse_date(end_date)
        expires_at = f"{parsed_end}T23:59:59"
    elif ret_date:
        expires_at = f"{ret_date}T23:59:59"
    else:
        expires_at = f"{dep_date}T23:59:59"

    print(
        f"[FlightTracker] ✈️ Initializing tracker: {origin} → {destination} "
        f"({dep_date}{' to ' + ret_date if ret_date else ''}) until {expires_at[:10]} | "
        f"bags: {carry_on} carry-on, {checked_bags} checked"
    )

    # Initial baseline headless scrape
    outbound, returning, page_url = scrape_flights_headless(
        origin=origin,
        destination=destination,
        date=dep_date,
        return_date=ret_date,
        passengers=passengers,
        cabin=cabin,
        carry_on=carry_on,
        checked_bags=checked_bags,
        airline=airline,
    )

    baseline_price = 999999
    best_airline = airline or "Unknown"
    itinerary_desc = "Flight details unavailable"

    if returning:
        cheapest_ret = min(returning, key=lambda x: _price_to_int(x.get("price", "999999")))
        baseline_price = _price_to_int(cheapest_ret.get("price", 999999))
        best_airline = cheapest_ret.get("airline") or (outbound[0].get("airline") if outbound else "Unknown")
        out0 = outbound[0] if outbound else {}
        itinerary_desc = (
            f"Outbound: {out0.get('airline', 'N/A')} {out0.get('departure', '')}-{out0.get('arrival', '')}; "
            f"Return: {cheapest_ret.get('airline', 'N/A')} {cheapest_ret.get('departure', '')}-{cheapest_ret.get('arrival', '')}"
        )
    elif outbound:
        cheapest_out = min(outbound, key=lambda x: _price_to_int(x.get("price", "999999")))
        baseline_price = _price_to_int(cheapest_out.get("price", 999999))
        best_airline = cheapest_out.get("airline") or "Unknown"
        itinerary_desc = f"Departing {cheapest_out.get('departure', '')}-{cheapest_out.get('arrival', '')}"

    tracker_id = f"ft_{uuid.uuid4().hex[:8]}"
    tracker = {
        "id": tracker_id,
        "status": "ACTIVE",
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "poll_times": ["08:30", "18:30"],
        "origin": origin,
        "destination": destination,
        "date": dep_date,
        "return_date": ret_date,
        "passengers": passengers,
        "cabin": cabin,
        "carry_on": carry_on,
        "checked_bags": checked_bags,
        "airline": airline,
        "baseline_price": baseline_price,
        "lowest_seen_price": baseline_price,
        "currency": "USD",
        "best_airline": best_airline,
        "itinerary": itinerary_desc,
        "history": [
            {
                "timestamp": now.isoformat(),
                "price": baseline_price,
                "airline": best_airline,
                "price_dropped": False,
            }
        ],
        "last_polled": now.isoformat(),
        "last_alerted": None,
    }

    data["trackers"].append(tracker)
    _save_data(data)

    bag_str = ""
    if carry_on > 0 and checked_bags > 0:
        bag_str = f" with {carry_on} carry-on and {checked_bags} checked bag(s)"
    elif carry_on > 0:
        bag_str = f" with {carry_on} carry-on bag(s)"
    elif checked_bags > 0:
        bag_str = f" with {checked_bags} checked bag(s)"

    msg = (
        f"Tracking flights from {origin} to {destination} ({dep_date}"
        f"{' to ' + ret_date if ret_date else ''}){bag_str}. "
        f"Baseline price is ${baseline_price} USD on {best_airline}. "
        f"I'll poll every morning and evening at 8:30 AM and 6:30 PM until {expires_at[:10]} "
        f"and alert you immediately if the price drops."
    )
    return {"status": "success", "tracker": tracker, "message": msg}


def get_active_trackers() -> list[dict]:
    """Returns all active, non-expired flight trackers, auto-expiring stale ones."""
    data = _load_data()
    now = datetime.now()
    active = []
    modified = False

    for t in data.get("trackers", []):
        if t.get("status") != "ACTIVE":
            continue

        expires_at = t.get("expires_at", "")
        try:
            exp_dt = datetime.fromisoformat(expires_at)
            if now > exp_dt:
                t["status"] = "EXPIRED"
                modified = True
                print(f"[FlightTracker] ⏳ Tracker {t['id']} expired on {expires_at[:10]}.")
                continue
        except Exception:
            pass

        active.append(t)

    if modified:
        _save_data(data)

    return active


def poll_tracker(tracker: dict) -> Optional[dict]:
    """
    Executes a single headless flight scrape for a given tracker.
    Returns an alert dict if the price dropped below lowest_seen_price.
    """
    now = datetime.now()
    t_id = tracker["id"]

    outbound, returning, page_url = scrape_flights_headless(
        origin=tracker["origin"],
        destination=tracker["destination"],
        date=tracker["date"],
        return_date=tracker.get("return_date"),
        passengers=tracker.get("passengers", 1),
        cabin=tracker.get("cabin", "economy"),
        carry_on=tracker.get("carry_on", 0),
        checked_bags=tracker.get("checked_bags", 0),
        airline=tracker.get("airline"),
    )

    current_price = 999999
    current_airline = tracker.get("best_airline", "Unknown")

    if returning:
        cheapest_ret = min(returning, key=lambda x: _price_to_int(x.get("price", "999999")))
        current_price = _price_to_int(cheapest_ret.get("price", 999999))
        current_airline = cheapest_ret.get("airline") or (outbound[0].get("airline") if outbound else current_airline)
    elif outbound:
        cheapest_out = min(outbound, key=lambda x: _price_to_int(x.get("price", "999999")))
        current_price = _price_to_int(cheapest_out.get("price", 999999))
        current_airline = cheapest_out.get("airline") or current_airline

    if current_price >= 999999:
        print(f"[FlightTracker] ⚠️ Could not extract valid price for tracker {t_id}")
        return None

    prev_lowest = tracker.get("lowest_seen_price", tracker.get("baseline_price", 999999))
    price_dropped = current_price < prev_lowest
    drop_amount = prev_lowest - current_price if price_dropped else 0

    # Update record
    data = _load_data()
    alert_info = None

    for t in data.get("trackers", []):
        if t["id"] == t_id:
            t["last_polled"] = now.isoformat()
            t["history"].append({
                "timestamp": now.isoformat(),
                "price": current_price,
                "airline": current_airline,
                "price_dropped": price_dropped,
                "drop_amount": drop_amount,
            })

            if price_dropped:
                t["lowest_seen_price"] = current_price
                t["best_airline"] = current_airline
                t["last_alerted"] = now.isoformat()

                bag_parts = []
                if t.get("carry_on", 0) > 0:
                    bag_parts.append(f"{t['carry_on']} carry-on")
                if t.get("checked_bags", 0) > 0:
                    bag_parts.append(f"{t['checked_bags']} checked bag(s)")
                bag_note = f" (includes {' and '.join(bag_parts)})" if bag_parts else ""

                alert_title = f"✈️ Flight Price Drop: ${current_price} USD"
                alert_body = (
                    f"{t['origin']} → {t['destination']} on {current_airline} dropped by ${drop_amount}!\n"
                    f"New price: ${current_price} USD{bag_note}."
                )
                spoken_alert = (
                    f"Flight price alert: Fares from {t['origin']} to {t['destination']} dropped by ${drop_amount} "
                    f"down to ${current_price} USD on {current_airline}{bag_note}."
                )

                _send_desktop_notification(alert_title, alert_body)
                alert_info = {
                    "tracker_id": t_id,
                    "origin": t["origin"],
                    "destination": t["destination"],
                    "old_price": prev_lowest,
                    "new_price": current_price,
                    "drop_amount": drop_amount,
                    "airline": current_airline,
                    "spoken_alert": spoken_alert,
                }
            break

    _save_data(data)
    return alert_info


def poll_all_active_trackers() -> list[dict]:
    """Polls all active trackers and returns a list of price drop alerts."""
    active = get_active_trackers()
    if not active:
        return []

    print(f"[FlightTracker] ⏰ Polling {len(active)} active flight tracker(s)...")
    alerts = []
    for t in active:
        try:
            alert = poll_tracker(t)
            if alert:
                alerts.append(alert)
        except Exception as e:
            print(f"[FlightTracker] ❌ Error polling tracker {t.get('id')}: {e}")

    return alerts


def list_flight_trackers(include_expired: bool = False) -> str:
    """Returns human-readable text listing all tracked flights."""
    data = _load_data()
    trackers = data.get("trackers", [])
    if not include_expired:
        trackers = [t for t in trackers if t.get("status") == "ACTIVE"]

    if not trackers:
        return "You have no active flight price trackers, sir."

    lines = ["Here are your active flight price trackers, sir:"]
    for i, t in enumerate(trackers, 1):
        bags = []
        if t.get("carry_on", 0) > 0:
            bags.append(f"{t['carry_on']} carry-on")
        if t.get("checked_bags", 0) > 0:
            bags.append(f"{t['checked_bags']} checked")
        bag_str = f" with {', '.join(bags)}" if bags else ""

        ret_str = f" returning {t['return_date']}" if t.get("return_date") else " (one-way)"
        exp_str = t.get("expires_at", "")[:10]
        lines.append(
            f"{i}. {t['origin']} to {t['destination']} on {t['date']}{ret_str}{bag_str}. "
            f"Lowest price seen: ${t.get('lowest_seen_price', t.get('baseline_price'))} USD ({t.get('best_airline')}). "
            f"Tracking active until {exp_str}."
        )

    return "\n".join(lines)


def cancel_flight_tracker(origin: str, destination: str) -> str:
    """Cancels tracking for a specific route."""
    data = _load_data()
    cancelled = 0
    for t in data.get("trackers", []):
        if (
            t.get("status") == "ACTIVE"
            and origin.lower() in t.get("origin", "").lower()
            and destination.lower() in t.get("destination", "").lower()
        ):
            t["status"] = "CANCELLED"
            cancelled += 1

    if cancelled > 0:
        _save_data(data)
        return f"Cancelled flight tracking for {origin} to {destination}, sir."
    return f"No active flight tracking found for {origin} to {destination}, sir."
