"""Template-only orchestrator: downloads all songs via OpenCV template matching."""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import time

import pyautogui

from .events import OrchestratorEvents, PrintEvents, C_TMPL, C_DONE, C_ERR, C_WARN, C_RESET
from .screenshot import take_screenshot_bgr, get_monitor_offset, get_screen_size
from .template_match import find_template, find_all_templates, find_button_in_row

# Paths
DL_DIR = os.path.expanduser("~/Downloads")
TUNEE_DIR = os.path.join(DL_DIR, "tunee")

# Template thresholds
DL_ICON_THRESHOLD = 0.7
MODAL_ROW_THRESHOLD = 0.7
VIDEO_DL_THRESHOLD = 0.7

# Timing
CLICK_DELAY = 1.5        # seconds after each click
VIDEO_WAIT_MAX = 90       # max seconds to wait for video download
VIDEO_POLL_INTERVAL = 3   # seconds between download checks
BETWEEN_SONGS_DELAY = 3   # seconds pause between songs

MAX_RETRIES = 5

# File extensions we look for
SONG_EXTENSIONS = {".mp3", ".wav", ".flac", ".lrc", ".mp4"}


def _click_at(x: int, y: int, label: str, events: OrchestratorEvents) -> None:
    """Click at screenshot coordinates (adds monitor offset)."""
    off_x, off_y = get_monitor_offset()
    abs_x = x + off_x
    abs_y = y + off_y
    events.on_log(f"  {C_TMPL}{label} at ({x},{y}) → click ({abs_x},{abs_y}){C_RESET}")
    pyautogui.click(abs_x, abs_y)


def _get_dl_files() -> set[str]:
    """Get all song-related files currently in ~/Downloads/."""
    files = set()
    for f in os.listdir(DL_DIR):
        if os.path.splitext(f)[1].lower() in SONG_EXTENSIONS:
            files.add(os.path.join(DL_DIR, f))
    return files


def _get_duration(mp3_path: str) -> str:
    """Get duration from an audio file via ffprobe. Returns e.g. '04m10s'."""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", mp3_path],
            text=True, timeout=10,
        ).strip()
        secs = float(out)
        m, s = divmod(int(secs), 60)
        return f"{m:02d}m{s:02d}s"
    except Exception:
        return "00m00s"


def _sanitize(name: str) -> str:
    """Remove characters that are problematic in folder names."""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip('. ')


def _is_duplicate(song_name: str, duration: str) -> bool:
    """Check if a song with same name + duration already exists in TUNEE_DIR."""
    if not os.path.isdir(TUNEE_DIR):
        return False
    sanitized = _sanitize(song_name)
    suffix = f" - {sanitized} - {duration}"
    for entry in os.listdir(TUNEE_DIR):
        if entry.endswith(suffix) and os.path.isdir(os.path.join(TUNEE_DIR, entry)):
            return True
    return False


def _move_to_subfolder(
    new_files: set[str], song_num: int, events: OrchestratorEvents,
) -> tuple[str | None, str, str]:
    """Move new downloads into a numbered subfolder under tunee/.

    Returns (folder_name | "DUPLICATE" | None, song_name, duration).
    """
    if not new_files:
        return None, "Unknown", "00m00s"

    os.makedirs(TUNEE_DIR, exist_ok=True)

    # Determine song name from the MP3 filename
    song_name = "Unknown"
    mp3_path = None
    for f in new_files:
        if f.endswith(".mp3"):
            mp3_path = f
            song_name = os.path.splitext(os.path.basename(f))[0]
            break

    # Get duration from MP3
    duration = "00m00s"
    if mp3_path:
        duration = _get_duration(mp3_path)

    # Check for duplicate
    if _is_duplicate(song_name, duration):
        events.on_log(f"  {C_WARN}DUPLICATE: {song_name} ({duration}) — deleting{C_RESET}")
        for f in new_files:
            os.remove(f)
        return "DUPLICATE", song_name, duration

    folder_name = f"{song_num:02d} - {_sanitize(song_name)} - {duration}"
    folder_path = os.path.join(TUNEE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for f in new_files:
        dst = os.path.join(folder_path, os.path.basename(f))
        shutil.move(f, dst)

    events.on_log(f"  {C_DONE}Moved {len(new_files)} files → {folder_name}/{C_RESET}")
    return folder_name, song_name, duration


def _wait_for_video_download(
    before_mp4s: set[str], events: OrchestratorEvents,
) -> bool:
    """Wait until a new .mp4 appears in ~/Downloads. Returns True if found."""
    events.on_log(f"  Waiting for video download (max {VIDEO_WAIT_MAX}s)...")

    for i in range(VIDEO_WAIT_MAX // VIDEO_POLL_INTERVAL):
        if events.should_stop():
            return False
        time.sleep(VIDEO_POLL_INTERVAL)
        current = set(glob.glob(os.path.join(DL_DIR, "*.mp4")))
        new_files = current - before_mp4s
        if new_files:
            name = os.path.basename(next(iter(new_files)))
            events.on_log(f"  {C_DONE}Video: {name}{C_RESET}")
            return True
        # Check for .crdownload (still downloading)
        downloading = glob.glob(os.path.join(DL_DIR, "*.crdownload"))
        if downloading:
            continue

    events.on_log(f"  {C_WARN}Video download timeout{C_RESET}")
    return False


def _wait_for_downloads_complete(events: OrchestratorEvents) -> None:
    """Wait until no .crdownload files remain (all downloads finished)."""
    for _ in range(30):
        if events.should_stop():
            return
        downloading = glob.glob(os.path.join(DL_DIR, "*.crdownload"))
        if not downloading:
            return
        time.sleep(1)


def _click_modal_row(
    tmpl_name: str, label: str, events: OrchestratorEvents,
) -> bool:
    """Find a modal row icon and click its Download button. Returns True if clicked."""
    for attempt in range(MAX_RETRIES):
        if events.should_stop():
            return False
        screenshot = take_screenshot_bgr()
        pos = find_button_in_row(screenshot, tmpl_name, row_threshold=MODAL_ROW_THRESHOLD)
        if pos:
            _click_at(pos[0], pos[1], label, events)
            time.sleep(CLICK_DELAY)
            return True
        time.sleep(0.5)
    return False


def _click_template(
    tmpl_name: str, label: str, events: OrchestratorEvents,
    threshold: float = 0.7,
) -> bool:
    """Find and click a template. Returns True if clicked."""
    for attempt in range(MAX_RETRIES):
        if events.should_stop():
            return False
        screenshot = take_screenshot_bgr()
        pos = find_template(screenshot, tmpl_name, threshold=threshold)
        if pos:
            _click_at(pos[0], pos[1], label, events)
            time.sleep(CLICK_DELAY)
            return True
        time.sleep(0.5)
    return False


def _download_song(
    icon_x: int, icon_y: int, song_num: int, events: OrchestratorEvents,
) -> tuple[str, str, str]:
    """Download all formats for one song.

    Returns: (result, song_name, duration)
      result: "ok", "duplicate", or "failed"
    """
    # Snapshot files before download
    files_before = _get_dl_files()

    # Step 1: Click the download icon to open modal
    _click_at(icon_x, icon_y, f"Song #{song_num} download icon", events)
    time.sleep(CLICK_DELAY)

    # Step 2: Click MP3 Download
    if not _click_modal_row("modal_mp3.png", "MP3 Download", events):
        events.on_log(f"  {C_ERR}MP3 not found — modal didn't open?{C_RESET}")
        pyautogui.press("escape")
        return "failed", "Unknown", "00m00s"
    events.on_log(f"  {C_DONE}MP3 ✓{C_RESET}")

    # Step 3: Click RAW Download
    if not _click_modal_row("modal_raw.png", "RAW Download", events):
        events.on_log(f"  {C_WARN}RAW not found — skipping{C_RESET}")
    else:
        events.on_log(f"  {C_DONE}RAW ✓{C_RESET}")

    # Step 4: Click LRC Download
    if not _click_modal_row("modal_lrc.png", "LRC Download", events):
        events.on_log(f"  {C_WARN}LRC not found — skipping{C_RESET}")
    else:
        events.on_log(f"  {C_DONE}LRC ✓{C_RESET}")

    # Step 5: Click VIDEO Download (opens Lyric Video modal)
    mp4s_before = set(glob.glob(os.path.join(DL_DIR, "*.mp4")))

    if not _click_modal_row("modal_video.png", "VIDEO Download", events):
        events.on_log(f"  {C_WARN}VIDEO not found — skipping{C_RESET}")
        pyautogui.press("escape")
        time.sleep(1)
        _wait_for_downloads_complete(events)
        new_files = _get_dl_files() - files_before
        result, song_name, duration = _move_to_subfolder(new_files, song_num, events)
        return ("duplicate" if result == "DUPLICATE" else "ok"), song_name, duration

    # Step 6: Click Download in Lyric Video modal
    time.sleep(1)
    if _click_template("lyric_video_download.png", "Video DL Button", events, VIDEO_DL_THRESHOLD):
        events.on_log(f"  {C_DONE}VIDEO DL ✓{C_RESET}")
        _wait_for_video_download(mp4s_before, events)
    else:
        events.on_log(f"  {C_WARN}Video DL button not found — pressing Escape{C_RESET}")
        pyautogui.press("escape")
        time.sleep(1)
        pyautogui.press("escape")
        time.sleep(1)

    _wait_for_downloads_complete(events)

    new_files = _get_dl_files() - files_before
    result, song_name, duration = _move_to_subfolder(new_files, song_num, events)
    return ("duplicate" if result == "DUPLICATE" else "ok"), song_name, duration


def run_task(
    max_songs: int = 50,
    max_scrolls: int = 15,
    start_num: int = 0,
    events: OrchestratorEvents | None = None,
) -> bool:
    """Download all songs by finding download icons top-to-bottom.

    Pure template matching — no VLM needed.
    """
    if events is None:
        events = PrintEvents()

    song_count = start_num
    duplicates = 0
    failures = 0
    last_bottom_y = 0

    os.makedirs(TUNEE_DIR, exist_ok=True)

    events.on_log(f"\n{'=' * 60}")
    events.on_log(f"  Template Downloader — max {max_songs} songs")
    events.on_log(f"  Output: {TUNEE_DIR}")
    events.on_log(f"{'=' * 60}\n")
    events.on_progress(song_count, max_songs)

    empty_scrolls = 0

    for scroll_round in range(max_scrolls + 1):
        if events.should_stop():
            events.on_log("Stopped by user.")
            break

        screenshot = take_screenshot_bgr()
        icons = find_all_templates(screenshot, "download_button.png",
                                   threshold=DL_ICON_THRESHOLD)

        if not icons:
            events.on_log("No download icons found on screen")
            break

        icons.sort(key=lambda m: m[1])
        events.on_icons_found(len(icons), scroll_round)

        if scroll_round == 0:
            min_y = 0
        else:
            min_y = last_bottom_y - 15

        eligible = [(ix, iy, c) for ix, iy, c in icons if iy > min_y]
        if not eligible:
            events.on_log(f"  All {len(icons)} icons already processed — scrolling")
            if scroll_round < max_scrolls:
                off_x, off_y = get_monitor_offset()
                sw, sh = get_screen_size()
                pyautogui.scroll(-5, x=round(sw * 0.15) + off_x,
                                 y=round(sh * 0.5) + off_y)
                time.sleep(2)
            continue

        songs_this_round = 0
        for ix, iy, conf in eligible:
            if events.should_stop():
                break
            if song_count >= max_songs:
                break

            tentative_num = song_count + 1
            songs_this_round += 1
            events.on_song_start(tentative_num, ix, iy)

            result, song_name, duration = _download_song(ix, iy, tentative_num, events)

            if result == "duplicate":
                duplicates += 1
                events.on_song_duplicate(tentative_num, song_name, duration)
            elif result == "ok":
                song_count += 1
                events.on_song_complete(song_count, f"{song_count:02d} - {_sanitize(song_name)} - {duration}")
                events.on_progress(song_count, max_songs)
            else:
                failures += 1
                events.on_song_failed(tentative_num)

            last_bottom_y = iy

            if song_count < max_songs and not events.should_stop():
                events.on_log(f"  Waiting {BETWEEN_SONGS_DELAY}s before next song...")
                time.sleep(BETWEEN_SONGS_DELAY)

        if song_count >= max_songs:
            break

        if songs_this_round == 0:
            empty_scrolls += 1
            if empty_scrolls >= 3:
                events.on_log(f"No new songs after {empty_scrolls} scrolls — done")
                break
        else:
            empty_scrolls = 0

        if scroll_round < max_scrolls and not events.should_stop():
            events.on_scroll(scroll_round)
            off_x, off_y = get_monitor_offset()
            sw, sh = get_screen_size()
            pyautogui.scroll(-5, x=round(sw * 0.15) + off_x,
                             y=round(sh * 0.5) + off_y)
            time.sleep(2)

    events.on_log(f"\n{'=' * 60}")
    events.on_log(f"  Done! Downloaded {song_count} unique songs to {TUNEE_DIR}")
    if duplicates:
        events.on_log(f"  ({duplicates} duplicates detected and skipped)")
    if failures:
        events.on_log(f"  ({failures} failures)")
    events.on_log(f"{'=' * 60}")
    events.on_progress(song_count, max_songs)
    return song_count > 0
