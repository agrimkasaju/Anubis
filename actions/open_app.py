# actions/open_app.py
# MARK XXV — Cross-Platform App Launcher

import time
import subprocess
import platform
import shutil

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_APP_ALIASES = {
    "whatsapp":           {"Windows": "WhatsApp",               "Darwin": "WhatsApp",            "Linux": "whatsapp"},
    "chrome":             {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                 "Darwin": "Google Chrome",       "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                "Darwin": "Firefox",             "Linux": "firefox"},
    "spotify":            {"Windows": "Spotify",                "Darwin": "Spotify",             "Linux": "spotify"},
    "vscode":             {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "visual studio code": {"Windows": "code",                   "Darwin": "Visual Studio Code",  "Linux": "code"},
    "discord":            {"Windows": "Discord",                "Darwin": "Discord",             "Linux": "discord"},
    "telegram":           {"Windows": "Telegram",               "Darwin": "Telegram",            "Linux": "telegram"},
    "instagram":          {"Windows": "Instagram",              "Darwin": "Instagram",           "Linux": "instagram"},
    "tiktok":             {"Windows": "TikTok",                 "Darwin": "TikTok",              "Linux": "tiktok"},
    "notepad":            {"Windows": "notepad.exe",            "Darwin": "TextEdit",            "Linux": "gedit"},
    "calculator":         {"Windows": "calc.exe",               "Darwin": "Calculator",          "Linux": "gnome-calculator"},
    "terminal":           {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "cosmic-term"},
    "cosmic terminal":    {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "cosmic-term"},
    "cosmic-terminal":   {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "cosmic-term"},
    "cmd":                {"Windows": "cmd.exe",                "Darwin": "Terminal",            "Linux": "bash"},
    "explorer":           {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "cosmic-files"},
    "file explorer":      {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "cosmic-files"},
    "files":              {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "cosmic-files"},
    "cosmic files":       {"Windows": "explorer.exe",           "Darwin": "Finder",              "Linux": "cosmic-files"},
    "paint":              {"Windows": "mspaint.exe",            "Darwin": "Preview",             "Linux": "gimp"},
    "word":               {"Windows": "winword",                "Darwin": "Microsoft Word",      "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                  "Darwin": "Microsoft Excel",     "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",               "Darwin": "Microsoft PowerPoint","Linux": "libreoffice --impress"},
    "vlc":                {"Windows": "vlc",                    "Darwin": "VLC",                 "Linux": "vlc"},
    "zoom":               {"Windows": "Zoom",                   "Darwin": "zoom.us",             "Linux": "zoom"},
    "slack":              {"Windows": "Slack",                  "Darwin": "Slack",               "Linux": "slack"},
    "steam":              {"Windows": "steam",                  "Darwin": "Steam",               "Linux": "steam"},
    "task manager":       {"Windows": "taskmgr.exe",            "Darwin": "Activity Monitor",    "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",           "Darwin": "System Preferences",  "Linux": "cosmic-settings"},
    "cosmic settings":    {"Windows": "ms-settings:",           "Darwin": "System Preferences",  "Linux": "cosmic-settings"},
    "cosmic store":       {"Windows": "ms-windows-store:",      "Darwin": "App Store",           "Linux": "cosmic-store"},
    "cosmic edit":        {"Windows": "notepad.exe",            "Darwin": "TextEdit",            "Linux": "cosmic-edit"},
    "powershell":         {"Windows": "powershell.exe",         "Darwin": "Terminal",            "Linux": "bash"},
    "edge":               {"Windows": "msedge",                 "Darwin": "Microsoft Edge",      "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                  "Darwin": "Brave Browser",       "Linux": "brave-browser"},
    "obsidian":           {"Windows": "Obsidian",               "Darwin": "Obsidian",            "Linux": "obsidian"},
    "notion":             {"Windows": "Notion",                 "Darwin": "Notion",              "Linux": "notion"},
    "blender":            {"Windows": "blender",                "Darwin": "Blender",             "Linux": "blender"},
    "capcut":             {"Windows": "CapCut",                 "Darwin": "CapCut",              "Linux": "capcut"},
    "postman":            {"Windows": "Postman",                "Darwin": "Postman",             "Linux": "postman"},
    "figma":              {"Windows": "Figma",                  "Darwin": "Figma",               "Linux": "figma"},
}


def _normalize(raw: str) -> str:
    system = platform.system()
    key    = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(system, raw)
    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(system, raw)
    return raw


def _is_running(app_name: str) -> bool:
    if not _PSUTIL:
        return True
    app_lower = app_name.lower().replace(" ", "").replace(".exe", "")
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                proc_name = proc.info["name"].lower().replace(" ", "").replace(".exe", "")
                if app_lower in proc_name or proc_name in app_lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


def _launch_windows(app_name: str) -> bool:
    try:
        import pyautogui
        pyautogui.PAUSE = 0.1
        pyautogui.press("win")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(3.0)
        return True
    except Exception as e:
        print(f"[open_app] ⚠️ Windows launch failed: {e}")
        return False

def _launch_macos(app_name: str) -> bool:
    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(["open", "-a", f"{app_name}.app"], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] ⚠️ macOS Spotlight failed: {e}")
        return False


def _launch_linux(app_name: str) -> bool:
    """Unified Linux application launcher supporting COSMIC, GNOME, Flatpak, and binaries."""
    import glob
    import os
    raw_query = app_name.strip()
    query_clean = raw_query.lower()

    # 1. Canonical Desktop Fallbacks
    CANONICAL_FALLBACKS = {
        "terminal": ["cosmic-term", "gnome-terminal", "alacritty", "kitty", "konsole", "xterm"],
        "settings": ["cosmic-settings", "gnome-control-center", "systemsettings"],
        "files": ["cosmic-files", "nautilus", "dolphin", "thunar"],
        "file explorer": ["cosmic-files", "nautilus", "dolphin"],
        "explorer": ["cosmic-files", "nautilus", "dolphin"],
        "editor": ["cosmic-edit", "gedit", "kate", "code"],
        "notepad": ["cosmic-edit", "gedit", "kate"],
        "store": ["cosmic-store", "gnome-software"],
        "app store": ["cosmic-store", "gnome-software"],
    }
    if query_clean in CANONICAL_FALLBACKS:
        for candidate in CANONICAL_FALLBACKS[query_clean]:
            bin_path = shutil.which(candidate)
            if bin_path:
                try:
                    subprocess.Popen([bin_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                    time.sleep(0.5)
                    return True
                except Exception:
                    pass

    # 2. Direct binary lookup in PATH
    candidates = [
        raw_query,
        query_clean,
        query_clean.replace(" ", "-"),
        query_clean.replace(" ", "_"),
        query_clean.replace("cosmic-terminal", "cosmic-term"),
        query_clean.replace("cosmic terminal", "cosmic-term"),
    ]
    for c in candidates:
        bin_path = shutil.which(c)
        if bin_path:
            try:
                subprocess.Popen([bin_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                time.sleep(0.5)
                return True
            except Exception:
                pass

    # 3. Dynamic .desktop file search & launch
    desktop_dirs = [
        "/usr/share/applications",
        os.path.expanduser("~/.local/share/applications"),
        "/var/lib/flatpak/exports/share/applications",
        os.path.expanduser("~/.local/share/flatpak/exports/share/applications")
    ]
    matched_desktop_id = None
    matched_desktop_file = None

    for d in desktop_dirs:
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "*.desktop")):
            desktop_id = os.path.basename(f)[:-8]  # strip .desktop
            try:
                content = open(f, errors="ignore").read()
                app_title = ""
                for line in content.splitlines():
                    if line.startswith("Name=") and not app_title:
                        app_title = line.split("=", 1)[1].strip()
                        break
                if app_title.lower() == query_clean:
                    matched_desktop_id = desktop_id
                    matched_desktop_file = f
                    break
                if query_clean in app_title.lower() or query_clean in desktop_id.lower():
                    matched_desktop_id = desktop_id
                    matched_desktop_file = f
            except Exception:
                continue
        if matched_desktop_id:
            break

    # Launch matched desktop entry
    if matched_desktop_id:
        if shutil.which("gtk-launch"):
            res = subprocess.run(["gtk-launch", matched_desktop_id], capture_output=True, timeout=5)
            if res.returncode == 0:
                time.sleep(0.5)
                return True

        if shutil.which("gio") and matched_desktop_file:
            res = subprocess.run(["gio", "launch", matched_desktop_file], capture_output=True, timeout=5)
            if res.returncode == 0:
                time.sleep(0.5)
                return True

        # Extract Exec command from desktop file
        if matched_desktop_file:
            try:
                content = open(matched_desktop_file, errors="ignore").read()
                for line in content.splitlines():
                    if line.startswith("Exec="):
                        exec_cmd = line.split("=", 1)[1].strip()
                        # Clean out desktop exec format codes (%u, %U, %f, %F)
                        clean_cmd = [part for part in exec_cmd.split() if not part.startswith("%")]
                        if clean_cmd and shutil.which(clean_cmd[0]):
                            subprocess.Popen(clean_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                            time.sleep(0.5)
                            return True
            except Exception:
                pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}


def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "Please specify which application to open, sir."

    system   = platform.system()
    launcher = _OS_LAUNCHERS.get(system)

    if launcher is None:
        return f"Unsupported OS: {system}"

    normalized = _normalize(app_name)
    print(f"[open_app] 🚀 Launching: {app_name} → {normalized} ({system})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        success = launcher(normalized)

        if success:
            return f"Opened {app_name} successfully, sir."

        if normalized != app_name:
            success = launcher(app_name)
            if success:
                return f"Opened {app_name} successfully, sir."

        return (
            f"I tried to open {app_name}, sir, but couldn't confirm it launched. "
            f"It may still be loading or might not be installed."
        )

    except Exception as e:
        print(f"[open_app] ❌ {e}")
        return f"Failed to open {app_name}, sir: {e}"