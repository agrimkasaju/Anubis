import json
import asyncio
from pathlib import Path

# Shared absolute path in your home directory
IPC_FILE = Path.home() / ".orion_job_ipc.json"

class JobSubmissionBridge:
    async def request_approval(self, job_data: dict) -> bool:
        """Writes the job to a file and polls for Orion's answer."""
        IPC_FILE.write_text(json.dumps({"status": "pending", "job": job_data}))
        print(f"\n[JobBridge] 📢 Requesting approval for {job_data.get('company')}...")
        
        while True:
            await asyncio.sleep(1)
            try:
                if IPC_FILE.exists():
                    data = json.loads(IPC_FILE.read_text())
                    if data.get("status") in ["approved", "rejected"]:
                        IPC_FILE.unlink()  # Clean up the file
                        return data["status"] == "approved"
            except Exception:
                pass

    def get_pending_job(self) -> dict | None:
        """Called by Orion to check if a job is waiting."""
        try:
            if IPC_FILE.exists():
                data = json.loads(IPC_FILE.read_text())
                if data.get("status") == "pending":
                    return data.get("job")
        except Exception:
            pass
        return None

    def resolve_approval(self, approved: bool):
        """Called by Orion to write the decision back to the file."""
        status = "approved" if approved else "rejected"
        try:
            if IPC_FILE.exists():
                data = json.loads(IPC_FILE.read_text())
                data["status"] = status
                IPC_FILE.write_text(json.dumps(data))
        except Exception:
            pass

bridge = JobSubmissionBridge()