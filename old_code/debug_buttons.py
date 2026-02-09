#!/usr/bin/env python3
"""
Debug-Script um die Struktur der Download-Buttons zu analysieren
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_buttons():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=False,
            user_data_dir="./cookies/chrome_profile"
        )

        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.tunee.ai/conversation/-PhXUDbLtFJTN4iL-")
        await asyncio.sleep(3)

        # Klicke auf "All Music" falls sichtbar
        try:
            await page.locator('text="All Music"').first.click()
            await asyncio.sleep(2)
        except:
            pass

        print("\n=== ANALYSIERE SONG-LISTE ===\n")

        # Analysiere die ersten 3 Songs
        result = await page.evaluate('''() => {
            const timeRegex = /^\\d{2}:\\d{2}$/;
            const results = [];
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent?.trim();
                // Finde Element mit Duration
                if (text && timeRegex.test(text) && el.childNodes.length === 1) {
                    const rect = el.getBoundingClientRect();
                    // Nur linke Seite
                    if (rect.left > 400 || rect.top < 50 || rect.top > 500) continue;

                    const duration = text;
                    let container = el.parentElement;

                    // Suche den Song-Container
                    for (let i = 0; i < 5 && container; i++) {
                        const cRect = container.getBoundingClientRect();
                        if (cRect.height > 40 && cRect.height < 150) {
                            // Finde Song-Name
                            const textNodes = container.querySelectorAll('span, div, p, a');
                            let songName = null;

                            for (const node of textNodes) {
                                const nodeText = node.textContent?.trim();
                                if (nodeText && nodeText.length > 2 && nodeText.length < 80 &&
                                    !timeRegex.test(nodeText) &&
                                    !['All Music', 'Favorites'].includes(nodeText) &&
                                    !nodeText.includes('\\n')) {
                                    songName = nodeText;
                                    break;
                                }
                            }

                            if (songName) {
                                // Analysiere ALLE Buttons in diesem Container
                                const buttons = container.querySelectorAll('button, [role="button"]');
                                const buttonInfo = [];

                                for (let j = 0; j < buttons.length; j++) {
                                    const btn = buttons[j];
                                    const btnRect = btn.getBoundingClientRect();
                                    const ariaLabel = btn.getAttribute('aria-label') || '';
                                    const title = btn.getAttribute('title') || '';
                                    const svgCount = btn.querySelectorAll('svg').length;
                                    const className = btn.className || '';

                                    buttonInfo.push({
                                        index: j,
                                        ariaLabel: ariaLabel,
                                        title: title,
                                        svgCount: svgCount,
                                        className: className.substring(0, 50),
                                        x: Math.round(btnRect.left),
                                        y: Math.round(btnRect.top),
                                        width: Math.round(btnRect.width),
                                        height: Math.round(btnRect.height)
                                    });
                                }

                                results.push({
                                    name: songName,
                                    duration: duration,
                                    buttons: buttonInfo,
                                    containerClass: container.className.substring(0, 100)
                                });

                                if (results.length >= 3) break;
                            }
                        }
                        container = container.parentElement;
                    }
                }
            }
            return results;
        }''')

        for idx, song in enumerate(result, 1):
            print(f"\n{'='*60}")
            print(f"Song #{idx}: {song['name']} ({song['duration']})")
            print(f"Container Class: {song['containerClass']}")
            print(f"\nButtons gefunden: {len(song['buttons'])}")

            for btn in song['buttons']:
                print(f"\n  Button #{btn['index']}:")
                print(f"    aria-label: '{btn['ariaLabel']}'")
                print(f"    title: '{btn['title']}'")
                print(f"    SVG Count: {btn['svgCount']}")
                print(f"    Position: x={btn['x']}, y={btn['y']}")
                print(f"    Size: {btn['width']}x{btn['height']}")
                print(f"    Class: {btn['className']}")

        print(f"\n{'='*60}\n")
        print("Drücke ENTER um zu beenden...")
        input()

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_buttons())
