#!/usr/bin/env python3
"""
Tunee.ai Download Automation
Hybrid-Ansatz: Playwright für Navigation + Python für Downloads
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from src.auth import has_saved_session, launch_with_real_chrome, save_cookies
from src.browser import TuneeBrowser
from src.downloader import TuneeDownloader


# Konfiguration
DEFAULT_URL = "https://www.tunee.ai/conversation/-PhXUDbLtFJTN4iL-"
DOWNLOADS_DIR = Path(__file__).parent / "downloads"


async def main(url: str = DEFAULT_URL):
    """Hauptprozess für den Download."""

    print("\n" + "="*60)
    print("TUNEE.AI DOWNLOAD AUTOMATION")
    print("="*60)
    print(f"URL: {url}")
    print(f"Downloads: {DOWNLOADS_DIR.absolute()}")
    print("="*60)

    # Prüfe ob Session existiert
    first_time = not has_saved_session()

    # Starte mit echtem Chrome (persistent context)
    context, _, playwright = await launch_with_real_chrome(url, first_time=first_time)
    page = context.pages[0] if context.pages else await context.new_page()

    # Falls nicht first_time, navigiere zur URL
    if not first_time:
        await page.goto(url)

    # Warte auf Seitenladung
    print("\nWarte auf Seitenladung...")
    await asyncio.sleep(3)

    # Browser-Automation initialisieren
    tunee_browser = TuneeBrowser(page)

    # Manuelle Vorbereitung
    print("\n" + "-"*60)
    print("VORBEREITUNG")
    print("-"*60)
    print("1. Stelle sicher, dass die Song-Liste links sichtbar ist")
    print("2. Klicke ggf. auf 'All Music' um die Liste zu öffnen")
    print("3. Scrolle NICHT - bleibe oben in der Liste")
    print("-"*60)
    input("\n>>> Drücke ENTER wenn die Song-Liste sichtbar ist... ")

    # Prüfe ob Musik-Liste geladen
    print("\nPrüfe Musik-Liste...")
    if not await tunee_browser.wait_for_music_list():
        print("\nFEHLER: Musik-Liste nicht gefunden.")
        print("Möglicherweise ist der Login abgelaufen.")
        print("Lösche den Ordner 'cookies/chrome_profile' und starte neu.")
        await context.close()
        await playwright.stop()
        return

    # Songs finden
    print("\nSuche Songs...")
    songs = await tunee_browser.get_song_list()

    if not songs:
        print("Keine Songs gefunden!")
        print("\nDrücke ENTER um den Browser zu schließen...")
        input()
        await context.close()
        await playwright.stop()
        return

    print(f"\n{len(songs)} Songs gefunden:")
    for idx, song in enumerate(songs, 1):
        print(f"  {idx}. {song['name']} ({song['duration']})")

    # Bestätigung
    print("\n" + "-"*40)
    proceed = input("Download starten? (j/n): ").strip().lower()
    if proceed != 'j':
        print("Abgebrochen.")
        await context.close()
        await playwright.stop()
        return

    # Songs verarbeiten (Certificate + Downloads)
    print("\n" + "="*60)
    print("VERARBEITE SONGS")
    print("="*60)

    all_links = []
    for idx, song in enumerate(songs, 1):
        print(f"\n[{idx}/{len(songs)}]", end="")
        links = await tunee_browser.process_song(song['name'], song['duration'])
        if links:
            all_links.append(links)
            url_count = sum([1 for x in [links.mp3_url, links.raw_url, links.video_url, links.lrc_url] if x])
            cert_status = "✓" if links.certificate_downloaded else "✗"
            print(f"    → {url_count} Downloads, Certificate: {cert_status}")
        else:
            print(f"    → FEHLGESCHLAGEN")

    # Cookies speichern
    await save_cookies(context)
    cookies = await context.cookies()

    # Downloads starten
    print("\n" + "="*60)
    print("STARTE DOWNLOADS")
    print("="*60)

    downloader = TuneeDownloader(DOWNLOADS_DIR)
    results = await downloader.download_all_songs(all_links, cookies)

    # Zusammenfassung
    print("\n" + "="*60)
    print("ZUSAMMENFASSUNG")
    print("="*60)
    print(f"Erfolgreich: {results['success']}")
    print(f"Fehlgeschlagen: {results['failed']}")
    print(f"Gesamtgröße: {results['total_size_mb']:.2f} MB")

    # Log speichern
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    log_file = DOWNLOADS_DIR / f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nLog gespeichert: {log_file}")

    # Browser schließen
    await context.close()
    await playwright.stop()

    print("\nFertig!")


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    asyncio.run(main(url))
