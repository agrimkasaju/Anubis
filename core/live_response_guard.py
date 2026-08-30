import logging
from pydantic import ValidationError

async def live_response_guard(session):
    """
    Wraps a Gemini Live session's receive generator to safely handle
    malformed server payloads that would otherwise trigger ValidationErrors.
    """
    while True:
        try:
            async for response in session.receive():
                yield response
            break  # End of stream
        except ValidationError as e:
            # Skip malformed payloads and continue receiving
            logging.warning(f"[LiveResponseGuard] Filtered malformed server payload: {e}")
            continue
        except Exception as e:
            logging.error(f"[LiveResponseGuard] Unexpected error: {e}")
            raise
