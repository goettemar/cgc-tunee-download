"""
Cookie/Session-Management für Google Auth.
Verwendet echtes Chrome-Profil um Google-Login-Block zu umgehen.
"""

import json
import os
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext

COOKIES_DIR = Path(__file__).parent.parent / "cookies"
COOKIES_FILE = COOKIES_DIR / "tunee_session.json"
CHROME_USER_DATA = COOKIES_DIR / "chrome_profile"
DOWNLOADS_DIR = Path.home() / "Downloads" / "tunee"


async def save_cookies(context: BrowserContext) -> None:
    """Speichert Cookies aus dem Browser-Context."""
    cookies = await context.cookies()
    COOKIES_DIR.mkdir(exist_ok=True)
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Cookies gespeichert: {COOKIES_FILE}")


async def load_cookies(context: BrowserContext) -> bool:
    """Lädt gespeicherte Cookies in den Browser-Context."""
    if not COOKIES_FILE.exists():
        print("Keine gespeicherten Cookies gefunden.")
        return False

    with open(COOKIES_FILE, "r") as f:
        cookies = json.load(f)

    await context.add_cookies(cookies)
    print(f"Cookies geladen: {len(cookies)} Einträge")
    return True


def has_saved_session() -> bool:
    """Prüft ob eine gespeicherte Session existiert."""
    return CHROME_USER_DATA.exists() or COOKIES_FILE.exists()


async def launch_with_real_chrome(url: str, first_time: bool = False):
    """
    Startet mit echtem Chrome und persistentem Profil.
    Google blockiert Playwright-Chromium, aber nicht echtes Chrome.
    """
    COOKIES_DIR.mkdir(exist_ok=True)
    CHROME_USER_DATA.mkdir(exist_ok=True)

    print("\n" + "="*60)
    if first_time:
        print("ERSTER START - LOGIN ERFORDERLICH")
        print("="*60)
        print("\n1. Echtes Chrome öffnet sich gleich")
        print("2. Logge dich mit Google bei Tunee ein")
        print("3. Warte bis die Musik-Seite vollständig geladen ist")
        print("4. Drücke ENTER hier im Terminal wenn fertig")
        print("\nHINWEIS: Dein Login wird im Profil gespeichert,")
        print("         beim nächsten Start bist du automatisch eingeloggt.")
    else:
        print("STARTE MIT GESPEICHERTEM PROFIL")
        print("="*60)
        print("\nDu solltest automatisch eingeloggt sein.")
        print("Falls nicht: Login durchführen und ENTER drücken.")
    print("\n" + "="*60 + "\n")

    playwright = await async_playwright().start()

    # Erstelle Downloads-Ordner
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    # Setze Chrome Preferences für Download-Pfad
    prefs_dir = CHROME_USER_DATA / "Default"
    prefs_dir.mkdir(exist_ok=True)
    prefs_file = prefs_dir / "Preferences"

    # Lade existierende Preferences oder erstelle neue
    if prefs_file.exists():
        with open(prefs_file, "r") as f:
            prefs = json.load(f)
    else:
        prefs = {}

    # Setze Download-Pfad
    if "download" not in prefs:
        prefs["download"] = {}
    prefs["download"]["default_directory"] = str(DOWNLOADS_DIR)
    prefs["download"]["prompt_for_download"] = False

    # Speichere Preferences
    with open(prefs_file, "w") as f:
        json.dump(prefs, f, indent=2)

    print(f"📁 Downloads gehen nach: {DOWNLOADS_DIR}")

    # Verwende persistent context mit echtem Chrome
    # Das speichert Login-Daten automatisch im Profil
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(CHROME_USER_DATA),
        channel="chrome",  # Echtes Chrome statt Playwright-Chromium
        headless=False,
        accept_downloads=True,  # Downloads akzeptieren
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ]
    )

    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(url)

    if first_time:
        input("\n>>> Drücke ENTER wenn du eingeloggt bist und die Seite geladen ist... ")
        # Cookies zusätzlich speichern als Backup
        await save_cookies(context)

    return context, None, playwright  # browser ist None bei persistent context


async def interactive_login(url: str):
    """Alias für launch_with_real_chrome beim ersten Start."""
    return await launch_with_real_chrome(url, first_time=True)
