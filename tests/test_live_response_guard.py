import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google.genai import live as live_module


class FakeApiClient:
    vertexai = False

    class _HttpOptions:
        api_version = "v1beta"
        headers = {}

    _http_options = _HttpOptions()


class FakeWebsocket:
    def __init__(self, responses):
        self._responses = responses
        self._index = 0

    async def recv(self, decode=False):
        if self._index >= len(self._responses):
            raise RuntimeError("no more responses")
        payload = self._responses[self._index]
        self._index += 1
        return payload

    async def send(self, payload):
        return None

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_receive_skips_malformed_server_payloads():
    session = live_module.AsyncSession(
        api_client=FakeApiClient(),
        websocket=FakeWebsocket([
            b'{"serverContent": []}',
            b'{"serverContent": {"turnComplete": true, "modelTurn": {"parts": [{"text": "ok"}]}}}',
        ]),
    )

    messages = []
    async for message in session.receive():
        messages.append(message)

    assert len(messages) == 2
    assert messages[0].text is None
    assert messages[1].text == "ok"
