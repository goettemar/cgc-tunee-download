"""Song-Download Tab."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar, QGroupBox
)
from PySide6.QtCore import Slot

from src.gui.log_widget import LogWidget
from src.core.song_worker import SongDownloadWorker


DEFAULT_URL = "https://www.tunee.ai/conversation/-PhXUDbLtFJTN4iL-"


class DownloadTab(QWidget):
    """Tab für Song-Downloads."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # URL-Eingabe
        url_group = QGroupBox("Tunee Conversation URL")
        url_layout = QHBoxLayout(url_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.tunee.ai/conversation/...")
        self.url_input.setText(DEFAULT_URL)
        url_layout.addWidget(self.url_input)

        layout.addWidget(url_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Download starten")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
            }
        """)
        self.start_btn.clicked.connect(self._start_download)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Stopp")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #c42b1c;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e63d2e;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
            }
        """)
        self.stop_btn.clicked.connect(self._stop_download)
        btn_layout.addWidget(self.stop_btn)

        self.continue_btn = QPushButton("Weiter")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c8527;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4ca82f;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
            }
        """)
        self.continue_btn.clicked.connect(self._continue_download)
        btn_layout.addWidget(self.continue_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Fortschritt
        progress_group = QGroupBox("Fortschritt")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_label = QLabel("Bereit")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_group)

        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)

        clear_btn = QPushButton("Log löschen")
        clear_btn.clicked.connect(self.log_widget.clear_log)
        log_layout.addWidget(clear_btn)

        layout.addWidget(log_group, stretch=1)

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.log_widget.append_error("Bitte URL eingeben!")
            return

        if not "tunee.ai" in url:
            self.log_widget.append_error("Ungültige URL - muss tunee.ai enthalten")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starte...")

        # Worker erstellen
        self.worker = SongDownloadWorker(url)

        # Signals verbinden
        self.worker.signals.log.connect(self.log_widget.append_log)
        self.worker.signals.log_success.connect(self.log_widget.append_success)
        self.worker.signals.log_error.connect(self.log_widget.append_error)
        self.worker.signals.log_warning.connect(self.log_widget.append_warning)

        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.song_started.connect(self._on_song_started)
        self.worker.signals.finished.connect(self._on_finished)
        self.worker.signals.error.connect(self._on_error)
        self.worker.signals.waiting_for_user.connect(self._on_waiting_for_user)

        self.worker.start()

    def _stop_download(self):
        if self.worker:
            self.worker.request_stop()
            self.log_widget.append_warning("Stoppe nach aktuellem Song...")
            self.continue_btn.setEnabled(False)

    def _continue_download(self):
        if self.worker:
            self.worker.confirm_ready()
            self.continue_btn.setEnabled(False)
            self.progress_label.setText("Downloads laufen...")

    @Slot(int, int)
    def _on_progress(self, current: int, total: int):
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"Song {current} von {total}")

    @Slot(str)
    def _on_song_started(self, song_name: str):
        self.progress_label.setText(f"Lade: {song_name[:30]}...")

    @Slot(int, int)
    def _on_finished(self, success: int, failed: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.continue_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Fertig: {success} erfolgreich, {failed} fehlgeschlagen")
        self.worker = None

    @Slot(str)
    def _on_error(self, error: str):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.continue_btn.setEnabled(False)
        self.progress_label.setText(f"Fehler: {error[:50]}")
        self.worker = None

    @Slot()
    def _on_waiting_for_user(self):
        self.continue_btn.setEnabled(True)
        self.progress_label.setText("Warte auf Vorbereitung - klicke 'Weiter' wenn bereit")
