#!/usr/bin/env python3
"""CGC Tunee Download — Template-based song downloader.

Uses OpenCV template matching to navigate tunee.ai
and download songs using PyAutoGUI.

Modes:
  --gui     Launch PySide6 GUI (default)
  --cli     Run in command-line mode
"""

import argparse
import os
import subprocess
import sys
import time

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
        "--window-size=1920,1080",
        url,
    ]
    print(f"[INFO] Launching Chrome: {url}")
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_cert_cli(args) -> int:
    """CLI mode for certificate downloads."""
    from src.cert_orchestrator import run_cert_task
    from src.screenshot import set_monitor, list_monitors

    set_monitor(args.monitor)

    print()
    print("=" * 50)
    print("  CGC Tunee Download — Certificate Downloader")
    print("=" * 50)
    print()

    monitors = list_monitors()
    mon = monitors[args.monitor]
    print(f"[OK]   Monitor {args.monitor}: {mon['width']}x{mon['height']} "
          f"@ ({mon['left']}, {mon['top']})")
    print()

    try:
        input("[WAIT] Press Enter when tunee.ai is open with the song list visible... ")
    except KeyboardInterrupt:
        print("\n[ABORT] Cancelled by user.")
        return 0

    print()
    success = run_cert_task(max_songs=args.songs, max_scrolls=args.scrolls)
    return 0 if success else 1


def run_cli(args) -> int:
    """Original CLI mode."""
    from src.orchestrator import run_task
    from src.screenshot import set_monitor, list_monitors

    # List monitors mode
    if args.list_monitors:
        monitors = list_monitors()
        for i, m in enumerate(monitors):
            label = "all combined" if i == 0 else f"monitor {i}"
            print(f"  {i}: {label} — {m['width']}x{m['height']} @ ({m['left']}, {m['top']})")
        return 0

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
        return 1
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
        return 0

    print()
    success = run_task(max_songs=args.songs)

    if chrome_proc:
        print("[INFO] Chrome is still running — close manually when done.")

    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(description="CGC Tunee Download")

    # Mode selection
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--gui", action="store_true", default=True,
                      help="Launch PySide6 GUI (default)")
    mode.add_argument("--cli", action="store_true",
                      help="Run in command-line mode")

    # CLI-only arguments
    parser.add_argument("--cert", action="store_true",
                        help="[CLI] Download certificates instead of songs")
    parser.add_argument("--no-chrome", action="store_true",
                        help="[CLI] Don't launch Chrome (assume it's already open)")
    parser.add_argument("--songs", type=int, default=50,
                        help="[CLI] Max songs to download (default: 50)")
    parser.add_argument("--scrolls", type=int, default=15,
                        help="[CLI] Max scroll rounds (default: 15)")
    parser.add_argument("--url", type=str, default=TUNEE_URL,
                        help=f"[CLI] Tunee URL to open (default: {TUNEE_URL})")
    parser.add_argument("--monitor", type=int, default=3,
                        help="[CLI] Monitor index to capture (1-based, default: 3)")
    parser.add_argument("--list-monitors", action="store_true",
                        help="[CLI] List available monitors and exit")
    args = parser.parse_args()

    if args.cli and args.cert:
        sys.exit(run_cert_cli(args))
    elif args.cli:
        sys.exit(run_cli(args))
    else:
        from src.gui.app import run_gui
        sys.exit(run_gui())


if __name__ == "__main__":
    main()
