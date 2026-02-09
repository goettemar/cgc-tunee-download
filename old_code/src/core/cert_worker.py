"""Worker für den Certificate-Download in einem separaten Thread."""

import asyncio
from pathlib import Path
from PySide6.QtCore import QThread

from src.core.signals import DownloadSignals
from src.auth import has_saved_session, launch_with_real_chrome, save_cookies, DOWNLOADS_DIR
from src.browser import TuneeBrowser


class CertificateWorker(QThread):
    """Worker-Thread für Certificate-Downloads."""

    def __init__(self, url: str, folders_without_cert: list[Path], parent=None):
        super().__init__(parent)
        self.url = url
        self.folders = folders_without_cert
        self.signals = DownloadSignals()
        self._stop_requested = False

    def request_stop(self):
        """Fordert den Worker auf, zu stoppen."""
        self._stop_requested = True

    def run(self):
        """Startet den Certificate-Download."""
        asyncio.run(self._async_run())

    async def _async_run(self):
        """Async Certificate-Logik."""
        context = None
        playwright = None

        try:
            self.signals.started.emit()
            self.signals.log.emit(f"Starte Certificate-Download")
            self.signals.log.emit(f"{len(self.folders)} Ordner ohne Certificate")

            # Prüfe ob Session existiert
            if not has_saved_session():
                self.signals.log_error.emit("Keine Session gefunden!")
                self.signals.log.emit("Bitte erst Songs herunterladen (dabei wird Login gespeichert)")
                self.signals.error.emit("Keine Session vorhanden")
                return

            # Starte Browser
            self.signals.log.emit("Starte Chrome...")
            context, _, playwright = await launch_with_real_chrome(self.url, first_time=False)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(self.url)

            self.signals.browser_ready.emit()
            self.signals.log.emit("Browser gestartet. Warte auf Seitenladung...")

            await asyncio.sleep(3)

            # Browser-Automation initialisieren
            tunee_browser = TuneeBrowser(page)

            # Warte auf Musik-Liste
            if not await tunee_browser.wait_for_music_list():
                self.signals.log_error.emit("Musik-Liste nicht gefunden!")
                self.signals.error.emit("Musik-Liste nicht gefunden")
                return

            # Songs finden
            songs = await tunee_browser.get_song_list()
            if not songs:
                self.signals.log_error.emit("Keine Songs gefunden!")
                self.signals.error.emit("Keine Songs gefunden")
                return

            # Song-Namen zu Dict für schnellen Lookup
            song_lookup = {s['name']: s for s in songs}

            self.signals.log.emit("")
            self.signals.log.emit("=" * 50)
            self.signals.log.emit("LADE CERTIFICATES")
            self.signals.log.emit("=" * 50)

            success_count = 0
            failed_count = 0

            for idx, folder in enumerate(self.folders, 1):
                if self._stop_requested:
                    self.signals.log_warning.emit("Download abgebrochen!")
                    break

                # Ordnername = SongName_Duration (z.B. "Quiet_Resolve_03-45")
                folder_name = folder.name

                # Extrahiere Song-Name und Duration aus Ordnername
                # Format: Name_MM-SS (Duration ist immer die letzten 5 Zeichen + Unterstrich)
                if len(folder_name) > 6 and folder_name[-6] == '_':
                    base_name = folder_name[:-6]  # Alles vor _MM-SS
                    duration_from_folder = folder_name[-5:].replace("-", ":")  # 03-45 -> 03:45
                else:
                    # Fallback für alte Ordner ohne Duration
                    base_name = folder_name
                    duration_from_folder = None

                self.signals.progress.emit(idx, len(self.folders))
                self.signals.song_started.emit(folder_name)
                self.signals.log.emit(f"\n[{idx}/{len(self.folders)}] {folder_name}")

                # Finde passenden Song über Name + Duration
                song = None

                # Erst exakte Suche mit Duration
                if duration_from_folder:
                    for name, s in song_lookup.items():
                        if name == base_name.replace("_", " ") and s['duration'] == duration_from_folder:
                            song = s
                            break

                # Dann Suche nur nach Name (für Ordner ohne Duration)
                if not song:
                    song = song_lookup.get(base_name.replace("_", " "))

                if not song:
                    # Versuche ähnliche Namen
                    for name, s in song_lookup.items():
                        if base_name.replace("_", " ").lower() in name.lower():
                            song = s
                            break

                if not song:
                    self.signals.log_warning.emit(f"  Song nicht auf Tunee gefunden")
                    failed_count += 1
                    continue

                # Song anklicken
                self.signals.log.emit(f"  Klicke Song: {song['name']}")
                if not await tunee_browser.click_song_in_list(song['name'], song['duration']):
                    self.signals.log_error.emit(f"  Konnte Song nicht anklicken")
                    failed_count += 1
                    continue

                await asyncio.sleep(1.5)

                # 3-Punkte-Menü öffnen
                self.signals.log.emit(f"  Öffne Menü...")
                if not await tunee_browser.open_three_dot_menu():
                    self.signals.log_error.emit(f"  Menü nicht gefunden")
                    failed_count += 1
                    continue

                # Copyright Certificate klicken
                self.signals.log.emit(f"  Klicke Copyright Certificate...")
                if not await tunee_browser.click_menu_item("Copyright Certificate"):
                    self.signals.log_error.emit(f"  Menüpunkt nicht gefunden")
                    await tunee_browser.close_modal()
                    failed_count += 1
                    continue

                await asyncio.sleep(1)

                # Certificate downloaden
                self.signals.log.emit(f"  Lade Certificate...")

                # Download erwarten
                try:
                    async with page.expect_download(timeout=30000) as download_info:
                        # Download-Button im Certificate-Modal klicken
                        await tunee_browser.download_copyright_certificate()

                    download = await download_info.value
                    target_path = folder / f"{folder_name}_certificate.pdf"
                    await download.save_as(str(target_path))

                    self.signals.log_success.emit(f"  -> Certificate gespeichert: {target_path.name}")
                    self.signals.song_complete.emit(folder_name, 1)
                    success_count += 1

                except Exception as e:
                    self.signals.log_error.emit(f"  -> Download fehlgeschlagen: {str(e)[:30]}")
                    failed_count += 1

                # Modal schließen
                await tunee_browser.close_modal()
                await asyncio.sleep(0.5)

            # Cookies speichern
            await save_cookies(context)

            # Zusammenfassung
            self.signals.log.emit("")
            self.signals.log.emit("=" * 50)
            self.signals.log_success.emit(f"FERTIG: {success_count} erfolgreich, {failed_count} fehlgeschlagen")
            self.signals.finished.emit(success_count, failed_count)

        except Exception as e:
            self.signals.log_error.emit(f"Fehler: {str(e)}")
            self.signals.error.emit(str(e))

        finally:
            if context:
                try:
                    await context.close()
                except:
                    pass
            if playwright:
                try:
                    await playwright.stop()
                except:
                    pass


def find_folders_without_certificate(base_dir: Path = DOWNLOADS_DIR) -> list[Path]:
    """
    Findet alle Song-Ordner ohne Certificate PDF.
    """
    if not base_dir.exists():
        return []

    folders_without_cert = []

    for folder in base_dir.iterdir():
        if not folder.is_dir():
            continue

        # Prüfe ob .pdf existiert
        has_pdf = any(f.suffix.lower() == '.pdf' for f in folder.iterdir() if f.is_file())

        if not has_pdf:
            # Prüfe ob es überhaupt Downloads gibt (mp3, flac, etc.)
            has_downloads = any(
                f.suffix.lower() in ['.mp3', '.flac', '.mp4', '.lrc']
                for f in folder.iterdir() if f.is_file()
            )
            if has_downloads:
                folders_without_cert.append(folder)

    return sorted(folders_without_cert)
