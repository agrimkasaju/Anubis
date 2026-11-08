#flight_finder.py
import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus

from config import is_windows, is_mac, is_linux
from actions.browser_control import _bt, _ensure_started, browser_control

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

_MONTH_MAP: dict[str, int] = {
    "january": 1, "february": 2, "march": 3,     "april": 4,
    "may": 5,     "june": 6,     "july": 7,       "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "ocak": 1,  "şubat": 2,  "mart": 3,   "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10,  "kasım": 11, "aralık": 12,
}

_RELATIVE_MAP_KEYS = {
    "today", "bugün",
    "tomorrow", "yarın",
}


def _parse_date(raw: str) -> str:
    raw   = raw.strip()
    lower = raw.lower()
    today = datetime.now()

    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw

    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    relative = {
        "today": today, "bugün": today,
        "tomorrow": today + timedelta(days=1),
        "yarın":    today + timedelta(days=1),
    }
    for key, val in relative.items():
        if key in lower:
            return val.strftime("%Y-%m-%d")

    # Clean conversational modifiers like "around", "close to", "about", "for", "on"
    cleaned = re.sub(r"(?i)\b(around|close to|about|on|for|from|to|near)\b", "", raw).strip()
    try:
        from dateutil import parser as dt_parser
        dt = dt_parser.parse(cleaned, fuzzy=True, default=today)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        pass

    for month_name, month_num in _MONTH_MAP.items():
        if month_name in lower:
            day_match = re.search(r"\d{1,2}", raw)
            if day_match:
                day  = int(day_match.group())
                year = today.year if month_num >= today.month else today.year + 1
                return f"{year}-{month_num:02d}-{day:02d}"

    print(f"[FlightFinder] ⚠️ Could not parse date '{raw}' — using today.")
    return today.strftime("%Y-%m-%d")


_CABIN_CODE: dict[str, str] = {
    "economy":  "1",
    "premium":  "2",
    "business": "3",
    "first":    "4",
}


def _build_google_flights_url(
    origin:      str,
    destination: str,
    date:        str,
    return_date: str | None = None,
    passengers:  int        = 1,
    cabin:       str        = "economy",
) -> str:
    cabin_code = _CABIN_CODE.get(cabin.lower(), "1")
    origin_enc      = quote_plus(origin)
    destination_enc = quote_plus(destination)

    if return_date:
        trip = f"Round+trip+flights+from+{origin_enc}+to+{destination_enc}+on+{date}+returning+{return_date}"
    else:
        trip = f"One+way+flights+from+{origin_enc}+to+{destination_enc}+on+{date}"

    return (
        f"https://www.google.com/travel/flights"
        f"?q={trip}"
        f"&curr=USD"
        f"&cabin={cabin_code}"
        f"&adults={passengers}"
    )


def _parse_flight_card(aria: str, raw_text: str) -> dict:
    flight = {
        "airline": "",
        "departure": "",
        "arrival": "",
        "duration": "",
        "stops": 0,
        "price": "",
        "currency": "USD",
        "is_round_trip": False,
        "separate_tickets": False,
        "layover": "",
        "arrival_date": "",
    }

    combined = (aria + " " + raw_text).lower()
    if "separate tickets" in combined:
        flight["separate_tickets"] = True
    if "round trip" in combined:
        flight["is_round_trip"] = True

    if aria:
        # Price extraction: e.g. "From 656 US dollars" or "From 656 Canadian dollars"
        pm = re.search(r"From\s+(\d[\d,]*)\s+([A-Za-z]+)\s+dollars", aria, re.IGNORECASE)
        if pm:
            flight["price"] = f"${pm.group(1)}"
            curr = pm.group(2).upper()
            flight["currency"] = "CAD" if "CANADIAN" in curr else "USD"
        else:
            pm2 = re.search(r"[$€£](\d[\d,]*)", aria)
            if pm2:
                flight["price"] = f"${pm2.group(1)}"

        # Stops & Airline: e.g. "Nonstop flight with WestJet." or "2 stops flight with Air Canada."
        am = re.search(r"(Nonstop|\d+\s+stops?)\s+flight with\s+([^.]+?)(?:\.|$)", aria, re.IGNORECASE)
        if am:
            stops_str = am.group(1)
            flight["stops"] = 0 if "nonstop" in stops_str.lower() else int(re.search(r"\d+", stops_str).group())
            flight["airline"] = am.group(2).strip()

        # Departure & Arrival times
        dm = re.search(r"Leaves\s+.*?\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))", aria)
        if dm:
            flight["departure"] = dm.group(1).strip()
        arm = re.search(r"arrives\s+.*?\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))(?:\s+on\s+([A-Za-z]+,\s+[A-Za-z]+\s+\d+))?", aria)
        if arm:
            flight["arrival"] = arm.group(1).strip()
            if arm.group(2):
                flight["arrival_date"] = arm.group(2).strip()

        # Total duration
        durm = re.search(r"Total duration\s+([^.]+?)(?:\.|$)", aria)
        if durm:
            flight["duration"] = durm.group(1).strip()

        # Layovers
        laym = re.findall(r"(\d+\s*hr(?:\s*\d+\s*min)?\s*layover\s+at\s+[^.]+)", aria, re.IGNORECASE)
        if laym:
            flight["layover"] = "; ".join(laym)

    # Fallback to raw text parsing for missing values
    if not flight["departure"] or not flight["airline"]:
        time_m = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*[–\-—]\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)(?:\+\d+)?)", raw_text)
        if time_m:
            flight["departure"] = flight["departure"] or time_m.group(1).strip()
            flight["arrival"] = flight["arrival"] or time_m.group(2).strip()

        dur_m = re.search(r"(\d+\s*h[r]?\s*(?:\d+\s*m(?:in)?)?)", raw_text)
        if dur_m:
            flight["duration"] = flight["duration"] or dur_m.group(1).strip()

        stops_m = re.search(r"(Nonstop|\d+\s*stop[s]?)", raw_text, re.IGNORECASE)
        if stops_m:
            flight["stops"] = 0 if "nonstop" in stops_m.group(1).lower() else int(re.search(r"\d+", stops_m.group(1)).group())

        price_m = re.search(r"(\$\d[\d,]*)", raw_text)
        if price_m:
            flight["price"] = flight["price"] or price_m.group(1).strip()

    return flight


async def _scrape_flights_async(
    origin:      str,
    destination: str,
    date:        str,
    return_date: str | None,
    passengers:  int,
    cabin:       str,
) -> tuple[list[dict], list[dict], str, str]:
    _ensure_started()
    page = await _bt._get_page()

    url = _build_google_flights_url(origin, destination, date, return_date, passengers, cabin)
    print(f"[FlightFinder] 🌐 Navigating to: {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=20000)

    # Wait for flight cards to render
    for _ in range(12):
        await asyncio.sleep(0.5)
        cards = await page.query_selector_all("li.pIav2d")
        if cards:
            break

    cards = await page.query_selector_all("li.pIav2d")
    outbound: list[dict] = []
    for c in cards[:5]:
        link = await c.query_selector("div.JMc5Xc")
        aria = await link.get_attribute("aria-label") if link else ""
        txt  = await c.inner_text()
        parsed = _parse_flight_card(aria, txt)
        if parsed.get("airline") or parsed.get("price"):
            outbound.append(parsed)

    returning: list[dict] = []
    # For round trips, inspect return leg details by clicking the top departing flight
    if return_date and cards:
        first_link = await cards[0].query_selector("div.JMc5Xc")
        if first_link:
            await page.evaluate("(el) => el.click()", first_link)
            # Wait for returning flights page to load
            for _ in range(16):
                await asyncio.sleep(0.5)
                txt = await page.inner_text("body")
                if "return to" in txt.lower() or "returning flights" in txt.lower():
                    break

            ret_cards = await page.query_selector_all("li.pIav2d")
            for c in ret_cards[:5]:
                link = await c.query_selector("div.JMc5Xc")
                aria = await link.get_attribute("aria-label") if link else ""
                txt  = await c.inner_text()
                parsed = _parse_flight_card(aria, txt)
                if parsed.get("airline") or parsed.get("price"):
                    returning.append(parsed)

    raw_text = await page.inner_text("body")
    return outbound, returning, page.url, raw_text


def _parse_flights_regex(raw_text: str) -> list[dict]:
    pattern = re.compile(
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*[–\-—]\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*\n+"
        r"([^\n]+)\s*\n+"
        r"(\d+\s*h[r]?\s*(?:\d+\s*m(?:in)?)?)\s*\n+"
        r"[^\n]+\s*\n+"
        r"(Nonstop|\d+\s*stop[s]?)"
        r"(?:.*?\n+)*?"
        r"(\$\d+)",
        re.MULTILINE
    )
    flights = []
    for m in pattern.finditer(raw_text):
        dep, arr, airline, dur, stops, price = m.groups()
        airline_clean = airline.split("Operated")[0].strip()
        stop_count = 0 if "nonstop" in stops.lower() else int(re.search(r"\d+", stops).group() if re.search(r"\d+", stops) else 1)
        flights.append({
            "airline": airline_clean,
            "departure": dep.strip(),
            "arrival": arr.strip(),
            "duration": dur.strip(),
            "stops": stop_count,
            "price": price.strip(),
            "currency": "USD"
        })
        if len(flights) >= 5:
            break
    return flights


def _parse_flights_with_gemini(
    raw_text:    str,
    origin:      str,
    destination: str,
    date:        str,
) -> list[dict]:
    from or_client import client

    prompt = (
        f"Extract flight options from {origin} to {destination} on {date} "
        f"from this Google Flights page text:\n\n{raw_text[:12000]}\n\n"
        f"Return ONLY a JSON object with this exact structure:\n"
        f'{{"flights": [{{"airline":"...","departure":"HH:MM","arrival":"HH:MM",'
        f'"duration":"Xh Ym","stops":0,"price":"...","currency":"USD"}}]}}\n'
        f'If no flights found, return: {{"flights": []}}'
    )

    try:
        result = client.chat_json(prompt, system="Return only valid JSON object. No extra text.")
        flights = result.get("flights") if isinstance(result, dict) else (result if isinstance(result, list) else [])
        if flights:
            return flights
    except Exception as e:
        print(f"[FlightFinder] ⚠️ parse failed: {e}")

    # Fallback to direct regex parser
    fallback = _parse_flights_regex(raw_text)
    if fallback:
        print(f"[FlightFinder] ✈️ Regex fallback found {len(fallback)} flights")
        return fallback

    return []


def _format_spoken(
    outbound:    list[dict],
    returning:   list[dict],
    origin:      str,
    destination: str,
    date:        str,
    return_date: str | None = None,
) -> str:
    trip_desc = f"{origin} to {destination} on {date}" + (f" returning {return_date}" if return_date else "")
    if not outbound:
        return (
            f"I couldn't find any flights for {trip_desc}, sir. "
            f"The page may not have loaded correctly."
        )

    # ONE-WAY TRIP
    if not return_date or not returning:
        lines = [f"Here are the top one-way flights from {origin} to {destination} on {date}, sir."]
        for i, f in enumerate(outbound[:3], 1):
            airline   = f.get("airline",   "Unknown airline")
            departure = f.get("departure", "--:--")
            arrival   = f.get("arrival",   "--:--")
            duration  = f.get("duration",  "")
            stops     = f.get("stops",     0)
            price     = f.get("price",     "")
            currency  = f.get("currency",  "USD")

            stop_str  = "non-stop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
            price_str = f"{price} {currency}".strip() if price else "price unavailable"
            dur_str   = f", {duration}" if duration else ""

            lines.append(
                f"Option {i}: {airline}, departing {departure}, "
                f"arriving {arrival}{dur_str}, {stop_str}, {price_str}."
            )

        priced = [f for f in outbound if f.get("price")]
        if priced:
            cheapest = min(
                priced,
                key=lambda x: int(re.sub(r"[^\d]", "", str(x["price"])) or "999999"),
            )
            lines.append(
                f"The cheapest one-way option is {cheapest.get('airline')} "
                f"at {cheapest.get('price')} {cheapest.get('currency', 'USD')}."
            )
        return " ".join(lines)

    # ROUND-TRIP
    lines = [f"Here are the flight options for a round trip from {origin} to {destination}, departing {date} and returning {return_date}, sir."]
    out0 = outbound[0]
    out_stops = "non-stop" if out0.get("stops", 0) == 0 else f"{out0.get('stops')} stop{'s' if out0.get('stops', 0) > 1 else ''}"
    lines.append(
        f"For your outbound flight on {date}, the recommended option is {out0.get('airline')}, leaving {origin} at {out0.get('departure')} and arriving in {destination} at {out0.get('arrival')} ({out0.get('duration')}, {out_stops})."
    )

    cheapest_ret = min(
        returning,
        key=lambda x: int(re.sub(r"[^\d]", "", str(x.get("price", "999999"))) or "999999")
    )
    same_airline_ret = next(
        (r for r in returning if out0.get("airline", "").lower() in r.get("airline", "").lower()),
        None
    )

    cheap_stops = "non-stop" if cheapest_ret.get("stops", 0) == 0 else f"{cheapest_ret.get('stops')} stop{'s' if cheapest_ret.get('stops', 0) > 1 else ''}"

    if cheapest_ret.get("airline", "").lower() != out0.get("airline", "").lower() or cheapest_ret.get("separate_tickets"):
        lines.append(
            f"The lowest combined round-trip total is {cheapest_ret.get('price')} {cheapest_ret.get('currency', 'USD')}. "
            f"Please note this lowest price requires separate tickets: flying {out0.get('airline')} outbound and {cheapest_ret.get('airline')} on the return flight departing at {cheapest_ret.get('departure')} ({cheapest_ret.get('duration')}, {cheap_stops})."
        )
        if same_airline_ret and same_airline_ret != cheapest_ret:
            same_stops = "non-stop" if same_airline_ret.get("stops", 0) == 0 else f"{same_airline_ret.get('stops')} stop{'s' if same_airline_ret.get('stops', 0) > 1 else ''}"
            lines.append(
                f"If you prefer to fly {out0.get('airline')} both ways {same_stops}, the total round-trip fare is {same_airline_ret.get('price')} {same_airline_ret.get('currency', 'USD')}, returning at {same_airline_ret.get('departure')} and arriving at {same_airline_ret.get('arrival')}."
            )
    else:
        lines.append(
            f"The round-trip flight on {cheapest_ret.get('airline')} is {cheapest_ret.get('price')} {cheapest_ret.get('currency', 'USD')} total, returning at {cheapest_ret.get('departure')} ({cheap_stops})."
        )

    if len(outbound) > 1:
        alt = outbound[1]
        lines.append(
            f"Alternatively, {alt.get('airline')} also offers outbound departures at {alt.get('departure')} with round-trip fares starting from {alt.get('price')}."
        )

    return " ".join(lines)


def _format_text_report(
    outbound:    list[dict],
    returning:   list[dict],
    origin:      str,
    destination: str,
    date:        str,
    return_date: str | None,
    page_url:    str,
) -> str:
    lines = [
        "JARVIS — Flight Search Results",
        "─" * 50,
        f"Trip Type : {'Round Trip' if return_date else 'One Way'}",
        f"Route     : {origin} → {destination}",
        f"Departure : {date}",
    ]
    if return_date:
        lines.append(f"Return    : {return_date}")
    lines += [
        f"Searched  : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Source    : {page_url}",
        "─" * 50,
        "",
    ]

    if not outbound:
        lines.append("No flights found.")
        return "\n".join(lines)

    lines.append(f"OUTBOUND FLIGHTS ({origin} → {destination}):")
    for i, f in enumerate(outbound, 1):
        stops    = f.get("stops", 0)
        stop_str = "Non-stop" if stops == 0 else f"{stops} stop(s)"
        lines += [
            f"Flight {i}:",
            f"  Airline   : {f.get('airline',   'N/A')}",
            f"  Departure : {f.get('departure', 'N/A')}",
            f"  Arrival   : {f.get('arrival',   'N/A')}",
            f"  Duration  : {f.get('duration',  'N/A')}",
            f"  Stops     : {stop_str}",
            f"  Price     : {f.get('price', 'N/A')} {f.get('currency', 'USD')}",
            "",
        ]

    if return_date and returning:
        lines.append("─" * 50)
        lines.append(f"RETURN OPTIONS ({destination} → {origin} on {return_date}):")
        for i, f in enumerate(returning, 1):
            stops    = f.get("stops", 0)
            stop_str = "Non-stop" if stops == 0 else f"{stops} stop(s)"
            sep_str  = " [Separate Tickets]" if f.get("separate_tickets") else ""
            lines += [
                f"Option {i}{sep_str}:",
                f"  Airline       : {f.get('airline',   'N/A')}",
                f"  Departure     : {f.get('departure', 'N/A')}",
                f"  Arrival       : {f.get('arrival',   'N/A')}",
                f"  Duration      : {f.get('duration',  'N/A')}",
                f"  Stops         : {stop_str}",
                f"  Total RT Fare : {f.get('price', 'N/A')} {f.get('currency', 'USD')}",
            ]
            if f.get("layover"):
                lines.append(f"  Layovers      : {f.get('layover')}")
            lines.append("")

    return "\n".join(lines)


def _save_to_desktop(content: str, origin: str, destination: str) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"flights_{origin}_{destination}_{ts}.txt".replace(" ", "_")
    desktop  = Path.home() / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    filepath = desktop / filename

    filepath.write_text(content, encoding="utf-8")
    print(f"[FlightFinder] 💾 Saved: {filepath}")

    try:
        if is_windows():
            subprocess.Popen(["notepad.exe", str(filepath)])
        elif is_mac():
            subprocess.Popen(["open", "-t", str(filepath)])
        else:
            subprocess.Popen(["xdg-open", str(filepath)])
    except Exception as e:
        print(f"[FlightFinder] ⚠️ Could not open text editor: {e}")

    return str(filepath)


def flight_finder(parameters: dict, player=None, speak=None) -> str:
    params = parameters or {}

    origin      = params.get("origin",      "").strip()
    destination = params.get("destination", "").strip()
    date_raw    = params.get("date",        "").strip()
    return_raw  = (params.get("return_date") or "").strip()
    passengers  = max(1, int(params.get("passengers", 1)))
    cabin       = params.get("cabin", "economy").strip().lower()
    save        = bool(params.get("save", False))

    if not origin or not destination:
        return "Please provide both origin and destination, sir."
    if not date_raw:
        return "Please provide a departure date, sir."

    if cabin not in _CABIN_CODE:
        cabin = "economy"

    date        = _parse_date(date_raw)
    return_date = _parse_date(return_raw) if return_raw else None

    # Handle year rollover for return trips (e.g. Dec 19 -> Jan 3)
    if return_date and date:
        try:
            dep_dt = datetime.strptime(date, "%Y-%m-%d")
            ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
            if ret_dt < dep_dt:
                ret_dt = ret_dt.replace(year=dep_dt.year + 1)
                return_date = ret_dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    if player:
        log_msg = f"[FlightFinder] {origin} → {destination} ({date} to {return_date})" if return_date else f"[FlightFinder] {origin} → {destination} on {date}"
        player.write_log(log_msg)

    if speak:
        speak_msg = f"Searching round-trip flights from {origin} to {destination}, departing {date} and returning {return_date}, sir." if return_date else f"Searching flights from {origin} to {destination} on {date}, sir."
        speak(speak_msg)

    print(
        f"[FlightFinder] ▶️ {origin} → {destination} | {date}"
        f"{' → ' + return_date if return_date else ''}"
        f" | {cabin} | {passengers} pax"
    )

    try:
        outbound: list[dict] = []
        returning: list[dict] = []
        page_url = ""
        raw_text = ""

        try:
            _ensure_started()
            outbound, returning, page_url, raw_text = _bt.run(
                _scrape_flights_async(origin, destination, date, return_date, passengers, cabin),
                timeout=35
            )
        except Exception as scrape_err:
            print(f"[FlightFinder] ⚠️ Direct browser scrape error: {scrape_err}, trying fallback...")
            page_url = _build_google_flights_url(origin, destination, date, return_date, passengers, cabin)
            browser_control({"action": "go_to", "url": page_url})
            import time
            time.sleep(4)
            raw_text = browser_control({"action": "get_text", "max_chars": 15000})

        # If DOM scraping produced no outbound cards, use Gemini/regex fallback on raw_text
        if not outbound and raw_text:
            outbound = _parse_flights_with_gemini(raw_text, origin, destination, date)

        if not outbound and not raw_text:
            return "Could not retrieve flight data, sir. The page may not have loaded."

        spoken = _format_spoken(outbound, returning, origin, destination, date, return_date)

        if speak:
            speak(spoken)

        result = spoken

        if save and outbound:
            report     = _format_text_report(outbound, returning, origin, destination, date, return_date, page_url)
            saved_path = _save_to_desktop(report, origin, destination)
            result    += f" Results saved to Desktop: {saved_path}"

        return result

    except Exception as e:
        print(f"[FlightFinder] ❌ {e}")
        return f"Flight search failed, sir: {e}"
