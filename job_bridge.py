"""
job_bridge.py

Thread-safe, atomic IPC bridge between ai_job_search and Orion Companion (Anubis).
Coordinates multi-candidate batch screening (Stage 1) and tailored application review (Stage 2).
Uses atomic file replacement (.tmp + os.replace) to eliminate race conditions.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any, Callable

IPC_FILE = Path.home() / ".orion_job_ipc.json"


def _write_atomic(data: dict) -> None:
    """Writes JSON payload atomically using temporary file and atomic replace."""
    tmp_file = IPC_FILE.with_suffix(".tmp")
    try:
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp_file, IPC_FILE)
    except Exception as e:
        print(f"[JobBridge] ⚠️ Atomic write error: {e}")


def _read_ipc() -> Optional[dict]:
    """Reads the current IPC payload safely."""
    if not IPC_FILE.exists():
        return None
    try:
        return json.loads(IPC_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


class JobSubmissionBridge:
    async def request_batch_selection(
        self,
        candidates: List[Dict[str, Any]],
        on_skip_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Stage 1: Publishes a batch of candidate listings (e.g. 10 jobs) for user screening.
        Polls until the user selects a candidate to scrape/tailor, or skips the batch.
        As the user skips individual jobs, triggers on_skip_callback(job_key) in real time.

        Returns:
            ("selected", chosen_candidate_dict)
            ("skip_all", None)
            ("rescan", None)
        """
        indexed_candidates = []
        for idx, c in enumerate(candidates, 1):
            c_copy = dict(c)
            c_copy["index"] = idx
            indexed_candidates.append(c_copy)

        payload = {
            "version": 2,
            "stage": "screen_batch",
            "status": "pending",
            "candidates": indexed_candidates,
            "skipped_keys": [],
            "selected_key": None,
        }
        _write_atomic(payload)
        print(f"\n[JobBridge] 📢 Published {len(indexed_candidates)} candidates for screening in Orion Dashboard...")

        processed_skips = set()

        while True:
            await asyncio.sleep(0.5)
            data = _read_ipc()
            if not data or data.get("stage") != "screen_batch":
                continue

            # Process any newly added individual skips
            skipped_keys = data.get("skipped_keys") or []
            for k in skipped_keys:
                if k not in processed_skips:
                    processed_skips.add(k)
                    if on_skip_callback:
                        try:
                            on_skip_callback(k)
                        except Exception as e:
                            print(f"[JobBridge] Error in skip callback for {k}: {e}")

            status = data.get("status")
            selected_key = data.get("selected_key")

            if status == "selected" and selected_key:
                chosen = next((c for c in indexed_candidates if c.get("job_key") == selected_key), None)
                if not chosen:
                    chosen = next((c for c in indexed_candidates if c.get("id") == selected_key), None)
                if chosen:
                    print(f"[JobBridge] ⚡ Selected for processing: {chosen.get('company')} — {chosen.get('title')}")
                    return ("selected", chosen)

            if status in ("skip_all", "rejected", "cancelled"):
                print("[JobBridge] ⏩ Entire batch skipped.")
                return ("skip_all", None)

            if status == "rescan":
                print("[JobBridge] 🔄 Requesting fresh scan.")
                return ("rescan", None)

            # If all candidates were individually skipped
            remaining = data.get("candidates") or []
            if len(remaining) == 0:
                print("[JobBridge] ⏩ All candidates skipped.")
                return ("skip_all", None)

    async def request_approval(self, job_data: dict) -> bool:
        """
        Stage 2: Requests final review approval for a compiled application (with PDFs).
        Keeps backwards compatibility with legacy request_approval.
        """
        payload = {
            "version": 2,
            "stage": "review",
            "status": "pending",
            "job": job_data,
        }
        _write_atomic(payload)
        print(f"\n[JobBridge] 📢 Requesting approval for {job_data.get('company')}...")

        while True:
            await asyncio.sleep(0.5)
            data = _read_ipc()
            if not data:
                continue
            if data.get("stage") == "review" and data.get("status") in ("approved", "rejected"):
                try:
                    if IPC_FILE.exists():
                        IPC_FILE.unlink()
                except Exception:
                    pass
                return data["status"] == "approved"

    def get_current_state(self) -> Optional[dict]:
        """Returns the full active IPC state dictionary."""
        return _read_ipc()

    def get_pending_job(self) -> Optional[dict]:
        """
        Backwards-compatible accessor for Orion Dashboard.
        If in 'review' stage, returns the single job with PDFs.
        If in 'screen_batch' stage, returns None (dashboard uses get_current_state).
        """
        data = _read_ipc()
        if not data:
            return None
        if data.get("status") == "pending" and data.get("stage") == "review":
            return data.get("job")
        if data.get("status") == "pending" and "job" in data:
            return data.get("job")
        return None

    def select_candidate(self, identifier: Any) -> Optional[dict]:
        """
        Called by Orion Dashboard (POST /api/job/select) or Voice action.
        Matches by job_key, 1-based index (int or str), or fuzzy company name.
        """
        data = _read_ipc()
        if not data or data.get("stage") != "screen_batch":
            return None

        candidates = data.get("candidates") or []
        chosen = None

        str_id = str(identifier).strip().lower()
        for c in candidates:
            if c.get("job_key", "").lower() == str_id:
                chosen = c
                break

        if not chosen:
            try:
                idx = int(str_id)
                for c in candidates:
                    if c.get("index") == idx:
                        chosen = c
                        break
            except ValueError:
                pass

        if not chosen:
            for c in candidates:
                if c.get("company", "").lower() == str_id:
                    chosen = c
                    break

        if chosen:
            data["status"] = "selected"
            data["selected_key"] = chosen["job_key"]
            _write_atomic(data)
            return chosen

        return None

    def skip_candidate(self, job_key: str) -> bool:
        """
        Called by Orion Dashboard (POST /api/job/skip) or Voice action.
        Removes the candidate from the list and appends to skipped_keys.
        """
        data = _read_ipc()
        if not data or data.get("stage") != "screen_batch":
            return False

        target_key = job_key.strip().lower()
        candidates = data.get("candidates") or []
        new_candidates = [c for c in candidates if c.get("job_key", "").lower() != target_key]

        skipped = data.get("skipped_keys") or []
        if target_key not in skipped:
            skipped.append(target_key)

        data["candidates"] = new_candidates
        data["skipped_keys"] = skipped

        if len(new_candidates) == 0:
            data["status"] = "skip_all"

        _write_atomic(data)
        return True

    def skip_all_candidates(self) -> bool:
        """Skips all remaining candidates in the batch."""
        data = _read_ipc()
        if not data or data.get("stage") != "screen_batch":
            return False

        candidates = data.get("candidates") or []
        skipped = data.get("skipped_keys") or []
        for c in candidates:
            k = c.get("job_key")
            if k and k not in skipped:
                skipped.append(k)

        data["candidates"] = []
        data["skipped_keys"] = skipped
        data["status"] = "skip_all"
        _write_atomic(data)
        return True

    def resolve_approval(self, approved: bool) -> None:
        """Called by Orion Dashboard to resolve Stage 2 review approval."""
        status = "approved" if approved else "rejected"
        data = _read_ipc() or {}
        data["status"] = status
        _write_atomic(data)


bridge = JobSubmissionBridge()
