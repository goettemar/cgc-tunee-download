"""Screenshot helper — Wayland-compatible with mss fallback."""

import base64
import io
import os
import subprocess
import tempfile

from PIL import Image

# Which mss monitor index to capture (1-based; set via set_monitor())
_monitor_idx: int = 1

# Detect Wayland session
_is_wayland: bool = os.environ.get("XDG_SESSION_TYPE") == "wayland"


def set_monitor(idx: int) -> None:
    """Set the monitor index to capture (1-based, matching mss numbering)."""
    global _monitor_idx
    _monitor_idx = idx


def list_monitors() -> list[dict]:
    """Return all monitors as dicts with left/top/width/height."""
    if _is_wayland:
        # Under Wayland we only reliably know the primary monitor via xrandr
        w, h = get_screen_size()
        return [{"left": 0, "top": 0, "width": w, "height": h},
                {"left": 0, "top": 0, "width": w, "height": h}]
    import mss
    with mss.mss() as sct:
        return list(sct.monitors)


def get_monitor_offset() -> tuple[int, int]:
    """Return (left, top) pixel offset of the selected monitor in the virtual desktop."""
    if _is_wayland:
        return 0, 0
    import mss
    with mss.mss() as sct:
        mon = sct.monitors[_monitor_idx]
        return mon["left"], mon["top"]


def get_screen_size() -> tuple[int, int]:
    """Return (width, height) of the selected monitor."""
    if _is_wayland:
        return _get_screen_size_wayland()
    import mss
    with mss.mss() as sct:
        mon = sct.monitors[_monitor_idx]
        return mon["width"], mon["height"]


def _get_screen_size_wayland() -> tuple[int, int]:
    """Get screen size under Wayland via xrandr."""
    try:
        out = subprocess.check_output(["xrandr", "--current"], text=True, timeout=5)
        for line in out.splitlines():
            if " connected" in line and "+" in line:
                # e.g. "Virtual-1 connected primary 1920x1080+0+0 ..."
                for part in line.split():
                    if "x" in part and "+" in part:
                        res = part.split("+")[0]
                        w, h = res.split("x")
                        return int(w), int(h)
    except Exception:
        pass
    return 1920, 1080


def _capture_wayland() -> Image.Image:
    """Capture the screen under Wayland using gnome-screenshot or grim."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        # Try gnome-screenshot first (most reliable on GNOME/Zorin)
        r = subprocess.run(
            ["gnome-screenshot", "-f", tmp_path],
            capture_output=True, timeout=10,
        )
        if r.returncode != 0:
            # Fallback to grim (wlroots-based compositors)
            subprocess.run(
                ["grim", tmp_path],
                capture_output=True, timeout=10, check=True,
            )
        return Image.open(tmp_path).convert("RGB")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# Max image dimension sent to VLM.
# UI-TARS coordinates will be in this resized space.
# Higher res = better for small UI elements, but slower inference.
MAX_VLM_WIDTH = 1920
MAX_VLM_HEIGHT = 1080


def take_screenshot() -> tuple[str, tuple[int, int]]:
    """Capture the selected monitor, resize for VLM, return as base64-encoded PNG.

    Returns:
        (base64_png, (width, height)) — the encoded image and its pixel dimensions
        (after resizing).
    """
    if _is_wayland:
        img = _capture_wayland()
    else:
        import mss
        with mss.mss() as sct:
            shot = sct.grab(sct.monitors[_monitor_idx])
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    # Resize to fit VLM input while keeping aspect ratio
    img.thumbnail((MAX_VLM_WIDTH, MAX_VLM_HEIGHT), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode(), img.size


def take_screenshot_bgr():
    """Capture the selected monitor as a BGR numpy array (for OpenCV template matching).

    Returns:
        numpy.ndarray in BGR format, at native monitor resolution (no resize).
    """
    import numpy as np

    if _is_wayland:
        img = _capture_wayland()
        arr = np.array(img)
        return arr[:, :, ::-1].copy()  # RGB → BGR

    import mss
    with mss.mss() as sct:
        shot = sct.grab(sct.monitors[_monitor_idx])
        # mss returns BGRA; convert to BGR for OpenCV
        img = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        return img[:, :, :3].copy()  # drop alpha, keep BGR


def get_image_size(b64_png: str) -> tuple[int, int]:
    """Get (width, height) of a base64-encoded PNG without fully decoding it."""
    data = base64.b64decode(b64_png)
    img = Image.open(io.BytesIO(data))
    return img.size
