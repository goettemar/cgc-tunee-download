#!/usr/bin/env python3
"""Test: Finde Download-Buttons in der Song-Liste"""

import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            "./cookies/chrome_profile",
            channel="chrome",
            headless=False
        )

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.tunee.ai/conversation/-PhXUDbLtFJTN4iL-")
        await asyncio.sleep(3)

        # Klicke auf "All Music"
        try:
            await page.locator('text="All Music"').first.click()
            await asyncio.sleep(2)
        except:
            pass

        print("\n=== TESTE DOWNLOAD-BUTTON CLICK ===\n")

        # Finde den ersten Song mit Duration 02:54
        result = await page.evaluate('''() => {
            // Finde alle Elemente mit "02:54"
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent?.trim();
                if (text === '02:54') {
                    const rect = el.getBoundingClientRect();

                    // Nur linke Seite
                    if (rect.left < 400 && rect.top > 50 && rect.top < 500) {
                        // Finde ALLE Buttons in der Nähe (gleiche Y-Position)
                        const allButtons = document.querySelectorAll('button, [role="button"], svg');
                        const nearbyElements = [];

                        for (const btn of allButtons) {
                            const btnRect = btn.getBoundingClientRect();

                            // Gleiche Zeile (±40px Y-Differenz)
                            if (Math.abs(btnRect.top - rect.top) < 40 &&
                                btnRect.left > rect.left - 200 &&
                                btnRect.left < rect.left + 400) {

                                nearbyElements.push({
                                    tag: btn.tagName,
                                    ariaLabel: btn.getAttribute('aria-label') || '',
                                    title: btn.getAttribute('title') || '',
                                    className: btn.className.substring(0, 50),
                                    x: Math.round(btnRect.left),
                                    y: Math.round(btnRect.top),
                                    width: Math.round(btnRect.width),
                                    height: Math.round(btnRect.height),
                                    innerHTML: btn.innerHTML.substring(0, 100)
                                });
                            }
                        }

                        return {
                            found: true,
                            durationX: Math.round(rect.left),
                            durationY: Math.round(rect.top),
                            nearbyElements: nearbyElements
                        };
                    }
                }
            }

            return { found: false };
        }''')

        if result['found']:
            print(f"Duration gefunden bei: x={result['durationX']}, y={result['durationY']}")
            print(f"\nElemente in der Nähe: {len(result['nearbyElements'])}\n")

            for idx, elem in enumerate(result['nearbyElements'], 1):
                print(f"Element #{idx}:")
                print(f"  Tag: {elem['tag']}")
                print(f"  Aria-Label: '{elem['ariaLabel']}'")
                print(f"  Title: '{elem['title']}'")
                print(f"  Position: x={elem['x']}, y={elem['y']}")
                print(f"  Size: {elem['width']}x{elem['height']}")
                print(f"  Class: {elem['className']}")
                print(f"  HTML: {elem['innerHTML'][:50]}...")
                print()
        else:
            print("Duration 02:54 nicht gefunden!")

        print("\nDrücke ENTER um zu beenden...")
        input()
        await context.close()

if __name__ == "__main__":
    asyncio.run(test())
