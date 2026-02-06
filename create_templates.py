#!/usr/bin/env python3
"""
Interactive Template Creator

Hilft beim Erstellen der Template-Screenshots für PyAutoGUI.
"""

import time
import pyautogui
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def countdown(seconds: int, message: str):
    """Countdown mit Nachricht."""
    print(f"\n{message}")
    for i in range(seconds, 0, -1):
        print(f"   {i}...", end="\r")
        time.sleep(1)
    print("   📸 Screenshot!")


def create_template(name: str, instructions: str, countdown_time: int = 5):
    """
    Erstellt ein Template-Screenshot.

    Args:
        name: Name des Templates (ohne .png)
        instructions: Anweisungen für den User
        countdown_time: Countdown-Zeit in Sekunden
    """
    print(f"\n{'='*60}")
    print(f"Template: {name}.png")
    print(f"{'='*60}")
    print(instructions)

    input("\n[ENTER] wenn bereit für Screenshot...")

    countdown(countdown_time, "Positioniere Maus und warte...")

    # Screenshot der ganzen Screen
    screenshot = pyautogui.screenshot()

    # Hole Mausposition
    x, y = pyautogui.position()
    print(f"Maus-Position: {x}, {y}")

    # Frage nach Region
    print("\nWie groß ist der Button?")
    print("1. Klein (~20x20px) - Icon")
    print("2. Mittel (~100x40px) - Button mit Text")
    print("3. Groß (~200x50px) - Großer Button")
    print("4. Manuell eingeben")

    choice = input("Wahl [1-4]: ").strip()

    if choice == "1":
        width, height = 20, 20
    elif choice == "2":
        width, height = 100, 40
    elif choice == "3":
        width, height = 200, 50
    elif choice == "4":
        width = int(input("Breite (px): "))
        height = int(input("Höhe (px): "))
    else:
        width, height = 100, 40

    # Region um Mausposition ausschneiden
    left = x - width // 2
    top = y - height // 2
    right = left + width
    bottom = top + height

    # Crop
    template = screenshot.crop((left, top, right, bottom))

    # Speichern
    output_path = TEMPLATES_DIR / f"{name}.png"
    template.save(output_path)

    print(f"✅ Gespeichert: {output_path}")

    # Vorschau (optional)
    preview = input("Vorschau anzeigen? [y/N]: ").lower()
    if preview == "y":
        template.show()


def main():
    """Hauptprogramm."""

    print("""
╔══════════════════════════════════════════════════════════════╗
║         Template Creator für Tunee Downloader                ║
╚══════════════════════════════════════════════════════════════╝

Dieser Wizard hilft dir, die benötigten Template-Screenshots
für die PyAutoGUI-basierte Automation zu erstellen.

VORBEREITUNG:
1. Öffne tunee.ai Conversation mit Songs im Browser
2. Stelle Browser auf ~1920x1080 (oder deine Standard-Auflösung)
3. Zoom auf 100%
4. Platziere Browserfenster mittig auf Screen

TIPP: Nutze flameshot oder gnome-screenshot für manuelle Kontrolle!
      Dieses Script ist nur ein Helper.
    """)

    ready = input("Bereit? [ENTER zum Starten, 'q' zum Abbrechen]: ")
    if ready.lower() == "q":
        return

    TEMPLATES_DIR.mkdir(exist_ok=True)

    # Template 1: Download-Button
    create_template(
        "download_button",
        """
1. Hover über einen Song in der linken Liste
2. Warte bis Download-Button erscheint (Icon neben Stern)
3. Positioniere Maus GENAU über dem Download-Icon
4. Drücke ENTER und lass Maus dort!
        """,
        countdown_time=3
    )

    # Template 2-5: Modal Buttons
    print("\n\nJetzt öffnen wir das Download-Modal...")
    input("Klicke auf Download-Button um Modal zu öffnen, dann [ENTER]")

    for name, label in [
        ("modal_mp3", "MP3 Button (erster Button)"),
        ("modal_raw", "RAW/FLAC Button (zweiter Button)"),
        ("modal_video", "VIDEO Button (dritter Button)"),
        ("modal_lrc", "LRC Button (vierter Button, kann ausgegraut sein)"),
    ]:
        create_template(
            name,
            f"""
Positioniere Maus über: {label}
(Mitte des Buttons)
            """,
            countdown_time=3
        )

    # Template 6: Lyric Video Download
    print("\n\nJetzt das Lyric Video Modal...")
    input("Klicke auf VIDEO-Button, warte bis Modal öffnet, dann [ENTER]")

    create_template(
        "lyric_video_download",
        """
Positioniere Maus über den Download-Button
(oben rechts im Lyric Video Modal)
        """,
        countdown_time=3
    )

    print("""

╔══════════════════════════════════════════════════════════════╗
║                  ✅ FERTIG!                                  ║
╚══════════════════════════════════════════════════════════════╝

Alle Templates wurden erstellt und sind in:
  """ + str(TEMPLATES_DIR) + """

NÄCHSTE SCHRITTE:
1. Prüfe die Templates (optional):
   python -c "from PIL import Image; Image.open('templates/download_button.png').show()"

2. Teste den Hybrid-Browser:
   python test_hybrid_browser.py

3. Starte Download mit GUI:
   ./start.sh
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Abgebrochen.")
    except Exception as e:
        print(f"\n\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
