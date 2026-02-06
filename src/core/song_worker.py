"""Worker für den Song-Download in einem separaten Thread."""

import asyncio
from pathlib import Path
from PySide6.QtCore import QThread

from src.core.signals import DownloadSignals
from src.auth import has_saved_session, launch_with_real_chrome, save_cookies
from src.browser import TuneeBrowser


class SongDownloadWorker(QThread):
    """Worker-Thread für den Song-Download."""

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.signals = DownloadSignals()
        self._stop_requested = False
        self._user_confirmed = False

    def request_stop(self):
        """Fordert den Worker auf, zu stoppen."""
        self._stop_requested = True

    def confirm_ready(self):
        """Wird von GUI aufgerufen wenn Benutzer bereit ist."""
        self._user_confirmed = True

    def run(self):
        """Startet den Download-Prozess."""
        asyncio.run(self._async_run())

    async def _async_run(self):
        """Async Download-Logik."""
        context = None
        playwright = None

        try:
            self.signals.started.emit()
            self.signals.log.emit(f"Starte Download von: {self.url}")

            # Prüfe ob Session existiert
            first_time = not has_saved_session()

            if first_time:
                self.signals.login_required.emit()
                self.signals.log_warning.emit("Erster Start - Login erforderlich!")
                self.signals.log.emit("Bitte im Browser mit Google einloggen...")

            # Starte Browser
            self.signals.log.emit("Starte Chrome...")
            context, _, playwright = await launch_with_real_chrome(self.url, first_time=first_time)
            page = context.pages[0] if context.pages else await context.new_page()

            if not first_time:
                await page.goto(self.url)

            self.signals.browser_ready.emit()
            self.signals.log.emit("Browser gestartet. Warte auf Seitenladung...")

            await asyncio.sleep(3)

            # Warte auf Benutzerbestätigung
            self.signals.log_warning.emit("")
            self.signals.log_warning.emit("=" * 50)
            self.signals.log_warning.emit("VORBEREITUNG")
            self.signals.log_warning.emit("=" * 50)
            self.signals.log.emit("1. Stelle sicher, dass die Song-Liste links sichtbar ist")
            self.signals.log.emit("2. Klicke ggf. auf 'All Music' um die Liste zu öffnen")
            self.signals.log.emit("3. Scrolle NICHT - bleibe oben in der Liste")
            self.signals.log_warning.emit("")
            self.signals.log_warning.emit("Klicke 'Weiter' wenn bereit...")

            self.signals.waiting_for_user.emit()

            # Warte auf Bestätigung
            while not self._user_confirmed and not self._stop_requested:
                await asyncio.sleep(0.1)

            if self._stop_requested:
                self.signals.log_warning.emit("Abgebrochen.")
                return

            self.signals.log_success.emit("Weiter geht's!")
            self.signals.log.emit("")

            # Browser-Automation initialisieren
            tunee_browser = TuneeBrowser(page)

            # Warte auf Musik-Liste
            self.signals.log.emit("Suche Musik-Liste...")
            if not await tunee_browser.wait_for_music_list():
                self.signals.log_error.emit("Musik-Liste nicht gefunden!")
                self.signals.log.emit("Tipp: Stelle sicher dass 'All Music' sichtbar ist")
                self.signals.error.emit("Musik-Liste nicht gefunden")
                return

            # Songs finden
            self.signals.log.emit("Suche Songs...")
            songs = await tunee_browser.get_song_list()

            if not songs:
                self.signals.log_error.emit("Keine Songs gefunden!")
                self.signals.error.emit("Keine Songs gefunden")
                return

            self.signals.log_success.emit(f"{len(songs)} Songs gefunden")
            for idx, song in enumerate(songs, 1):
                self.signals.log.emit(f"  {idx}. {song['name']} ({song['duration']})")

            # Songs verarbeiten
            self.signals.log.emit("")
            self.signals.log.emit("=" * 50)
            self.signals.log.emit("STARTE DOWNLOADS")
            self.signals.log.emit("=" * 50)

            success_count = 0
            failed_count = 0

            for idx, song in enumerate(songs, 1):
                if self._stop_requested:
                    self.signals.log_warning.emit("Download abgebrochen!")
                    break

                song_name = song['name']
                song_duration = song['duration']

                self.signals.progress.emit(idx, len(songs))
                self.signals.song_started.emit(song_name)
                self.signals.log.emit(f"\n[{idx}/{len(songs)}] {song_name}")

                result = await tunee_browser.process_song(song_name, song_duration)

                if result:
                    download_count = sum([
                        1 for x in [result.mp3_url, result.raw_url, result.video_url, result.lrc_url] if x
                    ])
                    self.signals.song_complete.emit(song_name, download_count)

                    if download_count > 0:
                        self.signals.log_success.emit(f"  -> {download_count}/4 Downloads erfolgreich")
                        success_count += 1
                    else:
                        self.signals.log_warning.emit(f"  -> Keine Downloads")
                        failed_count += 1
                else:
                    self.signals.song_failed.emit(song_name, "Verarbeitung fehlgeschlagen")
                    self.signals.log_error.emit(f"  -> FEHLGESCHLAGEN")
                    failed_count += 1

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
            # Browser schließen
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
