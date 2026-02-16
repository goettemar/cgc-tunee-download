"""Event abstraction for orchestrator ↔ UI/CLI communication."""

from __future__ import annotations

from abc import ABC, abstractmethod

# ANSI colors for CLI output
C_STEP = "\033[1;36m"
C_DONE = "\033[1;32m"
C_ERR = "\033[0;31m"
C_WARN = "\033[0;35m"
C_TMPL = "\033[0;36m"
C_RESET = "\033[0m"


class OrchestratorEvents(ABC):
    """Interface for orchestrator → UI/CLI callbacks."""

    @abstractmethod
    def on_log(self, msg: str) -> None: ...

    @abstractmethod
    def on_song_start(self, num: int, x: int, y: int) -> None: ...

    @abstractmethod
    def on_song_complete(self, num: int, folder: str) -> None: ...

    @abstractmethod
    def on_song_duplicate(self, num: int, name: str, duration: str) -> None: ...

    @abstractmethod
    def on_song_failed(self, num: int) -> None: ...

    @abstractmethod
    def on_progress(self, current: int, total: int) -> None: ...

    @abstractmethod
    def on_scroll(self, round_num: int) -> None: ...

    @abstractmethod
    def on_icons_found(self, count: int, round_num: int) -> None: ...

    def should_stop(self) -> bool:
        return False


class PrintEvents(OrchestratorEvents):
    """CLI: colored stdout output (preserves original behavior)."""

    def on_log(self, msg: str) -> None:
        print(msg)

    def on_song_start(self, num: int, x: int, y: int) -> None:
        print(f"\n{C_STEP}{'─' * 40}")
        print(f"  Song #{num} — icon at ({x},{y})")
        print(f"{'─' * 40}{C_RESET}")

    def on_song_complete(self, num: int, folder: str) -> None:
        print(f"  {C_DONE}Song #{num} complete! → {folder}{C_RESET}")

    def on_song_duplicate(self, num: int, name: str, duration: str) -> None:
        print(f"  {C_WARN}Song #{num} DUPLICATE: {name} ({duration}){C_RESET}")

    def on_song_failed(self, num: int) -> None:
        print(f"  {C_ERR}Song #{num} failed{C_RESET}")

    def on_progress(self, current: int, total: int) -> None:
        print(f"  Progress: {current}/{total}")

    def on_scroll(self, round_num: int) -> None:
        print(
            f"\n{C_STEP}Scrolling down for more songs... (round {round_num}){C_RESET}"
        )

    def on_icons_found(self, count: int, round_num: int) -> None:
        print(
            f"\n{C_STEP}Found {count} download icons "
            f"(scroll round {round_num}){C_RESET}"
        )


class SignalEvents(OrchestratorEvents):
    """GUI: forwards events to a DownloadWorker's Qt Signals."""

    def __init__(self, worker) -> None:
        self._worker = worker
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def on_log(self, msg: str) -> None:
        self._worker.log.emit(msg)

    def on_song_start(self, num: int, x: int, y: int) -> None:
        self._worker.song_started.emit(num, x, y)

    def on_song_complete(self, num: int, folder: str) -> None:
        self._worker.song_completed.emit(num, folder)

    def on_song_duplicate(self, num: int, name: str, duration: str) -> None:
        self._worker.song_duplicate.emit(num, name, duration)

    def on_song_failed(self, num: int) -> None:
        self._worker.song_failed.emit(num)

    def on_progress(self, current: int, total: int) -> None:
        self._worker.progress.emit(current, total)

    def on_scroll(self, round_num: int) -> None:
        self._worker.log.emit(f"Scrolling down (round {round_num})...")

    def on_icons_found(self, count: int, round_num: int) -> None:
        self._worker.icons_found.emit(count, round_num)

    def should_stop(self) -> bool:
        return self._stop
