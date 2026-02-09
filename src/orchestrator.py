"""Agent loop: screenshot -> VLM -> parse -> execute -> repeat."""

from __future__ import annotations

import time

from .screenshot import take_screenshot
from .vlm import ask_vlm
from .actions import parse_response, execute

# ANSI colors for terminal output
C_STEP = "\033[1;36m"    # cyan bold
C_THOUGHT = "\033[0;33m" # yellow
C_ACTION = "\033[0;32m"  # green
C_DONE = "\033[1;32m"    # green bold
C_ERR = "\033[0;31m"     # red
C_RESET = "\033[0m"

TASK_DOWNLOAD_ALL = (
    "Go to the music list on tunee.ai. Download every song one by one. "
    "For each song: hover over the song row to reveal icons, "
    "click the download icon (down-arrow), "
    "then in the modal click MP3 Download, wait 2 seconds, "
    "click RAW Download, wait 2 seconds, "
    "click LRC Download (skip if greyed out), wait 2 seconds, "
    "close the modal, and move to the next song. "
    "When all songs are downloaded, call finished()."
)


def run_task(task: str | None = None, max_steps: int = 30, dry_run: bool = False) -> bool:
    """Run the VLM agent loop.

    Args:
        task: Task description. Defaults to TASK_DOWNLOAD_ALL.
        max_steps: Maximum number of actions before giving up.
        dry_run: If True, print parsed actions but don't execute them.

    Returns:
        True if the task finished successfully, False if max_steps reached.
    """
    if task is None:
        task = TASK_DOWNLOAD_ALL

    action_history: list[str] = []

    print(f"\n{C_STEP}{'=' * 60}")
    print(f"  VLM Agent — max {max_steps} steps")
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

        # Append raw response to action history for context
        action_history.append(response.strip())

        if dry_run:
            print(f"  (dry-run — skipping execution)")
            if parsed.action_type == "finished":
                print(f"\n{C_DONE}Task would be finished.{C_RESET}")
                return True
            time.sleep(0.5)
            continue

        try:
            finished = execute(parsed, img_size)
        except Exception as e:
            print(f"  {C_ERR}Execution error: {e}{C_RESET}")
            action_history.append(f"Error: {e}")
            time.sleep(2)
            continue

        if finished:
            print(f"\n{C_DONE}Task finished successfully!{C_RESET}")
            return True

        # Wait between steps for UI to settle
        time.sleep(2)

        # Keep history manageable (last 10 exchanges)
        if len(action_history) > 10:
            action_history = action_history[-10:]

    print(f"\n{C_ERR}Max steps ({max_steps}) reached without finishing.{C_RESET}")
    return False
