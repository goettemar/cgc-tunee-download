"""
Vereinfachter Browser-Ansatz mit Playwright's nativen Locators
"""

import asyncio
from pathlib import Path
from playwright.async_api import Page

DOWNLOADS_DIR = Path.home() / "Downloads" / "tunee"

class SimpleTuneeBrowser:
    """Einfacher Browser mit Playwright-Locators"""

    def __init__(self, page: Page):
        self.page = page

    async def download_song_by_index(self, index: int, song_name: str, duration: str) -> bool:
        """
        Download Song über Index in der Liste (0-basiert).
        Einfacher Ansatz: Klicke auf Song-Index, dann auf Download im rechten Panel.
        """
        try:
            print(f"\n  [{song_name}] ({duration})")
            print(f"    Song #{index} in Liste...")

            # STRATEGIE: Nutze JavaScript um den N-ten Song zu finden und zu klicken
            clicked = await self.page.evaluate(f'''() => {{
                const searchDuration = '{duration}';
                const allElements = document.querySelectorAll('*');
                const songs = [];

                // Sammle alle Songs (mit Duration)
                for (const el of allElements) {{
                    const text = el.textContent?.trim();
                    const timeRegex = /^\\d{{2}}:\\d{{2}}$/;

                    if (text && timeRegex.test(text) && el.childNodes.length === 1) {{
                        const rect = el.getBoundingClientRect();
                        if (rect.left < 400 && rect.top > 50) {{
                            songs.push({{
                                element: el,
                                duration: text,
                                y: rect.top
                            }});
                        }}
                    }}
                }}

                // Sortiere nach Y-Position (von oben nach unten)
                songs.sort((a, b) => a.y - b.y);

                // Klicke auf den N-ten Song (Index)
                if (songs.length > {index}) {{
                    const song = songs[{index}];

                    // Finde klickbaren Container
                    let container = song.element.parentElement;
                    for (let i = 0; i < 5 && container; i++) {{
                        const cRect = container.getBoundingClientRect();
                        if (cRect.height > 40 && cRect.height < 120) {{
                            container.click();
                            return true;
                        }}
                        container = container.parentElement;
                    }}
                }}

                return false;
            }}''')

            if not clicked:
                print(f"    ✗ Song nicht gefunden")
                return False

            print(f"    ✓ Song angeklickt")
            await asyncio.sleep(2)  # Warte auf Panel-Update

            # Jetzt sollte das rechte Panel den Song anzeigen
            # Klicke auf "Download" Button im rechten Panel
            try:
                # Suche nach Download-Button im rechten Bereich (x > 400)
                download_clicked = await self.page.evaluate('''() => {
                    const buttons = document.querySelectorAll('button, [role="button"]');

                    for (const btn of buttons) {
                        const rect = btn.getBoundingClientRect();
                        const ariaLabel = btn.getAttribute('aria-label') || '';

                        // Download-Button im rechten Panel (x > 600, y < 300)
                        if (rect.left > 600 && rect.top > 100 && rect.top < 350 &&
                            ariaLabel.toLowerCase().includes('download')) {
                            btn.click();
                            return true;
                        }

                        // Auch nach SVG mit Download-Icon suchen
                        const svg = btn.querySelector('svg');
                        if (svg && rect.left > 600 && rect.top > 100 && rect.top < 350) {
                            const svgText = svg.innerHTML.toLowerCase();
                            if (svgText.includes('download') || svgText.includes('arrow')) {
                                btn.click();
                                return true;
                            }
                        }
                    }

                    return false;
                }''')

                if download_clicked:
                    print(f"    ✓ Download-Button geklickt")
                    await asyncio.sleep(1.5)

                    # Prüfe ob Modal geöffnet wurde
                    try:
                        await self.page.wait_for_selector('[role="dialog"]', timeout=3000)
                        print(f"    ✓ Download-Modal geöffnet")
                        return True
                    except:
                        print(f"    ✗ Modal öffnete sich nicht")
                        return False
                else:
                    print(f"    ✗ Download-Button nicht gefunden")
                    return False

            except Exception as e:
                print(f"    ✗ Fehler: {e}")
                return False

        except Exception as e:
            print(f"    ✗ Fehler: {e}")
            return False
