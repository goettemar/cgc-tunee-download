"""Screenshot helper using mss — multi-monitor aware."""

import base64
import io

import mss
from PIL import Image

# Which mss monitor index to capture (1-based; set via set_monitor())
_monitor_idx: int = 1


def set_monitor(idx: int) -> None:
    """Set the monitor index to capture (1-based, matching mss numbering)."""
    global _monitor_idx
    _monitor_idx = idx


def list_monitors() -> list[dict]:
    """Return all monitors as dicts with left/top/width/height."""
    with mss.mss() as sct:
        return list(sct.monitors)


def get_monitor_offset() -> tuple[int, int]:
    """Return (left, top) pixel offset of the selected monitor in the virtual desktop."""
    with mss.mss() as sct:
        mon = sct.monitors[_monitor_idx]
        return mon["left"], mon["top"]


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the selected monitor."""
    with mss.mss() as sct:
        mon = sct.monitors[_monitor_idx]
        return mon["width"], mon["height"]


# Max image dimension sent to VLM — smaller = faster + more consistent.
# UI-TARS coordinates will be in this resized space.
MAX_VLM_WIDTH = 1280
MAX_VLM_HEIGHT = 720


def take_screenshot() -> tuple[str, tuple[int, int]]:
    """Capture the selected monitor, resize for VLM, return as base64-encoded PNG.

    Returns:
        (base64_png, (width, height)) — the encoded image and its pixel dimensions
        (after resizing).
    """
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[_monitor_idx])
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    # Resize to fit VLM input while keeping aspect ratio
    img.thumbnail((MAX_VLM_WIDTH, MAX_VLM_HEIGHT), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode(), img.size


def get_image_size(b64_png: str) -> tuple[int, int]:
    """Get (width, height) of a base64-encoded PNG without fully decoding it."""
    data = base64.b64decode(b64_png)
    img = Image.open(io.BytesIO(data))
    return img.size
