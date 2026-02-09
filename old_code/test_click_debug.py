#!/usr/bin/env python3
"""
Debug-Version: Zeigt wo geklickt werden würde (ohne zu klicken)
"""

import time
import pyautogui
from pathlib import Path

templates_dir = Path(__file__).parent / "templates"

print("\n🔍 DEBUG MODE - Maus bewegt sich zu Klick-Positionen (ohne zu klicken)\n")
print("1. Öffne tunee.ai Download-Modal")
print("2. Das Script bewegt die Maus zu jeder Position")
print("3. Du siehst ob die Positionen stimmen\n")

input("Drücke ENTER wenn Modal offen ist...")

# 1. Finde MP3
template_path = templates_dir / "modal_mp3.png"
mp3_location = pyautogui.locateOnScreen(str(template_path), confidence=0.85)

if not mp3_location:
    print("❌ MP3 nicht gefunden")
    exit(1)

mp3_center = pyautogui.center(mp3_location)
print(f"✅ MP3 gefunden bei x={mp3_center.x}, y={mp3_center.y}\n")

# 2. Berechne Positionen
offset_x = 150

buttons = [
    ("MP3", mp3_center.x, mp3_center.y),
    ("RAW", mp3_center.x, mp3_center.y + 100),
    ("LRC", mp3_center.x, mp3_center.y + 300),
    ("VIDEO", mp3_center.x, mp3_center.y + 200),
]

print("Position-Check (mit +150px Offset für Download-Button):\n")

for label, base_x, base_y in buttons:
    click_x = base_x + offset_x
    click_y = base_y

    print(f"{label}:")
    print(f"  Template-Center: x={base_x}, y={base_y}")
    print(f"  Klick-Position:  x={click_x}, y={click_y} (+{offset_x}px)")

    # Bewege Maus (KEIN Klick!)
    print(f"  → Bewege Maus zu {label}...")
    pyautogui.moveTo(click_x, click_y, duration=1.0)
    time.sleep(2)
    print()

print("✅ Debug abgeschlossen!")
print("Waren die Maus-Positionen korrekt?")
