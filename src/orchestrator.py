"""Template-only orchestrator: downloads all songs via OpenCV template matching."""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import time

import pyautogui

from .screenshot import take_screenshot_bgr, get_monitor_offset, get_screen_size
from .template_match import find_template, find_all_templates, find_button_in_row

# ANSI colors
C_STEP = "\033[1;36m"
C_DONE = "\033[1;32m"
C_ERR = "\033[0;31m"
C_WARN = "\033[0;35m"
C_TMPL = "\033[0;36m"
C_RESET = "\033[0m"

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


def _click_at(x: int, y: int, label: str) -> None:
    """Click at screenshot coordinates (adds monitor offset)."""
    off_x, off_y = get_monitor_offset()
    abs_x = x + off_x
    abs_y = y + off_y
    print(f"  {C_TMPL}{label} at ({x},{y}) → click ({abs_x},{abs_y}){C_RESET}")
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


def _move_to_subfolder(new_files: set[str], song_num: int) -> str | None:
    """Move new downloads into a numbered subfolder under tunee/.

    Returns the folder name or None on failure.
    """
    if not new_files:
        return None

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

    folder_name = f"{song_num:02d} - {_sanitize(song_name)} - {duration}"
    folder_path = os.path.join(TUNEE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for f in new_files:
        dst = os.path.join(folder_path, os.path.basename(f))
        shutil.move(f, dst)

    print(f"  {C_DONE}Moved {len(new_files)} files → {folder_name}/{C_RESET}")
    return folder_name


def _wait_for_video_download(before_mp4s: set[str]) -> bool:
    """Wait until a new .mp4 appears in ~/Downloads. Returns True if found."""
    print(f"  Waiting for video download (max {VIDEO_WAIT_MAX}s)...", end="", flush=True)

    for i in range(VIDEO_WAIT_MAX // VIDEO_POLL_INTERVAL):
        time.sleep(VIDEO_POLL_INTERVAL)
        current = set(glob.glob(os.path.join(DL_DIR, "*.mp4")))
        new_files = current - before_mp4s
        if new_files:
            name = os.path.basename(next(iter(new_files)))
            print(f" {C_DONE}{name}{C_RESET}")
            return True
        # Check for .crdownload (still downloading)
        downloading = glob.glob(os.path.join(DL_DIR, "*.crdownload"))
        if downloading:
            print(".", end="", flush=True)
            continue
        print(".", end="", flush=True)

    print(f" {C_WARN}timeout{C_RESET}")
    return False


def _wait_for_downloads_complete() -> None:
    """Wait until no .crdownload files remain (all downloads finished)."""
    for _ in range(30):
        downloading = glob.glob(os.path.join(DL_DIR, "*.crdownload"))
        if not downloading:
            return
        time.sleep(1)


def _click_modal_row(tmpl_name: str, label: str) -> bool:
    """Find a modal row icon and click its Download button. Returns True if clicked."""
    for attempt in range(MAX_RETRIES):
        screenshot = take_screenshot_bgr()
        pos = find_button_in_row(screenshot, tmpl_name, row_threshold=MODAL_ROW_THRESHOLD)
        if pos:
            _click_at(pos[0], pos[1], label)
            time.sleep(CLICK_DELAY)
            return True
        time.sleep(0.5)
    return False


def _click_template(tmpl_name: str, label: str, threshold: float = 0.7) -> bool:
    """Find and click a template. Returns True if clicked."""
    for attempt in range(MAX_RETRIES):
        screenshot = take_screenshot_bgr()
        pos = find_template(screenshot, tmpl_name, threshold=threshold)
        if pos:
            _click_at(pos[0], pos[1], label)
            time.sleep(CLICK_DELAY)
            return True
        time.sleep(0.5)
    return False


def _download_song(icon_x: int, icon_y: int, song_num: int) -> bool:
    """Download all formats for one song. Returns True if successful."""
    # Snapshot files before download
    files_before = _get_dl_files()

    # Step 1: Click the download icon to open modal
    _click_at(icon_x, icon_y, f"Song #{song_num} download icon")
    time.sleep(CLICK_DELAY)

    # Step 2: Click MP3 Download
    if not _click_modal_row("modal_mp3.png", "MP3 Download"):
        print(f"  {C_ERR}MP3 not found — modal didn't open?{C_RESET}")
        pyautogui.press("escape")
        return False
    print(f"  {C_DONE}MP3 ✓{C_RESET}")

    # Step 3: Click RAW Download
    if not _click_modal_row("modal_raw.png", "RAW Download"):
        print(f"  {C_WARN}RAW not found — skipping{C_RESET}")
    else:
        print(f"  {C_DONE}RAW ✓{C_RESET}")

    # Step 4: Click LRC Download
    if not _click_modal_row("modal_lrc.png", "LRC Download"):
        print(f"  {C_WARN}LRC not found — skipping{C_RESET}")
    else:
        print(f"  {C_DONE}LRC ✓{C_RESET}")

    # Step 5: Click VIDEO Download (opens Lyric Video modal)
    mp4s_before = set(glob.glob(os.path.join(DL_DIR, "*.mp4")))

    if not _click_modal_row("modal_video.png", "VIDEO Download"):
        print(f"  {C_WARN}VIDEO not found — skipping{C_RESET}")
        pyautogui.press("escape")
        time.sleep(1)
        # Wait for pending downloads, then move files
        _wait_for_downloads_complete()
        new_files = _get_dl_files() - files_before
        _move_to_subfolder(new_files, song_num)
        return True

    # Step 6: Click Download in Lyric Video modal
    time.sleep(1)  # extra wait for modal animation
    if _click_template("lyric_video_download.png", "Video DL Button", VIDEO_DL_THRESHOLD):
        print(f"  {C_DONE}VIDEO DL ✓{C_RESET}")
        _wait_for_video_download(mp4s_before)
    else:
        print(f"  {C_WARN}Video DL button not found — pressing Escape{C_RESET}")
        pyautogui.press("escape")
        time.sleep(1)
        pyautogui.press("escape")
        time.sleep(1)

    # Wait for any remaining downloads to finish
    _wait_for_downloads_complete()

    # Move all new files into subfolder
    new_files = _get_dl_files() - files_before
    _move_to_subfolder(new_files, song_num)

    return True


def run_task(max_songs: int = 50, max_scrolls: int = 15, start_num: int = 0) -> bool:
    """Download all songs by finding download icons top-to-bottom.

    Pure template matching — no VLM needed.
    """
    song_count = start_num
    last_bottom_y = 0  # Y of last processed icon (for scroll overlap detection)

    # Ensure tunee output dir exists
    os.makedirs(TUNEE_DIR, exist_ok=True)

    print(f"\n{C_STEP}{'=' * 60}")
    print(f"  Template Downloader — max {max_songs} songs")
    print(f"  Output: {TUNEE_DIR}")
    print(f"{'=' * 60}{C_RESET}\n")

    empty_scrolls = 0  # consecutive scrolls with no new songs

    for scroll_round in range(max_scrolls + 1):
        # Find all download icons on current screen
        screenshot = take_screenshot_bgr()
        icons = find_all_templates(screenshot, "download_button.png",
                                   threshold=DL_ICON_THRESHOLD)

        if not icons:
            print(f"{C_WARN}No download icons found on screen{C_RESET}")
            break

        # Sort top to bottom
        icons.sort(key=lambda m: m[1])
        print(f"\n{C_STEP}Found {len(icons)} download icons "
              f"(scroll round {scroll_round}){C_RESET}")

        # Only process icons below the last-processed Y from previous round
        # This handles overlap when scrolling (top songs remain visible)
        if scroll_round == 0:
            min_y = 0
        else:
            min_y = last_bottom_y - 15  # small tolerance

        eligible = [(ix, iy, c) for ix, iy, c in icons if iy > min_y]
        if not eligible:
            eligible = icons  # fallback: process all if filter is too strict

        songs_this_round = 0
        for ix, iy, conf in eligible:
            if song_count >= max_songs:
                break

            song_count += 1
            songs_this_round += 1
            print(f"\n{C_STEP}{'─' * 40}")
            print(f"  Song #{song_count} — icon at ({ix},{iy})")
            print(f"{'─' * 40}{C_RESET}")

            success = _download_song(ix, iy, song_count)

            if success:
                print(f"  {C_DONE}Song #{song_count} complete!{C_RESET}")
            else:
                print(f"  {C_ERR}Song #{song_count} failed{C_RESET}")

            last_bottom_y = iy

            # Pause between songs
            if song_count < max_songs:
                print(f"  Waiting {BETWEEN_SONGS_DELAY}s before next song...")
                time.sleep(BETWEEN_SONGS_DELAY)

        if song_count >= max_songs:
            break

        if songs_this_round == 0:
            empty_scrolls += 1
            if empty_scrolls >= 3:
                print(f"{C_WARN}No new songs after {empty_scrolls} scrolls — done{C_RESET}")
                break
        else:
            empty_scrolls = 0

        # Scroll down for more songs
        if scroll_round < max_scrolls:
            print(f"\n{C_STEP}Scrolling down for more songs...{C_RESET}")
            off_x, off_y = get_monitor_offset()
            sw, sh = get_screen_size()
            pyautogui.scroll(-5, x=round(sw * 0.15) + off_x,
                             y=round(sh * 0.5) + off_y)
            time.sleep(2)

    print(f"\n{C_DONE}{'=' * 60}")
    print(f"  Done! Downloaded {song_count} songs to {TUNEE_DIR}")
    print(f"{'=' * 60}{C_RESET}")
    return song_count > 0
