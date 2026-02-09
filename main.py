#!/usr/bin/env python3
"""CGC Tunee Download — Template-based song downloader.

Uses OpenCV template matching to navigate tunee.ai
and download songs using PyAutoGUI.
"""

import argparse
import os
import subprocess
import sys
import time

from src.orchestrator import run_task
from src.screenshot import set_monitor, list_monitors

TUNEE_URL = "https://www.tunee.ai"


def launch_chrome(url: str) -> subprocess.Popen:
    """Launch Chrome with the tunee cookie profile, allowing multiple downloads."""
    cache_dir = os.path.expanduser("~/.cache/cgc_tunee_download/chrome_profile")
    cmd = [
        "google-chrome",
        f"--user-data-dir={cache_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        f"--window-size=1920,1080",
        url,
    ]
    print(f"[INFO] Launching Chrome: {url}")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description="CGC Tunee Download")
    parser.add_argument("--no-chrome", action="store_true",
                        help="Don't launch Chrome (assume it's already open)")
    parser.add_argument("--songs", type=int, default=50,
                        help="Max songs to download (default: 50)")
    parser.add_argument("--url", type=str, default=TUNEE_URL,
                        help=f"Tunee URL to open (default: {TUNEE_URL})")
    parser.add_argument("--monitor", type=int, default=3,
                        help="Monitor index to capture (1-based, default: 3 = left)")
    parser.add_argument("--list-monitors", action="store_true",
                        help="List available monitors and exit")
    args = parser.parse_args()

    # List monitors mode
    if args.list_monitors:
        monitors = list_monitors()
        for i, m in enumerate(monitors):
            label = "all combined" if i == 0 else f"monitor {i}"
            print(f"  {i}: {label} — {m['width']}x{m['height']} @ ({m['left']}, {m['top']})")
        return

    # Set monitor before anything else
    set_monitor(args.monitor)

    print()
    print("=" * 50)
    print("  CGC Tunee Download — Template Matching")
    print("=" * 50)
    print()

    # Show monitor info
    monitors = list_monitors()
    mon = monitors[args.monitor]
    print(f"[OK]   Monitor {args.monitor}: {mon['width']}x{mon['height']} "
          f"@ ({mon['left']}, {mon['top']})")

    # Check display
    display = os.environ.get("DISPLAY")
    if not display:
        print("[FAIL] $DISPLAY not set — need X11 display")
        sys.exit(1)
    print(f"[OK]   Display: {display}")
    print()

    # Launch Chrome
    chrome_proc = None
    if not args.no_chrome:
        chrome_proc = launch_chrome(args.url)
        time.sleep(3)

    # Wait for user confirmation
    try:
        input("[WAIT] Press Enter when tunee.ai is open with the song list visible... ")
    except KeyboardInterrupt:
        print("\n[ABORT] Cancelled by user.")
        if chrome_proc:
            chrome_proc.terminate()
        sys.exit(0)

    print()
    success = run_task(max_songs=args.songs)

    if chrome_proc:
        print("[INFO] Chrome is still running — close manually when done.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
