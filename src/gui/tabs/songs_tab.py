"""Songs tab — overview of downloaded songs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..styles import COLORS

TUNEE_DIR = Path.home() / "Downloads" / "tunee"

# Song file extensions
_SONG_EXTS = {".mp3", ".wav", ".flac", ".lrc", ".mp4"}


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
        self._count_label.setStyleSheet(
            f"font-weight: bold; color: {COLORS['text_muted']};"
        )
        header.addWidget(self._count_label)
        layout.addLayout(header)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(
            ["#", "Song Name", "Dauer", "Dateien", "MB", "Cert"]
        )
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
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

    def refresh(self) -> None:
        """Scan the tunee output directory and populate the table."""
        self._table.setRowCount(0)

        if not TUNEE_DIR.exists():
            self._count_label.setText("0 Songs")
            return

        folders = sorted(
            [d for d in TUNEE_DIR.iterdir() if d.is_dir()],
            key=lambda d: d.name,
        )

        # Count complete vs missing
        complete = 0
        missing = 0
        certs = 0
        for folder in folders:
            all_files = list(folder.iterdir())
            has_files = any(
                f.suffix.lower() in _SONG_EXTS for f in all_files if f.is_file()
            )
            has_cert = any(f.suffix.lower() == ".pdf" for f in all_files if f.is_file())
            if has_files:
                complete += 1
            else:
                missing += 1
            if has_cert:
                certs += 1

        parts = [f"{complete} Songs"]
        if missing > 0:
            parts.append(f"{missing} fehlend")
        parts.append(f"{certs}/{len(folders)} Certs")
        self._count_label.setText(", ".join(parts))

        self._table.setRowCount(len(folders))
        missing_brush = QBrush(QColor(COLORS["error"]))

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
            files = [f for f in folder.iterdir() if f.is_file()]
            song_files = [f for f in files if f.suffix.lower() in _SONG_EXTS]
            has_cert = any(f.suffix.lower() == ".pdf" for f in files)
            file_count = len(song_files)
            total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

            is_missing = file_count == 0

            cert_item = self._centered_item("✓" if has_cert else "✗")
            if has_cert:
                cert_item.setForeground(QBrush(QColor(COLORS["success"])))
            else:
                cert_item.setForeground(QBrush(QColor(COLORS["error"])))

            items = [
                self._centered_item(num),
                QTableWidgetItem("  " + song_name if is_missing else song_name),
                self._centered_item(display_dur),
                self._centered_item("fehlend" if is_missing else str(file_count)),
                self._centered_item("—" if is_missing else f"{total_mb:.0f}"),
                cert_item,
            ]

            for col, item in enumerate(items):
                if is_missing:
                    item.setForeground(missing_brush)
                self._table.setItem(row, col, item)

    @staticmethod
    def _centered_item(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
