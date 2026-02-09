"""State-machine orchestrator: manages song download sequence, VLM handles clicking."""

from __future__ import annotations

import time
from enum import Enum, auto

import pyautogui

from .screenshot import take_screenshot
from .vlm import ask_vlm
from .actions import parse_response, execute

# ANSI colors for terminal output
C_STEP = "\033[1;36m"    # cyan bold
C_THOUGHT = "\033[0;33m" # yellow
C_ACTION = "\033[0;32m"  # green
C_DONE = "\033[1;32m"    # green bold
C_ERR = "\033[0;31m"     # red
C_WARN = "\033[0;35m"    # magenta
C_STATE = "\033[1;33m"   # yellow bold
C_RESET = "\033[0m"


class State(Enum):
    """Download workflow states — one simple instruction per state."""
    SELECT_SONG = auto()
    OPEN_MODAL = auto()
    CLICK_MP3 = auto()
    CLICK_RAW = auto()
    CLICK_LRC = auto()
    CLICK_VIDEO = auto()
    CLICK_VIDEO_DL = auto()


# Simple, focused prompts for each state — the VLM only needs to do ONE thing
STATE_PROMPTS = {
    State.SELECT_SONG: (
        "You see tunee.ai with a song list on the left side. "
        "Click on the NEXT song name in the list — pick the one below the "
        "currently highlighted/selected song. If no song is highlighted, "
        "click the first song at the top. "
        "If there are no more songs visible in the list, call finished(). "
        "Do NOT call wait(). Just click the song name."
    ),
    State.OPEN_MODAL: (
        "You just clicked on a song. Small icons appeared on the right side of "
        "that song row (star, download arrow, etc.). "
        "Click the download arrow icon (small down-pointing arrow) on that row. "
        "Do NOT call wait()."
    ),
    State.CLICK_MP3: (
        "A download modal is open with buttons: MP3 Download, RAW Download, VIDEO, LRC Download. "
        "Click the 'MP3 Download' button. Do NOT call wait()."
    ),
    State.CLICK_RAW: (
        "The download modal is still open with buttons: MP3 Download, RAW Download, VIDEO, LRC Download. "
        "Click the 'RAW Download' button. Do NOT call wait()."
    ),
    State.CLICK_LRC: (
        "The download modal is still open with buttons: MP3 Download, RAW Download, VIDEO, LRC Download. "
        "Click the 'LRC Download' button. "
        "If 'LRC Download' is greyed out or disabled, call finished() to skip it. "
        "Do NOT call wait()."
    ),
    State.CLICK_VIDEO: (
        "The download modal is still open with buttons: MP3 Download, RAW Download, VIDEO, LRC Download. "
        "Click the 'VIDEO' button. This will open a second modal. "
        "Do NOT call wait()."
    ),
    State.CLICK_VIDEO_DL: (
        "A video download modal is open on top of the download modal. "
        "Click the download button in this video modal. "
        "This will close both modals. Do NOT call wait()."
    ),
}

# State transitions: current → next
NEXT_STATE = {
    State.SELECT_SONG: State.OPEN_MODAL,
    State.OPEN_MODAL: State.CLICK_MP3,
    State.CLICK_MP3: State.CLICK_RAW,
    State.CLICK_RAW: State.CLICK_LRC,
    State.CLICK_LRC: State.CLICK_VIDEO,
    State.CLICK_VIDEO: State.CLICK_VIDEO_DL,
    State.CLICK_VIDEO_DL: State.SELECT_SONG,
}

# Max retries per state before forcing advance
MAX_RETRIES_PER_STATE = 5
# Max scroll attempts before declaring "all done"
MAX_SCROLLS = 10


def _action_signature(parsed) -> str:
    """Create a short key for loop detection."""
    at = parsed.action_type
    box = parsed.params.get("start_box", "")
    return f"{at}:{box}" if box else at


def run_task(task: str | None = None, max_steps: int = 30, dry_run: bool = False) -> bool:
    """Run the state-machine download loop.

    The orchestrator tracks which download step we're on and gives the VLM
    a simple, focused instruction. The VLM just needs to find and click
    one element per step.
    """
    state = State.SELECT_SONG
    song_count = 0
    retries = 0
    last_sig = ""
    scrolls_without_new_song = 0

    print(f"\n{C_STEP}{'=' * 60}")
    print(f"  VLM State Machine — max {max_steps} steps")
    print(f"{'=' * 60}{C_RESET}\n")

    for step in range(1, max_steps + 1):
        prompt = STATE_PROMPTS[state]

        print(f"{C_STEP}[Step {step}/{max_steps}]{C_RESET} "
              f"{C_STATE}State: {state.name}{C_RESET}")

        screenshot_b64, img_size = take_screenshot()

        print(f"  Asking VLM (image {img_size[0]}x{img_size[1]})...")
        try:
            response = ask_vlm(screenshot_b64, prompt)
        except Exception as e:
            print(f"  {C_ERR}VLM error: {e}{C_RESET}")
            time.sleep(2)
            continue

        parsed = parse_response(response)

        print(f"  {C_THOUGHT}Thought: {parsed.thought}{C_RESET}")
        print(f"  {C_ACTION}Action:  {parsed.action_type}({parsed.params}){C_RESET}")

        # Handle finished() — meaning depends on state
        if parsed.action_type == "finished":
            if state == State.SELECT_SONG:
                # No more visible songs — scroll down to check for more
                if scrolls_without_new_song < MAX_SCROLLS:
                    scrolls_without_new_song += 1
                    print(f"  {C_WARN}No visible songs — scrolling down "
                          f"({scrolls_without_new_song}/{MAX_SCROLLS}){C_RESET}")
                    # Scroll the song list on the left side
                    from .screenshot import get_screen_size, get_monitor_offset
                    sw, sh = get_screen_size()
                    off_x, off_y = get_monitor_offset()
                    # Scroll in the left panel area (roughly x=200, y=center)
                    scroll_x = round(sw * 0.15) + off_x
                    scroll_y = round(sh * 0.5) + off_y
                    pyautogui.scroll(-5, x=scroll_x, y=scroll_y)
                    time.sleep(2)
                    continue
                else:
                    print(f"\n{C_DONE}All songs downloaded! ({song_count} songs){C_RESET}")
                    return True
            elif state == State.CLICK_LRC:
                # LRC greyed out — skip to VIDEO
                print(f"  {C_WARN}LRC skipped (greyed out){C_RESET}")
                state = State.CLICK_VIDEO
                retries = 0
                last_sig = ""
                continue
            else:
                # Spurious finished() in other states — ignore and retry
                print(f"  {C_WARN}Ignoring finished() in state {state.name}{C_RESET}")
                retries += 1
                continue

        # Suppress wait() — never useful in state machine mode
        if parsed.action_type == "wait":
            print(f"  {C_WARN}Suppressing wait() — not needed{C_RESET}")
            retries += 1
            if retries >= MAX_RETRIES_PER_STATE:
                print(f"  {C_WARN}Max retries in {state.name} — advancing{C_RESET}")
                state = NEXT_STATE[state]
                retries = 0
                last_sig = ""
            continue

        # Loop detection — same click repeated
        sig = _action_signature(parsed)
        if sig == last_sig and parsed.action_type == "click":
            retries += 1
            if retries >= MAX_RETRIES_PER_STATE:
                print(f"  {C_WARN}[LOOP] {sig} repeated {retries}x in {state.name} — "
                      f"pressing Escape and advancing{C_RESET}")
                pyautogui.press("escape")
                time.sleep(1)
                state = NEXT_STATE[state]
                retries = 0
                last_sig = ""
                continue
        else:
            retries = 0
            last_sig = sig

        if dry_run:
            print(f"  (dry-run — skipping)")
            time.sleep(0.3)
        else:
            try:
                execute(parsed, img_size)
            except Exception as e:
                print(f"  {C_ERR}Execution error: {e}{C_RESET}")
                retries += 1
                time.sleep(1)
                continue

        # Advance state after successful click
        prev_state = state
        state = NEXT_STATE[state]
        retries = 0
        last_sig = ""

        # Reset scroll counter when we start a new song download
        if prev_state == State.SELECT_SONG:
            scrolls_without_new_song = 0

        if prev_state == State.CLICK_VIDEO_DL:
            song_count += 1
            print(f"  {C_DONE}Song #{song_count} complete!{C_RESET}")

        # Brief pause for UI to settle
        time.sleep(1.5)

    print(f"\n{C_ERR}Max steps ({max_steps}) reached. "
          f"Downloaded {song_count} songs.{C_RESET}")
    return False


def run_task_freeform(task: str, max_steps: int = 30, dry_run: bool = False) -> bool:
    """Run the original free-form VLM agent loop (for custom tasks)."""
    action_history: list[str] = []

    print(f"\n{C_STEP}{'=' * 60}")
    print(f"  VLM Agent (freeform) — max {max_steps} steps")
    print(f"{'=' * 60}{C_RESET}\n")

    for step in range(1, max_steps + 1):
        print(f"{C_STEP}[Step {step}/{max_steps}]{C_RESET} Taking screenshot...")

        screenshot_b64, img_size = take_screenshot()

        print(f"  Asking VLM (image {img_size[0]}x{img_size[1]})...")
        try:
            response = ask_vlm(screenshot_b64, task, action_history or None)
        except Exception as e:
            print(f"  {C_ERR}VLM error: {e}{C_RESET}")
            time.sleep(2)
            continue

        parsed = parse_response(response)

        print(f"  {C_THOUGHT}Thought: {parsed.thought}{C_RESET}")
        print(f"  {C_ACTION}Action:  {parsed.action_type}({parsed.params}){C_RESET}")

        if parsed.action_type != "unknown":
            at = parsed.action_type
            box = parsed.params.get("start_box", "")
            entry = f"Step {step}: {at}({box})" if box else f"Step {step}: {at}()"
            action_history.append(entry)

        if dry_run:
            if parsed.action_type == "finished":
                print(f"\n{C_DONE}Task would be finished.{C_RESET}")
                return True
            time.sleep(0.5)
            continue

        try:
            finished = execute(parsed, img_size)
        except Exception as e:
            print(f"  {C_ERR}Execution error: {e}{C_RESET}")
            time.sleep(2)
            continue

        if finished:
            print(f"\n{C_DONE}Task finished successfully!{C_RESET}")
            return True

        time.sleep(1.5)

        if len(action_history) > 15:
            action_history = action_history[-15:]

    print(f"\n{C_ERR}Max steps ({max_steps}) reached without finishing.{C_RESET}")
    return False
