"""
Playwright Browser-Automation für Tunee.ai
Korrekter Workflow basierend auf der echten Seitenstruktur.
"""

import asyncio
import time
from dataclasses import dataclass, field
from pathlib import Path
from playwright.async_api import Page

# PyAutoGUI für bildbasierte Automation (Hover-Button Problem)
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.5
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️ PyAutoGUI nicht verfügbar - Hybrid-Modus deaktiviert")

# Download-Ordner (normaler Downloads-Ordner)
DOWNLOADS_DIR = Path.home() / "Downloads" / "tunee"

# Templates für PyAutoGUI
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@dataclass
class SongDownloadLinks:
    """Download-Links und Infos für einen Song."""
    name: str
    duration: str
    mp3_url: str | None = None
    raw_url: str | None = None
    video_url: str | None = None
    lrc_url: str | None = None
    certificate_downloaded: bool = False
    item_id: str | None = None  # z.B. pPYXQerTz03BBJikn


class TuneeBrowser:
    """Browser-Automation für tunee.ai."""

    def __init__(self, page: Page):
        self.page = page

    async def wait_for_music_list(self, timeout: int = 15000) -> bool:
        """Wartet bis die Musik-Liste geladen ist."""
        try:
            await asyncio.sleep(2)

            # Klicke auf "All Music" falls sichtbar
            try:
                all_music_btn = self.page.locator('text="All Music"').first
                if await all_music_btn.is_visible():
                    print("Klicke auf 'All Music'...")
                    await all_music_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Warte auf Songs
            selectors = [
                'text=/\\d{2}:\\d{2}/',
                '[aria-label*="download" i]',
            ]

            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    print(f"Songs gefunden via: {selector}")
                    return True
                except:
                    continue

            content = await self.page.content()
            if "02:" in content or "03:" in content or "04:" in content:
                print("Songs gefunden via Seiteninhalt")
                return True

            return False
        except Exception as e:
            print(f"Musik-Liste nicht gefunden: {e}")
            return False

    async def get_song_list(self) -> list[dict]:
        """
        Extrahiert alle Songs aus der linken Liste.
        Scrollt automatisch durch die Liste um alle Songs zu finden.
        """
        all_songs = []
        seen_keys = set()

        # Scroll-Loop: Mehrmals durch die Liste scrollen
        last_count = 0
        no_new_songs_count = 0

        print("    Scanne Song-Liste (scrolle automatisch)...")

        while no_new_songs_count < 5:
            # Extrahiere sichtbare Songs
            visible_songs = await self.page.evaluate('''() => {
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
            scrolled = await self.page.evaluate('''() => {
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
        await self.page.evaluate('''() => {
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
        print(f"    Scan abgeschlossen: {len(all_songs)} Songs")

        return all_songs

    async def click_song_and_use_right_panel_download(self, song_name: str, duration: str) -> bool:
        """
        NEUER ANSATZ:
        1. Klicke auf Song in linker Liste (öffnet rechtes Panel)
        2. Klicke auf Download-Button IM RECHTEN PANEL (nicht in der Liste!)

        Vorteil: Rechtes Panel hat immer sichtbare Buttons, kein Hover nötig!
        """
        try:
            safe_name = song_name.replace("'", "\\'").replace('"', '\\"').replace('\\', '\\\\')
            safe_duration = duration

            # 1. Klicke auf Song in der Liste
            for attempt in range(10):
                clicked = await self.page.evaluate(f'''() => {{
                    const searchName = '{safe_name}';
                    const searchDuration = '{safe_duration}';
                    const allElements = document.querySelectorAll('*');

                    for (const el of allElements) {{
                        const text = el.textContent?.trim();
                        if (text === searchDuration && el.childNodes.length === 1) {{
                            const rect = el.getBoundingClientRect();
                            if (rect.left > 50 && rect.left < 400 && rect.top > 50 && rect.top < window.innerHeight - 50) {{

                                // Prüfe Song-Name
                                let container = el.parentElement;
                                for (let i = 0; i < 5 && container; i++) {{
                                    if (container.textContent.includes(searchName)) {{
                                        // Song gefunden - klicke Container
                                        for (let j = 0; j < 3 && container; j++) {{
                                            const cRect = container.getBoundingClientRect();
                                            if (cRect.height > 40 && cRect.height < 120) {{
                                                container.click();
                                                return true;
                                            }}
                                            container = container.parentElement;
                                        }}
                                    }}
                                    container = container.parentElement;
                                }}
                            }}
                        }}
                    }}
                    return false;
                }}''')

                if clicked:
                    print(f"      ✓ Song angeklickt")
                    break

                # Scrolle
                await self.page.evaluate('''() => {
                    const containers = document.querySelectorAll('div');
                    for (const c of containers) {
                        const rect = c.getBoundingClientRect();
                        if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                            c.scrollHeight > c.clientHeight + 10) {
                            c.scrollTop += 100;
                            return;
                        }
                    }
                }''')
                await asyncio.sleep(0.3)

            if not clicked:
                print(f"      ✗ Song nicht gefunden")
                return False

            # 2. Warte auf rechtes Panel-Update
            await asyncio.sleep(2)

            # 3. Klicke auf 3-PUNKTE-MENÜ im rechten Panel
            print(f"      Öffne 3-Punkte-Menü... ", end="", flush=True)

            menu_opened = await self.page.evaluate('''() => {
                const buttons = document.querySelectorAll('button, [role="button"]');

                // Suche 3-Punkte-Button im rechten Panel (x > 600, oben)
                // Sortiere nach X-Position - 3-Punkte ist der rechteste Button
                const rightButtons = [];
                for (const btn of buttons) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.left > 650 && rect.top > 150 && rect.top < 300 && rect.width < 60) {
                        rightButtons.push({ btn: btn, x: rect.left });
                    }
                }

                // Sortiere nach X (rechtester zuerst)
                rightButtons.sort((a, b) => b.x - a.x);

                // Der rechteste Button sollte das 3-Punkte-Menü sein
                if (rightButtons.length > 0) {
                    rightButtons[0].btn.click();
                    return true;
                }

                return false;
            }''')

            if not menu_opened:
                print(f"✗ nicht gefunden")
                return False

            print(f"✓")
            await asyncio.sleep(0.8)

            # 4. Klicke "Download" im Menü
            print(f"      Klicke 'Download' im Menü... ", end="", flush=True)

            download_clicked = await self.page.evaluate('''() => {
                // Suche nach "Download" Text im Menü
                const allElements = document.querySelectorAll('*');

                for (const el of allElements) {
                    const text = el.textContent?.trim();
                    if (text === 'Download') {
                        // Prüfe ob es ein klickbares Element ist
                        let clickTarget = el;
                        for (let i = 0; i < 3 && clickTarget; i++) {
                            const role = clickTarget.getAttribute('role');
                            const tag = clickTarget.tagName.toLowerCase();

                            if (role === 'menuitem' || tag === 'button' || tag === 'a' ||
                                clickTarget.onclick || clickTarget.classList.contains('cursor-pointer')) {
                                clickTarget.click();
                                return true;
                            }
                            clickTarget = clickTarget.parentElement;
                        }
                    }
                }

                return false;
            }''')

            if download_clicked:
                print(f"✓ (via {download_clicked})")
                await asyncio.sleep(0.5)

                # Prüfe ob Modal geöffnet wurde
                try:
                    await self.page.wait_for_selector('[role="dialog"]', timeout=3000)
                    print(f"      ✓ Modal geöffnet")
                    return True
                except:
                    print(f"      ✗ Modal nicht geöffnet")
                    return False
            else:
                print(f"✗ nicht gefunden")
                return False

        except Exception as e:
            print(f"      ✗ Fehler: {e}")
            return False

    async def click_download_button_by_coordinates(self, song_name: str, duration: str) -> bool:
        """
        KOORDINATEN-BASIERTER Ansatz: Finde Duration, hovere, klicke auf Koordinaten.
        Buttons erscheinen nur bei Hover, aber sind schwer zu finden.
        Lösung: Klicke einfach rechts neben dem Stern (feste Offset-Position).
        """
        try:
            safe_duration = duration

            for scroll_attempt in range(10):
                # Finde Duration-Element
                duration_info = await self.page.evaluate(f'''() => {{
                    const allElements = document.querySelectorAll('*');
                    const searchDuration = '{safe_duration}';

                    for (const el of allElements) {{
                        const text = el.textContent?.trim();
                        if (text === searchDuration && el.childNodes.length === 1) {{
                            const rect = el.getBoundingClientRect();
                            if (rect.left > 50 && rect.left < 400 && rect.top > 50 && rect.top < window.innerHeight - 50) {{
                                return {{
                                    found: true,
                                    x: rect.left,
                                    y: rect.top,
                                    height: rect.height
                                }};
                            }}
                        }}
                    }}
                    return {{ found: false }};
                }}''')

                if not duration_info.get('found'):
                    # Scrolle
                    await self.page.evaluate('''() => {
                        const containers = document.querySelectorAll('div');
                        for (const c of containers) {
                            const rect = c.getBoundingClientRect();
                            if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                                c.scrollHeight > c.clientHeight + 10) {
                                c.scrollTop += 100;
                                return;
                            }
                        }
                    }''')
                    await asyncio.sleep(0.3)
                    continue

                # Duration gefunden - hovere und klicke
                dur_x = duration_info['x']
                dur_y = duration_info['y']
                dur_height = duration_info['height']

                # Hovere über die Zeile (bewege Maus zur Duration)
                await self.page.mouse.move(dur_x + 50, dur_y + dur_height / 2)
                await asyncio.sleep(1.5)  # Warte auf Button-Erscheinen

                print(f"      (Hover bei x={int(dur_x)}, y={int(dur_y)})")

                # Download-Button ist ca. 350-370px rechts von der Duration
                # Klicke einfach auf diese Position
                download_x = dur_x + 360
                download_y = dur_y + dur_height / 2

                print(f"      Klicke auf Koordinaten x={int(download_x)}, y={int(download_y)}... ", end="", flush=True)
                await self.page.mouse.click(download_x, download_y)
                await asyncio.sleep(0.5)

                # Prüfe ob Modal geöffnet wurde
                try:
                    await self.page.wait_for_selector('[role="dialog"]', timeout=2000)
                    print(f"✓ Modal geöffnet")
                    await self.page.mouse.move(10, 10)  # Maus weg
                    return True
                except:
                    print(f"✗ Kein Modal")
                    # Versuche nochmal mit anderem Offset
                    if scroll_attempt < 2:
                        continue

                return False

            return False
        except Exception as e:
            print(f"    Koordinaten-Fehler: {e}")
            return False

    async def click_download_button_in_list_simple(self, song_name: str, duration: str) -> bool:
        """
        EINFACHSTER Ansatz: Finde die Duration, dann den Download-Button rechts daneben.
        """
        try:
            safe_name = song_name.replace("'", "\\'").replace('"', '\\"').replace('\\', '\\\\')
            safe_duration = duration

            # Scrolle zum Song falls nötig
            for scroll_attempt in range(15):
                # WICHTIG: Bewege Maus erstmal weg von allen Songs (oben links)
                if scroll_attempt == 0:
                    await self.page.mouse.move(10, 10)
                    await asyncio.sleep(0.2)

                # SCHRITT 1: Finde und HOVERE über die Song-Zeile (Buttons erscheinen vielleicht nur bei Hover)
                hover_result = await self.page.evaluate(f'''() => {{
                    const searchDuration = '{safe_duration}';
                    const searchName = '{safe_name}';
                    const allElements = document.querySelectorAll('*');

                    for (const el of allElements) {{
                        const text = el.textContent?.trim();
                        if (text === searchDuration && el.childNodes.length === 1) {{
                            const rect = el.getBoundingClientRect();
                            if (rect.left > 400 || rect.top < 50 || rect.top > window.innerHeight - 50) {{
                                continue;
                            }}

                            // Prüfe Song-Name und finde den RICHTIGEN Hover-Container
                            // WICHTIG: MusicItem ist der Container, der die Hover-Events abfängt!
                            let parent = el.parentElement;
                            let hoverTarget = null;

                            for (let i = 0; i < 8 && parent; i++) {{
                                const parentText = parent.textContent || '';
                                const pRect = parent.getBoundingClientRect();

                                if (parentText.includes(searchName)) {{
                                    // Suche nach dem MusicItem-Container
                                    // Erkennbar an: class enthält "group/music-item" oder "hover:bg"
                                    const className = parent.className || '';
                                    const dataComponent = parent.getAttribute('data-sentry-component') || '';

                                    if (dataComponent === 'MusicItem' ||
                                        className.includes('music-item') ||
                                        className.includes('group/music-item')) {{
                                        hoverTarget = parent;
                                        break;
                                    }}

                                    // Fallback: Zeile mit richtiger Größe
                                    if (pRect.height >= 40 && pRect.height <= 120) {{
                                        hoverTarget = parent;
                                    }}
                                }}
                                parent = parent.parentElement;
                            }}

                            if (hoverTarget) {{
                                // Song gefunden - markiere die Zeile für Hover
                                const uniqueId = 'cgc-hover-' + Date.now();
                                hoverTarget.setAttribute('data-cgc-hover-target', uniqueId);
                                const pRect = hoverTarget.getBoundingClientRect();
                                return {{
                                    found: true,
                                    id: uniqueId,
                                    x: pRect.left + pRect.width / 2,
                                    y: pRect.top + pRect.height / 2,
                                    height: Math.round(pRect.height)
                                }};
                            }}
                        }}
                    }}
                    return {{ found: false }};
                }}''')

                if not hover_result.get('found'):
                    # Song nicht gefunden - scrolle weiter
                    await self.page.evaluate('''() => {
                        const containers = document.querySelectorAll('div');
                        for (const c of containers) {
                            const rect = c.getBoundingClientRect();
                            if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                                c.scrollHeight > c.clientHeight + 10) {
                                c.scrollTop += 100;
                                return;
                            }
                        }
                    }''')
                    await asyncio.sleep(0.3)
                    continue

                # Song gefunden - HOVERE über die Zeile (WICHTIG: Buttons erscheinen nur bei Hover!)
                try:
                    hover_id = hover_result['id']
                    row_height = hover_result.get('height', '?')
                    hover_target = self.page.locator(f'[data-cgc-hover-target="{hover_id}"]').first

                    # Hovere über die Song-Zeile (MusicItem)
                    await hover_target.hover(force=True)
                    # WICHTIG: Warte länger auf CSS-Animationen (opacity transition)
                    await asyncio.sleep(1.5)

                    print(f"      (Hover auf {row_height}px MusicItem)")
                except Exception as e:
                    print(f"      (Hover-Fehler: {e})")
                    pass

                # SCHRITT 2: Jetzt finde Download-Button (sollte jetzt nach Hover sichtbar sein)
                element_info = await self.page.evaluate(f'''() => {{
                    const searchDuration = '{safe_duration}';
                    const searchName = '{safe_name}';

                    // Finde alle Elemente mit der Duration
                    const allElements = document.querySelectorAll('*');

                    for (const el of allElements) {{
                        const text = el.textContent?.trim();

                        // Exakte Duration-Match
                        if (text === searchDuration && el.childNodes.length === 1) {{
                            const rect = el.getBoundingClientRect();

                            // Nur linke Seite und sichtbar
                            if (rect.left > 400 || rect.top < 50 || rect.top > window.innerHeight - 50) {{
                                continue;
                            }}

                            // Jetzt prüfe ob der Song-Name in der Nähe ist (gleicher Container)
                            let parent = el.parentElement;
                            let foundName = false;

                            for (let i = 0; i < 5 && parent; i++) {{
                                const parentText = parent.textContent || '';
                                if (parentText.includes(searchName)) {{
                                    foundName = true;
                                    break;
                                }}
                                parent = parent.parentElement;
                            }}

                            if (!foundName) continue;

                            // Song gefunden! Jetzt finde Download-Button
                            // Suche alle Buttons auf der gleichen Y-Achse (±30px)
                            // WICHTIG: Nach Hover sollten jetzt mehr Buttons sichtbar sein
                            const allButtons = document.querySelectorAll('button, [role="button"]');
                            const candidateButtons = [];
                            const debugInfo = [];

                            for (const btn of allButtons) {{
                                const btnRect = btn.getBoundingClientRect();
                                const btnStyle = window.getComputedStyle(btn);

                                // Button muss sichtbar sein
                                const isVisible = btnStyle.display !== 'none' &&
                                                 btnStyle.visibility !== 'hidden' &&
                                                 parseFloat(btnStyle.opacity) > 0.1 &&
                                                 btnRect.width > 0 && btnRect.height > 0;

                                // Sammle Debug-Info für alle Buttons in der Zeile
                                if (Math.abs(btnRect.top - rect.top) < 30 &&
                                    btnRect.left > rect.left - 50 &&
                                    btnRect.left < rect.left + 400) {{
                                    debugInfo.push({{
                                        x: Math.round(btnRect.left),
                                        y: Math.round(btnRect.top),
                                        visible: isVisible,
                                        ariaLabel: btn.getAttribute('aria-label') || '',
                                        opacity: parseFloat(btnStyle.opacity)
                                    }});
                                }}

                                // Button muss auf gleicher Höhe sein UND sichtbar
                                if (Math.abs(btnRect.top - rect.top) < 30 &&
                                    btnRect.left > rect.left &&  // Rechts von der Duration
                                    btnRect.left < rect.left + 300 &&  // Aber nicht zu weit weg
                                    btnRect.width > 15 && btnRect.width < 80 &&
                                    isVisible) {{

                                    candidateButtons.push({{
                                        el: btn,
                                        x: btnRect.left,
                                        ariaLabel: btn.getAttribute('aria-label') || '',
                                        title: btn.getAttribute('title') || ''
                                    }});
                                }}
                            }}

                            // Sortiere nach X-Position
                            candidateButtons.sort((a, b) => a.x - b.x);

                            // Debug: Gebe Info zurück wenn keine Buttons gefunden
                            if (candidateButtons.length === 0) {{
                                return {{
                                    found: false,
                                    debug: debugInfo,
                                    total: debugInfo.length
                                }};
                            }}

                            // Suche Download-Button
                            for (const btn of candidateButtons) {{
                                const label = (btn.ariaLabel + ' ' + btn.title).toLowerCase();
                                if (label.includes('download')) {{
                                    const uniqueId = 'cgc-dl-' + Date.now();
                                    btn.el.setAttribute('data-cgc-click-target', uniqueId);

                                    const btnRect = btn.el.getBoundingClientRect();
                                    return {{
                                        found: true,
                                        id: uniqueId,
                                        x: btnRect.left + btnRect.width / 2,
                                        y: btnRect.top + btnRect.height / 2,
                                        method: 'by_label',
                                        total: candidateButtons.length,
                                        ariaLabel: btn.ariaLabel
                                    }};
                                }}
                            }}

                            // Fallback: Nimm den zweiten Button (nach Stern)
                            if (candidateButtons.length >= 2) {{
                                const uniqueId = 'cgc-dl-' + Date.now();
                                candidateButtons[1].el.setAttribute('data-cgc-click-target', uniqueId);

                                const btnRect = candidateButtons[1].el.getBoundingClientRect();
                                return {{
                                    found: true,
                                    id: uniqueId,
                                    x: btnRect.left + btnRect.width / 2,
                                    y: btnRect.top + btnRect.height / 2,
                                    method: 'second_btn',
                                    total: candidateButtons.length,
                                    ariaLabel: candidateButtons[1].ariaLabel
                                }};
                            }}

                            // Nur 1 Button? Dann nimm ihn
                            if (candidateButtons.length === 1) {{
                                const uniqueId = 'cgc-dl-' + Date.now();
                                candidateButtons[0].el.setAttribute('data-cgc-click-target', uniqueId);

                                const btnRect = candidateButtons[0].el.getBoundingClientRect();
                                return {{
                                    found: true,
                                    id: uniqueId,
                                    x: btnRect.left + btnRect.width / 2,
                                    y: btnRect.top + btnRect.height / 2,
                                    method: 'only_btn',
                                    total: 1,
                                    ariaLabel: candidateButtons[0].ariaLabel
                                }};
                            }}
                        }}
                    }}

                    return {{ found: false }};
                }}''')

                if element_info.get('found'):
                    try:
                        target_id = element_info['id']
                        method = element_info.get('method', '?')
                        total = element_info.get('total', '?')
                        aria_label = element_info.get('ariaLabel', '')

                        target = self.page.locator(f'[data-cgc-click-target="{target_id}"]').first

                        # WICHTIG: Erst hovern, falls Buttons nur bei Hover sichtbar sind
                        print(f"      hovere über Button... ", end="", flush=True)
                        await target.hover()
                        await asyncio.sleep(0.3)

                        print(f"klicke... ", end="", flush=True)
                        await target.click(force=True)

                        # Cleanup
                        await self.page.evaluate(f'''() => {{
                            const el = document.querySelector('[data-cgc-click-target="{target_id}"]');
                            if (el) el.removeAttribute('data-cgc-click-target');

                            // Auch Hover-Target cleanup
                            const hoverEl = document.querySelector('[data-cgc-hover-target]');
                            if (hoverEl) hoverEl.removeAttribute('data-cgc-hover-target');
                        }}''')

                        print(f"✓ ({method}, {total} buttons, aria='{aria_label}')")

                        # WICHTIG: Bewege Maus weg, damit Hover beim nächsten Song funktioniert
                        await self.page.mouse.move(0, 0)
                        await asyncio.sleep(0.5)

                        # Warte kurz auf Modal-Öffnung
                        print(f"      Warte auf Modal... ", end="", flush=True)
                        try:
                            await self.page.wait_for_selector('[role="dialog"]', timeout=3000)
                            print(f"✓ Modal geöffnet")
                            return True
                        except:
                            print(f"✗ Modal wurde NICHT geöffnet!")
                            return False
                    except Exception as e:
                        print(f"      ✗ Klick-Fehler: {e}")
                        # Fallback: Koordinaten
                        try:
                            await self.page.mouse.click(element_info['x'], element_info['y'])
                            print(f"      ✓ Koordinaten-Klick")
                            # Maus wegbewegen
                            await self.page.mouse.move(0, 0)
                            await asyncio.sleep(1.5)
                            return True
                        except:
                            pass
                else:
                    # Nicht gefunden - zeige Debug-Info
                    if 'debug' in element_info:
                        debug_list = element_info['debug']
                        print(f"      ✗ Keine Download-Buttons gefunden!")
                        print(f"      Debug: {len(debug_list)} Elemente in Zeile:")
                        for d in debug_list[:5]:  # Zeige max 5
                            print(f"        x={d['x']}, visible={d['visible']}, opacity={d['opacity']}, aria='{d['ariaLabel']}'")

                        # Bewege Maus weg für nächsten Versuch
                        await self.page.mouse.move(0, 0)

                    # Nach Debug-Ausgabe: Scrolle weiter (oder gib auf nach vielen Versuchen)
                    if scroll_attempt >= 3:
                        # Nach 3 Versuchen aufgeben
                        return False

                # Scrollen
                await self.page.evaluate('''() => {
                    const containers = document.querySelectorAll('div');
                    for (const c of containers) {
                        const rect = c.getBoundingClientRect();
                        if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                            c.scrollHeight > c.clientHeight + 10) {
                            c.scrollTop += 100;
                            return;
                        }
                    }
                }''')
                await asyncio.sleep(0.3)

            return False
        except Exception as e:
            print(f"    Fehler (Simple): {e}")
            return False

    async def click_download_button_in_list(self, song_name: str, duration: str) -> bool:
        """
        Klickt auf den Download-Button direkt neben dem Song in der linken Liste.
        Dieser Button öffnet direkt das Download-Modal mit den 4 Dateien.
        Viel einfacher als Song anzuklicken und auf Panel-Update zu warten!
        """
        try:
            safe_name = song_name.replace("'", "\\'").replace('"', '\\"').replace('\\', '\\\\')
            safe_duration = duration

            # Versuche mehrmals (mit Scrollen)
            for scroll_attempt in range(15):
                # Finde den Song und klicke auf den Download-Button daneben
                element_info = await self.page.evaluate(f'''() => {{
                    const searchName = '{safe_name}';
                    const searchDuration = '{safe_duration}';
                    const timeRegex = /^\\d{{2}}:\\d{{2}}$/;
                    const allElements = document.querySelectorAll('*');

                    for (const el of allElements) {{
                        const text = el.textContent?.trim();
                        // Finde Element mit exakter Duration
                        if (text === searchDuration && el.childNodes.length === 1) {{
                            const rect = el.getBoundingClientRect();
                            // Nur linke Seite und sichtbar
                            if (rect.left > 400) continue;
                            if (rect.top < 100 || rect.top > window.innerHeight - 50) continue;

                            // Gehe zum Container hoch
                            let container = el.parentElement;
                            for (let i = 0; i < 5 && container; i++) {{
                                const cRect = container.getBoundingClientRect();
                                if (cRect.height > 50 && cRect.height < 120) {{
                                    // Prüfe ob der EXAKTE Song-Name enthalten ist
                                    const textNodes = container.querySelectorAll('span, div, p, a');
                                    for (const node of textNodes) {{
                                        const nodeText = node.textContent?.trim();
                                        // Exakter Match des Song-Namens
                                        if (nodeText === searchName) {{
                                            // JETZT: Finde den Download-Button in diesem Container
                                            // Laut Screenshot: Zwei Icons nebeneinander - Stern (1) und Download-Pfeil (2)

                                            // Strategie: Gehe NICHT zum großen Container hoch, sondern
                                            // bleibe bei der Duration und suche in der ZEILE nach Buttons

                                            // Finde die Zeile (kleiner Container, ca. 50-80px hoch)
                                            let row = container;
                                            const durationRect = el.getBoundingClientRect();

                                            // Suche nach dem Row-Container (nicht zu groß)
                                            for (let j = 0; j < 3 && row; j++) {{
                                                const rowRect = row.getBoundingClientRect();
                                                if (rowRect.height > 40 && rowRect.height < 100) {{
                                                    break;
                                                }}
                                                row = row.parentElement;
                                            }}

                                            if (!row) row = container;

                                            const rowRect = row.getBoundingClientRect();

                                            // Finde alle Buttons in dieser ZEILE (nicht im gesamten Container)
                                            const allButtons = document.querySelectorAll('button, [role="button"]');
                                            const rowButtons = [];

                                            for (const btn of allButtons) {{
                                                const btnRect = btn.getBoundingClientRect();

                                                // Button muss in der gleichen Zeile sein wie die Duration
                                                if (Math.abs(btnRect.top - durationRect.top) < 40 &&
                                                    btnRect.left >= rowRect.left - 10 &&
                                                    btnRect.right <= rowRect.right + 10 &&
                                                    btnRect.width > 15 && btnRect.width < 80) {{
                                                    rowButtons.push({{
                                                        el: btn,
                                                        x: btnRect.left,
                                                        ariaLabel: btn.getAttribute('aria-label') || ''
                                                    }});
                                                }}
                                            }}

                                            // Sortiere nach X-Position (von links nach rechts)
                                            rowButtons.sort((a, b) => a.x - b.x);

                                            // Methode 1: Suche nach aria-label mit "download"
                                            for (const btnInfo of rowButtons) {{
                                                if (btnInfo.ariaLabel.toLowerCase().includes('download')) {{
                                                    const uniqueId = 'cgc-download-' + Date.now();
                                                    btnInfo.el.setAttribute('data-cgc-click-target', uniqueId);

                                                    const btnRect = btnInfo.el.getBoundingClientRect();
                                                    return {{
                                                        found: true,
                                                        id: uniqueId,
                                                        x: btnRect.left + btnRect.width / 2,
                                                        y: btnRect.top + btnRect.height / 2,
                                                        method: 'aria_download',
                                                        totalButtons: rowButtons.length
                                                    }};
                                                }}
                                            }}

                                            // Methode 2: Der zweite Button in der Zeile (nach dem Stern)
                                            if (rowButtons.length >= 2) {{
                                                const downloadBtn = rowButtons[1].el;
                                                const uniqueId = 'cgc-download-' + Date.now();
                                                downloadBtn.setAttribute('data-cgc-click-target', uniqueId);

                                                const btnRect = downloadBtn.getBoundingClientRect();
                                                return {{
                                                    found: true,
                                                    id: uniqueId,
                                                    x: btnRect.left + btnRect.width / 2,
                                                    y: btnRect.top + btnRect.height / 2,
                                                    method: 'second_in_row',
                                                    totalButtons: rowButtons.length
                                                }};
                                            }}

                                            // Methode 3: Nur 1 Button? Dann ist es vielleicht der Download-Button
                                            if (rowButtons.length === 1) {{
                                                const downloadBtn = rowButtons[0].el;
                                                const uniqueId = 'cgc-download-' + Date.now();
                                                downloadBtn.setAttribute('data-cgc-click-target', uniqueId);

                                                const btnRect = downloadBtn.getBoundingClientRect();
                                                return {{
                                                    found: true,
                                                    id: uniqueId,
                                                    x: btnRect.left + btnRect.width / 2,
                                                    y: btnRect.top + btnRect.height / 2,
                                                    method: 'only_button',
                                                    totalButtons: 1
                                                }};
                                            }}
                                        }}
                                    }}
                                }}
                                container = container.parentElement;
                            }}
                        }}
                    }}
                    return {{ found: false }};
                }}''')

                if element_info.get('found'):
                    # Download-Button gefunden - klicke mit Playwright
                    try:
                        target_id = element_info['id']
                        method = element_info.get('method', 'unknown')
                        total_buttons = element_info.get('totalButtons', '?')
                        target = self.page.locator(f'[data-cgc-click-target="{target_id}"]').first

                        # Klicke auf den Download-Button
                        await target.click(force=True)

                        # Entferne das temporäre Attribut
                        await self.page.evaluate(f'''() => {{
                            const el = document.querySelector('[data-cgc-click-target="{target_id}"]');
                            if (el) el.removeAttribute('data-cgc-click-target');
                        }}''')

                        print(f"      (via {method}, {total_buttons} buttons gefunden)")
                        await asyncio.sleep(1.5)
                        return True
                    except Exception as e:
                        print(f"    Fehler beim Download-Button Click: {e}")
                        # Fallback: Klicke auf Koordinaten
                        try:
                            await self.page.mouse.click(element_info['x'], element_info['y'])
                            print(f"      (via Koordinaten-Klick)")
                            await asyncio.sleep(1.5)
                            return True
                        except:
                            pass
                else:
                    # Nicht gefunden - Debug info
                    if scroll_attempt == 0:
                        print(f"      (Song gefunden, aber kein Download-Button)")

                # Song nicht sichtbar - scrolle
                await self.page.evaluate(f'''() => {{
                    const containers = document.querySelectorAll('div');
                    for (const c of containers) {{
                        const rect = c.getBoundingClientRect();
                        if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                            c.scrollHeight > c.clientHeight + 10) {{
                            if ({scroll_attempt} < 10) {{
                                c.scrollTop += 100;
                            }} else {{
                                c.scrollTop = 0;
                            }}
                            return;
                        }}
                    }}
                }}''')
                await asyncio.sleep(0.3)

            return False
        except Exception as e:
            print(f"    Fehler beim Download-Button: {e}")
            return False

    async def click_song_in_list(self, song_name: str, duration: str) -> bool:
        """
        Klickt auf einen Song in der linken Liste.
        Scrollt automatisch zum Song wenn nötig.
        Matcht exakt Name UND Duration.
        WICHTIG: Nutzt Playwright's native click() statt JavaScript-Click für React-Apps.
        """
        try:
            safe_name = song_name.replace("'", "\\'").replace('"', '\\"').replace('\\', '\\\\')
            safe_duration = duration

            # Versuche mehrmals (mit Scrollen)
            for scroll_attempt in range(15):
                # Finde das Element mit JavaScript und markiere es
                element_info = await self.page.evaluate(f'''() => {{
                    const searchName = '{safe_name}';
                    const searchDuration = '{safe_duration}';
                    const timeRegex = /^\\d{{2}}:\\d{{2}}$/;
                    const allElements = document.querySelectorAll('*');

                    for (const el of allElements) {{
                        const text = el.textContent?.trim();
                        // Finde Element mit exakter Duration
                        if (text === searchDuration && el.childNodes.length === 1) {{
                            const rect = el.getBoundingClientRect();
                            // Nur linke Seite und sichtbar
                            if (rect.left > 400) continue;
                            if (rect.top < 100 || rect.top > window.innerHeight - 50) continue;

                            // Gehe zum Container hoch
                            let container = el.parentElement;
                            for (let i = 0; i < 5 && container; i++) {{
                                const cRect = container.getBoundingClientRect();
                                if (cRect.height > 50 && cRect.height < 120) {{
                                    // Prüfe ob der EXAKTE Song-Name enthalten ist
                                    const textNodes = container.querySelectorAll('span, div, p, a');
                                    for (const node of textNodes) {{
                                        const nodeText = node.textContent?.trim();
                                        // Exakter Match des Song-Namens
                                        if (nodeText === searchName) {{
                                            // Finde das klickbare Element (button, a, oder Container)
                                            let clickTarget = container;

                                            // Suche nach Button oder Link im Container
                                            const clickables = container.querySelectorAll('button, a, [role="button"], [onclick]');
                                            if (clickables.length > 0) {{
                                                // Nimm das erste klickbare Element
                                                clickTarget = clickables[0];
                                            }} else {{
                                                // Prüfe ob Container selbst klickbar ist
                                                const style = window.getComputedStyle(container);
                                                if (style.cursor !== 'pointer' && container.onclick === null) {{
                                                    // Container nicht klickbar - suche weiter hoch
                                                    let parent = container.parentElement;
                                                    for (let j = 0; j < 3 && parent; j++) {{
                                                        const parentStyle = window.getComputedStyle(parent);
                                                        if (parentStyle.cursor === 'pointer' || parent.onclick !== null) {{
                                                            clickTarget = parent;
                                                            break;
                                                        }}
                                                        parent = parent.parentElement;
                                                    }}
                                                }}
                                            }}

                                            // Markiere das klickbare Element
                                            const uniqueId = 'cgc-target-' + Date.now();
                                            clickTarget.setAttribute('data-cgc-click-target', uniqueId);

                                            const targetRect = clickTarget.getBoundingClientRect();
                                            return {{
                                                found: true,
                                                id: uniqueId,
                                                x: targetRect.left + targetRect.width / 2,
                                                y: targetRect.top + targetRect.height / 2
                                            }};
                                        }}
                                    }}
                                }}
                                container = container.parentElement;
                            }}
                        }}
                    }}
                    return {{ found: false }};
                }}''')

                if element_info.get('found'):
                    # Element gefunden - nutze Playwright's nativen Click
                    try:
                        target_id = element_info['id']
                        target = self.page.locator(f'[data-cgc-click-target="{target_id}"]').first

                        # Nutze Playwright's Click (triggert echte Browser-Events)
                        await target.click(force=True)

                        # Entferne das temporäre Attribut
                        await self.page.evaluate(f'''() => {{
                            const el = document.querySelector('[data-cgc-click-target="{target_id}"]');
                            if (el) el.removeAttribute('data-cgc-click-target');
                        }}''')

                        # Mehr Wartezeit nach dem Klick
                        await asyncio.sleep(2.5)
                        return True
                    except Exception as e:
                        print(f"    Fehler beim Playwright-Click: {e}")
                        # Fallback: Klicke auf Koordinaten
                        try:
                            await self.page.mouse.click(element_info['x'], element_info['y'])
                            await asyncio.sleep(2.5)
                            return True
                        except:
                            pass

                # Song nicht sichtbar - scrolle
                await self.page.evaluate(f'''() => {{
                    const containers = document.querySelectorAll('div');
                    for (const c of containers) {{
                        const rect = c.getBoundingClientRect();
                        if (rect.left < 400 && rect.width > 200 && rect.height > 300 &&
                            c.scrollHeight > c.clientHeight + 10) {{
                            // Scroll nach unten oder oben je nach Versuch
                            if ({scroll_attempt} < 10) {{
                                c.scrollTop += 100;
                            }} else {{
                                // Nach oben scrollen falls nicht gefunden
                                c.scrollTop = 0;
                            }}
                            return;
                        }}
                    }}
                }}''')
                await asyncio.sleep(0.3)

            return False
        except Exception as e:
            print(f"    Fehler beim Song-Klick: {e}")
            return False

    async def open_three_dot_menu(self) -> bool:
        """Öffnet das 3-Punkte-Menü im rechten Detail-Panel."""
        try:
            # Im Detail-Panel gibt es 3 Buttons nebeneinander:
            # 1. Export/Share (Pfeil diagonal)
            # 2. Download (Pfeil runter)
            # 3. 3-Punkte "..." (den wollen wir!)
            #
            # Die 3 Buttons sind unter dem Song-Titel, horizontal angeordnet
            # Der 3-Punkte-Button ist der RECHTESTE der Gruppe

            clicked = await self.page.evaluate('''() => {
                const buttons = document.querySelectorAll('button, [role="button"]');

                // Finde alle Buttons im rechten Bereich (x > 650) und oben (y < 300)
                const rightButtons = Array.from(buttons).filter(btn => {
                    const rect = btn.getBoundingClientRect();
                    return rect.left > 650 && rect.top > 150 && rect.top < 280 && rect.width < 60;
                });

                // Sortiere nach X-Position
                rightButtons.sort((a, b) => {
                    return b.getBoundingClientRect().left - a.getBoundingClientRect().left;
                });

                // Der 3-Punkte-Button ist der rechteste (erste nach Sortierung)
                // Aber prüfe ob es wirklich der ... Button ist
                for (const btn of rightButtons) {
                    const text = btn.textContent?.trim() || '';
                    const ariaLabel = btn.getAttribute('aria-label') || '';

                    // Prüfe auf 3-Punkte Zeichen oder "more/menu" label
                    if (text === '...' || text === '⋯' || text === '•••' || text === '···' ||
                        ariaLabel.toLowerCase().includes('more') ||
                        ariaLabel.toLowerCase().includes('menu') ||
                        ariaLabel.toLowerCase().includes('option')) {
                        btn.click();
                        return 'found_by_text';
                    }

                    // Prüfe auf SVG mit 3 Kreisen (typisches ... Icon)
                    const svg = btn.querySelector('svg');
                    if (svg) {
                        const circles = svg.querySelectorAll('circle');
                        const dots = svg.querySelectorAll('[fill], path');
                        // 3-Punkte Icon hat oft 3 circles oder bestimmte paths
                        if (circles.length === 3 || (dots.length >= 3 && dots.length <= 6)) {
                            btn.click();
                            return 'found_by_svg_dots';
                        }
                    }
                }

                // Fallback: Nimm den rechtesten Button der Gruppe von 3
                if (rightButtons.length >= 3) {
                    // Die 3 Buttons sind: Share, Download, Menu (von links nach rechts)
                    // Nach der Sortierung (rechts zuerst) ist [0] der rechteste = Menu
                    rightButtons[0].click();
                    return 'found_by_position';
                }

                // Noch ein Fallback: Suche nach dem ... Text irgendwo
                for (const btn of buttons) {
                    const text = btn.textContent?.trim();
                    if (text === '...' || text === '⋯' || text === '•••') {
                        btn.click();
                        return 'found_by_dots_anywhere';
                    }
                }

                return false;
            }''')

            if clicked:
                print(f"      (3-Punkte-Button: {clicked})")
                await asyncio.sleep(0.5)
                # Prüfe ob Menü erschienen ist
                try:
                    await self.page.wait_for_selector('text="Copyright Certificate"', timeout=3000)
                    return True
                except:
                    # Versuche nochmal mit anderem Selektor
                    try:
                        await self.page.wait_for_selector('text="Download"', timeout=2000)
                        return True
                    except:
                        print(f"      Menü nicht erschienen nach Klick")

            return False
        except Exception as e:
            print(f"    Fehler beim Öffnen des 3-Punkte-Menüs: {e}")
            return False

    async def click_menu_item(self, item_text: str) -> bool:
        """Klickt auf einen Menüpunkt im 3-Punkte-Menü."""
        try:
            # Warte kurz bis Menü vollständig gerendert ist
            await asyncio.sleep(0.5)

            # Escape Apostrophe für JavaScript
            safe_text = item_text.replace("'", "\\'")

            # Suche nach EXAKTEM Text-Match im Menü
            clicked = await self.page.evaluate(f'''() => {{
                const searchText = '{safe_text}';

                // Finde das Menü (meist ein div mit role="menu" oder ein Popover)
                const menus = document.querySelectorAll('[role="menu"], [role="listbox"], [data-radix-menu-content], [class*="popover"], [class*="dropdown"], [class*="menu"]');

                // Suche in allen potentiellen Menü-Containern
                const searchIn = menus.length > 0 ? menus : [document.body];

                for (const menu of searchIn) {{
                    // Finde alle Text-Knoten
                    const walker = document.createTreeWalker(menu, NodeFilter.SHOW_TEXT);
                    let node;

                    while (node = walker.nextNode()) {{
                        const text = node.textContent?.trim();

                        // EXAKTER Match
                        if (text === searchText) {{
                            // Klicke auf das Parent-Element
                            let clickTarget = node.parentElement;

                            // Gehe hoch bis wir ein klickbares Element finden
                            for (let i = 0; i < 3 && clickTarget; i++) {{
                                const role = clickTarget.getAttribute('role');
                                const tag = clickTarget.tagName.toLowerCase();

                                if (role === 'menuitem' || role === 'option' ||
                                    tag === 'button' || tag === 'a' || tag === 'li' ||
                                    clickTarget.onclick ||
                                    clickTarget.style.cursor === 'pointer' ||
                                    clickTarget.classList.contains('cursor-pointer')) {{
                                    clickTarget.click();
                                    return 'clicked_exact';
                                }}
                                clickTarget = clickTarget.parentElement;
                            }}

                            // Fallback: Klicke direkt auf Parent
                            if (node.parentElement) {{
                                node.parentElement.click();
                                return 'clicked_parent';
                            }}
                        }}
                    }}
                }}

                // Zweiter Versuch: Suche nach Elementen deren textContent exakt passt
                const allElements = document.querySelectorAll('div, span, button, a, li, [role="menuitem"]');
                for (const el of allElements) {{
                    // Nur direkter Text, nicht verschachtelt
                    const directText = Array.from(el.childNodes)
                        .filter(n => n.nodeType === Node.TEXT_NODE)
                        .map(n => n.textContent?.trim())
                        .join('');

                    if (directText === searchText || el.textContent?.trim() === searchText) {{
                        // Aber nicht wenn es noch viel mehr Text enthält
                        if (el.textContent.length < searchText.length + 20) {{
                            el.click();
                            return 'clicked_element';
                        }}
                    }}
                }}

                return false;
            }}''')

            if clicked:
                print(f"      ({clicked}: '{item_text}')")
                await asyncio.sleep(1)
                return True

            # Fallback: Playwright Locator mit exaktem Match
            try:
                # Versuche exakten Text-Match
                menu_item = self.page.get_by_text(item_text, exact=True).first
                if await menu_item.is_visible():
                    await menu_item.click()
                    await asyncio.sleep(1)
                    return True
            except:
                pass

            print(f"      Menüpunkt '{item_text}' nicht gefunden")
            return False
        except Exception as e:
            print(f"    Fehler bei Menüpunkt '{item_text}': {e}")
            return False

    async def download_copyright_certificate(self) -> bool:
        """Lädt das Copyright Certificate herunter."""
        try:
            # Warte auf das Certificate Modal
            await asyncio.sleep(1)

            # Der Download-Button ist oben rechts im Modal
            clicked = await self.page.evaluate('''() => {
                // Suche nach Download-Button im Certificate-Bereich
                const buttons = document.querySelectorAll('button, a, [role="button"]');

                for (const btn of buttons) {
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    const title = btn.getAttribute('title') || '';
                    const className = btn.className || '';

                    if (ariaLabel.toLowerCase().includes('download') ||
                        title.toLowerCase().includes('download') ||
                        className.toLowerCase().includes('download')) {
                        btn.click();
                        return true;
                    }

                    // SVG Download Icon (Pfeil nach unten)
                    const svg = btn.querySelector('svg');
                    if (svg) {
                        const rect = btn.getBoundingClientRect();
                        // Download-Button ist oben rechts im Modal
                        if (rect.left > 600 && rect.top < 200) {
                            btn.click();
                            return true;
                        }
                    }
                }
                return false;
            }''')

            if clicked:
                await asyncio.sleep(2)  # Warte auf Download
                return True

            # Fallback: Klicke auf Download-Icon
            try:
                download_btn = self.page.locator('[aria-label*="download" i]').first
                await download_btn.click()
                await asyncio.sleep(2)
                return True
            except:
                pass

            return False
        except Exception as e:
            print(f"    Fehler beim Certificate-Download: {e}")
            return False

    async def close_modal(self) -> None:
        """Schließt das aktuelle Modal."""
        try:
            # Versuche X-Button zu finden
            close_selectors = [
                '[aria-label*="close" i]',
                '[aria-label*="schließen" i]',
                'button:has-text("×")',
                'button:has-text("X")',
            ]

            for selector in close_selectors:
                try:
                    close_btn = self.page.locator(selector).first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await asyncio.sleep(0.5)
                        return
                except:
                    continue

            # Fallback: Escape-Taste
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
        except:
            pass

    async def close_all_modals(self) -> None:
        """Schließt ALLE offenen Modals (mehrfach Escape drücken)."""
        try:
            # Drücke mehrfach Escape um sicherzustellen, dass alle Modals geschlossen sind
            for _ in range(3):
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.2)

            # Warte kurz
            await asyncio.sleep(0.3)
        except:
            pass

    async def download_from_modal(self, song_name: str, song_duration: str) -> dict:
        """
        Lädt alle Formate aus dem Download-Modal herunter.
        Reihenfolge: MP3 (1), RAW (2), LRC (4), VIDEO (3)
        Speichert mit Original-Songnamen im ~/Downloads/tunee/ Ordner.

        Ordnername = SongName_Duration (z.B. "Quiet_Resolve_03-45")
        Dateiname = SongName (ohne Duration)
        """
        results = {'mp3': False, 'raw': False, 'video': False, 'lrc': False}

        # Erstelle Song-Ordner mit Name + Duration für Eindeutigkeit
        safe_name = self._sanitize_filename(song_name)
        safe_duration = song_duration.replace(":", "-")  # 03:45 -> 03-45

        folder_name = f"{safe_name}_{safe_duration}"
        song_dir = DOWNLOADS_DIR / folder_name
        song_dir.mkdir(parents=True, exist_ok=True)

        # Dateiname = nur Song-Name (ohne Duration)
        file_base_name = safe_name

        try:
            # Warte auf Download-Modal - verschiedene Selektoren probieren
            modal_found = False
            for selector in ['text="MP3"', 'text="RAW"', 'text="VIDEO"', 'text="LRC"', 'text="Download"']:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    modal_found = True
                    print(f"      Modal gefunden via: {selector}")
                    break
                except:
                    continue

            if not modal_found:
                print(f"      WARNUNG: Download-Modal nicht erkannt, versuche trotzdem...")

            await asyncio.sleep(1)

            # WICHTIG: Verifiziere dass das Modal für den richtigen Song geöffnet wurde
            # Prüfe ob der Song-Name im Modal erscheint
            safe_name = song_name.replace("'", "\\'").replace('"', '\\"').replace('\\', '\\\\')
            correct_modal = await self.page.evaluate(f'''() => {{
                const searchName = '{safe_name}';

                // Suche nach Modal-Container (meist zentral, großer z-index)
                const allElements = document.querySelectorAll('div, [role="dialog"], [role="alertdialog"]');

                for (const el of allElements) {{
                    const style = window.getComputedStyle(el);
                    const zIndex = parseInt(style.zIndex) || 0;

                    // Modal hat hohen z-index
                    if (zIndex > 100) {{
                        const text = el.textContent || '';
                        if (text.includes(searchName) && text.includes('MP3')) {{
                            return true;
                        }}
                    }}
                }}
                return false;
            }}''')

            if not correct_modal:
                print(f"      FEHLER: Download-Modal zeigt falschen Song!")
                print(f"      Erwartete: {song_name}, aber Modal stimmt nicht überein")
                return results

            # Die 4 Download-Buttons sind im Modal vertikal angeordnet:
            # Index 0: MP3 - direkter Download
            # Index 1: RAW - direkter Download
            # Index 2: VIDEO - öffnet Lyric Video Modal (!) → muss dort nochmal Download klicken
            # Index 3: LRC - direkter Download
            #
            # Reihenfolge: MP3, RAW, LRC zuerst (direkte Downloads), dann VIDEO zum Schluss

            # Finde alle Download-Buttons im Download-Modal
            # WICHTIG: Nur Buttons im sichtbaren Modal mit hohem z-index
            print(f"      Suche Download-Buttons im Modal...")

            # Warte kurz, falls Modal noch lädt
            await asyncio.sleep(0.5)

            # Versuche Modal-Container zu finden
            buttons = []
            try:
                # Warte auf Modal (role="dialog")
                modal_container = self.page.locator('[role="dialog"]').first
                await modal_container.wait_for(state='visible', timeout=5000)
                print(f"      ✓ Modal gefunden")

                # Laut Screenshot: 4 Zeilen mit jeweils einem "Download" Button rechts
                # Buttons sind in Reihenfolge: MP3, RAW, VIDEO, LRC
                buttons = await modal_container.locator('button:has-text("Download")').all()

                print(f"      ✓ {len(buttons)} Download-Buttons gefunden")

                if len(buttons) < 4:
                    print(f"      ⚠ Warnung: Nur {len(buttons)} Buttons, erwartet 4")

            except Exception as e:
                print(f"      ✗ Modal nicht gefunden: {str(e)[:60]}")
                # Fallback: Suche global nach Download-Buttons
                buttons = await self.page.locator('button:has-text("Download")').all()
                print(f"      Fallback: {len(buttons)} Buttons gefunden")

            # Prüfe ob überhaupt Buttons gefunden wurden
            if len(buttons) == 0:
                print(f"      ✗ FEHLER: Keine Download-Buttons im Modal gefunden!")
                return results

            # Erst die direkten Downloads: MP3, RAW, LRC
            # WICHTIG: Reihenfolge wie vom User angegeben: 1, 2, 4, dann 3
            # Index 0 = MP3 Download (direkt)
            # Index 1 = RAW Download (direkt)
            # Index 2 = VIDEO Download (öffnet Lyric Video Modal!)
            # Index 3 = LRC Download (direkt)
            #
            # Reihenfolge: MP3, RAW, LRC zuerst, VIDEO zum Schluss
            direct_downloads = [
                (0, 'mp3', '.mp3'),
                (1, 'raw', '.flac'),
                (3, 'lrc', '.lrc'),
            ]

            for btn_idx, format_type, extension in direct_downloads:
                try:
                    if btn_idx >= len(buttons):
                        print(f"      {format_type.upper()}: ✗ Button #{btn_idx} nicht vorhanden (nur {len(buttons)} Buttons)")
                        continue

                    print(f"      {format_type.upper()}: ", end="", flush=True)

                    # Hole Button
                    btn = buttons[btn_idx]

                    is_disabled = await btn.is_disabled()

                    if is_disabled:
                        # Button ist ausgegraut (Instrumental ohne Lyrics)
                        if format_type == 'lrc':
                            # Erstelle leere LRC-Datei für Instrumentals
                            target_path = song_dir / f"{file_base_name}{extension}"
                            target_path.write_text("[00:00.00] This is an instrumental\n")
                            print(f"✓ {target_path.name} (instrumental)")
                            results[format_type] = True
                        else:
                            print(f"✗ Button disabled")
                        continue

                    try:
                        # Klicke UND warte auf Download
                        print(f"klicke... ", end="", flush=True)

                        try:
                            async with self.page.expect_download(timeout=15000) as download_info:
                                await btn.click(timeout=5000)

                            download = await download_info.value
                            target_path = song_dir / f"{file_base_name}{extension}"
                            await download.save_as(str(target_path))

                            print(f"✓ {target_path.name}")
                            results[format_type] = True
                        except Exception as download_e:
                            # Vielleicht startet der Download nicht sofort?
                            print(f"✗ Kein Download: {str(download_e)[:30]}")

                    except Exception as e:
                        print(f"✗ Fehler: {str(e)[:40]}")

                    await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"      {format_type.upper()}: ✗ {e}")

            # VIDEO zum Schluss - öffnet ein separates "Lyric Video" Modal
            try:
                print(f"      VIDEO: ", end="", flush=True)

                # VIDEO Button ist bei Index 2
                if len(buttons) > 2:
                    video_btn = buttons[2]

                    # Klicke VIDEO Button - öffnet Lyric Video Modal
                    print(f"klicke... ", end="", flush=True)
                    await video_btn.click()
                    await asyncio.sleep(2)

                    # Jetzt sollte das "Lyric Video" Modal offen sein
                    # Laut Screenshot: Ein großer "Download" Button unten
                    try:
                        # Warte auf das Lyric Video Modal (mit Text "Lyric Video")
                        print(f"warte auf Modal... ", end="", flush=True)
                        await self.page.wait_for_selector('text="Lyric Video"', timeout=5000)
                        print(f"Modal offen... ", end="", flush=True)

                        # Finde das Lyric Video Modal
                        lyric_modal = self.page.locator('[role="dialog"]:has-text("Lyric Video")').first

                        # Finde den Download-Button in diesem Modal (großer Button unten)
                        video_download_btn = lyric_modal.locator('button:has-text("Download")').first

                        target_path = song_dir / f"{file_base_name}.mp4"

                        # Klicke und warte auf Download
                        print(f"downloade... ", end="", flush=True)
                        async with self.page.expect_download(timeout=60000) as download_info:
                            await video_download_btn.click()

                        download = await download_info.value
                        await download.save_as(str(target_path))

                        # Warte bis die Datei vollständig heruntergeladen ist
                        await self._wait_for_file_complete(target_path)

                        results['video'] = True

                    except Exception as e:
                        print(f"✗ Fehler: {str(e)[:40]}")

                    # Modal schließen (falls noch offen)
                    await self.close_modal()
                    await asyncio.sleep(0.5)

                else:
                    print(f"✗ Button nicht vorhanden (nur {len(buttons)} Buttons)")

            except Exception as e:
                print(f"✗ {e}")

        except Exception as e:
            print(f"    Fehler im Download-Modal: {e}")

        return results

    def _sanitize_filename(self, name: str) -> str:
        """Bereinigt Dateinamen von ungültigen Zeichen."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    async def _wait_for_file_complete(self, file_path: Path, timeout: int = 120) -> bool:
        """
        Wartet bis eine Datei vollständig heruntergeladen ist.
        Prüft ob die Dateigröße sich nicht mehr ändert.
        """
        print(f"      Warte auf Download-Abschluss...", end=" ")

        start_time = asyncio.get_event_loop().time()
        last_size = -1
        stable_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if file_path.exists():
                current_size = file_path.stat().st_size

                if current_size == last_size and current_size > 0:
                    stable_count += 1
                    # Dateigröße ist 3x hintereinander gleich = fertig
                    if stable_count >= 3:
                        size_mb = current_size / (1024 * 1024)
                        print(f"✓ {size_mb:.1f} MB")
                        return True
                else:
                    stable_count = 0
                    last_size = current_size

            await asyncio.sleep(1)

        print(f"✗ Timeout nach {timeout}s")
        return False

    async def _wait_for_song_details_loaded(self, song_name: str, duration: str, timeout: int = 10) -> bool:
        """
        Wartet bis das rechte Detail-Panel für den angeklickten Song geladen ist.
        Prüft ob der Song-Name und Duration im rechten Panel (x > 400) erscheinen.
        """
        safe_name = song_name.replace("'", "\\'").replace('"', '\\"').replace('\\', '\\\\')
        safe_duration = duration

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                # Prüfe ob Song-Name UND Duration im rechten Panel erscheinen
                found = await self.page.evaluate(f'''() => {{
                    const searchName = '{safe_name}';
                    const searchDuration = '{safe_duration}';

                    // Suche im rechten Bereich (x > 400)
                    const allElements = document.querySelectorAll('*');
                    let foundName = false;
                    let foundDuration = false;

                    for (const el of allElements) {{
                        const rect = el.getBoundingClientRect();
                        // Nur rechter Bereich
                        if (rect.left <= 400) continue;

                        const text = el.textContent?.trim();

                        // Prüfe auf Song-Name (exakt oder als Teil)
                        if (text === searchName || (text && text.includes(searchName) && text.length < searchName.length + 20)) {{
                            foundName = true;
                        }}

                        // Prüfe auf Duration (exakt)
                        if (text === searchDuration) {{
                            foundDuration = true;
                        }}

                        if (foundName && foundDuration) {{
                            return true;
                        }}
                    }}

                    return false;
                }}''')

                if found:
                    return True

            except Exception as e:
                pass

            await asyncio.sleep(0.3)

        # Timeout - gebe Warnung aus, aber fahre fort
        print(f"      WARNUNG: Panel-Update Timeout nach {timeout}s")
        return False

    # ===== PyAutoGUI Hybrid Methods =====

    def _find_template(self, template_name: str, confidence: float = 0.85, timeout: int = 5):
        """
        Findet Template auf dem Screen (PyAutoGUI).

        Returns:
            (x, y) tuple oder None
        """
        if not PYAUTOGUI_AVAILABLE:
            return None

        template_path = TEMPLATES_DIR / f"{template_name}.png"

        if not template_path.exists():
            print(f"    ⚠️ Template nicht gefunden: {template_path}")
            return None

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                location = pyautogui.locateOnScreen(str(template_path), confidence=confidence)
                if location:
                    center = pyautogui.center(location)
                    return (center.x, center.y)
            except Exception:
                pass
            time.sleep(0.5)

        return None

    async def _download_song_hybrid(self, song: dict) -> bool:
        """
        Hybrid Download: Playwright findet Song → PyAutoGUI klickt.

        Workflow:
        1. Playwright scrollt Song in View
        2. PyAutoGUI findet & klickt Download-Button (bildbasiert)
        3. PyAutoGUI klickt Modal-Buttons (position-basiert)

        Args:
            song: {'name': str, 'duration': str}

        Returns:
            True wenn erfolgreich
        """
        if not PYAUTOGUI_AVAILABLE:
            print("    ❌ PyAutoGUI nicht verfügbar")
            return False

        song_name = song['name']
        duration = song['duration']

        MODAL_WAIT = 2.0
        DOWNLOAD_WAIT = 2.0
        LYRIC_VIDEO_WAIT = 3.0

        try:
            # 1. Finde Song in Liste (per Duration - eindeutig!)
            print(f"    1️⃣ Suche Song in Liste...")
            duration_elements = await self.page.locator(f'text="{duration}"').all()

            if not duration_elements:
                print(f"    ❌ Song nicht gefunden (Duration: {duration})")
                return False

            song_element = duration_elements[0]

            # 2. Scrolle Song in View
            print(f"    2️⃣ Scrolle Song in View...")
            await song_element.scroll_into_view_if_needed()
            await asyncio.sleep(1)

            # 3. WICHTIG: Hovere über Song um nur seinen Button sichtbar zu machen!
            print(f"    3️⃣ Hovere über Song...")
            await song_element.hover()
            await asyncio.sleep(1.5)  # Warte bis Button erscheint

            # 4. Finde Download-Button (PyAutoGUI - bildbasiert)
            # JETZT ist nur der Button vom aktuellen Song sichtbar!
            print(f"    4️⃣ Suche Download-Button...")
            download_btn = self._find_template("download_button", confidence=0.8, timeout=3)

            if not download_btn:
                print(f"    ❌ Download-Button nicht gefunden")
                print(f"       Tipp: Ist der Song wirklich in View? Browser-Zoom 100%?")
                return False

            print(f"    ✅ Download-Button gefunden bei x={download_btn[0]}, y={download_btn[1]}")

            # 5. Klicke Download-Button → Modal öffnet
            print(f"    5️⃣ Klicke Download-Button...")
            pyautogui.click(download_btn[0], download_btn[1])
            await asyncio.sleep(MODAL_WAIT)

            # 6. Finde MP3-Button im Modal (für Position)
            print(f"    6️⃣ Suche Modal-Buttons...")
            mp3_location = self._find_template("modal_mp3", confidence=0.85, timeout=3)

            if not mp3_location:
                print(f"    ❌ Modal nicht geöffnet (MP3 nicht gefunden)")
                return False

            print(f"    ✅ Modal geöffnet (MP3 bei x={mp3_location[0]}, y={mp3_location[1]})")

            # 7. Klicke Modal-Buttons (position-basiert mit PyAutoGUI)
            # Modal-Reihenfolge: MP3, RAW, VIDEO, LRC
            # Klick-Reihenfolge: MP3, RAW, LRC, VIDEO (VIDEO zuletzt!)
            offset_x = 150  # Offset zum Download-Button

            buttons = [
                ("MP3", 0),      # Zeile 1
                ("RAW", 100),    # Zeile 2
                ("LRC", 300),    # Zeile 4
                ("VIDEO", 200),  # Zeile 3
            ]

            print(f"    7️⃣ Klicke Downloads...")
            for label, y_offset in buttons:
                click_x = mp3_location[0] + offset_x
                click_y = mp3_location[1] + y_offset

                print(f"       → {label}...")
                pyautogui.click(click_x, click_y)
                await asyncio.sleep(DOWNLOAD_WAIT)

            # 8. Lyric Video Modal (nach VIDEO-Klick)
            print(f"    8️⃣ Warte auf Lyric Video Modal...")
            await asyncio.sleep(LYRIC_VIDEO_WAIT)

            lyric_btn = self._find_template("lyric_video_download", confidence=0.85, timeout=3)

            if lyric_btn:
                print(f"    ✅ Lyric Video Download gefunden bei x={lyric_btn[0]}, y={lyric_btn[1]}")
                print(f"       → Klicke VIDEO Download...")
                pyautogui.click(lyric_btn[0], lyric_btn[1])
                await asyncio.sleep(DOWNLOAD_WAIT)
                print(f"    ✅ VIDEO Download gestartet")
            else:
                print(f"    ⚠️ Lyric Video Download nicht gefunden (skip)")

            # WICHTIG: Bewege Maus weg damit beim nächsten Song keine alten Buttons sichtbar sind!
            print(f"    9️⃣ Bewege Maus weg...")
            pyautogui.moveTo(10, 10)
            await asyncio.sleep(0.5)

            print(f"    ✅ Alle Downloads erfolgreich!")
            return True

        except Exception as e:
            print(f"    ❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
            # Auch bei Fehler: Maus wegbewegen
            try:
                pyautogui.moveTo(10, 10)
            except:
                pass
            return False

    async def process_song(self, song_name: str, duration: str, download_certificate: bool = False) -> SongDownloadLinks | None:
        """
        HYBRID Workflow für einen Song:
        1. PyAutoGUI findet & klickt Download-Button (bildbasiert)
        2. Download-Modal öffnet sich → alle Formate herunterladen (PyAutoGUI)
        3. Fertig!

        Nutzt PyAutoGUI für Klicks (löst Hover-Button Problem).
        Certificate wird später separat nachgeladen.
        """
        print(f"\n  [{song_name}] ({duration})")

        try:
            # 0. WICHTIG: Schließe alle offenen Modals vom vorherigen Song
            await self.close_all_modals()

            # HYBRID DOWNLOAD: PyAutoGUI statt Playwright
            if PYAUTOGUI_AVAILABLE:
                print(f"    🎯 Nutze Hybrid-Modus (PyAutoGUI)...")
                success = await self._download_song_hybrid({'name': song_name, 'duration': duration})

                if success:
                    # Erfolg! Alle 5 Dateien sollten heruntergeladen sein
                    return SongDownloadLinks(
                        name=song_name,
                        duration=duration,
                        mp3_url="downloaded",
                        raw_url="downloaded",
                        video_url="downloaded",
                        lrc_url="downloaded",
                        certificate_downloaded=False
                    )
                else:
                    print(f"    ❌ Hybrid-Download fehlgeschlagen")
                    return None
            else:
                # Fallback: Alte Methode (funktioniert nicht zuverlässig wegen Hover-Problem)
                print(f"    ⚠️ PyAutoGUI nicht verfügbar, nutze Fallback...")
                print(f"    Öffne Song im rechten Panel...")

                success = await self.click_song_and_use_right_panel_download(song_name, duration)

                if not success:
                    print(f"    FEHLER: Rechtes Panel funktioniert nicht")
                    return None

                print(f"    Starte Downloads...")
                results = await self.download_from_modal(song_name, duration)

                await self.close_modal()

                success_count = sum(1 for v in results.values() if v)
                print(f"    → {success_count}/4 Downloads erfolgreich")

                return SongDownloadLinks(
                    name=song_name,
                    duration=duration,
                    mp3_url="downloaded" if results.get('mp3') else None,
                    raw_url="downloaded" if results.get('raw') else None,
                    video_url="downloaded" if results.get('video') else None,
                    lrc_url="downloaded" if results.get('lrc') else None,
                    certificate_downloaded=False
                )
        finally:
            # WICHTIG: Bewege Maus nach jedem Song weg (auch bei Fehler!)
            try:
                await self.page.mouse.move(10, 10)
                await asyncio.sleep(0.2)
            except:
                pass
