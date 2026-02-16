"""Screenshot helper — Wayland-compatible with XDG Portal, gnome-screenshot fallback, and mss for X11."""

import base64
import io
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

# Which mss monitor index to capture (1-based; set via set_monitor())
_monitor_idx: int = 1

# Detect Wayland session
_is_wayland: bool = os.environ.get("XDG_SESSION_TYPE") == "wayland"

# Persistent portal helper process
_helper_proc: subprocess.Popen | None = None
_HELPER_SCRIPT = str(Path(__file__).parent / "_portal_helper.py")


def set_monitor(idx: int) -> None:
    """Set the monitor index to capture (1-based, matching mss numbering)."""
    global _monitor_idx
    _monitor_idx = idx


def list_monitors() -> list[dict]:
    """Return all monitors as dicts with left/top/width/height."""
    if _is_wayland:
        w, h = get_screen_size()
        return [
            {"left": 0, "top": 0, "width": w, "height": h},
            {"left": 0, "top": 0, "width": w, "height": h},
        ]
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
                for part in line.split():
                    if "x" in part and "+" in part:
                        res = part.split("+")[0]
                        w, h = res.split("x")
                        return int(w), int(h)
    except Exception:
        pass
    return 1920, 1080


# ── Wayland capture backends ──────────────────────────────────────────


def _get_helper() -> subprocess.Popen | None:
    """Get or start the persistent portal helper process."""
    global _helper_proc
    if _helper_proc is not None and _helper_proc.poll() is None:
        return _helper_proc

    try:
        _helper_proc = subprocess.Popen(
            ["/usr/bin/python3", _HELPER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # Wait for READY signal
        ready = _helper_proc.stdout.readline().strip()
        if ready == "READY":
            return _helper_proc
        _helper_proc.kill()
        _helper_proc = None
    except Exception:
        _helper_proc = None

    return None


def _capture_portal() -> Image.Image | None:
    """Capture via XDG Desktop Portal using persistent helper process (~1s)."""
    helper = _get_helper()
    if helper is None:
        return None

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        helper.stdin.write(tmp_path + "\n")
        helper.stdin.flush()
        response = helper.stdout.readline().strip()
        if (
            response == "OK"
            and os.path.exists(tmp_path)
            and os.path.getsize(tmp_path) > 0
        ):
            return Image.open(tmp_path).convert("RGB")
    except (BrokenPipeError, OSError):
        # Helper died, reset for next call
        global _helper_proc
        _helper_proc = None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return None


def _capture_gnome_screenshot() -> Image.Image:
    """Capture via gnome-screenshot CLI (~2.4s, fallback)."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            ["gnome-screenshot", "-f", tmp_path],
            capture_output=True,
            timeout=10,
        )
        return Image.open(tmp_path).convert("RGB")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _capture_wayland() -> Image.Image:
    """Capture the screen under Wayland. Tries fast portal first, then gnome-screenshot."""
    img = _capture_portal()
    if img is not None:
        return img
    return _capture_gnome_screenshot()


# ── Public API ────────────────────────────────────────────────────────

# Max image dimension sent to VLM.
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
        img = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(
            shot.height, shot.width, 4
        )
        return img[:, :, :3].copy()  # drop alpha, keep BGR


def get_image_size(b64_png: str) -> tuple[int, int]:
    """Get (width, height) of a base64-encoded PNG without fully decoding it."""
    data = base64.b64decode(b64_png)
    img = Image.open(io.BytesIO(data))
    return img.size
