"""Template-only orchestrator: downloads all songs via OpenCV template matching.

New workflow:
1. Scraper reads song list from tunee.ai page via CDP
2. Empty folders are pre-created for all songs
3. Downloader skips songs whose folders already have files
"""

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


# ── Helpers ──────────────────────────────────────────────────────────

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


def _duration_display_to_folder(display: str) -> str:
    """Convert 'MM:SS' → 'MMmSSs'."""
    parts = display.split(":")
    if len(parts) == 2:
        return f"{int(parts[0]):02d}m{int(parts[1]):02d}s"
    return "00m00s"


def _folder_has_files(folder_path: str) -> bool:
    """Check if a folder contains any song files."""
    if not os.path.isdir(folder_path):
        return False
    for f in os.listdir(folder_path):
        if os.path.splitext(f)[1].lower() in SONG_EXTENSIONS:
            return True
    return False


# ── Project preparation ──────────────────────────────────────────────

def prepare_project(songs: list[dict]) -> list[dict]:
    """Create empty folders for all songs from scraper data.

    Args:
        songs: list of {"name": str, "duration": str} from scraper
               (duration in "MM:SS" format)

    Returns:
        list of {"num": int, "name": str, "duration": str,
                 "folder": str, "complete": bool}
    """
    os.makedirs(TUNEE_DIR, exist_ok=True)
    result = []

    for i, song in enumerate(songs, 1):
        name = _sanitize(song["name"])
        dur = _duration_display_to_folder(song["duration"])
        folder_name = f"{i:02d} - {name} - {dur}"
        folder_path = os.path.join(TUNEE_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        complete = _folder_has_files(folder_path)
        result.append({
            "num": i,
            "name": song["name"],
            "duration": dur,
            "folder": folder_name,
            "complete": complete,
        })

    return result


def get_project_status() -> dict:
    """Get download status from existing folders.

    Returns {"total": int, "complete": int, "missing": int,
             "missing_nums": list[int]}
    """
    if not os.path.isdir(TUNEE_DIR):
        return {"total": 0, "complete": 0, "missing": 0, "missing_nums": []}

    folders = sorted(d for d in os.listdir(TUNEE_DIR)
                     if os.path.isdir(os.path.join(TUNEE_DIR, d)))
    total = len(folders)
    complete = 0
    missing_nums = []

    for folder in folders:
        path = os.path.join(TUNEE_DIR, folder)
        if _folder_has_files(path):
            complete += 1
        else:
            # Extract number from folder name
            match = re.match(r"(\d+)", folder)
            if match:
                missing_nums.append(int(match.group(1)))

    return {
        "total": total,
        "complete": complete,
        "missing": total - complete,
        "missing_nums": missing_nums,
    }


# ── Duplicate check (folder-based) ──────────────────────────────────

def _find_matching_folder(song_name: str, duration: str) -> str | None:
    """Find the pre-created folder matching this song.

    Tries exact match first (name + duration), then name-only with
    closest duration (±2 seconds tolerance).

    When multiple folders match (same song name, same/similar duration),
    prefers EMPTY folders (not yet downloaded) so that each version gets
    its own folder.
    """
    if not os.path.isdir(TUNEE_DIR):
        return None

    sanitized = _sanitize(song_name)
    exact_suffix = f" - {sanitized} - {duration}"

    # Exact match — collect ALL matching folders, prefer empty ones
    exact_matches = []
    for entry in sorted(os.listdir(TUNEE_DIR)):
        if entry.endswith(exact_suffix) and os.path.isdir(os.path.join(TUNEE_DIR, entry)):
            exact_matches.append(entry)

    if exact_matches:
        # Prefer an empty folder (not yet downloaded)
        for m in exact_matches:
            if not _folder_has_files(os.path.join(TUNEE_DIR, m)):
                return m
        # All have files — return first (numerically lowest)
        return exact_matches[0]

    # Fuzzy match: same name, duration ±2 seconds
    name_part = f" - {sanitized} - "
    dur_match = re.match(r"(\d+)m(\d+)s", duration)
    if not dur_match:
        return None
    target_secs = int(dur_match.group(1)) * 60 + int(dur_match.group(2))

    candidates = []
    for entry in sorted(os.listdir(TUNEE_DIR)):
        if name_part not in entry:
            continue
        if not os.path.isdir(os.path.join(TUNEE_DIR, entry)):
            continue
        m = re.search(r"(\d+)m(\d+)s$", entry)
        if not m:
            continue
        folder_secs = int(m.group(1)) * 60 + int(m.group(2))
        diff = abs(folder_secs - target_secs)
        if diff <= 2:
            candidates.append((diff, entry))

    if not candidates:
        return None

    # Sort by duration-closeness, then prefer empty folders
    candidates.sort(key=lambda c: c[0])
    for _, entry in candidates:
        if not _folder_has_files(os.path.join(TUNEE_DIR, entry)):
            return entry
    # All matching folders have files — return closest match
    return candidates[0][1]


def _is_already_downloaded(song_name: str, duration: str) -> bool:
    """Check if all matching folders already have files.

    Returns False if there is at least one empty matching folder
    (meaning this song version still needs to be downloaded).
    """
    if not os.path.isdir(TUNEE_DIR):
        return False

    sanitized = _sanitize(song_name)
    exact_suffix = f" - {sanitized} - {duration}"

    # Check all folders matching name + duration (exact)
    for entry in os.listdir(TUNEE_DIR):
        if entry.endswith(exact_suffix) and os.path.isdir(os.path.join(TUNEE_DIR, entry)):
            if not _folder_has_files(os.path.join(TUNEE_DIR, entry)):
                return False  # Empty matching folder exists → not a duplicate

    # Also check fuzzy matches (±2 seconds)
    name_part = f" - {sanitized} - "
    dur_match = re.match(r"(\d+)m(\d+)s", duration)
    if dur_match:
        target_secs = int(dur_match.group(1)) * 60 + int(dur_match.group(2))
        for entry in os.listdir(TUNEE_DIR):
            if name_part not in entry or not os.path.isdir(os.path.join(TUNEE_DIR, entry)):
                continue
            m = re.search(r"(\d+)m(\d+)s$", entry)
            if not m:
                continue
            folder_secs = int(m.group(1)) * 60 + int(m.group(2))
            if abs(folder_secs - target_secs) <= 2:
                if not _folder_has_files(os.path.join(TUNEE_DIR, entry)):
                    return False  # Empty matching folder → not a duplicate

    # No empty matching folder found — either all are full (true duplicate)
    # or no matching folder exists at all (new song, not a duplicate)
    folder = _find_matching_folder(song_name, duration)
    if not folder:
        return False
    return True


# ── Move files to folder ────────────────────────────────────────────

def _move_to_subfolder(
    new_files: set[str], song_num: int, events: OrchestratorEvents,
) -> tuple[str | None, str, str]:
    """Move new downloads into the matching pre-created folder.

    Falls back to creating a new numbered folder if no match found.
    Returns (folder_name | None, song_name, duration).
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

    # Try to find pre-created folder
    folder_name = _find_matching_folder(song_name, duration)
    if not folder_name:
        # Fallback: create new folder
        folder_name = f"{song_num:02d} - {_sanitize(song_name)} - {duration}"

    folder_path = os.path.join(TUNEE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    for f in new_files:
        dst = os.path.join(folder_path, os.path.basename(f))
        shutil.move(f, dst)

    events.on_log(f"  {C_DONE}Moved {len(new_files)} files → {folder_name}/{C_RESET}")
    return folder_name, song_name, duration


# ── Download helpers ─────────────────────────────────────────────────

def _wait_for_video_download(
    before_mp4s: set[str], events: OrchestratorEvents,
) -> bool:
    """Wait until a new .mp4 appears AND is fully downloaded.

    Checks file size stability to ensure Chrome has finished writing
    the file before returning.
    """
    events.on_log(f"  Waiting for video download (max {VIDEO_WAIT_MAX}s)...")

    mp4_path = None
    stable_count = 0

    for i in range(VIDEO_WAIT_MAX // VIDEO_POLL_INTERVAL):
        if events.should_stop():
            return False
        time.sleep(VIDEO_POLL_INTERVAL)

        current = set(glob.glob(os.path.join(DL_DIR, "*.mp4")))
        new_files = current - before_mp4s

        if new_files and not mp4_path:
            mp4_path = next(iter(new_files))
            events.on_log(f"  Video erschienen: {os.path.basename(mp4_path)}, warte auf vollständigen Download...")

        if mp4_path:
            try:
                size1 = os.path.getsize(mp4_path)
                time.sleep(2)
                size2 = os.path.getsize(mp4_path)
                if size1 == size2 and size1 > 0:
                    stable_count += 1
                    if stable_count >= 2:
                        events.on_log(f"  {C_DONE}Video: {os.path.basename(mp4_path)} ({size2 // 1024}KB){C_RESET}")
                        return True
                else:
                    stable_count = 0
            except OSError:
                stable_count = 0
                continue

        # Check for .crdownload (still downloading)
        downloading = glob.glob(os.path.join(DL_DIR, "*.crdownload"))
        if downloading:
            continue

    events.on_log(f"  {C_WARN}Video download timeout{C_RESET}")
    return False


def _wait_for_downloads_complete(events: OrchestratorEvents) -> None:
    """Wait until no .crdownload files remain AND all files have stable size."""
    stable_count = 0
    for _ in range(60):
        if events.should_stop():
            return
        downloading = glob.glob(os.path.join(DL_DIR, "*.crdownload"))
        if downloading:
            stable_count = 0
            time.sleep(1)
            continue

        # No .crdownload — verify all MP4s have stable size
        mp4s = glob.glob(os.path.join(DL_DIR, "*.mp4"))
        all_stable = True
        for mp4 in mp4s:
            try:
                s1 = os.path.getsize(mp4)
                time.sleep(0.3)
                s2 = os.path.getsize(mp4)
                if s1 != s2:
                    all_stable = False
                    break
            except OSError:
                all_stable = False
                break

        if all_stable:
            stable_count += 1
            if stable_count >= 2:
                return
        else:
            stable_count = 0
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


def _wait_for_new_mp3(files_before: set[str], events: OrchestratorEvents,
                      timeout: int = 30) -> str | None:
    """Wait for a new MP3 to appear in ~/Downloads. Returns path or None."""
    for _ in range(timeout):
        if events.should_stop():
            return None
        time.sleep(1)
        current = _get_dl_files()
        new_mp3s = [f for f in (current - files_before) if f.endswith(".mp3")]
        if new_mp3s:
            time.sleep(0.5)
            return new_mp3s[0]
        if glob.glob(os.path.join(DL_DIR, "*.crdownload")):
            continue
    return None


# ── Single song download ────────────────────────────────────────────

def _download_song(
    icon_x: int, icon_y: int, song_num: int, events: OrchestratorEvents,
) -> tuple[str, str, str]:
    """Download all formats for one song.

    Early duplicate check: downloads MP3 first, checks if the matching
    folder already has files, and only downloads remaining formats for
    new songs.

    Returns: (result, song_name, duration)
      result: "ok", "duplicate", or "failed"
    """
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

    # Step 3: Wait for MP3 and check if already downloaded
    mp3_path = _wait_for_new_mp3(files_before, events)
    if not mp3_path:
        events.on_log(f"  {C_ERR}MP3 download timeout{C_RESET}")
        pyautogui.press("escape")
        return "failed", "Unknown", "00m00s"

    song_name = os.path.splitext(os.path.basename(mp3_path))[0]
    duration = _get_duration(mp3_path)

    if _is_already_downloaded(song_name, duration):
        events.on_log(f"  {C_WARN}ALREADY DOWNLOADED: {song_name} ({duration}) — skipping{C_RESET}")
        os.remove(mp3_path)
        pyautogui.press("escape")
        time.sleep(1)
        return "duplicate", song_name, duration

    events.on_log(f"  New song: {song_name} ({duration}) — downloading remaining formats")

    # Step 4: Click RAW Download
    if not _click_modal_row("modal_raw.png", "RAW Download", events):
        events.on_log(f"  {C_WARN}RAW not found — skipping{C_RESET}")
    else:
        events.on_log(f"  {C_DONE}RAW ✓{C_RESET}")

    # Step 5: Click LRC Download
    if not _click_modal_row("modal_lrc.png", "LRC Download", events):
        events.on_log(f"  {C_WARN}LRC not found — skipping{C_RESET}")
    else:
        events.on_log(f"  {C_DONE}LRC ✓{C_RESET}")

    # Step 6: Click VIDEO Download (both modals close automatically)
    mp4s_before = set(glob.glob(os.path.join(DL_DIR, "*.mp4")))

    if not _click_modal_row("modal_video.png", "VIDEO Download", events):
        events.on_log(f"  {C_WARN}VIDEO not found — skipping{C_RESET}")
        pyautogui.press("escape")
        time.sleep(1)
        _wait_for_downloads_complete(events)
        new_files = _get_dl_files() - files_before
        _move_to_subfolder(new_files, song_num, events)
        return "ok", song_name, duration

    # Step 7: Click Download in Lyric Video modal (closes both modals automatically)
    time.sleep(1)
    if _click_template("lyric_video_download.png", "Video DL Button", events, VIDEO_DL_THRESHOLD):
        events.on_log(f"  {C_DONE}VIDEO DL ✓{C_RESET}")
        _wait_for_video_download(mp4s_before, events)
    else:
        events.on_log(f"  {C_WARN}Video DL button not found{C_RESET}")
        pyautogui.press("escape")
        time.sleep(1)

    _wait_for_downloads_complete(events)

    new_files = _get_dl_files() - files_before
    _move_to_subfolder(new_files, song_num, events)
    return "ok", song_name, duration


# ── Main download loop ───────────────────────────────────────────────

def run_task(
    max_songs: int = 50,
    max_scrolls: int = 15,
    start_num: int = 0,
    events: OrchestratorEvents | None = None,
) -> bool:
    """Download all songs by finding download icons top-to-bottom.

    Pre-created folders are used for duplicate detection: if a folder
    already has files, the song is skipped (only MP3 downloaded + checked).
    """
    if events is None:
        events = PrintEvents()

    song_count = start_num
    duplicates = 0
    failures = 0
    last_bottom_y = 0

    os.makedirs(TUNEE_DIR, exist_ok=True)

    status = get_project_status()
    events.on_log(f"\n{'=' * 60}")
    events.on_log(f"  Template Downloader — max {max_songs} songs")
    events.on_log(f"  Output: {TUNEE_DIR}")
    if status["total"] > 0:
        events.on_log(f"  Projekt: {status['total']} Songs, "
                      f"{status['complete']} fertig, {status['missing']} fehlend")
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
            events.on_log(f"{C_ERR}No download icons found on screen (round {scroll_round}){C_RESET}")
            events.on_log(f"  Saving debug screenshot to /tmp/cgc_debug_no_icons.png")
            import cv2 as _cv2
            _cv2.imwrite("/tmp/cgc_debug_no_icons.png", screenshot)
            break

        icons.sort(key=lambda m: m[1])
        events.on_icons_found(len(icons), scroll_round)

        if scroll_round == 0:
            min_y = 0
        else:
            # After scroll, only skip icons in the very top (likely still
            # visible from the previous round).  Use 15% of screen height
            # as cutoff — anything below is treated as new content.
            # Duplicate detection via folder check handles any re-encounters.
            _, sh = get_screen_size()
            min_y = int(sh * 0.15)

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
                events.on_song_complete(song_count, f"{_sanitize(song_name)} - {duration}")
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
    events.on_log(f"  Done! Downloaded {song_count} new songs to {TUNEE_DIR}")
    if duplicates:
        events.on_log(f"  ({duplicates} already downloaded — skipped)")
    if failures:
        events.on_log(f"  ({failures} failures)")
    events.on_log(f"{'=' * 60}")
    events.on_progress(song_count, max_songs)
    return song_count > 0
