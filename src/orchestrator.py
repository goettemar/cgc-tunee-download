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
    "You are on tunee.ai looking at a list of songs. "
    "Your goal: download every song one by one. "
    "For each song:\n"
    "1. Hover over the song row to reveal the action icons.\n"
    "2. Click the download icon (down-arrow icon) on that row.\n"
    "3. A download modal appears with buttons: MP3, RAW, VIDEO, LRC.\n"
    "4. Click 'MP3 Download' and wait 2 seconds.\n"
    "5. Click 'RAW Download' and wait 2 seconds.\n"
    "6. Click 'LRC Download' (skip if greyed out) and wait 2 seconds.\n"
    "7. Close the modal (click X or outside it).\n"
    "8. Move to the next song and repeat.\n"
    "9. When all songs are downloaded, call finished().\n\n"
    "Important: Only perform ONE action per step. "
    "If a download button starts a file download, just wait for it — don't navigate away."
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

    history: list[dict] = []

    print(f"\n{C_STEP}{'=' * 60}")
    print(f"  VLM Agent — max {max_steps} steps")
    print(f"{'=' * 60}{C_RESET}\n")

    for step in range(1, max_steps + 1):
        print(f"{C_STEP}[Step {step}/{max_steps}]{C_RESET} Taking screenshot...")

        screenshot_b64 = take_screenshot()

        print(f"  Asking VLM...")
        try:
            response = ask_vlm(screenshot_b64, task, history)
        except Exception as e:
            print(f"  {C_ERR}VLM error: {e}{C_RESET}")
            time.sleep(2)
            continue

        parsed = parse_response(response)

        print(f"  {C_THOUGHT}Thought: {parsed.thought}{C_RESET}")
        print(f"  {C_ACTION}Action:  {parsed.action_type}({parsed.params}){C_RESET}")

        # Append to history for context
        history.append({"role": "assistant", "content": response})

        if dry_run:
            print(f"  (dry-run — skipping execution)")
            if parsed.action_type == "finished":
                print(f"\n{C_DONE}Task would be finished.{C_RESET}")
                return True
            time.sleep(0.5)
            continue

        try:
            finished = execute(parsed)
        except Exception as e:
            print(f"  {C_ERR}Execution error: {e}{C_RESET}")
            history.append({"role": "user", "content": f"Error executing action: {e}. Try a different approach."})
            time.sleep(2)
            continue

        if finished:
            print(f"\n{C_DONE}Task finished successfully!{C_RESET}")
            return True

        # Wait between steps for UI to settle
        time.sleep(2)

        # Keep history manageable (last 10 exchanges)
        if len(history) > 20:
            history = history[-20:]

    print(f"\n{C_ERR}Max steps ({max_steps}) reached without finishing.{C_RESET}")
    return False
