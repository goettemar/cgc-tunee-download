"""Songs tab — overview of downloaded songs."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..state import get_state
from ..styles import COLORS

TUNEE_DIR = Path.home() / "Downloads" / "tunee"


class SongsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header row
        header = QHBoxLayout()
        self._refresh_btn = QPushButton("Aktualisieren")
        self._refresh_btn.setProperty("class", "secondary")
        self._refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self._refresh_btn)
        header.addStretch()
        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"font-weight: bold; color: {COLORS['text_muted']};")
        header.addWidget(self._count_label)
        layout.addLayout(header)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["#", "Song Name", "Dauer", "Dateien", "MB"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

    def refresh(self) -> None:
        """Scan the tunee output directory and populate the table."""
        self._table.setRowCount(0)

        if not TUNEE_DIR.exists():
            self._count_label.setText("0 Songs heruntergeladen")
            return

        folders = sorted(
            [d for d in TUNEE_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.name,
        )

        self._count_label.setText(f"{len(folders)} Songs heruntergeladen")
        self._table.setRowCount(len(folders))

        for row, folder in enumerate(folders):
            name = folder.name
            # Parse: "NN - SongName - MMmSSs"
            parts = name.split(" - ", 2)
            num = parts[0] if len(parts) >= 1 else ""
            song_name = parts[1] if len(parts) >= 2 else name
            duration = parts[2] if len(parts) >= 3 else ""

            # Format duration for display: "04m10s" → "04:10"
            display_dur = duration
            if duration and "m" in duration and "s" in duration:
                try:
                    m, s = duration.replace("s", "").split("m")
                    display_dur = f"{int(m):02d}:{int(s):02d}"
                except Exception:
                    pass

            # Count files and total size
            files = list(folder.iterdir())
            file_count = len([f for f in files if f.is_file()])
            total_mb = sum(f.stat().st_size for f in files if f.is_file()) / (1024 * 1024)

            self._table.setItem(row, 0, self._centered_item(num))
            self._table.setItem(row, 1, QTableWidgetItem(song_name))
            self._table.setItem(row, 2, self._centered_item(display_dur))
            self._table.setItem(row, 3, self._centered_item(str(file_count)))
            self._table.setItem(row, 4, self._centered_item(f"{total_mb:.0f}"))

    @staticmethod
    def _centered_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
