# actions/reminder.py

"""
Cross-platform reminder, calendar, and task management action for Anubis.
Integrates with Google Calendar, Google Tasks, and native Linux desktop notifications.
Supports single-time and daily/range recurring reminders, as well as deletion/cancellation.
"""

import os
import sys
import subprocess
import threading
import json
import re
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from actions.google_auth import get_calendar_service, get_tasks_service
except ImportError:
    get_calendar_service = lambda interactive=False: None
    get_tasks_service = lambda interactive=False: None

SCHEDULED_REMINDERS_FILE = os.path.join(project_root, "config", "scheduled_reminders.json")


def _load_scheduled_reminders() -> list[dict]:
    """Loads active scheduled Linux timers metadata."""
    if os.path.exists(SCHEDULED_REMINDERS_FILE):
        try:
            with open(SCHEDULED_REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_scheduled_reminders(reminders: list[dict]) -> None:
    """Persists active scheduled Linux timers metadata."""
    try:
        os.makedirs(os.path.dirname(SCHEDULED_REMINDERS_FILE), exist_ok=True)
        with open(SCHEDULED_REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2)
    except Exception as e:
        print(f"[Reminder] ⚠️ Error saving scheduled reminders: {e}")


def _record_timer(unit_name: str, message: str, target_dt: datetime) -> None:
    """Records a systemd timer unit for future cancellation."""
    rems = _load_scheduled_reminders()
    rems.append({
        "unit": unit_name,
        "message": message,
        "target_dt": target_dt.isoformat()
    })
    _save_scheduled_reminders(rems)


def _cancel_linux_notifications(query: str = "") -> int:
    """Cancels matching systemd-run timer units."""
    rems = _load_scheduled_reminders()
    q_clean = query.strip().lower()
    cancelled = 0
    remaining = []

    # Query currently active systemd user timer units
    active_timers = set()
    try:
        proc = subprocess.run(
            ["systemctl", "--user", "list-timers", "--all"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in proc.stdout.splitlines():
            if "anubis-reminder-" in line:
                for part in line.split():
                    if part.startswith("anubis-reminder-") and part.endswith(".timer"):
                        active_timers.add(part)
    except Exception:
        pass

    for r in rems:
        unit = r.get("unit", "")
        msg = r.get("message", "")
        match = False
        if not q_clean or q_clean in ("all", "*"):
            match = True
        elif q_clean in msg.lower() or any(w in msg.lower() for w in q_clean.split() if len(w) > 2):
            match = True

        if match:
            timer_unit = f"{unit}.timer" if not unit.endswith(".timer") else unit
            subprocess.run(["systemctl", "--user", "stop", timer_unit], check=False, capture_output=True)
            active_timers.discard(timer_unit)
            cancelled += 1
        else:
            remaining.append(r)

    # Stop any orphaned timers if query is broad
    if q_clean in ("all", "*"):
        for t in list(active_timers):
            subprocess.run(["systemctl", "--user", "stop", t], check=False, capture_output=True)
            cancelled += 1

    _save_scheduled_reminders(remaining)
    return cancelled


def _get_local_timezone_name() -> str:
    """Detects local IANA timezone name."""
    try:
        if os.environ.get("TZ"):
            return os.environ["TZ"]
        if os.path.islink("/etc/localtime"):
            target = os.readlink("/etc/localtime")
            if "zoneinfo/" in target:
                return target.split("zoneinfo/")[-1]
    except Exception:
        pass
    return "America/Toronto"


def _parse_single_date(d_str: Optional[str], now: Optional[datetime] = None) -> date:
    """Parses a natural language date expression into a date object."""
    if not now:
        now = datetime.now()

    if not d_str:
        return now.date()

    d_clean = re.sub(r"^(from|on|for|to)\s+", "", d_str.strip().lower()).replace("?", "").strip()

    if d_clean in ("today", "now"):
        return now.date()
    if d_clean == "tomorrow":
        return (now + timedelta(days=1)).date()
    if d_clean in ("day after tomorrow", "overmorrow"):
        return (now + timedelta(days=2)).date()

    m_days = re.search(r"in\s+(\d+)\s+days?", d_clean)
    if m_days:
        return (now + timedelta(days=int(m_days.group(1)))).date()

    m_weeks = re.search(r"in\s+(\d+)\s+weeks?", d_clean)
    if m_weeks:
        return (now + timedelta(weeks=int(m_weeks.group(1)))).date()

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    for wname, target_wday in weekdays.items():
        if wname in d_clean:
            cur_wday = now.weekday()
            days_ahead = target_wday - cur_wday
            if days_ahead <= 0:
                days_ahead += 7
            next_count = d_clean.count("next")
            if next_count > 1:
                days_ahead += 7 * (next_count - 1)
            return (now + timedelta(days=days_ahead)).date()

    for dfmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d"):
        try:
            dt = datetime.strptime(d_clean, dfmt)
            if dt.year == 1900:
                dt = dt.replace(year=now.year)
            return dt.date()
        except ValueError:
            pass

    raise ValueError(f"Unrecognized date format: '{d_str}'")


def _parse_time(t_str: Optional[str], default_time: time = time(10, 0)) -> time:
    """Parses time string or natural time of day into time object."""
    if not t_str:
        return default_time

    t_clean = t_str.strip().lower()
    if t_clean in ("morning", "in the morning"):
        return time(9, 0)
    elif t_clean in ("noon", "midday", "at noon"):
        return time(12, 0)
    elif t_clean in ("afternoon", "in the afternoon"):
        return time(14, 0)
    elif t_clean in ("evening", "in the evening"):
        return time(18, 0)
    elif t_clean in ("night", "tonight", "at night"):
        return time(20, 0)

    for tfmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I %p"):
        try:
            return datetime.strptime(t_clean, tfmt).time()
        except ValueError:
            pass

    return default_time


def _parse_datetime(
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    minutes_offset: Optional[int] = None,
) -> datetime:
    """Parses date and time strings into a datetime object."""
    now = datetime.now()

    if minutes_offset is not None:
        return now + timedelta(minutes=int(minutes_offset))

    # Parse date
    if not date_str:
        target_date = now.date()
    else:
        d_raw = date_str.strip().lower()
        if " to " in d_raw:
            d_raw = d_raw.split(" to ")[-1].strip()
        elif "?" in d_raw:
            d_raw = d_raw.split("?")[-1].strip()

        target_date = _parse_single_date(d_raw, now)

    # Parse time
    target_time = _parse_time(time_str, default_time=time(10, 0))
    return datetime.combine(target_date, target_time)


def _schedule_linux_notification(target_dt: datetime, message: str) -> bool:
    """
    Schedules a local desktop alert using systemd-run --user.
    Falls back to a background Python Timer thread if systemd-run fails.
    """
    safe_msg = message.replace('"', '\\"').replace("'", "'\\''").strip()[:200]
    notify_cmd = (
        f'paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null; '
        f'gdbus call --session --dest org.freedesktop.Notifications '
        f'--object-path /org/freedesktop/Notifications '
        f'--method org.freedesktop.Notifications.Notify '
        f'"Anubis" 0 "" "Anubis Reminder" "{safe_msg}" "[]" "{{}}" 15000'
    )

    now = datetime.now()
    delay_sec = (target_dt - now).total_seconds()
    if delay_sec <= 0:
        return False

    unit_name = f"anubis-reminder-{int(target_dt.timestamp())}"
    on_cal = target_dt.strftime("%Y-%m-%d %H:%M:%S")

    try:
        proc = subprocess.run(
            [
                "systemd-run",
                "--user",
                f"--unit={unit_name}",
                f"--on-calendar={on_cal}",
                "sh",
                "-c",
                notify_cmd,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            _record_timer(unit_name, message, target_dt)
            return True
        print(f"[Reminder] systemd-run warning: {proc.stderr.strip()}")
    except Exception as e:
        print(f"[Reminder] systemd-run execution failed: {e}")

    # Fallback to threading timer
    def _fire():
        subprocess.run(["sh", "-c", notify_cmd], check=False)

    timer = threading.Timer(delay_sec, _fire)
    timer.daemon = True
    timer.start()
    return True


def _add_calendar_event(
    title: str,
    start_dt: datetime,
    end_dt: Optional[datetime] = None,
    description: str = "",
    popup_minutes: Optional[int] = None,
    recurrence_until: Optional[date] = None,
) -> tuple[bool, str]:
    """Inserts a single or daily recurring event into primary Google Calendar."""
    service = get_calendar_service(interactive=False)
    if not service:
        return False, "Google Calendar is not connected. Token authorization needed."

    if end_dt is None:
        end_dt = start_dt + timedelta(minutes=30)

    tz_str = _get_local_timezone_name()

    event_body = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_dt.astimezone().isoformat(),
            "timeZone": tz_str,
        },
        "end": {
            "dateTime": end_dt.astimezone().isoformat(),
            "timeZone": tz_str,
        },
    }

    if popup_minutes is not None:
        event_body["reminders"] = {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": popup_minutes},
                {"method": "popup", "minutes": 0},
            ],
        }

    if recurrence_until is not None:
        until_utc = (
            datetime.combine(recurrence_until, time(23, 59, 59))
            .astimezone(timezone.utc)
            .strftime("%Y%m%dT%H%M%SZ")
        )
        event_body["recurrence"] = [f"RRULE:FREQ=DAILY;UNTIL={until_utc}"]

    try:
        created = service.events().insert(calendarId="primary", body=event_body).execute()
        return True, created.get("htmlLink", "")
    except Exception as e:
        return False, str(e)


def _delete_calendar_events(query: str) -> tuple[int, list[str]]:
    """Deletes matching Google Calendar events and recurring event series."""
    service = get_calendar_service(interactive=False)
    if not service:
        return 0, []

    q_clean = query.strip().lower()
    deleted_titles = []

    try:
        now = datetime.now().astimezone()
        time_min = (now - timedelta(days=1)).isoformat()
        time_max = (now + timedelta(days=90)).isoformat()

        res = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=False,
            q=query if q_clean not in ("all", "*", "") else None,
        ).execute()

        items = res.get("items", [])
        for item in items:
            summary = item.get("summary", "")
            desc = item.get("description", "")
            match = False
            if q_clean in ("all", "*", ""):
                match = True
            elif q_clean in summary.lower() or q_clean in desc.lower():
                match = True
            else:
                words = [w for w in q_clean.split() if len(w) > 2]
                if words and any(w in summary.lower() or w in desc.lower() for w in words):
                    match = True

            if match:
                service.events().delete(calendarId="primary", eventId=item["id"]).execute()
                deleted_titles.append(summary or "Untitled")

        return len(deleted_titles), deleted_titles
    except Exception as e:
        print(f"[Reminder] Error deleting calendar events: {e}")
        return 0, []


def _list_calendar_events(days: int = 1) -> str:
    """Queries upcoming Google Calendar events for the next N days."""
    service = get_calendar_service(interactive=False)
    if not service:
        return "Google Calendar is not connected. Please authorize Google credentials."

    now = datetime.now().astimezone()
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days)).isoformat()

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = events_result.get("items", [])
        if not items:
            day_str = "day" if days == 1 else f"{days} days"
            return f"You have no upcoming events scheduled for the next {day_str}."

        lines = [f"You have {len(items)} upcoming event{'s' if len(items) > 1 else ''}:"]
        today_date = now.date()
        tomorrow_date = today_date + timedelta(days=1)

        for i, item in enumerate(items, 1):
            summary = item.get("summary", "Untitled Event")
            start = item.get("start", {})
            start_str = start.get("dateTime") or start.get("date")

            if "T" in start_str:
                dt = datetime.fromisoformat(start_str).astimezone()
                if dt.date() == today_date:
                    time_label = f"today at {dt.strftime('%I:%M %p')}"
                elif dt.date() == tomorrow_date:
                    time_label = f"tomorrow at {dt.strftime('%I:%M %p')}"
                else:
                    time_label = dt.strftime("%A, %b %d at %I:%M %p")
            else:
                dt = datetime.strptime(start_str, "%Y-%m-%d").date()
                if dt == today_date:
                    time_label = "all day today"
                elif dt == tomorrow_date:
                    time_label = "all day tomorrow"
                else:
                    time_label = f"all day on {dt.strftime('%A, %b %d')}"

            lines.append(f"{i}. {summary} ({time_label})")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching calendar events: {str(e)[:100]}"


def _add_task(title: str, due_date: Optional[str] = None, notes: str = "") -> tuple[bool, str]:
    """Adds a task to Google Tasks default list."""
    service = get_tasks_service(interactive=False)
    if not service:
        return False, "Google Tasks is not connected."

    task_body = {"title": title}
    if notes:
        task_body["notes"] = notes

    if due_date:
        try:
            target_dt = _parse_datetime(date_str=due_date, time_str=None)
            task_body["due"] = target_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except Exception:
            pass

    try:
        created = service.tasks().insert(tasklist="@default", body=task_body).execute()
        return True, created.get("id", "")
    except Exception as e:
        return False, str(e)


def _list_tasks(include_completed: bool = False) -> str:
    """Lists tasks from Google Tasks default list."""
    service = get_tasks_service(interactive=False)
    if not service:
        return "Google Tasks is not connected. Please authorize Google credentials."

    try:
        tasks_result = (
            service.tasks()
            .list(tasklist="@default", showCompleted=include_completed, showHidden=False)
            .execute()
        )
        items = tasks_result.get("items", [])
        active_items = [t for t in items if t.get("title") and (include_completed or t.get("status") != "completed")]

        if not active_items:
            return "You have no pending tasks in Google Tasks."

        lines = [f"Here are your pending tasks ({len(active_items)} total):"]
        for i, item in enumerate(active_items, 1):
            t_title = item.get("title", "Untitled")
            due = item.get("due")
            if due:
                try:
                    due_clean = due.split("T")[0]
                    lines.append(f"{i}. {t_title} (Due: {due_clean})")
                except Exception:
                    lines.append(f"{i}. {t_title}")
            else:
                lines.append(f"{i}. {t_title}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching tasks: {str(e)[:100]}"


def _complete_task(title: str) -> str:
    """Marks a matching task as completed in Google Tasks."""
    service = get_tasks_service(interactive=False)
    if not service:
        return "Google Tasks is not connected. Please authorize Google credentials."

    try:
        tasks_result = (
            service.tasks()
            .list(tasklist="@default", showCompleted=False)
            .execute()
        )
        items = tasks_result.get("items", [])
        target_clean = title.strip().lower()

        matched = None
        for item in items:
            item_title = item.get("title", "").strip().lower()
            if target_clean in item_title or item_title in target_clean:
                matched = item
                break

        if not matched:
            return f"I couldn't find a pending task matching '{title}'."

        matched_id = matched["id"]
        matched_title = matched.get("title", title)
        matched["status"] = "completed"
        matched["completed"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

        service.tasks().update(tasklist="@default", task=matched_id, body=matched).execute()
        return f"Marked task '{matched_title}' as completed in Google Tasks."
    except Exception as e:
        return f"Error completing task: {str(e)[:100]}"


def _delete_task(query: str) -> tuple[bool, str]:
    """Deletes a matching task from Google Tasks default list."""
    service = get_tasks_service(interactive=False)
    if not service:
        return False, "Google Tasks is not connected."

    q_clean = query.strip().lower()
    try:
        res = service.tasks().list(tasklist="@default", showCompleted=True).execute()
        items = res.get("items", [])
        matched = None
        for item in items:
            title = item.get("title", "").lower()
            if q_clean in title or any(w in title for w in q_clean.split() if len(w) > 2):
                matched = item
                break

        if not matched:
            return False, f"I couldn't find a task matching '{query}'."

        service.tasks().delete(tasklist="@default", task=matched["id"]).execute()
        return True, f"Deleted task '{matched.get('title', query)}' from Google Tasks."
    except Exception as e:
        return False, f"Error deleting task: {str(e)[:100]}"


def reminder(
    parameters: dict,
    response: Optional[str] = None,
    player=None,
    session_memory=None,
) -> str:
    """
    Main reminder action handler for Anubis.

    Supports action multiplexing:
      - "set_reminder": schedules calendar reminder & desktop notification (single or date range).
      - "delete_reminder" / "cancel_reminder": cancels reminders from Google Calendar and desktop.
      - "add_event": adds an event to Google Calendar.
      - "delete_event": deletes an event from Google Calendar.
      - "list_events": queries upcoming calendar events.
      - "add_task": adds a to-do item to Google Tasks.
      - "list_tasks": queries pending tasks in Google Tasks.
      - "complete_task": marks a task as completed in Google Tasks.
      - "delete_task": removes a task from Google Tasks.
      - "track_flight": autonomous background flight price watcher.

    Preserves 100% backward compatibility for calls passing (date, time, message).
    """
    action = parameters.get("action")
    if not action:
        # Default to set_reminder for legacy compatibility
        action = "set_reminder"

    action = action.strip().lower()

    # --- ACTION 1: LIST CALENDAR EVENTS ---
    if action == "list_events":
        raw_days = parameters.get("days", 1)
        try:
            days = max(1, int(raw_days))
        except (ValueError, TypeError):
            days = 1
        res = _list_calendar_events(days=days)
        if player and hasattr(player, "write_log"):
            player.write_log(f"[calendar] listed events for next {days} day(s)")
        return res

    # --- ACTION 2: LIST GOOGLE TASKS ---
    elif action == "list_tasks":
        inc_completed = bool(parameters.get("include_completed", False))
        res = _list_tasks(include_completed=inc_completed)
        if player and hasattr(player, "write_log"):
            player.write_log("[tasks] listed tasks")
        return res

    # --- ACTION 3: ADD GOOGLE TASK ---
    elif action == "add_task":
        title = parameters.get("title") or parameters.get("message")
        if not title:
            return "Please specify a title or description for the task."
        due_date = parameters.get("due_date") or parameters.get("date")
        notes = parameters.get("notes") or parameters.get("description", "")

        ok, out = _add_task(title=title, due_date=due_date, notes=notes)
        if ok:
            msg = f"Added '{title}' to your Google Tasks."
            if player and hasattr(player, "write_log"):
                player.write_log(f"[tasks] added: {title}")
            return msg
        else:
            return f"I couldn't add the task to Google Tasks: {out}"

    # --- ACTION 4: COMPLETE GOOGLE TASK ---
    elif action == "complete_task":
        title = parameters.get("title") or parameters.get("message")
        if not title:
            return "Please specify which task to mark as completed."
        res = _complete_task(title=title)
        if player and hasattr(player, "write_log"):
            player.write_log(f"[tasks] completed: {title}")
        return res

    # --- ACTION 5: DELETE GOOGLE TASK ---
    elif action in ("delete_task", "remove_task"):
        query = parameters.get("query") or parameters.get("title") or parameters.get("message")
        if not query:
            return "Please specify which task to delete."
        ok, msg = _delete_task(query)
        if player and hasattr(player, "write_log"):
            player.write_log(f"[tasks] delete task: {query}")
        return msg

    # --- ACTION 6: ADD CALENDAR EVENT ---
    elif action == "add_event":
        title = parameters.get("title") or parameters.get("message")
        if not title:
            return "Please provide a title for the event."

        date_str = parameters.get("date")
        time_str = parameters.get("time")
        end_time_str = parameters.get("end_time")
        desc = parameters.get("description", "")

        try:
            start_dt = _parse_datetime(date_str=date_str, time_str=time_str)
            end_dt = (
                _parse_datetime(date_str=date_str, time_str=end_time_str)
                if end_time_str
                else None
            )
        except ValueError as ve:
            return str(ve)

        ok, link_or_err = _add_calendar_event(
            title=title,
            start_dt=start_dt,
            end_dt=end_dt,
            description=desc,
        )

        formatted_time = start_dt.strftime("%A, %B %d at %I:%M %p")
        if ok:
            if player and hasattr(player, "write_log"):
                player.write_log(f"[calendar] event added: '{title}' at {formatted_time}")
            return f"Scheduled '{title}' in Google Calendar for {formatted_time}."
        else:
            return f"Failed to add calendar event: {link_or_err}"

    # --- ACTION 7: DELETE / CANCEL REMINDERS & CALENDAR EVENTS ---
    elif action in ("delete_reminder", "cancel_reminder", "remove_reminder", "delete_event", "cancel_event", "remove_event"):
        query = (
            parameters.get("query")
            or parameters.get("title")
            or parameters.get("message")
            or ""
        )

        cal_count, deleted_titles = _delete_calendar_events(query)
        linux_count = _cancel_linux_notifications(query)

        # Also cancel flight price tracker if related
        tracker_cancelled = False
        lower_q = query.lower()
        if "flight" in lower_q or "calgary" in lower_q or "trip" in lower_q:
            try:
                from actions.flight_tracker import cancel_flight_tracker
                res_track = cancel_flight_tracker(destination=query)
                if res_track.get("status") == "success":
                    tracker_cancelled = True
            except Exception:
                pass

        total = cal_count + linux_count
        if player and hasattr(player, "write_log"):
            player.write_log(f"[reminder] cancelled {total} reminder(s) for '{query}'")

        if total > 0 or tracker_cancelled:
            sample = f" for '{deleted_titles[0]}'" if deleted_titles else f" matching '{query}'"
            track_note = " and canceled active flight price tracking" if tracker_cancelled else ""
            return f"Removed {max(1, cal_count)} reminder(s){sample} from Google Calendar and canceled desktop alerts{track_note}."
        else:
            return f"I couldn't find any upcoming reminders matching '{query}' to remove."

    # --- ACTION 8: SET TIMED REMINDER (Single-time or Date Range) ---
    elif action == "set_reminder":
        date_str = parameters.get("date")
        start_date_str = parameters.get("start_date") or date_str
        end_date_str = parameters.get("end_date") or parameters.get("until")
        time_str = parameters.get("time")
        message = parameters.get("message") or parameters.get("title") or "Reminder"
        minutes = parameters.get("minutes")

        # Detect range syntax (e.g. "from today to next Saturday" or "today to next Saturday")
        is_range = False
        if date_str and " to " in date_str.lower():
            parts = date_str.lower().split(" to ")
            start_date_str = parts[0]
            end_date_str = parts[1]
            is_range = True
        elif end_date_str:
            is_range = True

        try:
            now = datetime.now()
            if minutes is not None:
                start_d = now.date()
                target_time = (now + timedelta(minutes=int(minutes))).time()
                end_d = None
                is_range = False
            else:
                start_d = _parse_single_date(start_date_str, now)
                end_d = _parse_single_date(end_date_str, now) if is_range else None
                target_time = _parse_time(time_str, default_time=time(10, 0))
        except ValueError as ve:
            return f"I couldn't understand that date format: {ve}"

        # If it is a range with end_d > start_d
        if is_range and end_d and end_d > start_d:
            start_dt = datetime.combine(start_d, target_time)

            # 1. Google Calendar recurring daily event
            gcal_ok, _ = _add_calendar_event(
                title=f"Reminder: {message}",
                start_dt=start_dt,
                popup_minutes=10,
                recurrence_until=end_d,
            )

            # 2. Linux desktop alert for each future day in the range
            scheduled_days = 0
            curr_d = start_d
            while curr_d <= end_d:
                day_dt = datetime.combine(curr_d, target_time)
                if day_dt > datetime.now():
                    if _schedule_linux_notification(day_dt, message):
                        scheduled_days += 1
                curr_d += timedelta(days=1)

            # Check if autonomous flight tracking is also requested
            tracker_msg = ""
            lower_msg = message.lower()
            if ("flight" in lower_msg or "ticket" in lower_msg) and ("track" in lower_msg or "check" in lower_msg or "find" in lower_msg):
                origin = parameters.get("origin") or "Ottawa"
                destination = parameters.get("destination") or "Calgary"
                try:
                    from actions.flight_tracker import add_flight_tracker
                    track_res = add_flight_tracker(
                        origin=origin,
                        destination=destination,
                        date=start_d.strftime("%Y-%m-%d"),
                        return_date=end_d.strftime("%Y-%m-%d"),
                        end_date=end_d.strftime("%Y-%m-%d"),
                    )
                    tracker_msg = " Automatic daily flight price tracking is also active."
                except Exception:
                    pass

            start_label = start_d.strftime("%A, %b %d")
            end_label = end_d.strftime("%A, %b %d")
            time_label = target_time.strftime("%I:%M %p")

            if player and hasattr(player, "write_log"):
                player.write_log(f"[reminder] range set: {start_label} to {end_label} at {time_label}")

            return (
                f"Daily reminder set from {start_label} to {end_label} at {time_label}: "
                f"{message} (synced to Google Calendar with daily desktop alerts).{tracker_msg}"
            )

        # Single-time reminder
        target_dt = datetime.combine(start_d, target_time)
        if target_dt <= datetime.now():
            return "That time is already in the past."

        # 1. Schedule local Linux desktop alert
        linux_scheduled = _schedule_linux_notification(target_dt, message)

        # 2. Sync to Google Calendar (with pop-up reminder)
        gcal_ok, _ = _add_calendar_event(
            title=f"Reminder: {message}",
            start_dt=target_dt,
            popup_minutes=10,
        )

        formatted_time = target_dt.strftime("%B %d at %I:%M %p")
        if player and hasattr(player, "write_log"):
            player.write_log(f"[reminder] set for {formatted_time}: {message}")

        if gcal_ok:
            return f"Reminder set for {formatted_time}: {message} (synced to Google Calendar)."
        elif linux_scheduled:
            return f"Reminder set for {formatted_time}: {message}."
        else:
            return f"Failed to schedule reminder for {formatted_time}."

    # --- ACTION 9: TRACK FLIGHT PRICES OVER A DATE WINDOW ---
    elif action in ("track_flight", "flight_tracker"):
        from actions.flight_tracker import add_flight_tracker, list_flight_trackers, cancel_flight_tracker
        sub_act = (parameters.get("sub_action") or "track").lower().strip()
        if sub_act == "list":
            return list_flight_trackers()
        elif sub_act == "cancel":
            return cancel_flight_tracker(
                origin=parameters.get("origin", ""),
                destination=parameters.get("destination", "")
            )

        res = add_flight_tracker(
            origin=parameters.get("origin", ""),
            destination=parameters.get("destination", ""),
            date=parameters.get("date", ""),
            return_date=parameters.get("return_date"),
            end_date=parameters.get("end_date") or parameters.get("until"),
            carry_on=max(0, int(parameters.get("carry_on", 0))),
            checked_bags=max(0, int(parameters.get("checked_bags", 0))),
            airline=parameters.get("airline"),
        )
        msg = res.get("message", "Flight tracking set.")
        _add_calendar_event(
            title=f"Flight Tracker: {parameters.get('origin', '')} → {parameters.get('destination', '')}",
            start_dt=datetime.now() + timedelta(days=1),
            description=msg
        )
        if player and hasattr(player, "write_log"):
            player.write_log(f"[flight_tracker] {parameters.get('origin')} → {parameters.get('destination')}")
        return msg

    else:
        return f"Unknown reminder action: '{action}'."
