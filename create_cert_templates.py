#!/usr/bin/env python3
"""Interactive Template Creator for Certificate Downloads.

Guides the user through capturing 4 templates needed for the
certificate download workflow:
  1. Play button (overlay on song thumbnail)
  2. Three-dots menu in player modal
  3. "Copyright certificate" menu item
  4. Download button in certificate modal

Each step: position mouse over element -> press Enter -> script crops
a region around the mouse position -> saves as grayscale PNG.
"""

import sys
from pathlib import Path

import mss
import mss.tools
import numpy as np
from PIL import Image

TEMPLATES_DIR = Path(__file__).parent / "old_code" / "templates"

TEMPLATES = [
    {
        "name": "play_button",
        "size": (50, 50),
        "instructions": (
            "Schritt 1/4: PLAY-BUTTON\n"
            "  1. Hover ueber eine Song-Zeile in der Liste\n"
            "  2. Warte bis das Play-Overlay auf dem Thumbnail erscheint\n"
            "  3. Positioniere Maus GENAU ueber dem Play-Button\n"
            "  4. Druecke ENTER"
        ),
    },
    {
        "name": "three_dots",
        "size": (40, 40),
        "instructions": (
            "Schritt 2/4: DREI-PUNKTE-MENU\n"
            "  1. Klicke Play um den Player rechts zu oeffnen\n"
            "  2. Positioniere Maus ueber das 3-Punkte-Menu (... im Player)\n"
            "  3. Druecke ENTER"
        ),
    },
    {
        "name": "cert_menu_item",
        "size": (250, 45),
        "instructions": (
            'Schritt 3/4: "COPYRIGHT CERTIFICATE" MENU-EINTRAG\n'
            "  1. Klicke das 3-Punkte-Menu um es zu oeffnen\n"
            '  2. Positioniere Maus ueber "Copyright certificate" Text\n'
            "  3. Druecke ENTER"
        ),
    },
    {
        "name": "cert_download",
        "size": (60, 60),
        "instructions": (
            "Schritt 4/4: DOWNLOAD-BUTTON IM ZERTIFIKAT-MODAL\n"
            "  1. Klicke Copyright certificate um das Modal zu oeffnen\n"
            "  2. Positioniere Maus ueber den Download-Button (oben rechts)\n"
            "  3. Druecke ENTER"
        ),
    },
]


def capture_template(name: str, crop_w: int, crop_h: int) -> Path:
    """Take a screenshot, crop around mouse position, save as grayscale PNG."""
    import pyautogui

    x, y = pyautogui.position()

    with mss.mss() as sct:
        # Grab the monitor where the mouse is
        monitor = sct.monitors[0]  # full virtual screen
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    # Crop region centered on mouse
    left = max(0, x - crop_w // 2)
    top = max(0, y - crop_h // 2)
    right = left + crop_w
    bottom = top + crop_h

    cropped = img.crop((left, top, right, bottom))
    gray = cropped.convert("L")

    output = TEMPLATES_DIR / f"{name}.png"
    gray.save(output)
    return output


def main():
    print()
    print("=" * 60)
    print("  Certificate Template Creator")
    print("=" * 60)
    print()
    print("Erstellt die 4 Templates fuer den Zertifikat-Download.")
    print(f"Ausgabe-Ordner: {TEMPLATES_DIR}")
    print()
    print("VORBEREITUNG:")
    print("  1. Oeffne tunee.ai im Browser mit Song-Liste")
    print("  2. Browser auf Monitor positionieren")
    print()

    ready = input("Bereit? [ENTER zum Starten, 'q' zum Abbrechen]: ").strip()
    if ready.lower() == "q":
        return

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

    for tmpl in TEMPLATES:
        print()
        print("-" * 60)
        print(tmpl["instructions"])
        print("-" * 60)

        input("\n  [ENTER] wenn Maus positioniert ist...")

        w, h = tmpl["size"]
        out = capture_template(tmpl["name"], w, h)
        print(f"  Gespeichert: {out} ({w}x{h} px, grayscale)")

    print()
    print("=" * 60)
    print("  FERTIG! Alle 4 Certificate-Templates erstellt.")
    print("=" * 60)
    print()
    print("Naechste Schritte:")
    print("  1. Templates pruefen: ls -la old_code/templates/")
    print("  2. CLI-Test: ./start.sh --cli --cert --songs 2")
    print("  3. GUI-Test: ./start.sh  ->  'Zertifikate laden' Button")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAbgebrochen.")
        sys.exit(1)
