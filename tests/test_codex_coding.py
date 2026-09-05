import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from actions.codex_coding import codex_coding


class _FakeThread:
    def __init__(self, calls):
        self.calls = calls

    def run(self, prompt):
        self.calls["prompt"] = prompt
        return types.SimpleNamespace(final_response="done")


class _FakeCodex:
    calls = {}

    def __init__(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def thread_start(self, **kwargs):
        self.calls["thread"] = kwargs
        return _FakeThread(self.calls)


class CodexCodingTests(unittest.TestCase):
    def setUp(self):
        _FakeCodex.calls = {}
        self.sdk = types.SimpleNamespace(
            ApprovalMode=types.SimpleNamespace(deny_all="deny_all"),
            Codex=_FakeCodex,
            Sandbox=types.SimpleNamespace(read_only="read_only", workspace_write="workspace_write"),
        )

    def test_review_is_read_only_and_denies_escalation(self):
        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ), patch.dict(sys.modules, {"openai_codex": self.sdk}):
            result = codex_coding({"action": "review", "file_path": "app.py"})

        self.assertEqual(result, "done")
        self.assertEqual(_FakeCodex.calls["thread"]["sandbox"], "read_only")
        self.assertEqual(_FakeCodex.calls["thread"]["approval_mode"], "deny_all")
        self.assertEqual(_FakeCodex.calls["thread"]["cwd"], str(Path(workspace).resolve()))

    def test_path_outside_workspace_is_rejected(self):
        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ), patch.dict(sys.modules, {"openai_codex": self.sdk}):
            result = codex_coding({"action": "edit", "file_path": "../outside.py"})

        self.assertIn("Path must stay inside", result)
        self.assertNotIn("thread", _FakeCodex.calls)

    def test_unknown_action_defaults_to_read_only(self):
        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ), patch.dict(sys.modules, {"openai_codex": self.sdk}):
            result = codex_coding({"action": "unexpected", "description": "Inspect this"})

        self.assertEqual(result, "done")
        self.assertEqual(_FakeCodex.calls["thread"]["sandbox"], "read_only")

    def test_build_uses_workspace_write_in_project_subdirectory(self):
        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ), patch.dict(sys.modules, {"openai_codex": self.sdk}):
            result = codex_coding(
                {"action": "build", "project_name": "demo", "description": "Build a demo"}
            )

        expected = str((Path(workspace) / "demo").resolve())
        self.assertEqual(result, "done")
        self.assertEqual(_FakeCodex.calls["thread"]["sandbox"], "workspace_write")
        self.assertEqual(_FakeCodex.calls["thread"]["cwd"], expected)


if __name__ == "__main__":
    unittest.main()
