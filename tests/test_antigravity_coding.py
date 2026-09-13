import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from actions.antigravity_coding import antigravity_coding


class AntigravityCodingTests(unittest.TestCase):
    def setUp(self):
        self.mock_agy = "/fake/bin/agy"

    @patch("actions.antigravity_coding._find_agy_binary")
    @patch("subprocess.run")
    def test_review_is_read_only_and_uses_plan_mode(self, mock_run, mock_find_bin):
        mock_find_bin.return_value = self.mock_agy
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"status": "SUCCESS", "response": "Code review complete."}),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ):
            result = antigravity_coding({"action": "review", "file_path": "app.py"})

        self.assertEqual(result, "Code review complete.")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "plan")
        self.assertIn("--sandbox", cmd)
        self.assertIn("--dangerously-skip-permissions", cmd)
        self.assertEqual(mock_run.call_args[1]["cwd"], str(Path(workspace).resolve()))

    @patch("actions.antigravity_coding._find_agy_binary")
    @patch("subprocess.run")
    def test_edit_uses_accept_edits_mode(self, mock_run, mock_find_bin):
        mock_find_bin.return_value = self.mock_agy
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"status": "SUCCESS", "response": "File updated."}),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ):
            result = antigravity_coding(
                {"action": "edit", "file_path": "app.py", "description": "Add login"}
            )

        self.assertEqual(result, "File updated.")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "accept-edits")
        self.assertNotIn("--sandbox", cmd)

    @patch("actions.antigravity_coding._find_agy_binary")
    @patch("subprocess.run")
    def test_path_outside_workspace_is_rejected(self, mock_run, mock_find_bin):
        mock_find_bin.return_value = self.mock_agy

        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ):
            result = antigravity_coding({"action": "edit", "file_path": "../outside.py"})

        self.assertIn("Path must stay inside", result)
        mock_run.assert_not_called()

    @patch("actions.antigravity_coding._find_agy_binary")
    @patch("subprocess.run")
    def test_unknown_action_defaults_to_plan_mode(self, mock_run, mock_find_bin):
        mock_find_bin.return_value = self.mock_agy
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"status": "SUCCESS", "response": "Analysis done."}),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ):
            result = antigravity_coding({"action": "unexpected", "description": "Inspect this"})

        self.assertEqual(result, "Analysis done.")
        cmd = mock_run.call_args[0][0]
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "plan")
        self.assertIn("--sandbox", cmd)

    @patch("actions.antigravity_coding._find_agy_binary")
    @patch("subprocess.run")
    def test_build_uses_workspace_write_in_project_subdirectory(self, mock_run, mock_find_bin):
        mock_find_bin.return_value = self.mock_agy
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"status": "SUCCESS", "response": "Build succeeded."}),
            stderr="",
        )

        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ):
            result = antigravity_coding(
                {"action": "build", "project_name": "demo", "description": "Build a demo"}
            )

        expected = str((Path(workspace) / "demo").resolve())
        self.assertEqual(result, "Build succeeded.")
        cmd = mock_run.call_args[0][0]
        self.assertIn("--mode", cmd)
        self.assertEqual(cmd[cmd.index("--mode") + 1], "accept-edits")
        self.assertEqual(mock_run.call_args[1]["cwd"], expected)

    @patch("actions.antigravity_coding._find_agy_binary")
    def test_missing_binary_returns_friendly_error(self, mock_find_bin):
        mock_find_bin.return_value = None
        result = antigravity_coding({"action": "review", "description": "test"})
        self.assertIn("not installed or not found", result)

    @patch("actions.antigravity_coding._find_agy_binary")
    @patch("subprocess.run")
    def test_timeout_returns_clear_message(self, mock_run, mock_find_bin):
        mock_find_bin.return_value = self.mock_agy
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["agy"], timeout=10)

        with tempfile.TemporaryDirectory() as workspace, patch.dict(
            os.environ, {"ANUBIS_CODE_WORKSPACE": workspace}
        ):
            result = antigravity_coding({"action": "review", "timeout": 10})

        self.assertIn("timed out after 10s", result)


if __name__ == "__main__":
    unittest.main()
