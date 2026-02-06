#!/usr/bin/env python3
"""
Einfacher Template-Test ohne GUI-Dependencies
"""

import sys
from pathlib import Path

# Disable tkinter warnings
import warnings
warnings.filterwarnings("ignore")

try:
    import pyautogui
    print("✅ PyAutoGUI importiert")
except Exception as e:
    print(f"❌ PyAutoGUI Import-Fehler: {e}")
    sys.exit(1)

def test_templates():
    """Testet ob alle Templates vorhanden sind."""
    templates_dir = Path(__file__).parent / "templates"

    required_templates = [
        "download_button.png",
        "modal_mp3.png",
        "modal_raw.png",
        "modal_video.png",
        "modal_lrc.png",
        "lyric_video_download.png",
    ]

    print("\n" + "="*60)
    print("Template-Check")
    print("="*60)

    all_found = True
    for template in required_templates:
        path = templates_dir / template
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {template:30} ({size:>6} bytes)")
        else:
            print(f"❌ {template:30} FEHLT!")
            all_found = False

    if not all_found:
        print("\n❌ Nicht alle Templates vorhanden!")
        return False

    print("\n✅ Alle Templates vorhanden!")
    return True


def test_screen_matching():
    """Testet Template-Matching auf aktuellem Screen."""

    print("\n" + "="*60)
    print("Screen-Matching Test")
    print("="*60)
    print("\n💡 Öffne tunee.ai im Browser und hover über einen Song...")
    print("   Das Script sucht dann nach den Buttons auf dem Screen.\n")

    input("Drücke ENTER wenn bereit...")

    templates_dir = Path(__file__).parent / "templates"

    # Teste nur die wichtigsten Templates
    test_templates = [
        ("download_button", 0.8),
        ("modal_mp3", 0.85),
    ]

    for template_name, confidence in test_templates:
        template_path = templates_dir / f"{template_name}.png"

        print(f"\n🔍 Suche: {template_name}.png (confidence={confidence})")

        try:
            location = pyautogui.locateOnScreen(str(template_path), confidence=confidence)

            if location:
                center = pyautogui.center(location)
                print(f"   ✅ GEFUNDEN bei: x={center.x}, y={center.y}")
                print(f"      Größe: {location.width}x{location.height}")
            else:
                print(f"   ⚠️  Nicht gefunden")
                print(f"      (Normal wenn Button nicht sichtbar)")

        except Exception as e:
            print(f"   ❌ Fehler: {e}")

    print("\n" + "="*60)


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              Template Test (ohne tkinter)                    ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Test 1: Templates vorhanden?
    if not test_templates():
        return

    # Test 2: Screen-Matching?
    choice = input("\nScreen-Matching testen? [y/N]: ").lower()
    if choice == "y":
        test_screen_matching()

    print("\n✅ Tests abgeschlossen!")


if __name__ == "__main__":
    main()
