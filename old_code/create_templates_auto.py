#!/usr/bin/env python3
"""
Automatische Template-Erstellung für PyAutoGUI.
Öffnet Tunee, User navigiert manuell zur Song-Liste, erstellt Template-Screenshots.

Wichtig: Klicks werden per Playwright page.mouse gemacht (triggert React Events),
PyAutoGUI wird nur für Screenshots/Template-Crops genutzt.
"""

import asyncio
import time
import sys
from pathlib import Path
from playwright.async_api import async_playwright

import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

TEMPLATES_DIR = Path(__file__).parent / "templates"
COOKIES_DIR = Path(__file__).parent / "cookies" / "chrome_profile"


async def viewport_to_screen(page, vp_x, vp_y):
    """Konvertiert Viewport -> Screen Koordinaten."""
    info = await page.evaluate('''() => ({
        screenX: window.screenX,
        screenY: window.screenY,
        outerHeight: window.outerHeight,
        innerHeight: window.innerHeight
    })''')
    chrome_h = info['outerHeight'] - info['innerHeight']
    return int(info['screenX'] + vp_x), int(info['screenY'] + chrome_h + vp_y)


async def find_songs(page):
    """Findet Songs in der Liste per JS-Evaluate."""
    return await page.evaluate('''() => {
        const timeRegex = /^\\d{2}:\\d{2}$/;
        const results = [];
        const allElements = document.querySelectorAll('*');
        for (const el of allElements) {
            const text = el.textContent?.trim();
            if (text && timeRegex.test(text) && el.childNodes.length === 1) {
                const rect = el.getBoundingClientRect();
                if (rect.left > 600 || rect.left < -100) continue;
                let container = el.parentElement;
                for (let i = 0; i < 5 && container; i++) {
                    const cRect = container.getBoundingClientRect();
                    if (cRect.height > 40 && cRect.height < 150) {
                        const textNodes = container.querySelectorAll('span, div, p, a');
                        for (const node of textNodes) {
                            const nodeText = node.textContent?.trim();
                            if (nodeText && nodeText.length > 2 && nodeText.length < 80 &&
                                !timeRegex.test(nodeText) && !nodeText.includes('\\n') &&
                                !['All Music', 'Favorites', 'All', 'Share'].includes(nodeText)) {
                                results.push({
                                    name: nodeText, duration: text,
                                    x: cRect.left + cRect.width / 2,
                                    y: cRect.top + cRect.height / 2,
                                    width: cRect.width, height: cRect.height,
                                    right: cRect.right, top: cRect.top, bottom: cRect.bottom
                                });
                                break;
                            }
                        }
                        break;
                    }
                    container = container.parentElement;
                }
            }
        }
        return results.length > 0 ? results : null;
    }''')


async def find_hover_buttons(page, song_y):
    """Findet alle klickbaren Elemente in der Song-Zeile (bei Hover sichtbar)."""
    return await page.evaluate('''(songY) => {
        const candidates = [];
        const allEls = document.querySelectorAll('button, [role="button"], a, svg, [class*="icon"], [class*="btn"]');
        for (const el of allEls) {
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.width > 60 || rect.height > 60) continue;
            if (rect.width < 5 || rect.height < 5) continue;
            if (Math.abs(rect.top + rect.height/2 - songY) > 35) continue;

            const html = el.outerHTML?.toLowerCase() || '';
            const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
            const className = (el.className?.toString() || '').toLowerCase();
            const title = (el.getAttribute('title') || '').toLowerCase();

            candidates.push({
                x: rect.left + rect.width/2,
                y: rect.top + rect.height/2,
                w: rect.width, h: rect.height,
                left: rect.left, right: rect.right,
                tag: el.tagName,
                aria: ariaLabel,
                title: title,
                hasDownload: html.includes('download') || ariaLabel.includes('download') ||
                             title.includes('download') || html.includes('arrow-down') ||
                             html.includes('save'),
                hasStar: html.includes('star') || html.includes('favorite') || html.includes('fav'),
                hasMore: html.includes('more') || html.includes('dots') || html.includes('menu'),
                className: className.substring(0, 60)
            });
        }
        // Sortiere nach X-Position (links nach rechts)
        candidates.sort((a, b) => a.x - b.x);
        return candidates;
    }''', song_y)


async def main():
    TEMPLATES_DIR.mkdir(exist_ok=True)

    print("=== Automatische Template-Erstellung ===\n")

    # Stale SingletonLock entfernen
    lock = COOKIES_DIR / "SingletonLock"
    if lock.exists():
        lock.unlink()
        print("   SingletonLock entfernt.")

    async with async_playwright() as p:
        print("1. Starte Browser mit Chrome-Profil...")
        context = await p.chromium.launch_persistent_context(
            str(COOKIES_DIR),
            channel="chrome",
            headless=False,
            no_viewport=True,
            args=["--start-maximized"],
        )
        page = context.pages[0] if context.pages else await context.new_page()

        url = sys.argv[1] if len(sys.argv) > 1 else "https://www.tunee.ai/conversation/-PhXUDbLtFJTN4iL-"
        print(f"2. Oeffne: {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # Escape fuer Google Translate Popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(0.5)

        # Warte auf User-Navigation
        print("""
+------------------------------------------------------------------+
|  MANUELLE NAVIGATION                                              |
|                                                                    |
|  1. Im Browser: Navigiere zum Tunee-Projekt                       |
|  2. Klicke auf "All Music" (Song-Liste mit MM:SS Zeiten)          |
|  3. Wenn Song-Liste sichtbar ist:                                 |
|                                                                    |
|     touch /tmp/tunee_ready                                         |
|                                                                    |
|  Warte max. 300 Sekunden...                                       |
+------------------------------------------------------------------+
""")

        signal_file = Path("/tmp/tunee_ready")
        signal_file.unlink(missing_ok=True)  # Altes Signal entfernen

        for i in range(300):
            if signal_file.exists():
                print(f"   Signal empfangen nach {i+1}s!")
                signal_file.unlink()
                break
            await asyncio.sleep(1)
            if i % 30 == 29:
                print(f"   ... warte ({i+1}s)")
        else:
            print("   Timeout nach 300s!")
            await context.close()
            return

        # Aktuellsten Tab nutzen
        page = context.pages[-1]
        await asyncio.sleep(2)

        # === Songs suchen ===
        print("\n3. Suche Songs...")
        songs = None
        for attempt in range(20):
            songs = await find_songs(page)
            if songs:
                print(f"   {len(songs)} Songs gefunden!")
                break
            await asyncio.sleep(1)

        if not songs:
            print("   FEHLER: Keine Songs gefunden!")
            screen = pyautogui.screenshot()
            screen.save("/tmp/tunee_nosongs.png")
            print("   Debug: /tmp/tunee_nosongs.png")
            await context.close()
            return

        for i, s in enumerate(songs[:5]):
            print(f"   [{i}] {s['name']} ({s['duration']})")

        song = songs[0]
        print(f"\n   Nutze: '{song['name']}' VP({song['x']:.0f}, {song['y']:.0f})")

        # === SCHRITT 1: Hover ueber Song ===
        print("\n4. Hover ueber Song (Playwright mouse + PyAutoGUI)...")

        # Erst Maus wegbewegen (kein Hover-Zustand)
        await page.mouse.move(10, 10)
        pyautogui.moveTo(10, 10)
        await asyncio.sleep(0.5)

        # Screenshot VOR Hover
        pre_hover = pyautogui.screenshot()
        pre_hover.save("/tmp/tunee_pre_hover.png")

        # Jetzt Hover: Playwright mouse + PyAutoGUI parallel
        song_sx, song_sy = await viewport_to_screen(page, song['x'], song['y'])
        print(f"   Viewport: ({song['x']:.0f}, {song['y']:.0f}) -> Screen: ({song_sx}, {song_sy})")

        # Playwright Hover (triggert CSS :hover im Browser)
        await page.mouse.move(song['x'], song['y'])
        # PyAutoGUI auch bewegen (sichtbar fuer User)
        pyautogui.moveTo(song_sx, song_sy, duration=0.3)
        await asyncio.sleep(2)

        # Screenshot MIT Hover
        hover_screen = pyautogui.screenshot()
        hover_screen.save("/tmp/tunee_hover.png")
        print("   Screenshots: /tmp/tunee_pre_hover.png, /tmp/tunee_hover.png")

        # === SCHRITT 2: Download-Button finden ===
        print("\n5. Suche Download-Button in Song-Zeile...")
        buttons = await find_hover_buttons(page, song['y'])

        if buttons:
            print(f"   {len(buttons)} Elemente in Song-Zeile gefunden:")
            dl_btn = None
            for btn in buttons:
                flags = []
                if btn['hasDownload']: flags.append("DOWNLOAD")
                if btn['hasStar']: flags.append("STAR")
                if btn['hasMore']: flags.append("MORE")
                flag_str = " ".join(flags) if flags else ""
                print(f"     VP({btn['x']:.0f},{btn['y']:.0f}) {btn['w']:.0f}x{btn['h']:.0f} "
                      f"{btn['tag']} {flag_str} {btn['aria']} {btn['className'][:30]}")
                if btn['hasDownload'] and not dl_btn:
                    dl_btn = btn

            if not dl_btn:
                # Kein expliziter Download-Button gefunden
                # Nehme den rechtesten Button (typisch Download-Icon Position)
                rightmost = [b for b in buttons if not b['hasStar'] and not b['hasMore']]
                if rightmost:
                    dl_btn = rightmost[-1]
                    print(f"   -> Nutze rechtesten Button als Download: VP({dl_btn['x']:.0f},{dl_btn['y']:.0f})")
                else:
                    dl_btn = buttons[-1]
                    print(f"   -> Fallback auf letzten Button: VP({dl_btn['x']:.0f},{dl_btn['y']:.0f})")
            else:
                print(f"   -> Download-Button gefunden: VP({dl_btn['x']:.0f},{dl_btn['y']:.0f})")
        else:
            print("   Keine Buttons in Song-Zeile gefunden!")
            # Schaetzung: rechts in der Song-Zeile
            dl_btn = {
                'x': song['right'] - 25,
                'y': song['y'],
                'w': 20, 'h': 20
            }
            print(f"   -> Schaetze Position: VP({dl_btn['x']:.0f},{dl_btn['y']:.0f})")

        # === SCHRITT 3: Download-Button Template erstellen ===
        print("\n6. Erstelle download_button.png...")
        btn_sx, btn_sy = await viewport_to_screen(page, dl_btn['x'], dl_btn['y'])
        btn_w = max(int(dl_btn.get('w', 20)) + 12, 30)
        btn_h = max(int(dl_btn.get('h', 20)) + 12, 30)
        crop = hover_screen.crop((
            btn_sx - btn_w // 2, btn_sy - btn_h // 2,
            btn_sx + btn_w // 2, btn_sy + btn_h // 2
        ))
        crop.save(TEMPLATES_DIR / "download_button.png")
        print(f"   download_button.png: {btn_w}x{btn_h}px (Screen: {btn_sx},{btn_sy})")

        # === SCHRITT 4: Download-Button klicken (Playwright mouse!) ===
        print("\n7. Klicke Download-Button per Playwright...")
        # Nochmal Hover sicherstellen
        await page.mouse.move(dl_btn['x'], dl_btn['y'])
        await asyncio.sleep(0.5)
        # Klick per Playwright (triggert React Events!)
        await page.mouse.click(dl_btn['x'], dl_btn['y'])
        print(f"   Klick bei VP({dl_btn['x']:.0f},{dl_btn['y']:.0f})")

        # Warte auf Modal
        await asyncio.sleep(3)

        # Pruefen ob Modal offen ist
        modal_check = await page.evaluate('''() => {
            // Suche nach MP3 text als Indikator fuer offenes Modal
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                const text = el.textContent?.trim();
                if (text && /^MP3$/i.test(text) && el.childNodes.length <= 2) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.left > 0) {
                        return true;
                    }
                }
            }
            return false;
        }''')

        if not modal_check:
            print("   Modal nicht geoeffnet! Versuche nochmal...")
            # Nochmal Hover + Klick
            await page.mouse.move(song['x'], song['y'])
            await asyncio.sleep(1)
            await page.mouse.move(dl_btn['x'], dl_btn['y'])
            await asyncio.sleep(0.5)
            await page.mouse.click(dl_btn['x'], dl_btn['y'])
            await asyncio.sleep(3)

            modal_check = await page.evaluate('''() => {
                const allEls = document.querySelectorAll('*');
                for (const el of allEls) {
                    const text = el.textContent?.trim();
                    if (text && /^MP3$/i.test(text) && el.childNodes.length <= 2) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0 && rect.left > 0) return true;
                    }
                }
                return false;
            }''')

        if not modal_check:
            print("   Modal immer noch nicht offen!")
            print("   Versuche Doppelklick auf verschiedene X-Positionen...")
            # Probiere verschiedene X-Positionen rechts in der Song-Zeile
            for offset_x in [song['right'] - 20, song['right'] - 35, song['right'] - 50]:
                await page.mouse.move(song['x'], song['y'])
                await asyncio.sleep(0.5)
                await page.mouse.move(offset_x, song['y'])
                await asyncio.sleep(0.3)
                await page.mouse.click(offset_x, song['y'])
                await asyncio.sleep(2)

                modal_check = await page.evaluate('''() => {
                    const allEls = document.querySelectorAll('*');
                    for (const el of allEls) {
                        const text = el.textContent?.trim();
                        if (text && /^MP3$/i.test(text) && el.childNodes.length <= 2) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && rect.left > 0) return true;
                        }
                    }
                    return false;
                }''')

                if modal_check:
                    print(f"   Modal geoeffnet bei VP({offset_x:.0f},{song['y']:.0f})!")
                    break
                else:
                    await page.keyboard.press('Escape')
                    await asyncio.sleep(0.3)

        if not modal_check:
            screen = pyautogui.screenshot()
            screen.save("/tmp/tunee_no_modal.png")
            print("   FEHLER: Modal konnte nicht geoeffnet werden!")
            print("   Debug: /tmp/tunee_no_modal.png")
            print("\n   Bitte oeffne das Modal manuell (Download-Icon in Song-Zeile klicken)")
            print("   Dann: touch /tmp/tunee_modal_ready")

            signal_file2 = Path("/tmp/tunee_modal_ready")
            signal_file2.unlink(missing_ok=True)
            for i in range(120):
                if signal_file2.exists():
                    signal_file2.unlink()
                    print("   Signal empfangen!")
                    break
                await asyncio.sleep(1)
                if i % 30 == 29:
                    print(f"   ... warte ({i+1}s)")
            else:
                print("   Timeout! Breche ab.")
                await context.close()
                return

        # === SCHRITT 5: Modal MP3 Template ===
        print("\n8. Erstelle modal_mp3.png...")
        await asyncio.sleep(1)
        modal_screen = pyautogui.screenshot()
        modal_screen.save("/tmp/tunee_modal.png")

        mp3_info = await page.evaluate('''() => {
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                const text = el.textContent?.trim();
                if (text && /^MP3$/i.test(text) && el.childNodes.length <= 2) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 10 && rect.height > 5 && rect.left > 0) {
                        // Suche passendes Container-Element (Button/Zeile)
                        let row = el;
                        for (let i = 0; i < 5; i++) {
                            const p = row.parentElement;
                            if (!p) break;
                            const pRect = p.getBoundingClientRect();
                            if (pRect.width > 150 && pRect.height > 25 && pRect.height < 100) {
                                return {x: pRect.left + pRect.width/2, y: pRect.top + pRect.height/2,
                                        w: pRect.width, h: pRect.height,
                                        clickX: pRect.left + pRect.width/2,
                                        clickY: pRect.top + pRect.height/2};
                            }
                            row = p;
                        }
                        return {x: rect.left + rect.width/2, y: rect.top + rect.height/2,
                                w: Math.max(rect.width, 80), h: Math.max(rect.height, 30),
                                clickX: rect.left + rect.width/2,
                                clickY: rect.top + rect.height/2};
                    }
                }
            }
            return null;
        }''')

        if mp3_info:
            mp3_sx, mp3_sy = await viewport_to_screen(page, mp3_info['x'], mp3_info['y'])
            mp3_w = min(int(mp3_info['w']), 350)
            mp3_h = min(int(mp3_info['h']) + 6, 60)
            crop = modal_screen.crop((
                mp3_sx - mp3_w // 2, mp3_sy - mp3_h // 2,
                mp3_sx + mp3_w // 2, mp3_sy + mp3_h // 2
            ))
            crop.save(TEMPLATES_DIR / "modal_mp3.png")
            print(f"   modal_mp3.png: {mp3_w}x{mp3_h}px")
            print(f"   MP3 bei VP({mp3_info['x']:.0f},{mp3_info['y']:.0f})")
        else:
            print("   MP3 nicht im Modal gefunden!")
            print("   Debug: /tmp/tunee_modal.png")

        # === SCHRITT 6: VIDEO klicken fuer Lyric Video Modal ===
        print("\n9. Suche VIDEO-Button im Modal...")
        video_info = await page.evaluate('''() => {
            const allEls = document.querySelectorAll('*');
            for (const el of allEls) {
                const text = el.textContent?.trim();
                if (text && /^VIDEO$/i.test(text) && el.childNodes.length <= 2) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 10 && rect.height > 5 && rect.left > 0) {
                        // Suche Container (klickbare Zeile)
                        let row = el;
                        for (let i = 0; i < 5; i++) {
                            const p = row.parentElement;
                            if (!p) break;
                            const pRect = p.getBoundingClientRect();
                            if (pRect.width > 150 && pRect.height > 25 && pRect.height < 100) {
                                return {
                                    x: pRect.left + pRect.width/2,
                                    y: pRect.top + pRect.height/2,
                                    w: pRect.width, h: pRect.height,
                                    // Download-Icon ist typisch rechts in der Zeile
                                    dlIconX: pRect.right - 30,
                                    dlIconY: pRect.top + pRect.height/2
                                };
                            }
                            row = p;
                        }
                        return {
                            x: rect.left + rect.width/2,
                            y: rect.top + rect.height/2,
                            w: rect.width, h: rect.height,
                            dlIconX: rect.right + 30,
                            dlIconY: rect.top + rect.height/2
                        };
                    }
                }
            }
            return null;
        }''')

        if video_info:
            print(f"   VIDEO gefunden bei VP({video_info['x']:.0f},{video_info['y']:.0f})")
            # Klicke auf den Download-Icon rechts in der VIDEO-Zeile
            vid_click_x = video_info['dlIconX']
            vid_click_y = video_info['dlIconY']
            print(f"   Klicke VIDEO-Download bei VP({vid_click_x:.0f},{vid_click_y:.0f})...")

            vid_sx, vid_sy = await viewport_to_screen(page, vid_click_x, vid_click_y)
            pyautogui.moveTo(vid_sx, vid_sy, duration=0.3)
            await page.mouse.click(vid_click_x, vid_click_y)
            await asyncio.sleep(4)

            lyric_screen = pyautogui.screenshot()
            lyric_screen.save("/tmp/tunee_lyric_modal.png")

            # Suche Download-Button im Lyric Video Modal
            lyric_dl = await page.evaluate('''() => {
                const btns = document.querySelectorAll('button, a, [role="button"]');
                for (const btn of btns) {
                    const text = (btn.textContent?.trim() || '').toLowerCase();
                    const html = btn.outerHTML.toLowerCase();
                    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.width < 250 && rect.height < 80 &&
                        (text.includes('download') || aria.includes('download') ||
                         html.includes('download'))) {
                        return {x: rect.left + rect.width/2, y: rect.top + rect.height/2,
                                w: rect.width, h: rect.height};
                    }
                }
                return null;
            }''')

            if lyric_dl:
                ldl_sx, ldl_sy = await viewport_to_screen(page, lyric_dl['x'], lyric_dl['y'])
                ldl_w = max(int(lyric_dl['w']) + 10, 40)
                ldl_h = max(int(lyric_dl['h']) + 10, 30)
                crop = lyric_screen.crop((
                    ldl_sx - ldl_w // 2, ldl_sy - ldl_h // 2,
                    ldl_sx + ldl_w // 2, ldl_sy + ldl_h // 2
                ))
                crop.save(TEMPLATES_DIR / "lyric_video_download.png")
                print(f"   lyric_video_download.png: {ldl_w}x{ldl_h}px")
            else:
                print("   Lyric Video Download-Button nicht gefunden!")
                print("   Debug: /tmp/tunee_lyric_modal.png")
        else:
            print("   VIDEO nicht im Modal gefunden")

        # === Aufraeumen ===
        print("\n10. Aufraeumen...")
        for _ in range(3):
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.3)
        pyautogui.moveTo(10, 10)
        await page.mouse.move(10, 10)

        # === Ergebnis ===
        print("\n" + "=" * 50)
        print("ERGEBNIS")
        print("=" * 50)
        all_ok = True
        for name in ["download_button", "modal_mp3", "lyric_video_download"]:
            path = TEMPLATES_DIR / f"{name}.png"
            if path.exists():
                from PIL import Image
                img = Image.open(path)
                print(f"   {name}.png: {img.size[0]}x{img.size[1]}px")
            else:
                print(f"   {name}.png: FEHLT!")
                all_ok = False

        if all_ok:
            print("\n   Alle 3 Templates erstellt!")
        else:
            print("\n   Einige Templates fehlen - pruefe Debug-Screenshots in /tmp/")

        print("\nBrowser bleibt 60s offen. Ctrl+C zum Beenden.")
        try:
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            pass

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
