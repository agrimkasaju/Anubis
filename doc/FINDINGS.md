# Findings: Anubis Dynamic Reminders & Flight Tracking

### Discovery 1: Google Calendar Recurrence (RRULE)
- Google Calendar API supports standard recurrence strings: `"recurrence": ["RRULE:FREQ=DAILY;UNTIL=YYYYMMDDTHHMMSSZ"]`.
- When querying events with `singleEvents=True`, Google Calendar expands the recurring series into individual daily items for `waybar-ycal` and Anubis.
- When deleting with `singleEvents=False`, deleting the master recurring event removes all occurrences across the entire range cleanly.

### Discovery 2: Safeguarded Event Deletion
- `delete_reminder` is restricted with `reminders_only=True` to match events containing `"Reminder:"` or `"Flight Tracker:"`. This prevents accidental deletion of non-reminder personal events (such as booked flights or meetings).
- Systemd user timer tracking: Timers are registered in `config/scheduled_reminders.json` and stopped via `systemctl --user stop <unit>.timer`.
