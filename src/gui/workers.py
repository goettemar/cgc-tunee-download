"""Worker threads for background tasks."""

from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from ..events import SignalEvents
from ..orchestrator import run_task
from ..screenshot import set_monitor
from .state import get_state


class BaseWorker(QThread):
    progress = Signal(int, int)        # current, total
    status = Signal(str)
    log = Signal(str)
    error = Signal(str)
    finished_work = Signal(bool, str)  # success, message


class DownloadWorker(BaseWorker):
    song_started = Signal(int, int, int)   # num, x, y
    song_completed = Signal(int, str)      # num, folder_name
    song_duplicate = Signal(int, str, str) # num, name, duration
    song_failed = Signal(int)              # num
    icons_found = Signal(int, int)         # count, scroll_round

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events: SignalEvents | None = None

    def request_stop(self) -> None:
        if self._events:
            self._events.request_stop()

    def run(self) -> None:
        state = get_state()
        cfg = state.config

        self._events = SignalEvents(self)

        try:
            set_monitor(cfg.monitor_index)
            success = run_task(
                max_songs=cfg.max_songs,
                max_scrolls=cfg.max_scrolls,
                events=self._events,
            )
            if self._events.should_stop():
                self.finished_work.emit(False, "Vom Benutzer gestoppt")
            elif success:
                self.finished_work.emit(True, "Download abgeschlossen")
            else:
                self.finished_work.emit(False, "Keine Songs gefunden")
        except Exception as exc:
            self.error.emit(f"Fehler: {exc}")
            self.log.emit(traceback.format_exc())
            self.finished_work.emit(False, str(exc))
        finally:
            self._events = None
