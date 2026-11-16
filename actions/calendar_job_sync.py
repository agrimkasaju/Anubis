"""
actions/calendar_job_sync.py

Synchronizes applied and skipped job history between ai_job_search and Google Calendar.
Maintains EXACTLY ONE persistent synchronization event on Google Calendar containing
a clean, copy-pastable JSON payload of applied_jobs.json, preventing calendar clutter.

Features:
- Push local applied_jobs.json to the single Google Calendar sync event.
- Pull from the Google Calendar sync event into local applied_jobs.json & job_history.json.
- Copy-pastable JSON string export and direct JSON import.
"""

import os
import sys
import re
import json
import gzip
import base64
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from actions.google_auth import get_calendar_service, get_target_calendar_id
except Exception:
    get_calendar_service = lambda interactive=False: None
    get_target_calendar_id = lambda: "primary"
from job_history import (
    HISTORY_FILE,
    APPLIED_FILE,
    get_job_history,
    _load_json,
    _save_json,
    parse_key,
)

SYNC_EVENT_SUMMARY = "[Orion Sync] applied_jobs.json"
SYNC_STATE_FILE = Path.home() / ".orion_calendar_sync.json"


def _get_tracked_event_id() -> Optional[str]:
    if SYNC_STATE_FILE.exists():
        try:
            data = json.loads(SYNC_STATE_FILE.read_text(encoding="utf-8"))
            return data.get("event_id")
        except Exception:
            return None
    return None


def _save_tracked_event_id(event_id: str, html_link: str = ""):
    try:
        SYNC_STATE_FILE.write_text(
            json.dumps(
                {
                    "event_id": event_id,
                    "html_link": html_link,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def find_sync_calendar_event(service) -> Optional[dict]:
    """Finds the single Orion sync event on Google Calendar."""
    cal_id = get_target_calendar_id()
    # 1. Try tracked event ID first
    tracked_id = _get_tracked_event_id()
    if tracked_id:
        try:
            ev = service.events().get(calendarId=cal_id, eventId=tracked_id).execute()
            if ev and ev.get("status") != "cancelled":
                return ev
        except Exception:
            pass

    # 2. Search by exact summary
    try:
        res = service.events().list(
            calendarId=cal_id,
            q=SYNC_EVENT_SUMMARY,
            maxResults=10,
        ).execute()
        items = res.get("items", [])
        for item in items:
            if item.get("summary") == SYNC_EVENT_SUMMARY and item.get("status") != "cancelled":
                _save_tracked_event_id(item["id"], item.get("htmlLink", ""))
                return item
    except Exception as e:
        print(f"[CalendarJobSync] Search error: {e}")

    return None


def format_sync_event_body(applied_keys: list[str], history_items: list[dict]) -> dict:
    """Constructs the single sync event resource with a copy-pastable JSON payload."""
    now_local = datetime.now().astimezone()
    now_utc = datetime.now(timezone.utc)
    today_str = now_local.strftime("%Y-%m-%d")
    tomorrow_str = (now_local + timedelta(days=1)).strftime("%Y-%m-%d")

    applied_count = sum(1 for h in history_items if (h.get("status") or "").lower() == "applied")
    skipped_count = sum(1 for h in history_items if (h.get("status") or "").lower() == "skipped")
    total_keys = len(applied_keys)

    # Base64-encoded compressed full payload to safely fit within Google Calendar's 8192 char limit
    full_json_bytes = json.dumps(applied_keys).encode("utf-8")
    compressed_b64 = base64.b64encode(gzip.compress(full_json_bytes)).decode("ascii")

    # Readable copy-pastable payload capped to stay well under the 8192 char limit
    readable_keys = applied_keys
    sample_text = json.dumps(readable_keys, indent=2)
    truncated_readable = False
    if len(sample_text) > 4000:
        readable_keys = applied_keys[:50]
        sample_text = json.dumps(readable_keys, indent=2)
        truncated_readable = True

    description = f"""====================================================
ORION COMPANION & AI JOB SEARCH - SYNC STATE
====================================================
Last Updated: {now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")}
Total Applied Roles: {applied_count}
Total Skipped Roles: {skipped_count}
Total Unique Job Keys: {total_keys}

--- COMPACT SYNC PAYLOAD (Base64/Gzip) ---
```payload
gz:b64:{compressed_b64}
```

--- COPY-PASTABLE applied_jobs.json{" (Recent Sample)" if truncated_readable else ""} ---
```json
{sample_text}
```
--- END PAYLOAD ---

Instructions:
1. Orion Pull from Calendar automatically decodes the full payload.
2. Individual calendar events are also maintained for each applied job.
"""

    if len(description) > 8000:
        description = f"""====================================================
ORION COMPANION & AI JOB SEARCH - SYNC STATE
====================================================
Last Updated: {now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")}
Total Applied Roles: {applied_count}
Total Skipped Roles: {skipped_count}
Total Unique Job Keys: {total_keys}

--- COMPACT SYNC PAYLOAD (Base64/Gzip) ---
```payload
gz:b64:{compressed_b64}
```
"""

    return {
        "summary": SYNC_EVENT_SUMMARY,
        "description": description,
        "colorId": "10",  # Basil Green
        "start": {"date": today_str},
        "end": {"date": tomorrow_str},
        "extendedProperties": {
            "private": {
                "source": "anubis_job_sync",
                "type": "applied_jobs_json",
                "total_keys": str(total_keys),
                "updated_at": now_utc.isoformat(),
            }
        },
    }


def format_job_event(job: dict) -> dict:
    """Constructs a Google Calendar event resource dictionary from a job history item."""
    status = (job.get("status") or "applied").strip().lower()
    company = (job.get("company") or "Company").strip()
    title = (job.get("title") or "Role").strip()
    job_key = (job.get("job_key") or f"{company}_{title}").strip().lower()
    apply_url = (job.get("apply_url") or "").strip()
    ts = job.get("timestamp")

    if ts:
        try:
            start_dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except Exception:
            start_dt = datetime.now(timezone.utc)
    elif job.get("iso_date"):
        try:
            start_dt = datetime.fromisoformat(job["iso_date"])
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
        except Exception:
            start_dt = datetime.now(timezone.utc)
    else:
        start_dt = datetime.now(timezone.utc)

    end_dt = start_dt + timedelta(minutes=30)
    color_id = "10" if status == "applied" else "8"
    summary_prefix = "Applied" if status == "applied" else "Skipped"

    description_lines = [
        f"Company: {company}",
        f"Role: {title}",
        f"Status: {status.upper()}",
        f"Job Key: {job_key}",
    ]
    if apply_url and apply_url != "N/A":
        description_lines.append(f"Posting URL: {apply_url}")

    iso_date = job.get("iso_date") or start_dt.isoformat()
    description_lines.append(f"Recorded Date: {iso_date}")

    artifacts = []
    if job.get("resume_pdf"):
        artifacts.append(f"• Resume: {job['resume_pdf']}")
    if job.get("cover_letter_pdf"):
        artifacts.append(f"• Cover Letter: {job['cover_letter_pdf']}")
    if job.get("combined_pdf"):
        artifacts.append(f"• Combined PDF: {job['combined_pdf']}")

    if artifacts:
        description_lines.append("\nTailored Application Artifacts:")
        description_lines.extend(artifacts)

    return {
        "summary": f"{summary_prefix}: {company} - {title}",
        "description": "\n".join(description_lines),
        "colorId": color_id,
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "extendedProperties": {
            "private": {
                "source": "anubis_ai_job_search",
                "job_key": job_key,
                "status": status,
            }
        },
    }


def sync_individual_job_events(service=None, limit: int = 200) -> dict:
    """
    Synchronizes applied job entries from job_history.json as individual Google Calendar events.
    Checks existing events to prevent duplicate creation.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return {"status": "error", "message": "No calendar service"}

    cal_id = get_target_calendar_id()
    history = _load_json(HISTORY_FILE, [])
    applied_jobs = [h for h in history if (h.get("status") or "").lower() == "applied"]

    existing_keys = set()
    existing_summaries = set()
    try:
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=90)).isoformat()
        time_max = (now + timedelta(days=90)).isoformat()
        page_token = None
        while True:
            res = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                maxResults=250,
                pageToken=page_token,
            ).execute()
            for item in res.get("items", []):
                summ = (item.get("summary") or "").strip()
                if summ:
                    existing_summaries.add(summ.lower())
                ext_k = item.get("extendedProperties", {}).get("private", {}).get("job_key")
                if ext_k:
                    existing_keys.add(ext_k.lower())
            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        print(f"[CalendarJobSync] Notice fetching existing events: {e}")

    created_count = 0
    for job in applied_jobs[:limit]:
        company = (job.get("company") or "").strip()
        title = (job.get("title") or "").strip()
        job_key = (job.get("job_key") or f"{company}_{title}").strip().lower()
        expected_summary = f"applied: {company} - {title}".lower()

        if job_key in existing_keys or expected_summary in existing_summaries:
            continue

        body = format_job_event(job)
        try:
            service.events().insert(calendarId=cal_id, body=body).execute()
            existing_keys.add(job_key)
            existing_summaries.add(expected_summary)
            created_count += 1
        except Exception as e:
            print(f"[CalendarJobSync] Error inserting event for {job_key}: {e}")

    return {
        "status": "success",
        "new_events_created": created_count,
        "total_applied_tracked": len(applied_jobs),
    }


def push_job_sync_to_calendar(service=None) -> dict:
    """
    Pushes applied jobs to Google Calendar:
    1. Creates/updates individual calendar events for applied jobs (with date, time, company, resume links).
    2. Updates the persistent sync event [Orion Sync] applied_jobs.json with the full state.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return {
            "status": "error",
            "message": "Google Calendar authentication unavailable. Ensure service account or google_token.json is valid.",
        }

    # 1. Sync individual applied job events
    ind_res = sync_individual_job_events(service=service)

    # 2. Update persistent all-in-one sync event
    get_job_history()
    applied_keys = _load_json(APPLIED_FILE, [])
    clean_keys = []
    for k in applied_keys:
        k_str = k if isinstance(k, str) else k.get("job_key")
        if k_str and k_str not in clean_keys:
            clean_keys.append(k_str)

    history = _load_json(HISTORY_FILE, [])
    body = format_sync_event_body(clean_keys, history)

    cal_id = get_target_calendar_id()
    existing_event = find_sync_calendar_event(service)

    try:
        if existing_event:
            event_id = existing_event["id"]
            updated = service.events().patch(
                calendarId=cal_id,
                eventId=event_id,
                body=body,
            ).execute()
            html_link = updated.get("htmlLink", "")
            _save_tracked_event_id(event_id, html_link)
            return {
                "status": "success",
                "action": "updated",
                "event_id": event_id,
                "html_link": html_link,
                "new_events_created": ind_res.get("new_events_created", 0),
                "total_keys": len(clean_keys),
                "message": f"Synced {len(clean_keys)} applied jobs to calendar ({ind_res.get('new_events_created', 0)} new individual events created).",
            }
        else:
            created = service.events().insert(
                calendarId=cal_id,
                body=body,
            ).execute()
            event_id = created.get("id")
            html_link = created.get("htmlLink", "")
            _save_tracked_event_id(event_id, html_link)
            return {
                "status": "success",
                "action": "created",
                "event_id": event_id,
                "html_link": html_link,
                "new_events_created": ind_res.get("new_events_created", 0),
                "total_keys": len(clean_keys),
                "message": f"Created single sync event ({ind_res.get('new_events_created', 0)} new individual events created).",
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Calendar sync failed: {str(e)}",
        }


def pull_job_sync_from_calendar(service=None) -> dict:
    """
    Pulls applied jobs from Google Calendar and merges them into local applied_jobs.json and job_history.json.
    Sources:
    1. Base64/Gzip compact payload from the single sync event.
    2. Plain JSON array from the sync event description (with fallback regex to handle partial/truncated JSON).
    3. Individual Google Calendar events (Applied: ...) across the past 365 days.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return {
            "status": "error",
            "message": "Google Calendar authentication unavailable.",
        }

    recovered_keys = set()
    sync_event = find_sync_calendar_event(service)

    if sync_event:
        description = sync_event.get("description", "")

        # 1. Check for compressed base64 payload: gz:b64:<encoded>
        b64_match = re.search(r"gz:b64:([A-Za-z0-9+/=]+)", description)
        if b64_match:
            try:
                decompressed = gzip.decompress(base64.b64decode(b64_match.group(1))).decode("utf-8")
                keys_list = json.loads(decompressed)
                if isinstance(keys_list, list):
                    for k in keys_list:
                        if isinstance(k, str) and k.strip():
                            recovered_keys.add(k.strip())
            except Exception as e:
                print(f"[CalendarJobSync] Notice decompressing payload: {e}")

        # 2. Check for plain JSON array in code block: ```json [...] ```
        if not recovered_keys:
            json_match = re.search(r"```(?:json)?\s*(\[\s*[\s\S]*?\s*\])\s*```", description)
            if not json_match:
                json_match = re.search(r"(\[\s*\"[^\"]+\"[\s\S]*?\])", description)

            if json_match:
                try:
                    keys_list = json.loads(json_match.group(1).strip())
                    if isinstance(keys_list, list):
                        for k in keys_list:
                            if isinstance(k, str) and k.strip():
                                recovered_keys.add(k.strip())
                except Exception:
                    pass

        # 3. Fallback for truncated/unclosed JSON: extract all quoted strings following [
        if not recovered_keys and "[" in description:
            try:
                content_after = description[description.find("[") :]
                end_marker = content_after.find("--- END")
                if end_marker != -1:
                    content_after = content_after[:end_marker]
                extracted = re.findall(r'"([a-zA-Z0-9_\-\.\:\(\)\,\&]+)"', content_after)
                for k in extracted:
                    k_clean = k.strip()
                    if k_clean and not k_clean.startswith("http") and len(k_clean) > 2 and " " not in k_clean:
                        recovered_keys.add(k_clean)
            except Exception:
                pass

    # 4. Enrich & Fallback: Query individual calendar events from Google Calendar
    try:
        cal_id = get_target_calendar_id()
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=365)).isoformat()
        page_token = None
        while True:
            res = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                singleEvents=True,
                maxResults=250,
                pageToken=page_token,
            ).execute()
            for ev in res.get("items", []):
                k = ev.get("extendedProperties", {}).get("private", {}).get("job_key")
                if k:
                    recovered_keys.add(k.strip().lower())
                else:
                    summ = (ev.get("summary") or "").strip()
                    if summ.startswith("Applied: ") and " - " in summ:
                        parts = summ[len("Applied: ") :].split(" - ", 1)
                        if len(parts) == 2:
                            c, t = parts[0].strip().replace(" ", "_"), parts[1].strip().replace(" ", "_")
                            recovered_keys.add(f"{c}_{t}".lower())
            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        print(f"[CalendarJobSync] Notice fetching individual calendar events: {e}")

    if not recovered_keys:
        return {
            "status": "error",
            "message": "Could not find any applied jobs in Google Calendar sync event or individual calendar events.",
        }

    return import_applied_keys(list(recovered_keys))


def import_applied_keys(incoming_keys: list) -> dict:
    """Merges incoming job keys into applied_jobs.json and job_history.json."""
    current_applied = _load_json(APPLIED_FILE, [])
    current_set = set()
    for k in current_applied:
        k_str = k if isinstance(k, str) else k.get("job_key")
        if k_str:
            current_set.add(k_str)

    new_keys = []
    for k in incoming_keys:
        k_str = k if isinstance(k, str) else (k.get("job_key") if isinstance(k, dict) else None)
        if k_str and k_str not in current_set:
            new_keys.append(k_str)
            current_applied.append(k_str)
            current_set.add(k_str)

    if new_keys:
        _save_json(APPLIED_FILE, current_applied)

    # Sync missing keys into job_history.json
    history = _load_json(HISTORY_FILE, [])
    history_keys = {h.get("job_key") for h in history if h.get("job_key")}
    new_history_entries = 0
    now_ts = int(datetime.now(timezone.utc).timestamp())
    now_iso = datetime.now(timezone.utc).isoformat()

    for k in new_keys:
        if k not in history_keys:
            company, title = parse_key(k)
            history.append({
                "job_key": k,
                "company": company,
                "title": title,
                "apply_url": "",
                "status": "applied",
                "timestamp": now_ts,
                "iso_date": now_iso,
                "source": "calendar_sync",
            })
            history_keys.add(k)
            new_history_entries += 1

    if new_history_entries > 0:
        _save_json(HISTORY_FILE, history)

    return {
        "status": "success",
        "new_keys_added": len(new_keys),
        "total_applied_keys": len(current_applied),
        "new_history_entries": new_history_entries,
        "message": f"Successfully synced {len(new_keys)} new job(s). Total tracked: {len(current_applied)}.",
    }


# Backwards compatibility alias
sync_all_jobs_to_calendar = push_job_sync_to_calendar


if __name__ == "__main__":
    print("[CalendarJobSync] Pushing single sync event to Google Calendar...")
    res = push_job_sync_to_calendar()
    print(json.dumps(res, indent=2))
