"""Optional, workspace-restricted Antigravity CLI coding action."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess


WORKSPACE_ENV = "ANUBIS_CODE_WORKSPACE"
WRITE_ACTIONS = {"edit", "build", "write", "optimize"}
READ_ACTIONS = {"explain", "review", "analyze"}


def _workspace_root() -> Path:
    configured = os.getenv(WORKSPACE_ENV)
    root = Path(configured).expanduser() if configured else Path.home() / "Desktop" / "JarvisProjects"
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _inside_workspace(raw_path: str, root: Path) -> Path:
    path = Path(raw_path).expanduser()
    resolved = (path if path.is_absolute() else root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Path must stay inside the Antigravity workspace: {root}")
    return resolved


def _working_directory(parameters: dict, root: Path) -> Path:
    project_name = str(parameters.get("project_name", "")).strip()
    if not project_name:
        return root
    workdir = _inside_workspace(project_name, root)
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def _find_agy_binary() -> str | None:
    env_bin = os.getenv("ANUBIS_ANTIGRAVITY_BIN") or os.getenv("ANTIGRAVITY_BIN")
    if env_bin and (shutil.which(env_bin) or (Path(env_bin).is_file() and os.access(env_bin, os.X_OK))):
        return env_bin

    which_bin = shutil.which("agy")
    if which_bin:
        return which_bin

    for candidate in [
        Path.home() / ".local" / "bin" / "agy",
        Path.home() / "bin" / "agy",
        Path("/usr/local/bin/agy"),
    ]:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)

    return None


def _build_prompt(parameters: dict, root: Path) -> str:
    action = str(parameters.get("action", "auto")).strip().lower() or "auto"
    description = str(parameters.get("description") or parameters.get("instruction") or "").strip()
    lines = [
        f"Coding action: {action}",
        f"Request: {description or 'Complete the requested coding task.'}",
    ]

    for key in ("file_path", "output_path"):
        value = str(parameters.get(key, "")).strip()
        if value:
            lines.append(f"{key}: {_inside_workspace(value, root)}")

    language = str(parameters.get("language", "")).strip()
    if language:
        lines.append(f"Language: {language}")

    code = str(parameters.get("code", "")).strip()
    if code:
        lines.append(f"Code supplied by the user:\n{code}")

    if action in WRITE_ACTIONS:
        lines.append(
            "Work only inside the current working directory / configured workspace. "
            "Implement the requested changes or code directly."
        )
    else:
        lines.append(
            "Work only inside the configured workspace. "
            "For explain, review, or analyze actions, inspect and report without modifying files."
        )

    return "\n\n".join(lines)


def _build_agy_command(
    agy_bin: str,
    prompt: str,
    action: str,
    workdir: Path,
) -> list[str]:
    cmd = [
        agy_bin,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
    ]

    if action in WRITE_ACTIONS:
        cmd.extend(["--mode", "accept-edits"])
    else:
        cmd.extend(["--mode", "plan", "--sandbox"])

    model = os.getenv("ANUBIS_ANTIGRAVITY_MODEL")
    if model:
        cmd.extend(["--model", model])

    effort = os.getenv("ANUBIS_ANTIGRAVITY_EFFORT")
    if effort:
        cmd.extend(["--effort", effort])

    cmd.extend(["--add-dir", str(workdir)])
    return cmd


def antigravity_coding(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """Run one coding request through Google Antigravity CLI ('agy')."""
    del response, session_memory
    parameters = dict(parameters or {})
    action = str(parameters.get("action", "auto")).strip().lower() or "auto"

    agy_bin = _find_agy_binary()
    if not agy_bin:
        return (
            "Antigravity CLI ('agy') is not installed or not found on PATH. "
            "Please ensure agy is installed or set ANUBIS_ANTIGRAVITY_BIN."
        )

    try:
        root = _workspace_root()
        workdir = _working_directory(parameters, root)
        prompt = _build_prompt(parameters, root)

        if player and hasattr(player, "write_log"):
            player.write_log(f"[Antigravity] Starting {action} task in {workdir.name}...")

        if speak:
            speak("Starting the sandboxed coding task with Antigravity, sir.")

        cmd = _build_agy_command(agy_bin, prompt, action, workdir)
        timeout_sec = int(parameters.get("timeout") or os.getenv("ANUBIS_ANTIGRAVITY_TIMEOUT", "120"))

        result = subprocess.run(
            cmd,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

        if result.returncode != 0 and not result.stdout.strip():
            err = result.stderr.strip() or f"Process exited with code {result.returncode}"
            return f"Antigravity CLI task failed: {err}"

        output = result.stdout.strip()
        try:
            data = json.loads(output)
            resp = (data.get("response") or "").strip()
            if data.get("status") == "SUCCESS":
                return resp or "Antigravity CLI completed the task."
            error_msg = data.get("error") or resp or f"status {data.get('status')}"
            return f"Antigravity CLI task ended with: {error_msg}"
        except json.JSONDecodeError:
            return output or "Antigravity CLI completed with empty output."

    except subprocess.TimeoutExpired:
        return f"Antigravity CLI task timed out after {timeout_sec}s."
    except Exception as exc:
        return f"Antigravity coding task failed: {exc}"
