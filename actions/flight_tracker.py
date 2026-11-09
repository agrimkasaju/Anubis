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


def _format_calendar_details(
    tracker: dict,
    price: int,
    drop_amount: int = 0,
    airline: Optional[str] = None,
    page_url: Optional[str] = None,
    flight_options: Optional[list[dict]] = None,
    returning_options: Optional[list[dict]] = None,
) -> tuple[str, str]:
    now = datetime.now()
    origin = tracker.get("origin", "Origin")
    destination = tracker.get("destination", "Destination")
    dep_date = tracker.get("date", "")
    ret_date = tracker.get("return_date")
    currency = tracker.get("currency", "USD")
    best_airline = airline or tracker.get("best_airline", "Unknown")

    bag_parts = []
    if tracker.get("carry_on", 0) > 0:
        bag_parts.append(f"{tracker['carry_on']} carry-on")
    if tracker.get("checked_bags", 0) > 0:
        bag_parts.append(f"{tracker['checked_bags']} checked bag(s)")
    bag_desc = f"Included Bags: {', '.join(bag_parts)}" if bag_parts else "Included Bags: Base fare (0 bags)"

    dates_desc = f"{dep_date} to {ret_date}" if ret_date else dep_date
    saving_text = f" (Dropped by ${drop_amount}!)" if drop_amount > 0 else " (Target Low Price Deal)"

    # Identify lowest overall and best nonstop from flight_options
    opts = [f for f in (flight_options or tracker.get("top_options", [])) if _price_to_int(f.get("price", "999999")) < 999999]
    cheapest = min(opts, key=lambda x: _price_to_int(x["price"])) if opts else None
    nonstops = [f for f in opts if f.get("stops", 0) == 0]
    best_nonstop = min(nonstops, key=lambda x: _price_to_int(x["price"])) if nonstops else None

    # Title
    if cheapest and best_nonstop and cheapest != best_nonstop:
        c_price = _price_to_int(cheapest["price"])
        ns_price = _price_to_int(best_nonstop["price"])
        cal_title = f"✈️ Flight Deal: {origin} → {destination} (From ${c_price} | Nonstop ${ns_price} {currency})"
    else:
        cal_title = f"✈️ Flight Deal: {origin} → {destination} (${price} {currency})"

    lines = [
        "🎯 Low Price Flight Notification from Anubis",
        "",
        f"• Route: {origin} to {destination}",
        f"• Travel Dates: {dates_desc}",
        f"• Lowest Fare: ${price} {currency}{saving_text}",
        f"• Airline: {best_airline}",
        f"• {bag_desc}",
        f"• Detected: {now.strftime('%A, %b %d at %I:%M %p')}",
    ]

    if opts:
        lines.append("")
        lines.append("────────────────────────────────────────")
        lines.append("🏆 TOP FLIGHT OPTIONS BREAKDOWN:")
        lines.append("")

        seen_keys = set()
        count = 0
        for f in opts:
            p_val = _price_to_int(f.get("price", "999999"))
            f_air = f.get("airline", "Airline")
            dep_t = f.get("departure", "")
            arr_t = f.get("arrival", "")
            stops = f.get("stops", 0)
            stops_str = "Nonstop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
            dur = f.get("duration", "")

            key = (f_air, p_val, dep_t)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            count += 1

            if f == cheapest:
                badge = "🥇 Lowest Fare"
            elif f == best_nonstop:
                badge = "⚡ Best Nonstop"
            else:
                badge = f"Option {count}"

            lines.append(f"{badge}: {f_air} — ${p_val} {currency}")
            lines.append(f"   • Flight: {dep_t} → {arr_t} ({dur}, {stops_str})")
            if f.get("layover"):
                lines.append(f"   • Layovers: {f['layover']}")

            # If return options exist and match first option
            if returning_options and count == 1:
                ret0 = returning_options[0]
                r_air = ret0.get("airline", f_air)
                r_dep = ret0.get("departure", "")
                r_arr = ret0.get("arrival", "")
                r_stops = "Nonstop" if ret0.get("stops", 0) == 0 else f"{ret0.get('stops')} stop(s)"
                lines.append(f"   • Return Leg: {r_air} {r_dep} → {r_arr} ({r_stops})")

            lines.append("")
            if count >= 4:
                break

        lines.append("────────────────────────────────────────")

    if page_url:
        lines.append(f"🔗 Google Flights Booking Link:\n{page_url}")

    return cal_title, "\n".join(lines)


def sync_price_drop_to_calendar(
    tracker: dict,
    price: int,
    drop_amount: int = 0,
    airline: Optional[str] = None,
    page_url: Optional[str] = None,
    flight_options: Optional[list[dict]] = None,
    returning_options: Optional[list[dict]] = None,
) -> tuple[bool, str]:
    """
    Adds a Google Calendar notification event for a detected low price flight deal.
    Sets as an all-day event on the current local day so it appears on the correct calendar date in every timezone.
    Includes full flight details (lowest fare, best nonstop, times, stops, layovers, booking link).
    """
    try:
        from actions.google_auth import get_calendar_service
        service = get_calendar_service(interactive=False)
        if not service:
            return False, "Google Calendar is not connected."

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

        origin = tracker.get("origin", "Origin")
        destination = tracker.get("destination", "Destination")

        cal_title, cal_desc = _format_calendar_details(
            tracker=tracker,
            price=price,
            drop_amount=drop_amount,
            airline=airline,
            page_url=page_url,
            flight_options=flight_options,
            returning_options=returning_options,
        )

        # Delete any existing deal events for this route to avoid duplicates
        try:
            q_res = service.events().list(calendarId="primary", q=f"Flight Deal: {origin} → {destination}").execute()
            for old_item in q_res.get("items", []):
                service.events().delete(calendarId="primary", eventId=old_item["id"]).execute()
        except Exception:
            pass

        body = {
            "summary": cal_title,
            "description": cal_desc,
            "start": {"date": today_str},
            "end": {"date": tomorrow_str},
        }
        created = service.events().insert(calendarId="primary", body=body).execute()
        print(f"[FlightTracker] 📅 Synced flight deal (${price}) to Google Calendar on {today_str}: {cal_title}")
        return True, created.get("htmlLink", "")
    except Exception as e:
        print(f"[FlightTracker] ⚠️ Calendar sync error: {e}")
        return False, str(e)


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

    candidates = [f for f in (outbound + returning) if _price_to_int(f.get("price")) < 999999]
    if airline and candidates:
        pref = [f for f in candidates if airline.lower() in f.get("airline", "").lower()]
        if pref:
            candidates = pref

    best_candidate = min(candidates, key=lambda x: _price_to_int(x.get("price"))) if candidates else {}
    baseline_price = _price_to_int(best_candidate.get("price", 999999))
    best_airline = best_candidate.get("airline") or (airline or "Unknown")

    nonstops = [f for f in (outbound + returning) if f.get("stops", 0) == 0 and _price_to_int(f.get("price")) < 999999]
    best_nonstop = min(nonstops, key=lambda x: _price_to_int(x.get("price"))) if nonstops else None

    itinerary_desc = f"{best_airline} {best_candidate.get('departure', '')}-{best_candidate.get('arrival', '')} ({best_candidate.get('duration', '')})"
    if best_nonstop and best_nonstop != best_candidate:
        itinerary_desc += f"; Nonstop: {best_nonstop.get('airline')} at ${best_nonstop.get('price')}"

    tracker_id = f"ft_{uuid.uuid4().hex[:8]}"
    tracker = {
        "id": tracker_id,
        "status": "ACTIVE",
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "poll_times": ["17:00", "20:30"],
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
        "top_options": outbound[:5],
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

    # Sync initial baseline flight deal to Google Calendar
    try:
        sync_price_drop_to_calendar(
            tracker=tracker,
            price=baseline_price,
            drop_amount=0,
            airline=best_airline,
            page_url=page_url,
            flight_options=outbound,
            returning_options=returning,
        )
    except Exception as ce:
        print(f"[FlightTracker] ⚠️ Calendar sync notice: {ce}")

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
        f"I'll poll during your evening window at 5:00 PM and 8:30 PM until {expires_at[:10]} "
        f"(with automatic catch-up if your computer turns on past 5:00 PM) "
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

    candidates = [f for f in (outbound + returning) if _price_to_int(f.get("price")) < 999999]
    if tracker.get("airline") and candidates:
        pref = [f for f in candidates if tracker["airline"].lower() in f.get("airline", "").lower()]
        if pref:
            candidates = pref

    best_candidate = min(candidates, key=lambda x: _price_to_int(x.get("price"))) if candidates else {}
    current_price = _price_to_int(best_candidate.get("price", 999999))
    current_airline = best_candidate.get("airline") or tracker.get("best_airline", "Unknown")

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
            if outbound:
                t["top_options"] = outbound[:5]
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

                # Sync price drop deal notification to Google Calendar
                try:
                    sync_price_drop_to_calendar(
                        tracker=t,
                        price=current_price,
                        drop_amount=drop_amount,
                        airline=current_airline,
                        page_url=page_url,
                        flight_options=outbound,
                        returning_options=returning,
                    )
                except Exception as ce:
                    print(f"[FlightTracker] ⚠️ Calendar sync notice: {ce}")

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


def sync_active_trackers_to_calendar() -> str:
    """Syncs the current best flight deals for all active trackers to Google Calendar."""
    active = get_active_trackers()
    if not active:
        return "You have no active flight price trackers to sync to Google Calendar."

    synced = []
    for t in active:
        price = t.get("lowest_seen_price", t.get("baseline_price", 0))
        airline = t.get("best_airline", "Unknown")
        ok, res = sync_price_drop_to_calendar(
            tracker=t,
            price=price,
            drop_amount=0,
            airline=airline,
            flight_options=t.get("top_options"),
        )
        if ok:
            synced.append(f"{t['origin']} → {t['destination']} (${price} USD on {airline})")

    if synced:
        return f"Added low price flight deal notification to Google Calendar for: {', '.join(synced)}."
    else:
        return "Failed to sync flight deals to Google Calendar."
