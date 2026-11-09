# Ledger: Anubis Google Calendar, Tasks & Flight Tracking Integration

| Timestamp | Phase | Action | Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| 2026-11-08 14:48 | Init | Task started via PLAN.md | DONE | Durable state initialized |
| 2026-11-08 14:49 | Phase 1 | Python environment & dependencies | DONE | `google-auth-oauthlib` installed in `.venv` |
| 2026-11-08 14:51 | Phase 1 | Created `actions/google_auth.py` | DONE | OAuth flow with secure permissions and fallback |
| 2026-11-08 14:52 | Phase 2 | Rewrote `actions/reminder.py` | DONE | Replaced Windows code with GCal, GTasks & Linux DBus/systemd |
| 2026-11-08 14:53 | Phase 3 | Updated `TOOLS` in `main.py` | DONE | Live API schema upgraded with multiplexed action enum |
| 2026-11-08 14:53 | Phase 4 | Updated `agent/planner.py` | DONE | Planner prompt spec & few-shot examples updated |
| 2026-11-08 14:55 | Phase 5 | Interactive OAuth consent | DONE | Granted scopes and saved `config/google_token.json` |
| 2026-11-08 15:02 | Phase 5 | Natural date parsing added | DONE | Supports "next Saturday", "next next Saturday" |
| 2026-11-08 15:06 | Phase 6 | Range Reminders & Cancellation | DONE | Implemented date-range recurrence (RRULE) and `delete_reminder` / `delete_event` / `delete_task` |
| 2026-11-08 15:11 | Phase 6 | Service restart & verification | DONE | Cleaned up pending Calgary reminders and restarted `anubis.service` |
