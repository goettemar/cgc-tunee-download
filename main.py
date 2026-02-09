#!/usr/bin/env python3
"""CGC Tunee Download — VLM-based song downloader.

Uses UI-TARS 1.5 7B via Ollama to visually navigate tunee.ai
and download songs using PyAutoGUI.
"""

import argparse
import os
import subprocess
import sys
import time

from src.vlm import check_ollama_running, check_model_available, MODEL
from src.orchestrator import run_task, TASK_DOWNLOAD_ALL

CHROME_PROFILE = os.path.join(os.path.dirname(__file__), "cookies", "chrome_profile")
TUNEE_URL = "https://www.tunee.ai"


def preflight_checks() -> bool:
    """Run preflight checks. Returns True if all pass."""
    ok = True

    # Display
    display = os.environ.get("DISPLAY")
    if not display:
        print("[FAIL] $DISPLAY not set — need X11 display")
        ok = False
    else:
        print(f"[OK]   Display: {display}")

    # Ollama
    if not check_ollama_running():
        print("[FAIL] Ollama not running — start with: sudo snap start ollama.ollama")
        ok = False
    else:
        print("[OK]   Ollama is running")

    # Model
    if ok and not check_model_available():
        print(f"[FAIL] Model {MODEL} not found — pull with: ollama pull {MODEL}")
        ok = False
    elif ok:
        print(f"[OK]   Model {MODEL} available")

    return ok


def launch_chrome(url: str) -> subprocess.Popen:
    """Launch Chrome with the tunee cookie profile."""
    cache_dir = os.path.expanduser("~/.cache/cgc_tunee_download/chrome_profile")
    cmd = [
        "google-chrome",
        f"--user-data-dir={cache_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--window-size=1920,1080",
        url,
    ]
    print(f"[INFO] Launching Chrome: {url}")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description="CGC Tunee Download — VLM Agent")
    parser.add_argument("--test", action="store_true",
                        help="Test mode: single screenshot + VLM call, no execution")
    parser.add_argument("--no-chrome", action="store_true",
                        help="Don't launch Chrome (assume it's already open)")
    parser.add_argument("--steps", type=int, default=50,
                        help="Max agent steps (default: 50)")
    parser.add_argument("--task", type=str, default=None,
                        help="Custom task prompt (default: download all songs)")
    parser.add_argument("--url", type=str, default=TUNEE_URL,
                        help=f"Tunee URL to open (default: {TUNEE_URL})")
    args = parser.parse_args()

    print()
    print("=" * 50)
    print("  CGC Tunee Download — VLM Agent")
    print("  Model: UI-TARS 1.5 7B via Ollama")
    print("=" * 50)
    print()

    # Preflight
    if not preflight_checks():
        print("\n[ABORT] Preflight checks failed.")
        sys.exit(1)

    print()

    # Test mode
    if args.test:
        print("[TEST] Running single VLM inference (dry-run)...")
        print()
        run_task(task=args.task, max_steps=1, dry_run=True)
        return

    # Launch Chrome
    chrome_proc = None
    if not args.no_chrome:
        chrome_proc = launch_chrome(args.url)
        time.sleep(3)

    # Wait for user confirmation
    try:
        input("[WAIT] Press Enter when you're logged into tunee.ai and ready... ")
    except KeyboardInterrupt:
        print("\n[ABORT] Cancelled by user.")
        if chrome_proc:
            chrome_proc.terminate()
        sys.exit(0)

    print()

    # Run agent
    success = run_task(task=args.task, max_steps=args.steps)

    if chrome_proc:
        print("[INFO] Chrome is still running — close manually when done.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
