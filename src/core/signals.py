"""Signale für die Kommunikation zwischen Worker und GUI."""

from PySide6.QtCore import QObject, Signal


class DownloadSignals(QObject):
    """Signale für den Download-Prozess."""

    # Fortschritt: (aktuell, gesamt)
    progress = Signal(int, int)

    # Log-Nachrichten
    log = Signal(str)
    log_success = Signal(str)
    log_error = Signal(str)
    log_warning = Signal(str)

    # Song-Events
    song_started = Signal(str)  # Song-Name
    song_complete = Signal(str, int)  # Song-Name, erfolgreiche Downloads (0-4)
    song_failed = Signal(str, str)  # Song-Name, Fehler

    # Prozess-Events
    started = Signal()
    finished = Signal(int, int)  # erfolgreiche, fehlgeschlagene
    error = Signal(str)  # Kritischer Fehler

    # Browser-Events
    browser_ready = Signal()
    login_required = Signal()
    waiting_for_user = Signal()  # Wartet auf Benutzerbestätigung
