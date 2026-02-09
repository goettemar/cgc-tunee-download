#!/usr/bin/env python3
"""
Test-Script für Hybrid-Browser

Testet PyAutoGUI Template-Matching und Hybrid-Download-Workflow.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from src.browser_hybrid import HybridBrowser, TemplateConfig
from src.auth import get_chrome_context


async def test_template_matching():
    """Testet Template-Matching ohne Browser."""
    print("\n" + "="*60)
    print("TEST 1: Template-Matching (ohne Browser)")
    print("="*60)

    config = TemplateConfig()

    # Prüfe welche Templates vorhanden sind
    templates_dir = config.templates_dir
    if not templates_dir.exists():
        print(f"❌ Templates-Verzeichnis nicht gefunden: {templates_dir}")
        return False

    templates = list(templates_dir.glob("*.png"))
    if not templates:
        print(f"❌ Keine Templates gefunden in: {templates_dir}")
        print("\n💡 Erstelle zuerst Templates mit:")
        print("   python create_templates.py")
        return False

    print(f"\n✅ Templates gefunden: {len(templates)}")
    for template in templates:
        print(f"   - {template.name}")

    # Teste Template-Matching
    import pyautogui
    print("\n📸 Teste Template-Matching auf aktuellem Screen...")

    for template in templates:
        template_name = template.stem
        print(f"\n🔍 Suche: {template_name}")

        try:
            location = pyautogui.locateOnScreen(str(template), confidence=0.8)
            if location:
                center = pyautogui.center(location)
                print(f"   ✅ Gefunden bei: {center}")
            else:
                print(f"   ⚠️ Nicht gefunden (normal wenn Button nicht sichtbar)")
        except Exception as e:
            print(f"   ❌ Fehler: {e}")

    return True


async def test_hybrid_download():
    """Testet kompletten Hybrid-Download-Workflow."""
    print("\n" + "="*60)
    print("TEST 2: Hybrid-Download-Workflow")
    print("="*60)

    # URL abfragen
    url = input("\nTunee Conversation URL: ").strip()
    if not url:
        print("❌ Keine URL angegeben")
        return False

    print("\n🌐 Öffne Browser...")

    async with async_playwright() as p:
        # Browser starten (echtes Chrome)
        context = await get_chrome_context(p)
        page = await context.new_page()

        # Hybrid-Browser erstellen
        hybrid = HybridBrowser(page)

        # Zur Conversation navigieren
        print(f"📂 Lade: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Test-Song (User-Input)
        print("\n" + "="*60)
        print("Wähle einen Test-Song aus der Liste:")
        print("="*60)

        song_name = input("Song-Name: ").strip()
        duration = input("Duration (z.B. 03:45): ").strip()

        if not song_name or not duration:
            print("❌ Song-Name oder Duration fehlt")
            await context.close()
            return False

        # Hybrid-Download starten
        print("\n🚀 Starte Hybrid-Download...")
        result = await hybrid.download_song_hybrid(song_name, duration)

        # Ergebnis
        print("\n" + "="*60)
        print("ERGEBNIS")
        print("="*60)

        if result["success"]:
            print(f"✅ Erfolg!")
            print(f"📦 Downloads: {', '.join(result['files'])}")
        else:
            print(f"❌ Fehler: {result.get('error', 'Unbekannt')}")

        # Browser offen lassen für Debugging
        print("\n💡 Browser bleibt offen für Debugging...")
        input("Drücke ENTER zum Beenden...")

        await context.close()

    return result["success"]


async def main():
    """Hauptprogramm."""

    print("""
╔══════════════════════════════════════════════════════════════╗
║         Hybrid-Browser Test Suite                           ║
╚══════════════════════════════════════════════════════════════╝

Testet PyAutoGUI-basierte Automation für Tunee-Downloads.
    """)

    # Test 1: Template-Matching
    template_ok = await test_template_matching()

    if not template_ok:
        print("\n❌ Template-Test fehlgeschlagen.")
        print("   Bitte erstelle zuerst Templates mit: python create_templates.py")
        return

    # Test 2: Hybrid-Download (optional)
    print("\n" + "="*60)
    choice = input("\nHybrid-Download testen? [y/N]: ").lower()

    if choice == "y":
        success = await test_hybrid_download()

        if success:
            print("\n✅ Hybrid-Download funktioniert!")
        else:
            print("\n⚠️ Hybrid-Download hatte Probleme.")
            print("   Mögliche Ursachen:")
            print("   - Templates nicht genau genug")
            print("   - Browser-Zoom nicht 100%")
            print("   - Screen-Resolution anders als bei Template-Erstellung")

    print("\n✅ Tests abgeschlossen!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n❌ Abgebrochen.")
    except Exception as e:
        print(f"\n\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
