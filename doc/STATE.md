# Execution State: Anubis Flight Tracking & Dynamic Reminders

- **Current Epoch:** Phase 9 — Evening Polling Window (5:00 PM – 9:30 PM) with Boot/Wake Catch-Up
- **Status:** COMPLETED
- **Daemon Status:** Active in `anubis.service` under `systemctl --user`.
- **Verified Capabilities:**
  - **Evening Availability Customization**: Polling no longer runs in the morning. Tailored strictly to evening availability when the laptop is online (5:00 PM to 9:30 PM).
  - **Automatic Catch-Up on Wake/Boot**: If the laptop is not on at 5:00 PM, whenever it powers on or wakes past 5:00 PM, `FlightPollerDaemon` automatically detects the missed check and executes an immediate catch-up poll.
  - **Second Evening Fare Update Poll**: Executes an evening update poll at 8:30 PM (before the laptop goes offline at 9:30 PM) to catch late airline price changes.
  - **State Persistence**: `data/flight_poll_state.json` tracks completed daily slots (`17:00`, `20:30`) and enforces a 45-minute debounce interval so reboots or restarts never double-scrape.
  - **Google Calendar Flight Deal Notifications**: When a low price or price drop is targeted/detected by flight finder & the background flight tracker, a notification event is automatically created in Google Calendar on the local date (e.g. `✈️ Flight Deal: Ottawa → Calgary ($851 USD)`).
  - **Clean Documentation**: All task execution markdown files (`PLAN.md`, `STATE.md`, `FINDINGS.md`, `LEDGER.md`) organized cleanly into `doc/`.
