# Execution State: Anubis Flight Tracking & Dynamic Reminders

- **Current Epoch:** Phase 7 — Decoupling Flight Tracking & Calendar Reminders
- **Status:** COMPLETED
- **Daemon Status:** Active in `anubis.service` under `systemctl --user`.
- **Verified Capabilities:**
  - **Decoupled Architecture**: Flight price tracking is 100% local in `data/flight_trackers.json`, polled twice daily (08:30 & 18:30) headlessly, alerting on price drops via desktop notification. Google Calendar is dedicated solely to user events and personal tasks.
  - **Date-Specific Calendar Lookup**: `reminder(action="list_events", date="...")` queries events on specific dates (e.g. `2026-12-19` or `December 19th`), properly surfacing confirmed events like `Booked trip to Calgary (all day on Saturday, Dec 19)`.
  - **Date-Range / Recurring Reminders**: Supports phrases like *"from today to next Saturday"* or explicit `start_date` and `end_date`. Schedules native Google Calendar daily recurrence via `RRULE:FREQ=DAILY;UNTIL=...` and registers user-space timers in `systemd-run --user` for each upcoming day in the range.
  - **Reminder & Event Cancellation**: Supports `delete_reminder`, `delete_event`, `cancel_reminder`, and `delete_task`. Deletes matched events/recurring series from Google Calendar while protecting confirmed personal events (like appointments/trips), and cancels registered systemd timer units.
  - **Clean Documentation**: All task execution markdown files (`PLAN.md`, `STATE.md`, `FINDINGS.md`, `LEDGER.md`) organized cleanly into `doc/`.
