"""Hauptfenster der Tunee Download Anwendung."""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.gui.download_tab import DownloadTab
from src.gui.certificate_tab import CertificateTab


class MainWindow(QMainWindow):
    """Hauptfenster mit Tabs für Downloads und Certificates."""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Tunee Download Manager")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        # Dark Theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #252526;
                color: #d4d4d4;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #d4d4d4;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #0e639c;
            }
            QTabBar::tab:hover {
                background-color: #3c3c3c;
            }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 6px;
                color: #d4d4d4;
            }
            QLineEdit:focus {
                border: 1px solid #0e639c;
            }
            QProgressBar {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                background-color: #3c3c3c;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
            }
        """)

        # Tab-Widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Download Tab
        self.download_tab = DownloadTab()
        self.tabs.addTab(self.download_tab, "Song Download")

        # Certificate Tab
        self.certificate_tab = CertificateTab()
        self.tabs.addTab(self.certificate_tab, "Certificates")

        # Statusbar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Tunee Download Manager - Bereit")
