"""Screenshot helper using mss."""

import base64
import io

import mss
from PIL import Image


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the primary monitor."""
    with mss.mss() as sct:
        mon = sct.monitors[1]  # primary monitor (0 = all monitors combined)
        return mon["width"], mon["height"]


def take_screenshot() -> str:
    """Capture the primary monitor and return as base64-encoded PNG."""
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
