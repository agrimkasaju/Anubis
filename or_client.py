import json
import logging
import sys
from pathlib import Path
from typing import Optional
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("groq_client")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR     = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"

def _load_api_key() -> str:
    try:
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("groq_api_key", "").strip()
        if not key:
            raise ValueError("groq_api_key is empty in api_keys.json")
        return key
    except Exception as e:
        raise RuntimeError(f"Failed to load Groq API key: {e}")

# Fast open-source model hosted on Groq LPU hardware
DEFAULT_MODEL = "qwen/qwen3.8-27b"
FALLBACK_MODEL = "openai/gpt-oss-120b"

class GroqClient:
    """Small wrapper around Groq-hosted text models."""

    def __init__(self) -> None:
        self.api_key = _load_api_key()
        self.client = Groq(api_key=self.api_key)

    def chat(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=model or DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[Groq Client] Error during chat call: {e}")
            return ""

    def chat_json(
        self,
        prompt: str,
        system: str = "Return ONLY valid JSON.",
        model: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> dict:
        try:
            resp = self.client.chat.completions.create(
                model=model or DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                temperature=0.2
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            logger.error(f"[Groq Client] JSON error: {e}")
            return {}

    def multi_turn(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=model or DEFAULT_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[Groq Client] Multi-turn error: {e}")
            return ""

    def vision(self, *args, **kwargs) -> str:
        raise NotImplementedError("Vision is not configured for the Groq client; use screen_process.")

    def vision_from_file(self, *args, **kwargs) -> str:
        raise NotImplementedError("Vision is not configured for the Groq client; use screen_process.")

    def available_models(self) -> dict:
        return {
            "text_models": [DEFAULT_MODEL],
            "vision_models": [],
            "rate_limited": [],
            "total_text": 1,
            "total_vision": 0,
        }

client = GroqClient()

if __name__ == "__main__":
    print("=" * 55)
    print("  Anubis — Groq Client Self-Test")
    print("=" * 55)

    print("\n[TEST 1] Basic chat...")
    reply = client.chat("Introduce yourself in one sentence.")
    if reply:
        print(f"  Response : {reply}")
        print(f"  Status   : PASS ✓")
    else:
        print(f"  Status   : FAIL ✗ — No response received from Groq.")
