import json
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "api_keys.json"
_ENV_PATH = Path(__file__).parent.parent / ".env"

if _ENV_PATH.exists():
    try:
        for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))
    except Exception:
        pass

DEFAULT_GEMINI_MODEL      = "gemini-3.8-flash"
DEFAULT_GEMINI_LITE_MODEL = "gemini-3.5-flash-lite"

# Use a dedicated Live API endpoint for bidiGenerateContent:
DEFAULT_GEMINI_LIVE_MODEL = "gemini-3.1-flash-live-preview"

def get_config() -> dict:
    if _CONFIG_PATH.exists():
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    return get_config().get("os_system", "windows").lower()

def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"


def get_gemini_model(default: str | None = None) -> str:
    return os.getenv("GEMINI_MODEL", default or DEFAULT_GEMINI_MODEL)


def get_gemini_lite_model(default: str | None = None) -> str:
    return os.getenv("GEMINI_LITE_MODEL", default or DEFAULT_GEMINI_LITE_MODEL)


def get_gemini_live_model(default: str | None = None) -> str:
    return os.getenv("GEMINI_LIVE_MODEL", default or DEFAULT_GEMINI_LIVE_MODEL)