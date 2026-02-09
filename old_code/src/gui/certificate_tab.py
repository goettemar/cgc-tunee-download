"""Certificate-Download Tab."""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar, QGroupBox,
    QListWidget, QListWidgetItem, QFileDialog
)
from PySide6.QtCore import Slot

from src.gui.log_widget import LogWidget
from src.core.cert_worker import CertificateWorker, find_folders_without_certificate
from src.auth import DOWNLOADS_DIR


DEFAULT_URL = "https://www.tunee.ai/conversation/-PhXUDbLtFJTN4iL-"


class CertificateTab(QWidget):
    """Tab für Certificate-Downloads."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.folders_without_cert = []
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

        # Ordner-Auswahl
        folder_group = QGroupBox("Download-Ordner")
        folder_layout = QHBoxLayout(folder_group)

        self.folder_input = QLineEdit()
        self.folder_input.setText(str(DOWNLOADS_DIR))
        self.folder_input.setReadOnly(True)
        folder_layout.addWidget(self.folder_input)

        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(40)
        browse_btn.clicked.connect(self._browse_folder)
        folder_layout.addWidget(browse_btn)

        scan_btn = QPushButton("Scannen")
        scan_btn.clicked.connect(self._scan_folders)
        folder_layout.addWidget(scan_btn)

        layout.addWidget(folder_group)

        # Liste der Ordner ohne Certificate
        list_group = QGroupBox("Ordner ohne Certificate")
        list_layout = QVBoxLayout(list_group)

        self.folder_list = QListWidget()
        list_layout.addWidget(self.folder_list)

        self.list_label = QLabel("Klicke 'Scannen' um Ordner zu finden")
        list_layout.addWidget(self.list_label)

        layout.addWidget(list_group)

        # Buttons
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("Certificates laden")
        self.start_btn.setEnabled(False)
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

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Download-Ordner wählen",
            str(DOWNLOADS_DIR)
        )
        if folder:
            self.folder_input.setText(folder)

    def _scan_folders(self):
        folder_path = Path(self.folder_input.text())

        if not folder_path.exists():
            self.log_widget.append_error(f"Ordner existiert nicht: {folder_path}")
            return

        self.folders_without_cert = find_folders_without_certificate(folder_path)

        self.folder_list.clear()
        for folder in self.folders_without_cert:
            item = QListWidgetItem(folder.name)
            self.folder_list.addItem(item)

        count = len(self.folders_without_cert)
        self.list_label.setText(f"{count} Ordner ohne Certificate gefunden")

        if count > 0:
            self.start_btn.setEnabled(True)
            self.log_widget.append_success(f"{count} Ordner ohne Certificate gefunden")
        else:
            self.start_btn.setEnabled(False)
            self.log_widget.append_log("Alle Ordner haben bereits ein Certificate")

    def _start_download(self):
        if not self.folders_without_cert:
            self.log_widget.append_error("Keine Ordner zum Verarbeiten!")
            return

        url = self.url_input.text().strip()
        if not url or "tunee.ai" not in url:
            self.log_widget.append_error("Bitte gültige Tunee-URL eingeben!")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starte...")

        # Worker erstellen
        self.worker = CertificateWorker(url, self.folders_without_cert)

        # Signals verbinden
        self.worker.signals.log.connect(self.log_widget.append_log)
        self.worker.signals.log_success.connect(self.log_widget.append_success)
        self.worker.signals.log_error.connect(self.log_widget.append_error)
        self.worker.signals.log_warning.connect(self.log_widget.append_warning)

        self.worker.signals.progress.connect(self._on_progress)
        self.worker.signals.song_started.connect(self._on_folder_started)
        self.worker.signals.finished.connect(self._on_finished)
        self.worker.signals.error.connect(self._on_error)

        self.worker.start()

    def _stop_download(self):
        if self.worker:
            self.worker.request_stop()
            self.log_widget.append_warning("Stoppe nach aktuellem Ordner...")

    @Slot(int, int)
    def _on_progress(self, current: int, total: int):
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"Ordner {current} von {total}")

        # Markiere aktuellen Ordner in Liste
        if current > 0 and current <= self.folder_list.count():
            self.folder_list.setCurrentRow(current - 1)

    @Slot(str)
    def _on_folder_started(self, folder_name: str):
        self.progress_label.setText(f"Lade: {folder_name[:30]}...")

    @Slot(int, int)
    def _on_finished(self, success: int, failed: int):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Fertig: {success} erfolgreich, {failed} fehlgeschlagen")
        self.worker = None

        # Liste neu scannen
        self._scan_folders()

    @Slot(str)
    def _on_error(self, error: str):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_label.setText(f"Fehler: {error[:50]}")
        self.worker = None
