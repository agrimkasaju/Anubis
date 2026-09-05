"""Optional, workspace-restricted Codex coding action."""

from __future__ import annotations

import os
from pathlib import Path


WORKSPACE_ENV = "ANUBIS_CODE_WORKSPACE"
WRITE_ACTIONS = {"edit", "build"}


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
        raise ValueError(f"Path must stay inside the Codex workspace: {root}")
    return resolved


def _working_directory(parameters: dict, root: Path) -> Path:
    project_name = str(parameters.get("project_name", "")).strip()
    if not project_name:
        return root
    workdir = _inside_workspace(project_name, root)
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


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

    lines.append(
        "Work only inside the configured workspace. Do not request broader permissions. "
        "For explain, review, or analyze actions, inspect and report without changing files."
    )
    return "\n\n".join(lines)


def codex_coding(parameters: dict, response=None, player=None, session_memory=None, speak=None) -> str:
    """Run one coding request through the official Codex Python SDK."""
    del response, player, session_memory
    parameters = dict(parameters or {})
    action = str(parameters.get("action", "auto")).strip().lower() or "auto"

    try:
        from openai_codex import ApprovalMode, Codex, Sandbox
    except ImportError:
        return "Codex SDK is not installed. Run: uv pip install openai-codex"

    try:
        root = _workspace_root()
        workdir = _working_directory(parameters, root)
        prompt = _build_prompt(parameters, root)
        sandbox = Sandbox.workspace_write if action in WRITE_ACTIONS else Sandbox.read_only

        if speak:
            speak("Starting the sandboxed coding task, sir.")

        with Codex() as codex:
            thread = codex.thread_start(
                approval_mode=ApprovalMode.deny_all,
                cwd=str(workdir),
                ephemeral=True,
                model=os.getenv("ANUBIS_CODEX_MODEL") or None,
                sandbox=sandbox,
            )
            result = thread.run(prompt)

        return (result.final_response or "Codex completed the task.").strip()
    except Exception as exc:
        return f"Codex coding task failed: {exc}"
