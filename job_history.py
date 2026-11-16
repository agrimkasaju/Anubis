"""
Job History Store & Management for Orion and ai_job_search.
Maintains persistent record of applied and skipped jobs, with automatic
migration from applied_jobs.json and PDF metadata detection.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timezone

HISTORY_FILE = Path("/home/grim/Downloads/ai_job_search/ai_job_search/job_history.json")
APPLIED_FILE = Path("/home/grim/Downloads/ai_job_search/ai_job_search/applied_jobs.json")
OUTPUT_DIR = Path("/home/grim/Downloads/ai_job_search/ai_job_search/output")


def parse_key(k: str) -> tuple[str, str]:
    """Extracts company and role title from standard job key format."""
    parts = k.split("_", 1)
    comp = parts[0].capitalize() if parts else "Unknown"
    title = parts[1].replace("_", " ").title() if len(parts) > 1 else ""
    return comp, title


def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def _save_json(path: Path, data):
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[JobHistory] Error saving {path}: {e}")


def record_job_history(job_data: dict, status: str = "applied") -> dict:
    """
    Records or updates a job in job_history.json and syncs with applied_jobs.json.
    status: 'applied' or 'skipped'
    """
    job_key = (job_data.get("job_key") or "").strip()
    company = (job_data.get("company") or "").strip()
    title = (job_data.get("title") or "").strip()
    apply_url = (job_data.get("apply_url") or "").strip()

    if not job_key and company and title:
        job_key = f"{company}_{title}".replace(" ", "_").lower()

    if not job_key:
        return {}

    now_ts = int(time.time())
    iso_str = datetime.now(timezone.utc).isoformat()

    history = _load_json(HISTORY_FILE, [])

    # Check if entry already exists
    entry = None
    for item in history:
        if item.get("job_key") == job_key:
            entry = item
            break

    if entry:
        entry["status"] = status
        entry["timestamp"] = now_ts
        entry["iso_date"] = iso_str
        if company:
            entry["company"] = company
        if title:
            entry["title"] = title
        if apply_url and apply_url != "N/A":
            entry["apply_url"] = apply_url
        if job_data.get("resume_pdf"):
            entry["resume_pdf"] = job_data["resume_pdf"]
        if job_data.get("cover_letter_pdf"):
            entry["cover_letter_pdf"] = job_data["cover_letter_pdf"]
        if job_data.get("combined_pdf"):
            entry["combined_pdf"] = job_data["combined_pdf"]
        if job_data.get("stage"):
            entry["stage"] = job_data["stage"]
    else:
        entry = {
            "job_key": job_key,
            "company": company or parse_key(job_key)[0],
            "title": title or parse_key(job_key)[1],
            "apply_url": apply_url if apply_url != "N/A" else "",
            "status": status,
            "timestamp": now_ts,
            "iso_date": iso_str,
            "stage": job_data.get("stage", ""),
            "resume_pdf": job_data.get("resume_pdf") or job_data.get("cv_pdf"),
            "cover_letter_pdf": job_data.get("cover_letter_pdf") or job_data.get("cl_pdf"),
            "combined_pdf": job_data.get("combined_pdf"),
        }
        history.insert(0, entry)

    _save_json(HISTORY_FILE, history)

    # Sync into applied_jobs.json so scraper won't re-prompt
    applied_list = _load_json(APPLIED_FILE, [])
    normalized_keys = set()
    for k in applied_list:
        k_str = k if isinstance(k, str) else k.get("job_key")
        if k_str:
            normalized_keys.add(k_str)

    if job_key not in normalized_keys:
        applied_list.append(job_key)
        _save_json(APPLIED_FILE, applied_list)

    return entry


def remove_from_job_history(job_key: str) -> bool:
    """
    Removes an item from both job_history.json and applied_jobs.json,
    unlocking it for future reapplication.
    """
    if not job_key:
        return False

    clean_target = job_key.strip().lower()

    # 1. Remove from job_history.json
    history = _load_json(HISTORY_FILE, [])
    orig_len = len(history)
    history = [item for item in history if item.get("job_key", "").strip().lower() != clean_target]
    if len(history) != orig_len:
        _save_json(HISTORY_FILE, history)

    # 2. Remove from applied_jobs.json
    applied_list = _load_json(APPLIED_FILE, [])
    new_applied = []
    for k in applied_list:
        k_str = (k if isinstance(k, str) else k.get("job_key", "")).strip().lower()
        if k_str and k_str != clean_target:
            new_applied.append(k)

    if len(new_applied) != len(applied_list):
        _save_json(APPLIED_FILE, new_applied)

    return True


def get_job_history() -> dict:
    """
    Returns {'applied': [...], 'skipped': [...]}, sorted with most recent first.
    Performs auto-seeding of any legacy entries from applied_jobs.json.
    """
    history = _load_json(HISTORY_FILE, [])
    applied_keys = _load_json(APPLIED_FILE, [])

    known_keys = {item.get("job_key") for item in history if item.get("job_key")}
    dirty = False

    for k in applied_keys:
        key_str = k if isinstance(k, str) else k.get("job_key")
        if not key_str or key_str in known_keys:
            continue

        comp, title = parse_key(key_str)
        mtime = time.time()
        res_pdf = None
        cl_pdf = None
        comb_pdf = None

        safe_comp = "".join(x for x in comp if x.isalnum() or x in " _-").replace(" ", "_").lower()
        raw_comp = comp.lower()

        if OUTPUT_DIR.exists():
            for p in OUTPUT_DIR.iterdir():
                p_lower = p.name.lower()
                if p_lower.startswith(safe_comp) or p_lower.startswith(raw_comp):
                    if "resume" in p_lower and p.suffix.lower() == ".pdf":
                        res_pdf = f"output/{p.name}"
                        mtime = min(mtime, p.stat().st_mtime)
                    elif "cover_letter" in p_lower and p.suffix.lower() == ".pdf":
                        cl_pdf = f"output/{p.name}"
                    elif "combined" in p_lower and p.suffix.lower() == ".pdf":
                        comb_pdf = f"output/{p.name}"

        entry = {
            "job_key": key_str,
            "company": comp,
            "title": title,
            "apply_url": "",
            "status": "applied",
            "timestamp": int(mtime),
            "iso_date": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            "resume_pdf": res_pdf,
            "cover_letter_pdf": cl_pdf,
            "combined_pdf": comb_pdf,
        }
        history.append(entry)
        known_keys.add(key_str)
        dirty = True

    if dirty:
        _save_json(HISTORY_FILE, history)

    applied = [h for h in history if h.get("status") == "applied"]
    skipped = [h for h in history if h.get("status") == "skipped"]

    applied.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    skipped.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    return {"applied": applied, "skipped": skipped}
