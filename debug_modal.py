#!/usr/bin/env python3
"""
Debug: Öffne Download-Modal und mache Screenshot + analysiere Buttons
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def debug_modal():
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

        print("\n=== ÖFFNE DOWNLOAD-MODAL VOM ERSTEN SONG ===\n")

        # Finde ersten Song mit 02:54
        result = await page.evaluate('''() => {
            const allElements = document.querySelectorAll('*');

            for (const el of allElements) {
                const text = el.textContent?.trim();
                if (text === '02:54') {
                    const rect = el.getBoundingClientRect();

                    if (rect.left < 400 && rect.top > 50 && rect.top < 500) {
                        // Finde Container
                        let parent = el.parentElement;
                        for (let i = 0; i < 5 && parent; i++) {
                            const pRect = parent.getBoundingClientRect();
                            if (pRect.height >= 40 && pRect.height <= 120) {
                                const uniqueId = 'cgc-hover-' + Date.now();
                                parent.setAttribute('data-cgc-hover-target', uniqueId);
                                return {
                                    found: true,
                                    id: uniqueId,
                                    x: pRect.left + pRect.width / 2,
                                    y: pRect.top + pRect.height / 2
                                };
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
            }
            return { found: false };
        }''')

        if not result['found']:
            print("Song nicht gefunden!")
            await context.close()
            return

        # Hovere über Song
        print("1. Hovere über ersten Song...")
        hover_target = page.locator(f'[data-cgc-hover-target="{result["id"]}"]').first
        await hover_target.hover()
        await asyncio.sleep(1)
        print("   ✓ Hover aktiv (Song sollte grau sein)")

        # Finde und klicke Download-Button
        print("\n2. Suche Download-Button...")
        btn_result = await page.evaluate('''() => {
            const allButtons = document.querySelectorAll('button, [role="button"]');
            const hoverElement = document.querySelector('[data-cgc-hover-target]');
            if (!hoverElement) return { found: false };

            const hoverRect = hoverElement.getBoundingClientRect();
            const buttons = [];

            for (const btn of allButtons) {
                const btnRect = btn.getBoundingClientRect();
                const btnStyle = window.getComputedStyle(btn);

                if (Math.abs(btnRect.top - hoverRect.top) < 30 &&
                    btnRect.left > hoverRect.left &&
                    btnRect.left < hoverRect.left + 300 &&
                    btnStyle.display !== 'none' &&
                    parseFloat(btnStyle.opacity) > 0.1) {

                    buttons.push({
                        ariaLabel: btn.getAttribute('aria-label') || '',
                        x: Math.round(btnRect.left),
                        visible: true
                    });

                    // Markiere zweiten Button (Download)
                    if (buttons.length === 2) {
                        const uniqueId = 'cgc-download-' + Date.now();
                        btn.setAttribute('data-cgc-click-target', uniqueId);
                        return { found: true, id: uniqueId, totalButtons: buttons.length };
                    }
                }
            }

            return { found: false, buttons: buttons };
        }''')

        if not btn_result['found']:
            print(f"   ✗ Download-Button nicht gefunden!")
            print(f"   Buttons: {btn_result.get('buttons', [])}")
            await context.close()
            return

        print(f"   ✓ Download-Button gefunden ({btn_result['totalButtons']} Buttons in Zeile)")

        # Klicke Download-Button
        print("\n3. Klicke Download-Button...")
        download_btn = page.locator(f'[data-cgc-click-target="{btn_result["id"]}"]').first
        await download_btn.click()
        await asyncio.sleep(2)
        print("   ✓ Button geklickt")

        # Modal sollte jetzt offen sein - mache Screenshot
        print("\n4. Analysiere Download-Modal...")
        screenshot_path = Path("./debug_modal_screenshot.png")
        await page.screenshot(path=str(screenshot_path))
        print(f"   ✓ Screenshot gespeichert: {screenshot_path}")

        # Analysiere Modal
        modal_info = await page.evaluate('''() => {
            // Finde Modal
            const modals = document.querySelectorAll('[role="dialog"], [role="alertdialog"]');

            for (const modal of modals) {
                const modalStyle = window.getComputedStyle(modal);
                const zIndex = parseInt(modalStyle.zIndex) || 0;

                if (zIndex > 100) {
                    // Modal gefunden - sammle alle Buttons
                    const buttons = modal.querySelectorAll('button');
                    const buttonInfo = [];

                    for (let i = 0; i < buttons.length; i++) {
                        const btn = buttons[i];
                        const btnRect = btn.getBoundingClientRect();
                        const btnStyle = window.getComputedStyle(btn);

                        buttonInfo.push({
                            index: i,
                            text: btn.textContent?.trim() || '',
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            className: btn.className.substring(0, 60),
                            disabled: btn.disabled,
                            visible: btnStyle.display !== 'none' && parseFloat(btnStyle.opacity) > 0.1,
                            x: Math.round(btnRect.left),
                            y: Math.round(btnRect.top),
                            width: Math.round(btnRect.width),
                            height: Math.round(btnRect.height)
                        });
                    }

                    return {
                        found: true,
                        modalText: modal.textContent?.substring(0, 300),
                        buttons: buttonInfo
                    };
                }
            }

            return { found: false };
        }''')

        if modal_info['found']:
            print(f"\n   ✓ Download-Modal gefunden!")
            print(f"\n   Modal-Text: {modal_info['modalText'][:150]}...\n")
            print(f"   Buttons im Modal: {len(modal_info['buttons'])}\n")

            for btn in modal_info['buttons']:
                print(f"   Button #{btn['index']}:")
                print(f"     Text: '{btn['text']}'")
                print(f"     Aria-Label: '{btn['ariaLabel']}'")
                print(f"     Disabled: {btn['disabled']}")
                print(f"     Visible: {btn['visible']}")
                print(f"     Position: x={btn['x']}, y={btn['y']}")
                print(f"     Size: {btn['width']}x{btn['height']}")
                print(f"     Class: {btn['className']}")
                print()
        else:
            print("   ✗ Kein Modal gefunden!")

        print("\nDrücke ENTER um zu beenden...")
        input()
        await context.close()

if __name__ == "__main__":
    asyncio.run(debug_modal())
