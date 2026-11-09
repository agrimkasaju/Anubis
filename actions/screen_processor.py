import io
import json
import os
import sys
import time
from pathlib import Path
import shutil
import subprocess
import tempfile
import cv2
import mss
from PIL import Image
from google import genai
from google.genai import types

from config import get_gemini_model, get_gemini_lite_model

def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

IMG_MAX_W = 1024
IMG_MAX_H = 768
JPEG_Q    = 75


def _get_api_key() -> str:
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            keys = json.load(f)
        return keys.get("gemini_api_key", "")
    except Exception:
        return ""

def _capture_screenshot() -> bytes:
    # 1. Native Wayland / COSMIC capture (avoids blank Xwayland root window)
    if shutil.which("cosmic-screenshot"):
        try:
            with tempfile.TemporaryDirectory() as td:
                res = subprocess.run(
                    ["cosmic-screenshot", "--interactive=false", "--notify=false", "--save-dir", td],
                    capture_output=True, text=True, timeout=5
                )
                out_file = res.stdout.strip()
                if os.path.exists(out_file):
                    with Image.open(out_file) as img:
                        img = img.convert("RGB")
                        img.thumbnail([IMG_MAX_W, IMG_MAX_H], Image.BILINEAR)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=JPEG_Q)
                        return buf.getvalue()
        except Exception as e:
            print(f"[ScreenProcess] ⚠️ cosmic-screenshot failed: {e}")

    if shutil.which("grim"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png") as tf:
                subprocess.run(["grim", tf.name], check=True, timeout=5)
                with Image.open(tf.name) as img:
                    img = img.convert("RGB")
                    img.thumbnail([IMG_MAX_W, IMG_MAX_H], Image.BILINEAR)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=JPEG_Q)
                    return buf.getvalue()
        except Exception as e:
            print(f"[ScreenProcess] ⚠️ grim failed: {e}")

    # 2. Fallback to mss (Windows, macOS, X11)
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.thumbnail([IMG_MAX_W, IMG_MAX_H], Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_Q)
        return buf.getvalue()


def _capture_camera() -> bytes:
    cap = cv2.VideoCapture(0)
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()
    if not ret or frame is None:
        raise RuntimeError("Could not capture camera frame.")
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    img.thumbnail([IMG_MAX_W, IMG_MAX_H], Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_Q)
    return buf.getvalue()


def screen_process(
    parameters: dict = None,
    response: str | None = None,
    player=None,
    session_memory=None,
) -> str:
    user_text = (parameters or {}).get("text") or (parameters or {}).get("user_text", "")
    prompt = user_text.strip() if user_text else "Describe concisely what is currently on the screen."
    angle = (parameters or {}).get("angle", "screen").lower().strip()

    try:
        if angle == "camera":
            image_bytes = _capture_camera()
        else:
            image_bytes = _capture_screenshot()
    except Exception as e:
        print(f"[ScreenProcess] ❌ Capture error: {e}")
        return f"Failed to capture {angle}: {e}"

    models = [get_gemini_model(), get_gemini_lite_model()]
    client = genai.Client(api_key=_get_api_key())
    last_err = None

    for model in models:
        try:
            res = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt
                ]
            )
            desc = res.text.strip()
            print(f"[ScreenProcess] 🖥️ Screen analysis ({model}): {desc}")
            if player and hasattr(player, "write_log"):
                player.write_log(f"Vision: {desc}")
            return desc
        except Exception as e:
            last_err = e
            print(f"[ScreenProcess] ⚠️ {model} failed ({e}), attempting fallback...")
            time.sleep(0.5)

    print(f"[ScreenProcess] ❌ All models failed: {last_err}")
    return f"Error analyzing {angle}: {last_err}"


def warmup_session(player=None):
    pass
