"""
actions/calendar_job_sync.py

Synchronizes applied and skipped job history from ai_job_search to Google Calendar.
Supports batch sync for all history entries as well as real-time single-job posting.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from actions.google_auth import get_calendar_service
from job_history import HISTORY_FILE, get_job_history, _load_json, _save_json


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
    else:
        start_dt = datetime.now(timezone.utc)

    end_dt = start_dt + timedelta(minutes=30)

    # Visual distinction: Green (10) for Applied, Graphite/Gray (8) for Skipped
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


def post_single_job_to_calendar(job: dict, service=None) -> tuple[bool, str, Optional[str]]:
    """
    Posts a single job to Google Calendar.
    Returns: (success: bool, message: str, event_id: str | None)
    """
    if not service:
        service = get_calendar_service(interactive=False)
    if not service:
        return False, "Google Calendar service unavailable (check authentication).", None

    event_body = format_job_event(job)
    try:
        created = service.events().insert(calendarId="primary", body=event_body).execute()
        event_id = created.get("id")
        return True, "Calendar event created.", event_id
    except Exception as e:
        return False, f"Calendar insert error: {e}", None


def sync_all_jobs_to_calendar(
    target: str = "all",
    force: bool = False,
    max_items: Optional[int] = None
) -> dict:
    """
    Syncs applied and/or skipped jobs from job_history.json to Google Calendar.
    target: 'all' | 'applied' | 'skipped'
    force: If True, re-creates events even if previously marked calendar_synced.
    """
    service = get_calendar_service(interactive=False)
    if not service:
        return {
            "status": "error",
            "message": "Google Calendar authentication unavailable. Ensure config/google_token.json is valid."
        }

    # Ensure legacy items are seeded
    get_job_history()

    history = _load_json(HISTORY_FILE, [])
    target = (target or "all").lower().strip()

    synced_applied = 0
    synced_skipped = 0
    already_synced = 0
    failed_count = 0
    total_processed = 0

    dirty = False

    for item in history:
        status = (item.get("status") or "").lower().strip()
        if target != "all" and status != target:
            continue

        if not force and item.get("calendar_synced") and item.get("calendar_event_id"):
            already_synced += 1
            continue

        if max_items and total_processed >= max_items:
            break

        success, msg, event_id = post_single_job_to_calendar(item, service=service)
        if success and event_id:
            item["calendar_synced"] = True
            item["calendar_event_id"] = event_id
            item["calendar_synced_at"] = datetime.now(timezone.utc).isoformat()
            dirty = True
            if status == "applied":
                synced_applied += 1
            else:
                synced_skipped += 1
        else:
            failed_count += 1
            print(f"[CalendarJobSync] ⚠️ Failed for {item.get('job_key')}: {msg}")

        total_processed += 1
        # Gentle throttling to prevent Google Calendar 429 rate limit errors
        time.sleep(0.06)

    if dirty:
        _save_json(HISTORY_FILE, history)

    total_new = synced_applied + synced_skipped
    return {
        "status": "success",
        "total_history_records": len(history),
        "synced_new": total_new,
        "synced_applied": synced_applied,
        "synced_skipped": synced_skipped,
        "already_synced": already_synced,
        "failed_count": failed_count,
        "message": (
            f"Successfully synced {total_new} jobs to Google Calendar "
            f"({synced_applied} applied, {synced_skipped} skipped). "
            f"{already_synced} were already up to date."
        ),
    }


if __name__ == "__main__":
    print("[CalendarJobSync] Running job history calendar sync...")
    res = sync_all_jobs_to_calendar()
    print(json.dumps(res, indent=2))
