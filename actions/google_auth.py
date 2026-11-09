"""
Google OAuth 2.0 authentication helper for Google Calendar and Google Tasks in Anubis.
"""

import os
import sys
import warnings
from typing import Optional

# Suppress minor API version deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/tasks",
]

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
TOKEN_FILE = os.path.join(CONFIG_DIR, "google_token.json")
FALLBACK_TOKEN_FILE = os.path.expanduser("~/.cache/waybar-ycal/token.json")
CREDENTIALS_CANDIDATES = [
    os.path.join(CONFIG_DIR, "credentials.json"),
    os.path.expanduser("~/.config/waybar-ycal/credentials.json"),
]


def get_credentials_path() -> Optional[str]:
    """Finds an existing client secrets credentials.json file."""
    for path in CREDENTIALS_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def get_credentials(interactive: bool = False) -> Optional[Credentials]:
    """
    Retrieves or refreshes OAuth2 credentials.
    If interactive is True, opens the browser flow when token is missing or invalid.
    """
    creds = None
    # 1. Primary token file
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"[GoogleAuth] Failed loading cached token: {e}")
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            return creds
        except Exception as e:
            print(f"[GoogleAuth] Token refresh failed: {e}")
            creds = None

    # 2. Check fallback token from waybar-ycal if not in interactive mode
    if not interactive and os.path.exists(FALLBACK_TOKEN_FILE):
        try:
            fallback_creds = Credentials.from_authorized_user_file(FALLBACK_TOKEN_FILE)
            if fallback_creds and fallback_creds.valid:
                return fallback_creds
            if fallback_creds and fallback_creds.expired and fallback_creds.refresh_token:
                fallback_creds.refresh(Request())
                return fallback_creds
        except Exception as e:
            print(f"[GoogleAuth] Fallback token check failed: {e}")

    if interactive:
        cred_path = get_credentials_path()
        if not cred_path:
            print("[GoogleAuth] No client credentials.json found.")
            return None

        try:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
            _save_token(creds)
            return creds
        except Exception as e:
            print(f"[GoogleAuth] Interactive OAuth failed: {e}")
            return None

    return None


def _save_token(creds: Credentials) -> None:
    """Saves credentials JSON securely with chmod 0600."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass


def get_calendar_service(interactive: bool = False) -> Optional[Resource]:
    """Returns Google Calendar v3 service resource or None."""
    creds = get_credentials(interactive=interactive)
    if not creds:
        return None
    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"[GoogleAuth] Failed to build calendar service: {e}")
        return None


def get_tasks_service(interactive: bool = False) -> Optional[Resource]:
    """Returns Google Tasks v1 service resource or None."""
    creds = get_credentials(interactive=interactive)
    if not creds:
        return None
    try:
        return build("tasks", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        print(f"[GoogleAuth] Failed to build tasks service: {e}")
        return None


if __name__ == "__main__":
    print("[GoogleAuth] Running interactive authentication...")
    c = get_credentials(interactive=True)
    if c and c.valid:
        print(f"[GoogleAuth] Successfully authenticated! Token saved to {TOKEN_FILE}")
    else:
        print("[GoogleAuth] Authentication failed or was aborted.")
        sys.exit(1)
