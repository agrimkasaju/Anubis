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
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks",
]

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")
TOKEN_FILE = os.path.join(CONFIG_DIR, "google_token.json")
SERVICE_ACCOUNT_FILE = os.path.join(CONFIG_DIR, "service_account.json")
FALLBACK_TOKEN_FILES = [
    os.path.expanduser("~/.config/waybar-ycal/token.json"),
    os.path.expanduser("~/.cache/waybar-ycal/token.json"),
]
CREDENTIALS_CANDIDATES = [
    os.path.join(CONFIG_DIR, "credentials.json"),
    os.path.expanduser("~/.config/waybar-ycal/credentials.json"),
]


def get_service_account_credentials() -> Optional[service_account.Credentials]:
    """Loads service account credentials if config/service_account.json exists."""
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        try:
            return service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        except Exception as e:
            print(f"[GoogleAuth] Failed loading service account credentials: {e}")
    return None


def get_target_calendar_id() -> str:
    """Returns the target Google Calendar ID (user email for service accounts or 'primary')."""
    if os.environ.get("GOOGLE_CALENDAR_ID"):
        return os.environ["GOOGLE_CALENDAR_ID"].strip()

    account_file = os.path.expanduser("~/.config/waybar-ycal/account.txt")
    if os.path.exists(account_file):
        try:
            with open(account_file, "r", encoding="utf-8") as f:
                acc = f.read().strip()
                if acc and "@" in acc:
                    return acc
        except Exception:
            pass

    return "kasajuagrim@gmail.com"


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
    if not interactive:
        for fallback_file in FALLBACK_TOKEN_FILES:
            if os.path.exists(fallback_file):
                try:
                    fallback_creds = Credentials.from_authorized_user_file(fallback_file)
                    if fallback_creds and fallback_creds.valid:
                        return fallback_creds
                    if fallback_creds and fallback_creds.expired and fallback_creds.refresh_token:
                        fallback_creds.refresh(Request())
                        return fallback_creds
                except Exception as e:
                    print(f"[GoogleAuth] Fallback token check ({fallback_file}) failed: {e}")

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
    """
    Returns Google Calendar v3 service resource or None.
    Prioritizes permanent Service Account if configured, falling back to OAuth.
    """
    sa_creds = get_service_account_credentials()
    if sa_creds:
        try:
            return build("calendar", "v3", credentials=sa_creds, cache_discovery=False)
        except Exception as e:
            print(f"[GoogleAuth] Failed to build calendar service with service account: {e}")

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
    sa_creds = get_service_account_credentials()
    if sa_creds:
        try:
            return build("tasks", "v1", credentials=sa_creds, cache_discovery=False)
        except Exception as e:
            print(f"[GoogleAuth] Failed to build tasks service with service account: {e}")

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
