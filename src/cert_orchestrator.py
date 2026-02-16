"""Certificate download orchestrator — downloads PDF certificates for songs.

Completely separate from the song download flow in orchestrator.py.
Imports shared helpers from orchestrator.py but does not modify it.

Workflow per song:
  1. Hover song row -> play button appears
  2. Click play -> player modal opens
  3. Click three-dots menu in player
  4. Click "Copyright certificate" menu item
  5. Click download button in certificate modal
  6. Wait for PDF -> move to song folder
  7. Press Escape to close modals
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import time

import pyautogui

from .events import OrchestratorEvents, PrintEvents, C_DONE, C_ERR, C_WARN, C_RESET
from .orchestrator import (
    _click_at,
    TUNEE_DIR,
    DL_DIR,
    SONG_EXTENSIONS,
)
from .screenshot import take_screenshot_bgr, get_monitor_offset, get_screen_size
from .scraper import get_song_list
from .template_match import find_all_templates, find_template

# Timing
CERT_CLICK_DELAY = 1.5
CERT_WAIT_MAX = 30  # max seconds to wait for PDF download
BETWEEN_CERTS_DELAY = 2
MAX_RETRIES = 3


# ── Helpers ──────────────────────────────────────────────────────────


def find_folders_needing_certs() -> dict[int, str]:
    """Scan ~/Downloads/tunee/ and find folders that have songs but no PDF.

    Returns:
        dict mapping folder number (1-based) -> folder path
    """
    if not os.path.isdir(TUNEE_DIR):
        return {}

    result = {}
    for entry in sorted(os.listdir(TUNEE_DIR)):
        folder_path = os.path.join(TUNEE_DIR, entry)
        if not os.path.isdir(folder_path):
            continue

        # Extract folder number
        match = re.match(r"(\d+)", entry)
        if not match:
            continue
        num = int(match.group(1))

        # Check: has song files but no PDF
        has_songs = False
        has_pdf = False
        for f in os.listdir(folder_path):
            ext = os.path.splitext(f)[1].lower()
            if ext in SONG_EXTENSIONS:
                has_songs = True
            if ext == ".pdf":
                has_pdf = True

        if has_songs and not has_pdf:
            result[num] = folder_path

    return result


def _get_pdf_files() -> set[str]:
    """Get all PDF files currently in ~/Downloads/."""
    files = set()
    for f in os.listdir(DL_DIR):
        if f.lower().endswith(".pdf"):
            files.add(os.path.join(DL_DIR, f))
    return files


def _wait_for_new_pdf(
    before: set[str],
    events: OrchestratorEvents,
    timeout: int = CERT_WAIT_MAX,
) -> str | None:
    """Wait for a new PDF to appear in ~/Downloads/. Returns path or None."""
    for _ in range(timeout):
        if events.should_stop():
            return None
        time.sleep(1)
        current = _get_pdf_files()
        new_pdfs = current - before
        if new_pdfs:
            time.sleep(0.5)  # let file finish writing
            return next(iter(new_pdfs))
        # Check for in-progress downloads
        if glob.glob(os.path.join(DL_DIR, "*.crdownload")):
            continue
    return None


def _safe_mouse_position() -> None:
    """Move mouse to screen center to avoid PyAutoGUI fail-safe."""
    off_x, off_y = get_monitor_offset()
    sw, sh = get_screen_size()
    pyautogui.moveTo(sw // 2 + off_x, sh // 2 + off_y, _pause=False)


def _close_modals() -> None:
    """Press Escape three times to reliably close cert modal + player."""
    _safe_mouse_position()
    for _ in range(3):
        pyautogui.press("escape")
        time.sleep(0.5)


def _scroll_to_top() -> None:
    """Scroll browser page to the very top to ensure icon-to-song alignment."""
    off_x, off_y = get_monitor_offset()
    sw, sh = get_screen_size()
    pyautogui.click(round(sw * 0.5) + off_x, round(sh * 0.5) + off_y)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "Home")
    time.sleep(1.5)


def _find_folder_for_pdf(pdf_name: str) -> str | None:
    """Find the song folder matching a certificate PDF by name.

    Searches all folders in TUNEE_DIR and checks if the folder's song name
    appears in the PDF filename (case-insensitive). Prefers the longest
    match and folders that don't already have a PDF.
    """
    if not os.path.isdir(TUNEE_DIR):
        return None

    pdf_lower = pdf_name.lower()
    candidates = []

    for entry in sorted(os.listdir(TUNEE_DIR)):
        folder_path = os.path.join(TUNEE_DIR, entry)
        if not os.path.isdir(folder_path):
            continue

        match = re.match(r"\d+\s*-\s*(.+?)\s*-\s*\d{2}m\d{2}s$", entry)
        if not match:
            continue

        song_name = match.group(1).strip()
        if song_name.lower() in pdf_lower:
            has_pdf = any(f.lower().endswith(".pdf") for f in os.listdir(folder_path))
            candidates.append((len(song_name), has_pdf, folder_path))

    if not candidates:
        return None

    # Prefer: longest name match first, then folders without existing PDF
    candidates.sort(key=lambda c: (-c[0], c[1]))
    return candidates[0][2]


def _download_certificate(
    icon_x: int,
    icon_y: int,
    events: OrchestratorEvents,
) -> tuple[str, str | None]:
    """Download the certificate for the song at the given icon position.

    Uses name-based matching to find the correct target folder instead of
    relying on position-based mapping.

    Returns:
        (result, folder_name) where result is "ok", "duplicate", or "failed".
    """
    off_x, off_y = get_monitor_offset()

    # Step 1: Hover over the song row (left side, same Y as download icon)
    hover_x = 200
    hover_y = icon_y
    events.on_log(f"  Hover song row at ({hover_x}, {hover_y})")
    pyautogui.moveTo(hover_x + off_x, hover_y + off_y)
    time.sleep(1)

    # Step 2: Find and click play button
    for attempt in range(MAX_RETRIES):
        if events.should_stop():
            return ("failed", None)
        screenshot = take_screenshot_bgr()
        pos = find_template(screenshot, "play_button.png", threshold=0.7)
        if pos:
            _click_at(pos[0], pos[1], "Play button", events)
            break
        time.sleep(0.5)
    else:
        events.on_log(f"  {C_ERR}Play button not found{C_RESET}")
        return ("failed", None)

    time.sleep(3.0)  # player needs time to fully load the new song

    # Step 3: Find and click three-dots menu
    for attempt in range(MAX_RETRIES):
        if events.should_stop():
            return ("failed", None)
        screenshot = take_screenshot_bgr()
        pos = find_template(screenshot, "three_dots.png", threshold=0.7)
        if pos:
            _click_at(pos[0], pos[1], "Three-dots menu", events)
            break
        time.sleep(0.5)
    else:
        events.on_log(f"  {C_ERR}Three-dots menu not found{C_RESET}")
        _close_modals()
        return ("failed", None)

    time.sleep(1)

    # Step 4: Find and click "Copyright certificate" menu item
    for attempt in range(MAX_RETRIES):
        if events.should_stop():
            return ("failed", None)
        screenshot = take_screenshot_bgr()
        pos = find_template(screenshot, "cert_menu_item.png", threshold=0.7)
        if pos:
            _click_at(pos[0], pos[1], "Copyright certificate", events)
            break
        time.sleep(0.5)
    else:
        events.on_log(f"  {C_ERR}Certificate menu item not found{C_RESET}")
        _close_modals()
        return ("failed", None)

    time.sleep(1.5)

    # Step 5: Remember PDFs before, then click download
    pdfs_before = _get_pdf_files()

    for attempt in range(MAX_RETRIES):
        if events.should_stop():
            return ("failed", None)
        screenshot = take_screenshot_bgr()
        pos = find_template(screenshot, "cert_download.png", threshold=0.7)
        if pos:
            _click_at(pos[0], pos[1], "Certificate download", events)
            break
        time.sleep(0.5)
    else:
        events.on_log(f"  {C_ERR}Certificate download button not found{C_RESET}")
        _close_modals()
        return ("failed", None)

    # Step 6: Wait for PDF
    pdf_path = _wait_for_new_pdf(pdfs_before, events)
    if not pdf_path:
        events.on_log(f"  {C_ERR}PDF download timeout{C_RESET}")
        _close_modals()
        return ("failed", None)

    # Step 7: Close modals
    _close_modals()

    # Step 8: Find correct folder by PDF name (name-based matching)
    pdf_name = os.path.basename(pdf_path)
    folder_path = _find_folder_for_pdf(pdf_name)

    if not folder_path:
        events.on_log(f"  {C_WARN}Kein passender Ordner fuer '{pdf_name}'{C_RESET}")
        return ("failed", None)

    folder_name = os.path.basename(folder_path)

    # Check if folder already has a certificate
    existing_pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    if existing_pdfs:
        events.on_log(f"  {C_WARN}'{folder_name}' hat bereits ein Zertifikat{C_RESET}")
        os.remove(pdf_path)
        return ("duplicate", folder_name)

    # Step 9: Move PDF to song folder
    dst = os.path.join(folder_path, pdf_name)
    shutil.move(pdf_path, dst)
    events.on_log(f"  {C_DONE}Certificate: {pdf_name} -> {folder_name}/{C_RESET}")

    return ("ok", folder_name)


# ── Main certificate loop ────────────────────────────────────────────


def run_cert_task(
    max_songs: int = 50,
    max_scrolls: int = 15,
    events: OrchestratorEvents | None = None,
) -> bool:
    """Download certificates for songs that don't have one yet.

    Position-based matching: CDP song list order matches download icon
    order on screen. Folder number -> song index in CDP list.
    """
    if events is None:
        events = PrintEvents()

    # Step 1: Get song list from CDP
    events.on_log("Scanne Songliste von tunee.ai...")
    try:
        songs = get_song_list()
    except Exception as exc:
        events.on_log(f"{C_ERR}Scraper-Fehler: {exc}{C_RESET}")
        return False
    events.on_log(f"{len(songs)} Songs gefunden")

    # Step 2: Find folders needing certificates
    need_certs = find_folders_needing_certs()
    if not need_certs:
        events.on_log(f"{C_DONE}Alle Ordner haben bereits Zertifikate!{C_RESET}")
        return True

    events.on_log(
        f"{len(need_certs)} Ordner brauchen Zertifikate: "
        f"{sorted(need_certs.keys())}"
    )

    # Step 3: Build set of song indices needing certs (0-based)
    # Folder number N -> song index N-1 in CDP list
    need_cert_at_index = set()
    for folder_num in need_certs:
        idx = folder_num - 1  # 0-based
        if 0 <= idx < len(songs):
            need_cert_at_index.add(idx)

    total_needed = len(need_cert_at_index)
    completed = 0
    failures = 0
    song_idx = 0  # Global position counter across scrolls

    events.on_log(f"\n{'=' * 60}")
    events.on_log(f"  Certificate Downloader — {total_needed} Zertifikate")
    events.on_log(f"  Output: {TUNEE_DIR}")
    events.on_log(f"{'=' * 60}\n")
    events.on_progress(0, total_needed)

    # Scroll to top to ensure first icon matches first song
    _scroll_to_top()
    events.on_log("Seite nach oben gescrollt")

    for scroll_round in range(max_scrolls + 1):
        if events.should_stop():
            events.on_log("Stopped by user.")
            break

        # Find download icons on current screen
        screenshot = take_screenshot_bgr()
        icons = find_all_templates(screenshot, "download_button.png", threshold=0.7)

        if not icons:
            events.on_log(
                f"{C_WARN}Keine Download-Icons auf dem Screen (Runde {scroll_round}){C_RESET}"
            )
            break

        # Sort top-to-bottom
        icons.sort(key=lambda m: m[1])
        events.on_icons_found(len(icons), scroll_round)

        # Filter icons based on scroll round.
        # After scroll, the first row is often partially hidden behind the
        # sticky header — play button overlay won't appear.  Skip it.
        if scroll_round == 0:
            min_y = 0
        else:
            _, sh = get_screen_size()
            min_y = int(sh * 0.15)

        eligible = [(ix, iy, c) for ix, iy, c in icons if iy > min_y]

        if not eligible:
            events.on_log(f"  Alle {len(icons)} Icons bereits verarbeitet — scrolle")
            if scroll_round < max_scrolls:
                _scroll_down()
            continue

        for ix, iy, conf in eligible:
            if events.should_stop():
                break
            if completed >= max_songs:
                break

            current_folder_num = song_idx + 1  # 1-based

            if song_idx in need_cert_at_index:
                events.on_song_start(current_folder_num, ix, iy)
                events.on_log(f"  Zertifikat fuer Icon #{current_folder_num}")

                try:
                    result, folder_name = _download_certificate(ix, iy, events)
                except pyautogui.FailSafeException:
                    events.on_log(
                        f"  {C_WARN}Fail-safe ausgeloest — ueberspringe{C_RESET}"
                    )
                    _safe_mouse_position()
                    time.sleep(1)
                    result, folder_name = "failed", None

                if result == "ok":
                    completed += 1
                    events.on_song_complete(current_folder_num, folder_name or "?")
                    events.on_progress(completed, total_needed)
                elif result == "duplicate":
                    pass
                else:
                    failures += 1
                    events.on_song_failed(current_folder_num)

                if completed < total_needed and not events.should_stop():
                    time.sleep(BETWEEN_CERTS_DELAY)

            song_idx += 1

        if completed >= max_songs or completed >= total_needed:
            break

        # Scroll down for more icons
        if scroll_round < max_scrolls and not events.should_stop():
            events.on_scroll(scroll_round)
            _scroll_down()

    events.on_log(f"\n{'=' * 60}")
    events.on_log(f"  Fertig! {completed} Zertifikate heruntergeladen")
    if failures:
        events.on_log(f"  ({failures} fehlgeschlagen)")
    events.on_log(f"{'=' * 60}")
    events.on_progress(completed, total_needed)
    return completed > 0


def _scroll_down() -> None:
    """Scroll down on the song list."""
    off_x, off_y = get_monitor_offset()
    sw, sh = get_screen_size()
    pyautogui.scroll(-5, x=round(sw * 0.15) + off_x, y=round(sh * 0.5) + off_y)
    time.sleep(2)
