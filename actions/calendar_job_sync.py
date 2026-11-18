"""
actions/calendar_job_sync.py

Synchronizes applied and skipped job history between ai_job_search and Google Calendar.
Uses Daily Application Digests (one clean all-day event per active application day):
- Summary: 📝 Applied: 5 roles (Shopify, NVIDIA, Databricks...)
- Description: Rich markdown digest listing company, title, timestamps, posting URLs, and tailored PDF links.
- Embedded payload: Compact compressed backup (gz:b64) for instantaneous two-way sync.
- Zero overlapping event clutter.
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
from collections import defaultdict

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

DIGEST_EVENT_PREFIX = "📝 Applied:"


def format_daily_digest_body(date_str: str, day_jobs: list[dict], all_applied_keys: list[str] = None) -> dict:
    """
    Constructs an all-day Daily Digest event for a specific date containing all roles applied on that day.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        dt = datetime.now().date()
    next_day_str = (dt + timedelta(days=1)).strftime("%Y-%m-%d")

    count = len(day_jobs)
    comps = []
    for j in day_jobs:
        c = (j.get("company") or "").strip()
        if c and c not in comps:
            comps.append(c)

    if count == 1:
        comp = comps[0] if comps else "Company"
        title = (day_jobs[0].get("title") or "Role").strip()
        summary = f"📝 Applied: {comp} - {title}"
    else:
        sample_comps = ", ".join(comps[:3])
        if len(comps) > 3:
            sample_comps += f" +{len(comps) - 3} more"
        summary = f"📝 Applied: {count} roles ({sample_comps})"

    # Rich formatted description
    lines = [
        "====================================================",
        f"📝 JOB APPLICATIONS DIGEST — {date_str}",
        "====================================================",
        f"Total Roles Applied: {count}",
        f"Companies: {', '.join(comps)}",
        "",
        "--- APPLIED ROLES ---",
    ]

    for idx, j in enumerate(day_jobs, 1):
        comp = (j.get("company") or "Unknown").strip()
        title = (j.get("title") or "Role").strip()
        job_key = (j.get("job_key") or f"{comp}_{title}").strip().lower()
        url = (j.get("apply_url") or "").strip()
        ts = j.get("timestamp")
        time_label = ""
        if ts:
            try:
                local_dt = datetime.fromtimestamp(int(ts)).astimezone()
                time_label = f" ({local_dt.strftime('%I:%M %p').lstrip('0')})"
            except Exception:
                pass

        lines.append(f"{idx}. {comp} — {title}{time_label}")
        lines.append(f"   • Job Key: {job_key}")
        if url and url != "N/A":
            lines.append(f"   • URL: {url}")
        if j.get("resume_pdf"):
            lines.append(f"   • Resume: {j['resume_pdf']}")
        if j.get("cover_letter_pdf"):
            lines.append(f"   • Cover Letter: {j['cover_letter_pdf']}")
        if j.get("combined_pdf"):
            lines.append(f"   • Combined PDF: {j['combined_pdf']}")
        lines.append("")

    if all_applied_keys:
        full_json_bytes = json.dumps(all_applied_keys).encode("utf-8")
        compressed_b64 = base64.b64encode(gzip.compress(full_json_bytes)).decode("ascii")
        lines.extend([
            "--- COMPACT BACKUP PAYLOAD (Orion Auto-Sync) ---",
            "```payload",
            f"gz:b64:{compressed_b64}",
            "```",
            "",
        ])

    lines.append("Synchronized by Orion Companion & ai_job_search.")
    description = "\n".join(lines)
    if len(description) > 8000:
        description = description[:7800] + "\n\n... (trimmed for calendar limit)"

    job_keys_list = [j.get("job_key") for j in day_jobs if j.get("job_key")]

    return {
        "summary": summary,
        "description": description,
        "colorId": "10",  # Basil Green
        "start": {"date": date_str},
        "end": {"date": next_day_str},
        "extendedProperties": {
            "private": {
                "source": "anubis_daily_digest",
                "date": date_str,
                "count": str(count),
                "job_keys": json.dumps(job_keys_list),
            }
        },
    }


def cleanup_legacy_individual_events(service=None) -> int:
    """
    Scans for and purges any legacy individual job events (e.g. 'Applied: ...' 30-min events)
    and legacy '[Orion Sync]' all-day banners to keep the calendar grid clean.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return 0

    cal_id = get_target_calendar_id()
    deleted_count = 0
    try:
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=180)).isoformat()
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

            for ev in res.get("items", []):
                summary = (ev.get("summary") or "").strip()
                ext = ev.get("extendedProperties", {}).get("private", {})
                is_old_individual = (
                    ext.get("source") in ("anubis_ai_job_search", "anubis_job_sync")
                    or (summary.startswith("Applied: ") and not summary.startswith(DIGEST_EVENT_PREFIX))
                    or summary.startswith("Skipped: ")
                    or summary == "[Orion Sync] applied_jobs.json"
                )
                if is_old_individual and ext.get("source") != "anubis_daily_digest":
                    try:
                        service.events().delete(calendarId=cal_id, eventId=ev["id"]).execute()
                        deleted_count += 1
                    except Exception:
                        pass

            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        print(f"[CalendarJobSync] Legacy cleanup notice: {e}")

    return deleted_count


def sync_daily_digest_events(service=None) -> dict:
    """
    Groups all applied jobs by date and maintains exactly one clean all-day digest event per day.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return {"status": "error", "message": "No calendar service"}

    cal_id = get_target_calendar_id()
    history = _load_json(HISTORY_FILE, [])
    applied_jobs = [h for h in history if (h.get("status") or "").lower() == "applied"]

    # Load all applied keys
    applied_keys = _load_json(APPLIED_FILE, [])
    clean_keys = []
    for k in applied_keys:
        k_str = k if isinstance(k, str) else k.get("job_key")
        if k_str and k_str not in clean_keys:
            clean_keys.append(k_str)

    # Group applied jobs by date
    days = defaultdict(list)
    for job in applied_jobs:
        ts = job.get("timestamp")
        iso = job.get("iso_date")
        if ts:
            try:
                dt = datetime.fromtimestamp(int(ts)).astimezone()
            except Exception:
                dt = datetime.now().astimezone()
        elif iso:
            try:
                dt = datetime.fromisoformat(iso).astimezone()
            except Exception:
                dt = datetime.now().astimezone()
        else:
            dt = datetime.now().astimezone()
        day_key = dt.strftime("%Y-%m-%d")
        days[day_key].append(job)

    # Find existing daily digest events on calendar
    existing_digests = {}
    try:
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=180)).isoformat()
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
            for ev in res.get("items", []):
                ext = ev.get("extendedProperties", {}).get("private", {})
                d_key = ext.get("date")
                if not d_key and ev.get("start", {}).get("date"):
                    d_key = ev["start"]["date"]
                if ext.get("source") == "anubis_daily_digest" or (ev.get("summary") or "").startswith("📝 Applied"):
                    if d_key:
                        existing_digests[d_key] = ev["id"]
            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        print(f"[CalendarJobSync] Error listing existing digests: {e}")

    # Identify the latest active date to attach the compressed backup payload
    latest_date = max(days.keys()) if days else None

    digests_created = 0
    digests_updated = 0

    for d_key, day_jobs in days.items():
        payload_keys = clean_keys if d_key == latest_date else None
        body = format_daily_digest_body(d_key, day_jobs, all_applied_keys=payload_keys)

        existing_id = existing_digests.get(d_key)
        try:
            if existing_id:
                service.events().patch(calendarId=cal_id, eventId=existing_id, body=body).execute()
                digests_updated += 1
            else:
                service.events().insert(calendarId=cal_id, body=body).execute()
                digests_created += 1
        except Exception as e:
            print(f"[CalendarJobSync] Error writing digest for {d_key}: {e}")

    # Clean up stale digest events for dates that no longer contain applied jobs
    stale_digests_deleted = 0
    for d_key, ev_id in existing_digests.items():
        if d_key not in days:
            try:
                service.events().delete(calendarId=cal_id, eventId=ev_id).execute()
                stale_digests_deleted += 1
            except Exception as e:
                print(f"[CalendarJobSync] Error deleting stale digest for {d_key}: {e}")

    # Purge old 30-min clutter
    deleted_legacy = cleanup_legacy_individual_events(service)

    return {
        "status": "success",
        "digests_created": digests_created,
        "digests_updated": digests_updated,
        "stale_digests_deleted": stale_digests_deleted,
        "total_days_tracked": len(days),
        "total_applied_jobs": len(applied_jobs),
        "deleted_legacy_events": deleted_legacy,
        "message": f"Synced {len(days)} daily application digests ({digests_created} new, {digests_updated} updated, {stale_digests_deleted} stale removed). Cleaned up {deleted_legacy} legacy events.",
    }


def push_job_sync_to_calendar(service=None) -> dict:
    """
    Pushes applied jobs to Google Calendar using Daily Application Digests.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return {
            "status": "error",
            "message": "Google Calendar authentication unavailable. Ensure service account or google_token.json is valid.",
        }

    return sync_daily_digest_events(service=service)


def pull_job_sync_from_calendar(service=None) -> dict:
    """
    Pulls applied jobs from Google Calendar Daily Digest events and merges them into local applied_jobs.json and job_history.json.
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return {
            "status": "error",
            "message": "Google Calendar authentication unavailable.",
        }

    cal_id = get_target_calendar_id()
    recovered_keys = set()

    try:
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
                summary = (ev.get("summary") or "").strip()
                ext = ev.get("extendedProperties", {}).get("private", {})
                desc = ev.get("description", "")

                # 1. From daily digest job_keys JSON in private properties
                if ext.get("job_keys"):
                    try:
                        k_list = json.loads(ext["job_keys"])
                        for k in k_list:
                            if k and isinstance(k, str):
                                recovered_keys.add(k.strip().lower())
                    except Exception:
                        pass

                # 2. From compressed payload if present in description
                b64_match = re.search(r"gz:b64:([A-Za-z0-9+/=]+)", desc)
                if b64_match:
                    try:
                        decompressed = gzip.decompress(base64.b64decode(b64_match.group(1))).decode("utf-8")
                        k_list = json.loads(decompressed)
                        for k in k_list:
                            if k and isinstance(k, str):
                                recovered_keys.add(k.strip().lower())
                    except Exception:
                        pass

                # 3. From Job Key: lines in description
                for line in desc.splitlines():
                    if "Job Key:" in line:
                        k = line.split("Job Key:")[-1].strip().lower()
                        if k and len(k) > 2:
                            recovered_keys.add(k)

            page_token = res.get("nextPageToken")
            if not page_token:
                break
    except Exception as e:
        print(f"[CalendarJobSync] Notice querying digests: {e}")

    if not recovered_keys:
        return {
            "status": "error",
            "message": "No applied job digest events found on Google Calendar.",
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
    print("[CalendarJobSync] Pushing Daily Application Digests to Google Calendar...")
    res = push_job_sync_to_calendar()
    print(json.dumps(res, indent=2))
