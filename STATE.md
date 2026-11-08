# Execution State: Flight Price Poller & Tracker Engine

- **Current Epoch:** Phase 5 — Verification & End-to-End Testing
- **Status:** COMPLETED
- **Daemon Status:** Active in `anubis.service` under `systemctl --user`.
- **Verified Capabilities:**
  - `scrape_flights_headless`: Quietly queries Google Flights headlessly via Playwright Chromium without UI popups.
  - **Baggage Filter Enforcement**: Applies carry-on (0, 1+), checked bags (0, 1+), or combined bag filters automatically during each poll.
  - `add_flight_tracker`: Anchors baseline fare, calculates expiration window, and registers tracker in `data/flight_trackers.json`.
  - `poll_tracker` / `poll_all_active_trackers`: Detects price drops below `lowest_seen_price`, writes history, dispatches desktop alerts (`gdbus`) with audio chime (`paplay`).
  - **Reminder System Integration**: Reminders asking to track or check flight prices automatically register active flight tracking records and sync calendar reminders.
  - **Scheduled Polling**: `FlightPollerDaemon` runs at 08:30 and 18:30 local time.
