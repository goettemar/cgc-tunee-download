"""Main window with header and tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QLinearGradient, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .styles import COLORS, STYLESHEET
from .tabs.dashboard_tab import DashboardTab
from .tabs.settings_tab import SettingsTab
from .tabs.songs_tab import SongsTab


class _Header(QWidget):
    """Teal gradient header bar."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self.setFixedHeight(70)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, QColor(COLORS["teal_dark"]))
        grad.setColorAt(1, QColor(COLORS["teal_light"]))
        p.fillRect(self.rect(), grad)

        p.setPen(QColor("white"))
        font = QFont()
        font.setPixelSize(22)
        font.setBold(True)
        p.setFont(font)
        p.drawText(
            self.rect().adjusted(24, 0, 0, 0),
            Qt.AlignmentFlag.AlignVCenter,
            self._title,
        )
        p.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CGC Tunee Download")
        self.setMinimumSize(900, 700)
        self.resize(1000, 800)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        layout.addWidget(_Header("CGC Tunee Download"))

        # Tab widget
        tabs = QTabWidget()
        tabs.setContentsMargins(12, 12, 12, 12)

        self._dashboard_tab = DashboardTab()
        self._songs_tab = SongsTab()
        self._settings_tab = SettingsTab()

        # Wire cross-tab references
        self._dashboard_tab._songs_tab = self._songs_tab

        tabs.addTab(self._dashboard_tab, "Dashboard")
        tabs.addTab(self._songs_tab, "Songs")
        tabs.addTab(self._settings_tab, "Einstellungen")

        # Wrap in padded container
        tab_container = QWidget()
        tcl = QVBoxLayout(tab_container)
        tcl.setContentsMargins(12, 12, 12, 12)
        tcl.addWidget(tabs)

        layout.addWidget(tab_container)
