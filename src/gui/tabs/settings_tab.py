"""Settings tab — configuration for all download parameters."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..state import get_state
from ..styles import COLORS

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "old_code" / "templates"
REQUIRED_TEMPLATES = [
    "download_button.png",
    "modal_mp3.png",
    "modal_raw.png",
    "modal_video.png",
    "modal_lrc.png",
    "lyric_video_download.png",
]


class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Allgemein ──
        general = QGroupBox("Allgemein")
        gl = QVBoxLayout(general)

        # URL
        row = QHBoxLayout()
        row.addWidget(QLabel("Tunee URL:"))
        self._url = QLineEdit()
        row.addWidget(self._url)
        gl.addLayout(row)

        # Output dir
        row = QHBoxLayout()
        row.addWidget(QLabel("Ausgabeverzeichnis:"))
        self._output_dir = QLineEdit()
        row.addWidget(self._output_dir)
        gl.addLayout(row)

        # Monitor
        row = QHBoxLayout()
        row.addWidget(QLabel("Monitor:"))
        self._monitor = QComboBox()
        self._populate_monitors()
        row.addWidget(self._monitor)
        gl.addLayout(row)

        # Max songs / scrolls
        row = QHBoxLayout()
        row.addWidget(QLabel("Max. Songs:"))
        self._max_songs = QSpinBox()
        self._max_songs.setRange(1, 500)
        row.addWidget(self._max_songs)
        row.addWidget(QLabel("Max. Scrolls:"))
        self._max_scrolls = QSpinBox()
        self._max_scrolls.setRange(1, 100)
        row.addWidget(self._max_scrolls)
        gl.addLayout(row)

        layout.addWidget(general)

        # ── Timing ──
        timing = QGroupBox("Timing")
        tl = QVBoxLayout(timing)

        row = QHBoxLayout()
        row.addWidget(QLabel("Klick-Verzögerung (s):"))
        self._click_delay = QDoubleSpinBox()
        self._click_delay.setRange(0.1, 10.0)
        self._click_delay.setSingleStep(0.1)
        row.addWidget(self._click_delay)
        row.addWidget(QLabel("Zwischen Songs (s):"))
        self._between_delay = QDoubleSpinBox()
        self._between_delay.setRange(0.5, 30.0)
        self._between_delay.setSingleStep(0.5)
        row.addWidget(self._between_delay)
        tl.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Video-Warten max. (s):"))
        self._video_wait = QSpinBox()
        self._video_wait.setRange(10, 300)
        row.addWidget(self._video_wait)
        row.addStretch()
        tl.addLayout(row)

        layout.addWidget(timing)

        # ── Template-Matching ──
        tmpl = QGroupBox("Template-Matching")
        ml = QVBoxLayout(tmpl)

        row = QHBoxLayout()
        row.addWidget(QLabel("DL-Icon Schwelle:"))
        self._dl_thresh = QDoubleSpinBox()
        self._dl_thresh.setRange(0.1, 1.0)
        self._dl_thresh.setSingleStep(0.05)
        self._dl_thresh.setDecimals(2)
        row.addWidget(self._dl_thresh)
        row.addWidget(QLabel("Modal-Zeile:"))
        self._modal_thresh = QDoubleSpinBox()
        self._modal_thresh.setRange(0.1, 1.0)
        self._modal_thresh.setSingleStep(0.05)
        self._modal_thresh.setDecimals(2)
        row.addWidget(self._modal_thresh)
        row.addWidget(QLabel("Video-DL:"))
        self._video_thresh = QDoubleSpinBox()
        self._video_thresh.setRange(0.1, 1.0)
        self._video_thresh.setSingleStep(0.05)
        self._video_thresh.setDecimals(2)
        row.addWidget(self._video_thresh)
        ml.addLayout(row)

        # Check templates button
        row = QHBoxLayout()
        self._check_btn = QPushButton("Templates prüfen")
        self._check_btn.setProperty("class", "secondary")
        self._check_btn.clicked.connect(self._check_templates)
        row.addWidget(self._check_btn)
        self._tmpl_status = QLabel("")
        row.addWidget(self._tmpl_status)
        row.addStretch()
        ml.addLayout(row)

        layout.addWidget(tmpl)

        # ── Save Button ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Einstellungen speichern")
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _populate_monitors(self) -> None:
        try:
            from ...screenshot import list_monitors
            monitors = list_monitors()
            for i, m in enumerate(monitors):
                if i == 0:
                    continue  # skip "all combined"
                self._monitor.addItem(
                    f"Monitor {i}: {m['width']}x{m['height']} @ ({m['left']},{m['top']})",
                    userData=i,
                )
        except Exception:
            for i in range(1, 5):
                self._monitor.addItem(f"Monitor {i}", userData=i)

    def _load_config(self) -> None:
        cfg = get_state().config
        self._url.setText(cfg.tunee_url)
        self._output_dir.setText(cfg.output_dir)

        # Select correct monitor in combo
        for i in range(self._monitor.count()):
            if self._monitor.itemData(i) == cfg.monitor_index:
                self._monitor.setCurrentIndex(i)
                break

        self._max_songs.setValue(cfg.max_songs)
        self._max_scrolls.setValue(cfg.max_scrolls)
        self._click_delay.setValue(cfg.click_delay)
        self._between_delay.setValue(cfg.between_songs_delay)
        self._video_wait.setValue(cfg.video_wait_max)
        self._dl_thresh.setValue(cfg.dl_icon_threshold)
        self._modal_thresh.setValue(cfg.modal_row_threshold)
        self._video_thresh.setValue(cfg.video_dl_threshold)

    def _save_config(self) -> None:
        cfg = get_state().config
        cfg.tunee_url = self._url.text()
        cfg.output_dir = self._output_dir.text()
        cfg.monitor_index = self._monitor.currentData() or 3
        cfg.max_songs = self._max_songs.value()
        cfg.max_scrolls = self._max_scrolls.value()
        cfg.click_delay = self._click_delay.value()
        cfg.between_songs_delay = self._between_delay.value()
        cfg.video_wait_max = self._video_wait.value()
        cfg.dl_icon_threshold = self._dl_thresh.value()
        cfg.modal_row_threshold = self._modal_thresh.value()
        cfg.video_dl_threshold = self._video_thresh.value()
        cfg.save()

        QMessageBox.information(self, "Gespeichert", "Einstellungen wurden gespeichert.")

    def _check_templates(self) -> None:
        found = 0
        missing = []
        for name in REQUIRED_TEMPLATES:
            if (TEMPLATES_DIR / name).exists():
                found += 1
            else:
                missing.append(name)

        if missing:
            self._tmpl_status.setText(
                f'<span style="color:{COLORS["error"]}">'
                f'{found}/{len(REQUIRED_TEMPLATES)} — Fehlend: {", ".join(missing)}</span>'
            )
        else:
            self._tmpl_status.setText(
                f'<span style="color:{COLORS["success"]}">'
                f'{found}/{len(REQUIRED_TEMPLATES)} Templates vorhanden</span>'
            )
