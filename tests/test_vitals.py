"""
Unit tests for on-demand vitals engine and tool schema.
"""

import os
import sys
import pytest

ANUBIS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ANUBIS_DIR not in sys.path:
    sys.path.insert(0, ANUBIS_DIR)

from actions.vitals import collect_system_vitals
from main import TOOL_DECLARATIONS

def test_collect_system_vitals():
    data = collect_system_vitals(focus="all")
    assert isinstance(data, dict)
    assert "speech_summary" in data
    assert len(data["speech_summary"]) > 10
    assert "cpu" in data
    assert "memory" in data
    assert "gpu" in data
    assert data["cpu"]["percent"] >= 0.0
    assert data["memory"]["percent"] >= 0.0


def test_tool_declarations_includes_vitals():
    tool_names = [t["name"] for t in TOOL_DECLARATIONS]
    assert "get_system_vitals" in tool_names
    vitals_tool = next(t for t in TOOL_DECLARATIONS if t["name"] == "get_system_vitals")
    assert "parameters" in vitals_tool
    assert "focus" in vitals_tool["parameters"]["properties"]


@pytest.mark.asyncio
async def test_jarvis_live_execute_vitals_tool():
    from unittest.mock import MagicMock
    from main import JarvisLive

    agent = JarvisLive.__new__(JarvisLive)
    agent.ui = MagicMock()

    class MockFC:
        id = "vitals-call-1"
        name = "get_system_vitals"
        args = {"focus": "all"}

    res = await agent._execute_tool(MockFC())
    resp_map = dict(res.response)
    summary = resp_map.get("result", "")
    assert ("CPU" in summary or "nominal" in summary or "vitals" in summary)
    assert agent.ui.show_vitals_toast.called
    toast_arg = agent.ui.show_vitals_toast.call_args[0][0]
    assert "cpu" in toast_arg
    assert "memory" in toast_arg

