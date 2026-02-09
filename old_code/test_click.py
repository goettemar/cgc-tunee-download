#!/usr/bin/env python3
"""
Einfacher Klick-Test für PyAutoGUI

Findet Download-Button und klickt darauf.
"""

import time
import pyautogui
from pathlib import Path

def test_download_button_click():
    """Findet und klickt den Download-Button."""

    templates_dir = Path(__file__).parent / "templates"

    print("\n" + "="*60)
    print("PyAutoGUI Klick-Test")
    print("="*60)
    print("\n1. Öffne tunee.ai im Browser (rechter Monitor)")
    print("2. Hover über einen Song (Download-Button sichtbar)")
    print("3. Das Script klickt dann auf den Button\n")

    input("Drücke ENTER wenn bereit...")

    print("\n🔍 Suche Download-Button...")

    template_path = templates_dir / "download_button.png"
    location = pyautogui.locateOnScreen(str(template_path), confidence=0.8)

    if not location:
        print("❌ Download-Button nicht gefunden!")
        print("   - Ist der Song gehovered?")
        print("   - Ist der Browser auf dem rechten Monitor?")
        print("   - Ist der Browser-Zoom 100%?")
        return False

    center = pyautogui.center(location)
    print(f"✅ Download-Button gefunden bei: x={center.x}, y={center.y}")

    # Countdown vor Klick
    print("\n⏱️ Klicke in 3 Sekunden...")
    for i in range(3, 0, -1):
        print(f"   {i}...")
        time.sleep(1)

    # KLICK!
    print(f"\n🖱️ KLICK auf {center.x}, {center.y}")
    pyautogui.click(center.x, center.y)

    print("\n✅ Klick ausgeführt!")
    print("   → Das Modal sollte jetzt geöffnet sein")

    # Warte kurz
    time.sleep(2)

    # Suche nach Modal-Buttons (position-basiert)
    print("\n🔍 Suche Modal-Buttons...")

    # STRATEGIE: Finde nur MP3 (erste Zeile), dann position-basiert für Rest
    # Grund: Alle Zeilen sehen ähnlich aus, PyAutoGUI findet sonst immer MP3

    template_path = templates_dir / "modal_mp3.png"
    mp3_location = pyautogui.locateOnScreen(str(template_path), confidence=0.85)

    if not mp3_location:
        print("   ❌ MP3 nicht gefunden - Modal nicht geöffnet?")
        return True

    mp3_center = pyautogui.center(mp3_location)
    print(f"   ✅ MP3 gefunden bei x={mp3_center.x}, y={mp3_center.y}")

    # Berechne Positionen der anderen Buttons (relativ zu MP3)
    # Modal-Reihenfolge: MP3, RAW, VIDEO, LRC (von oben nach unten)
    # Klick-Reihenfolge: MP3, RAW, LRC, VIDEO (LRC vor VIDEO!)

    # WICHTIG: VIDEO muss ZULETZT geklickt werden! (schließt das Modal)
    found_buttons = [
        ("MP3", mp3_center),                                                             # Zeile 1
        ("RAW", type('obj', (object,), {'x': mp3_center.x, 'y': mp3_center.y + 100})()),  # Zeile 2
        ("LRC", type('obj', (object,), {'x': mp3_center.x, 'y': mp3_center.y + 300})()),  # Zeile 4!
        ("VIDEO", type('obj', (object,), {'x': mp3_center.x, 'y': mp3_center.y + 200})()),  # Zeile 3!
    ]

    for label, center in found_buttons:
        print(f"   → {label} Position: x={center.x}, y={center.y}")

    if found_buttons:
        print(f"\n✅ Modal ist geöffnet! {len(found_buttons)} Buttons gefunden")

        # Frage ob wir klicken sollen
        choice = input("\nAuf die Buttons klicken? [y/N]: ").lower()

        if choice == "y":
            # Offset: Klicke rechts vom Template-Center (auf den schwarzen "Download" Button)
            # Template = ganze Zeile (~400-500px), Download-Button ist bei ~80-90% der Breite
            offset_x = 150  # 150 Pixel nach rechts (zur Mitte des Download-Buttons)

            for label, center in found_buttons:
                click_x = center.x + offset_x
                click_y = center.y
                print(f"\n🖱️ Klicke {label} bei x={click_x}, y={click_y} (Offset +{offset_x}px)...")
                pyautogui.click(click_x, click_y)
                time.sleep(2)  # Warte auf Download

            print("\n✅ Alle 4 Buttons geklickt!")

            # VIDEO öffnet das Lyric Video Modal
            print("\n⏱️ Warte auf Lyric Video Modal...")
            time.sleep(3)  # Warte bis Modal geöffnet ist

            # Suche Download-Button im Lyric Video Modal
            print("🔍 Suche Download-Button im Lyric Video Modal...")
            lyric_template = templates_dir / "lyric_video_download.png"
            lyric_location = pyautogui.locateOnScreen(str(lyric_template), confidence=0.85)

            if lyric_location:
                lyric_center = pyautogui.center(lyric_location)
                print(f"   ✅ Lyric Video Download gefunden bei x={lyric_center.x}, y={lyric_center.y}")

                print("\n🖱️ Klicke Lyric Video Download...")
                pyautogui.click(lyric_center.x, lyric_center.y)
                time.sleep(2)

                print("\n✅ VIDEO Download gestartet!")
            else:
                print("   ❌ Lyric Video Download-Button nicht gefunden")
                print("      Ist das Lyric Video Modal geöffnet?")

            print("\n✅ Alle Downloads abgeschlossen!")
    else:
        print("\n⚠️ Modal-Buttons nicht gefunden")
        print("   Ist das Modal wirklich geöffnet?")

    return True


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           PyAutoGUI Download-Button Klick-Test               ║
╚══════════════════════════════════════════════════════════════╝
    """)

    try:
        test_download_button_click()
    except KeyboardInterrupt:
        print("\n\n❌ Abgebrochen")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
