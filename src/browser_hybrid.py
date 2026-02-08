"""
Hybrid Browser: Playwright (Navigation) + PyAutoGUI (Visual Clicks)

Löst das Hover-Button-Problem durch bildbasierte Automation.
"""

import asyncio
import time
from pathlib import Path
from dataclasses import dataclass
from playwright.async_api import Page

# PyAutoGUI import mit Fehlerbehandlung (tkinter optional)
try:
    import pyautogui
    # Sicherheitseinstellungen für PyAutoGUI
    pyautogui.FAILSAFE = True  # Maus in obere linke Ecke = Notfall-Stop
    pyautogui.PAUSE = 0.5  # Pause zwischen Actions
except Exception as e:
    print(f"⚠️ PyAutoGUI Import-Warnung: {e}")
    print("   Kernfunktionen sollten trotzdem funktionieren...")
    import sys
    # Mock pyautogui wenn Import fehlschlägt
    class MockPyAutoGUI:
        FAILSAFE = True
        PAUSE = 0.5
        def size(self): return (1920, 1080)
        def locateOnScreen(self, *args, **kwargs): return None
        def click(self, *args, **kwargs): pass
        def moveTo(self, *args, **kwargs): pass
        def center(self, *args, **kwargs): return type('obj', (object,), {'x': 0, 'y': 0})()
    pyautogui = MockPyAutoGUI()


@dataclass
class TemplateConfig:
    """Konfiguration für Template-Matching."""

    # Template-Pfade
    templates_dir: Path = Path(__file__).parent.parent / "templates"

    # Confidence-Schwellwerte (0.0 - 1.0)
    download_button_confidence: float = 0.8
    modal_button_confidence: float = 0.85

    # Timeouts
    template_search_timeout: int = 5  # Sekunden
    hover_wait: float = 1.5  # Sekunden nach Hover
    click_wait: float = 2.0  # Sekunden nach Klick

    def get_template_path(self, name: str) -> Path:
        """Gibt Pfad zu Template-Datei zurück."""
        return self.templates_dir / f"{name}.png"


class HybridBrowser:
    """
    Hybrid-Browser mit Playwright (Navigation) + PyAutoGUI (Klicks).

    Workflow:
    1. Playwright findet Element-Positionen im Viewport
    2. PyAutoGUI konvertiert zu Screen-Koordinaten
    3. PyAutoGUI führt Hover/Klicks aus (bildbasiert)
    """

    def __init__(self, page: Page, config: TemplateConfig | None = None):
        self.page = page
        self.config = config or TemplateConfig()

        # Screen-Größe ermitteln
        self.screen_width, self.screen_height = pyautogui.size()
        print(f"Screen: {self.screen_width}x{self.screen_height}")

    async def get_browser_window_position(self) -> dict:
        """
        Ermittelt Position des Browser-Fensters auf dem Screen.

        Returns:
            {"x": int, "y": int, "width": int, "height": int}
        """
        # Playwright-Viewport-Größe
        viewport = self.page.viewport_size

        # Für Chrome: Browser-Fenster ist normalerweise maximiert
        # oder wir können es über pyautogui.getWindowsWithTitle() finden
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle("Chromium")
            if not windows:
                windows = gw.getWindowsWithTitle("Chrome")

            if windows:
                win = windows[0]
                return {
                    "x": win.left,
                    "y": win.top,
                    "width": win.width,
                    "height": win.height
                }
        except Exception as e:
            print(f"Warnung: Fensterposition nicht ermittelbar: {e}")

        # Fallback: Annahme maximiertes Fenster
        return {
            "x": 0,
            "y": 0,
            "width": self.screen_width,
            "height": self.screen_height
        }

    async def viewport_to_screen(self, viewport_x: int, viewport_y: int) -> tuple[int, int]:
        """
        Konvertiert Viewport-Koordinaten zu Screen-Koordinaten.

        Args:
            viewport_x: X-Position im Playwright-Viewport
            viewport_y: Y-Position im Playwright-Viewport

        Returns:
            (screen_x, screen_y) Tuple
        """
        window_pos = await self.get_browser_window_position()

        # Browser-Chrome-Höhe (Tabs, Adressleiste) schätzen
        chrome_height = 100  # Typisch ~80-120px

        screen_x = window_pos["x"] + viewport_x
        screen_y = window_pos["y"] + chrome_height + viewport_y

        return screen_x, screen_y

    def find_template(self, template_name: str, confidence: float = 0.8) -> tuple[int, int] | None:
        """
        Findet Template auf dem Screen (bildbasiert).

        Args:
            template_name: Name des Templates (ohne .png)
            confidence: Matching-Confidence (0.0 - 1.0)

        Returns:
            (x, y) Center-Koordinaten oder None
        """
        template_path = self.config.get_template_path(template_name)

        if not template_path.exists():
            print(f"⚠️ Template nicht gefunden: {template_path}")
            return None

        try:
            location = pyautogui.locateOnScreen(
                str(template_path),
                confidence=confidence
            )

            if location:
                # Center des gefundenen Bereichs
                center = pyautogui.center(location)
                print(f"✓ Template '{template_name}' gefunden bei {center}")
                return center.x, center.y
            else:
                print(f"✗ Template '{template_name}' nicht gefunden")
                return None

        except Exception as e:
            print(f"Fehler beim Template-Matching: {e}")
            return None

    def wait_for_template(
        self,
        template_name: str,
        confidence: float = 0.8,
        timeout: int = 5
    ) -> tuple[int, int] | None:
        """
        Wartet bis Template erscheint (mit Timeout).

        Args:
            template_name: Name des Templates
            confidence: Matching-Confidence
            timeout: Timeout in Sekunden

        Returns:
            (x, y) Koordinaten oder None
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            pos = self.find_template(template_name, confidence)
            if pos:
                return pos
            time.sleep(0.5)

        print(f"⏱️ Timeout: Template '{template_name}' nicht gefunden")
        return None

    async def hover_and_click_template(
        self,
        template_name: str,
        confidence: float = 0.8,
        hover_wait: float | None = None
    ) -> bool:
        """
        Findet Template, hovert darüber und klickt.

        Args:
            template_name: Name des Templates
            confidence: Matching-Confidence
            hover_wait: Wartezeit nach Hover (nutzt config default wenn None)

        Returns:
            True wenn erfolgreich
        """
        hover_wait = hover_wait or self.config.hover_wait

        # Template finden
        pos = self.wait_for_template(template_name, confidence, self.config.template_search_timeout)
        if not pos:
            return False

        x, y = pos

        # Hover (sanfte Bewegung)
        print(f"Hovering zu {x}, {y}...")
        pyautogui.moveTo(x, y, duration=0.3)
        time.sleep(hover_wait)

        # Klick
        print(f"Klicke auf {x}, {y}...")
        pyautogui.click(x, y)
        time.sleep(self.config.click_wait)

        return True

    async def click_element_by_position(self, viewport_x: int, viewport_y: int) -> bool:
        """
        Klickt auf Element basierend auf Viewport-Position (Playwright).

        Args:
            viewport_x: X-Position im Playwright-Viewport
            viewport_y: Y-Position im Playwright-Viewport

        Returns:
            True wenn erfolgreich
        """
        screen_x, screen_y = await self.viewport_to_screen(viewport_x, viewport_y)

        print(f"Klicke auf Screen-Position: {screen_x}, {screen_y}")
        pyautogui.click(screen_x, screen_y)
        time.sleep(self.config.click_wait)

        return True

    async def hover_element_by_position(self, viewport_x: int, viewport_y: int) -> bool:
        """
        Hovert über Element basierend auf Viewport-Position.

        Args:
            viewport_x: X-Position im Playwright-Viewport
            viewport_y: Y-Position im Playwright-Viewport

        Returns:
            True wenn erfolgreich
        """
        screen_x, screen_y = await self.viewport_to_screen(viewport_x, viewport_y)

        print(f"Hovering zu Screen-Position: {screen_x}, {screen_y}")
        pyautogui.moveTo(screen_x, screen_y, duration=0.3)
        time.sleep(self.config.hover_wait)

        return True

    # === Song-Download Workflow ===

    async def download_song_hybrid(self, song_name: str, duration: str) -> dict:
        """
        Download-Workflow mit Hybrid-Approach.

        Strategie:
        1. Playwright findet Song-Element
        2. PyAutoGUI hovert über Song (löst CSS opacity aus)
        3. PyAutoGUI findet Download-Button (bildbasiert)
        4. PyAutoGUI klickt Modal-Buttons (bildbasiert)

        Args:
            song_name: Name des Songs
            duration: Duration (z.B. "03:45")

        Returns:
            {"success": bool, "files": list[str], "error": str}
        """
        result = {
            "success": False,
            "files": [],
            "error": None
        }

        try:
            # Step 1: Playwright findet Song-Position
            print(f"\n📀 Song: {song_name} ({duration})")
            print("1️⃣ Suche Song-Element mit Playwright...")

            # Finde Song über Duration-Text
            duration_elements = await self.page.locator(f'text="{duration}"').all()
            if not duration_elements:
                result["error"] = f"Song mit Duration {duration} nicht gefunden"
                return result

            # Nehme erstes Element (sollte unser Song sein)
            song_element = duration_elements[0]

            # Hole Bounding Box (Position im Viewport)
            bbox = await song_element.bounding_box()
            if not bbox:
                result["error"] = "Bounding Box nicht ermittelbar"
                return result

            # Center des Song-Elements
            viewport_x = bbox["x"] + bbox["width"] / 2
            viewport_y = bbox["y"] + bbox["height"] / 2

            print(f"   Song-Position (Viewport): {viewport_x:.0f}, {viewport_y:.0f}")

            # Step 2: PyAutoGUI hovert über Song
            print("2️⃣ Hovering über Song (PyAutoGUI)...")
            await self.hover_element_by_position(int(viewport_x), int(viewport_y))

            # Step 3: PyAutoGUI findet Download-Button (bildbasiert)
            print("3️⃣ Suche Download-Button (bildbasiert)...")
            download_clicked = await self.hover_and_click_template(
                "download_button",
                confidence=self.config.download_button_confidence
            )

            if not download_clicked:
                result["error"] = "Download-Button nicht gefunden"
                return result

            # Step 4: Modal sollte offen sein - klicke Download-Buttons
            # WICHTIG: VIDEO kommt zuletzt, weil es das Modal schließt!
            print("4️⃣ Klicke Modal-Buttons...")

            modal_buttons = [
                ("modal_mp3", "MP3"),
                ("modal_raw", "RAW/FLAC"),
                ("modal_lrc", "LRC"),
                # VIDEO wird separat behandelt (siehe unten)
            ]

            for template, label in modal_buttons:
                print(f"   → {label}...")
                clicked = await self.hover_and_click_template(
                    template,
                    confidence=self.config.modal_button_confidence
                )
                if clicked:
                    result["files"].append(label)
                else:
                    print(f"   ⚠️ {label} Button nicht gefunden (skip)")

            # VIDEO zum Schluss (öffnet separates Modal)
            print("   → VIDEO...")
            video_clicked = await self.hover_and_click_template(
                "modal_video",
                confidence=self.config.modal_button_confidence
            )

            if video_clicked:
                # Warte auf Lyric Video Modal
                await asyncio.sleep(2)

                # Klicke Download-Button im Video-Modal
                video_download = await self.hover_and_click_template(
                    "lyric_video_download",
                    confidence=self.config.modal_button_confidence
                )
                if video_download:
                    result["files"].append("VIDEO")

            result["success"] = len(result["files"]) > 0
            print(f"✅ Downloads: {', '.join(result['files'])}")

        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Fehler: {e}")

        return result


def create_hybrid_browser(page: Page) -> HybridBrowser:
    """Factory-Funktion für Hybrid-Browser."""
    return HybridBrowser(page)
