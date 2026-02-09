"""Template matching using OpenCV — finds UI elements by image."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

TEMPLATES_DIR = Path(__file__).parent.parent / "old_code" / "templates"

# Pre-load templates as grayscale
_cache: dict[str, np.ndarray] = {}


def _load(name: str) -> np.ndarray:
    """Load a template image (grayscale, cached)."""
    if name not in _cache:
        path = TEMPLATES_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"Failed to read template: {path}")
        _cache[name] = img
    return _cache[name]


def find_template(
    screenshot_bgr: np.ndarray,
    template_name: str,
    threshold: float = 0.8,
) -> tuple[int, int] | None:
    """Find a template in a screenshot. Returns center (x, y) or None.

    Args:
        screenshot_bgr: Screenshot as BGR numpy array (from mss/PIL).
        template_name: Filename in templates/ directory.
        threshold: Minimum match confidence (0-1).

    Returns:
        (x, y) center of best match, or None if below threshold.
    """
    gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
    tmpl = _load(template_name)
    th, tw = tmpl.shape[:2]

    result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < threshold:
        return None

    # max_loc is top-left corner, return center
    cx = max_loc[0] + tw // 2
    cy = max_loc[1] + th // 2
    return cx, cy


def find_all_templates(
    screenshot_bgr: np.ndarray,
    template_name: str,
    threshold: float = 0.8,
) -> list[tuple[int, int, float]]:
    """Find ALL occurrences of a template. Returns list of (x, y, confidence)."""
    gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
    tmpl = _load(template_name)
    th, tw = tmpl.shape[:2]

    result = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)

    matches = []
    for pt_y, pt_x in zip(*locations):
        cx = pt_x + tw // 2
        cy = pt_y + th // 2
        conf = result[pt_y, pt_x]
        matches.append((cx, cy, float(conf)))

    # Deduplicate nearby matches (within 20px)
    if not matches:
        return []

    matches.sort(key=lambda m: -m[2])  # best confidence first
    filtered = []
    for m in matches:
        if all(abs(m[0] - f[0]) > 20 or abs(m[1] - f[1]) > 20 for f in filtered):
            filtered.append(m)

    return filtered


def find_button_in_row(
    screenshot_bgr: np.ndarray,
    row_template: str,
    row_threshold: float = 0.8,
    button_offset_x: int = 555,
) -> tuple[int, int] | None:
    """Find a row icon template, then return the Download button position.

    Locates the row by its icon (MP3/RAW/LRC/VIDEO), then returns
    coordinates offset to the right where the Download button sits.
    """
    gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)
    row_tmpl = _load(row_template)
    rh, rw = row_tmpl.shape[:2]

    result = cv2.matchTemplate(gray, row_tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < row_threshold:
        return None

    # Icon center
    icon_cx = max_loc[0] + rw // 2
    icon_cy = max_loc[1] + rh // 2

    # Download button is button_offset_x pixels to the right of the icon center
    btn_x = icon_cx + button_offset_x
    btn_y = icon_cy
    return btn_x, btn_y
