#!/usr/bin/env python3
"""
Hybrid Song Downloader - Alle Songs einer Tunee-Conversation downloaden

Nutzt Playwright (Navigation) + PyAutoGUI (Klicks) für zuverlässige Downloads.
"""

import asyncio
import time
import sys
from pathlib import Path
from playwright.async_api import async_playwright, Page
import pyautogui

# Templates
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Timeouts und Delays
SCROLL_DELAY = 1.5  # Sekunden zwischen Scroll-Aktionen
MODAL_WAIT = 2.0    # Sekunden nach Modal-Öffnung
DOWNLOAD_WAIT = 2.0 # Sekunden zwischen Downloads
LYRIC_VIDEO_WAIT = 3.0  # Sekunden für Lyric Video Modal


def find_template(template_name: str, confidence: float = 0.85, timeout: int = 5):
    """Findet Template auf dem Screen."""
    template_path = TEMPLATES_DIR / f"{template_name}.png"

    if not template_path.exists():
        print(f"    ⚠️ Template nicht gefunden: {template_path}")
        return None

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateOnScreen(str(template_path), confidence=confidence)
            if location:
                return pyautogui.center(location)
        except Exception as e:
            pass
        time.sleep(0.5)

    return None


async def get_all_songs(page: Page) -> list[dict]:
    """
    Sammelt alle Songs aus der Conversation (mit Scrollen).
    Nutzt die funktionierende Logik aus browser.py!

    Returns:
        Liste von Songs: [{"name": str, "duration": str}, ...]
    """
    print("\n📋 Sammle Song-Liste...")

    # Warte bis Seite geladen
    await asyncio.sleep(3)

    all_songs = []
    seen_keys = set()
    last_count = 0
    no_new_songs_count = 0

    print("    Scanne Song-Liste (scrolle automatisch)...")

    while no_new_songs_count < 5:
        # Extrahiere sichtbare Songs (JavaScript-Evaluation wie im Original!)
        visible_songs = await page.evaluate('''() => {
            const results = [];
            const timeRegex = /^\\d{2}:\\d{2}$/;
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent?.trim();
                if (text && timeRegex.test(text) && el.childNodes.length === 1) {
                    const rect = el.getBoundingClientRect();
                    // Nur linke Seite (x < 400)
                    if (rect.left > 400) continue;

                    const duration = text;
                    let container = el.parentElement;

                    // Suche den Song-Container
                    for (let i = 0; i < 4 && container; i++) {
                        const cRect = container.getBoundingClientRect();
                        if (cRect.height > 40 && cRect.height < 150) {
                            // Finde den Song-Namen
                            const textNodes = container.querySelectorAll('span, div, p, a');
                            for (const node of textNodes) {
                                const nodeText = node.textContent?.trim();

                                if (nodeText &&
                                    nodeText.length > 2 &&
                                    nodeText.length < 80 &&
                                    !timeRegex.test(nodeText) &&
                                    !['All Music', 'Favorites', 'All', 'Share', 'Home'].includes(nodeText) &&
                                    !nodeText.includes('\\n') &&
                                    node.childNodes.length <= 2) {

                                    results.push({ name: nodeText, duration: duration });
                                    break;
                                }
                            }
                            break;
                        }
                        container = container.parentElement;
                    }
                }
            }
            return results;
        }''')

        # Füge neue Songs hinzu (dedupliziert über Name+Duration)
        for song in visible_songs:
            key = f"{song['name']}|{song['duration']}"
            if key not in seen_keys:
                seen_keys.add(key)
                all_songs.append({'name': song['name'], 'duration': song['duration']})

        # Prüfe Fortschritt
        if len(all_songs) == last_count:
            no_new_songs_count += 1
        else:
            no_new_songs_count = 0
            print(f"      ... {len(all_songs)} Songs gefunden")
            last_count = len(all_songs)

        # Scrolle die Song-Liste
        await page.evaluate('''() => {
            const containers = document.querySelectorAll('div');
            for (const c of containers) {
                const rect = c.getBoundingClientRect();
                if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                    c.scrollHeight > c.clientHeight + 10) {
                    c.scrollTop += 150;
                    return true;
                }
            }
            return false;
        }''')

        await asyncio.sleep(0.3)

    # Scroll zurück nach oben
    await page.evaluate('''() => {
        const containers = document.querySelectorAll('div');
        for (const c of containers) {
            const rect = c.getBoundingClientRect();
            if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                c.scrollHeight > c.clientHeight + 10) {
                c.scrollTop = 0;
                return;
            }
        }
    }''')

    await asyncio.sleep(0.3)
    print(f"\n✅ {len(all_songs)} Songs gefunden!\n")

    return all_songs


async def download_song_hybrid(page: Page, song: dict, song_number: int, total_songs: int) -> bool:
    """
    Downloadet einen Song mit Hybrid-Approach.

    Args:
        page: Playwright Page
        song: Song-Dict mit name und duration
        song_number: Aktuelle Song-Nummer (1-based)
        total_songs: Gesamtanzahl Songs

    Returns:
        True wenn erfolgreich
    """
    print(f"\n{'='*60}")
    print(f"Song {song_number}/{total_songs}: {song['name']} ({song['duration']})")
    print(f"{'='*60}")

    try:
        # 1. Finde Song in Liste (per Duration)
        print("1️⃣ Suche Song in Liste...")
        duration_elements = await page.locator(f'text="{song["duration"]}"').all()

        if not duration_elements:
            print(f"    ❌ Song nicht gefunden (Duration: {song['duration']})")
            return False

        song_element = duration_elements[0]

        # 2. Scrolle Song in View
        print("2️⃣ Scrolle Song in View...")
        await song_element.scroll_into_view_if_needed()
        await asyncio.sleep(1)

        # 3. Finde Download-Button (PyAutoGUI - bildbasiert)
        print("3️⃣ Suche Download-Button...")
        download_btn = find_template("download_button", confidence=0.8, timeout=3)

        if not download_btn:
            # Fallback: Mit Hover
            print("    ⚠️ Button nicht gefunden, versuche mit Hover...")
            await song_element.hover()
            await asyncio.sleep(1.5)
            download_btn = find_template("download_button", confidence=0.8, timeout=3)

        if not download_btn:
            print("    ❌ Download-Button nicht gefunden")
            return False

        print(f"    ✅ Download-Button gefunden bei x={download_btn.x}, y={download_btn.y}")

        # 4. Klicke Download-Button → Modal öffnet
        print("4️⃣ Klicke Download-Button...")
        pyautogui.click(download_btn.x, download_btn.y)
        await asyncio.sleep(MODAL_WAIT)

        # 5. Finde MP3-Button im Modal (für Position)
        print("5️⃣ Suche Modal-Buttons...")
        mp3_location = find_template("modal_mp3", confidence=0.85, timeout=3)

        if not mp3_location:
            print("    ❌ Modal nicht geöffnet (MP3 nicht gefunden)")
            return False

        print(f"    ✅ Modal geöffnet (MP3 bei x={mp3_location.x}, y={mp3_location.y})")

        # 6. Klicke Modal-Buttons (position-basiert)
        # Modal-Reihenfolge: MP3, RAW, VIDEO, LRC
        # Klick-Reihenfolge: MP3, RAW, LRC, VIDEO (VIDEO zuletzt!)
        offset_x = 150  # Offset zum Download-Button

        buttons = [
            ("MP3", 0),      # Zeile 1
            ("RAW", 100),    # Zeile 2
            ("LRC", 300),    # Zeile 4
            ("VIDEO", 200),  # Zeile 3
        ]

        print("6️⃣ Klicke Downloads...")
        for label, y_offset in buttons:
            click_x = mp3_location.x + offset_x
            click_y = mp3_location.y + y_offset

            print(f"    → {label}...")
            pyautogui.click(click_x, click_y)
            await asyncio.sleep(DOWNLOAD_WAIT)

        # 7. Lyric Video Modal (nach VIDEO-Klick)
        print("7️⃣ Warte auf Lyric Video Modal...")
        await asyncio.sleep(LYRIC_VIDEO_WAIT)

        lyric_btn = find_template("lyric_video_download", confidence=0.85, timeout=3)

        if lyric_btn:
            print(f"    ✅ Lyric Video Download gefunden bei x={lyric_btn.x}, y={lyric_btn.y}")
            print("    → Klicke VIDEO Download...")
            pyautogui.click(lyric_btn.x, lyric_btn.y)
            await asyncio.sleep(DOWNLOAD_WAIT)
            print("    ✅ VIDEO Download gestartet")
        else:
            print("    ⚠️ Lyric Video Download nicht gefunden (skip)")

        print(f"\n✅ Song {song_number}/{total_songs} erfolgreich heruntergeladen!")
        return True

    except Exception as e:
        print(f"\n❌ Fehler bei Song {song_number}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Hauptprogramm."""

    print("""
╔══════════════════════════════════════════════════════════════╗
║         Hybrid Song Downloader für Tunee.ai                  ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # URL ist optional (ändert sich nach Login!)
    if len(sys.argv) > 1:
        start_url = sys.argv[1]
    else:
        start_url = "https://www.tunee.ai"

    print(f"\n🌐 Start-URL: {start_url}")
    print("💡 URLs ändern sich nach Login - du navigierst manuell zur Conversation!")

    async with async_playwright() as p:
        # Browser starten (echtes Chrome mit Profil)
        print("\n🚀 Starte Browser...")

        chrome_profile = Path.home() / ".cache" / "cgc_tunee_download" / "chrome_profile"
        chrome_profile.mkdir(parents=True, exist_ok=True)

        context = await p.chromium.launch_persistent_context(
            str(chrome_profile),
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )

        page = await context.new_page()

        # Zur Start-Seite navigieren
        print("📂 Öffne Tunee.ai...")
        await page.goto(start_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Prüfe ob Login nötig
        print("\n🔐 Prüfe Login-Status...")

        # Wenn Login-Seite oder keine Conversation sichtbar, warte auf User
        if "sign" in page.url.lower() or "login" in page.url.lower() or "conversation" not in page.url.lower():
            print("\n" + "="*60)
            print("⚠️  LOGIN & NAVIGATION ERFORDERLICH")
            print("="*60)
            print("\n1. Logge dich im Browser ein (Google, etc.)")
            print("2. Navigiere manuell zu deiner gewünschten Conversation")
            print("3. Warte bis die Song-Liste sichtbar ist")
            print("4. Drücke ENTER im Terminal\n")
            print("💡 TIPP: Die Conversation-URL ändert sich nach jedem Login!")
            print("   Öffne sie manuell im Browser und bleib dort.\n")

            input("Drücke ENTER wenn Song-Liste sichtbar ist...")

        print(f"✅ Bereit! Versuche Songs zu finden...")

        # Song-Liste sammeln
        songs = await get_all_songs(page)

        if not songs:
            print("❌ Keine Songs gefunden")
            await context.close()
            return

        # User-Confirmation
        print(f"\n📊 {len(songs)} Songs bereit zum Download")
        choice = input("\nAlle Songs downloaden? [y/N]: ").lower()

        if choice != "y":
            print("❌ Abgebrochen")
            await context.close()
            return

        # Download-Loop
        print("\n" + "="*60)
        print("START DOWNLOAD")
        print("="*60)

        successful = 0
        failed = 0

        for i, song in enumerate(songs, 1):
            success = await download_song_hybrid(page, song, i, len(songs))

            if success:
                successful += 1
            else:
                failed += 1

            # Kurze Pause zwischen Songs
            if i < len(songs):
                await asyncio.sleep(2)

        # Zusammenfassung
        print("\n" + "="*60)
        print("DOWNLOAD ABGESCHLOSSEN")
        print("="*60)
        print(f"✅ Erfolgreich: {successful}")
        print(f"❌ Fehlgeschlagen: {failed}")
        print(f"📊 Gesamt: {len(songs)}")

        input("\nDrücke ENTER zum Beenden...")
        await context.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Abgebrochen")
    except Exception as e:
        print(f"\n\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
