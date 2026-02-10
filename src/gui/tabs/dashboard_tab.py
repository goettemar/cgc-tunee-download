"""Dashboard tab — monitoring, start/stop, preflight checks, log."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..state import get_state
from ..styles import COLORS, LOG_PANEL_STYLE
from ..workers import CertWorker, DownloadWorker, ScanWorker

TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "old_code" / "templates"
REQUIRED_TEMPLATES = [
    "download_button.png", "modal_mp3.png", "modal_raw.png",
    "modal_video.png", "modal_lrc.png", "lyric_video_download.png",
]

CERT_TEMPLATES = [
    "play_button.png", "three_dots.png",
    "cert_menu_item.png", "cert_download.png",
]

# Strip ANSI escape sequences for GUI log
_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: DownloadWorker | None = None
        self._cert_worker: CertWorker | None = None
        self._chrome_proc: subprocess.Popen | None = None
        self._scan_worker: ScanWorker | None = None
        self._songs_tab = None  # set by MainWindow after construction
        self._build_ui()
        self._run_preflight()

    # ── UI Construction ──────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Preflight checks
        pf = QGroupBox("Preflight-Checks")
        pfl = QVBoxLayout(pf)
        self._preflight_labels: dict[str, QLabel] = {}
        for key in ("display", "monitor", "templates", "chrome"):
            lbl = QLabel()
            pfl.addWidget(lbl)
            self._preflight_labels[key] = lbl
        layout.addWidget(pf)

        # Controls
        ctrl = QGroupBox("Steuerung")
        cl = QVBoxLayout(ctrl)

        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("Start")
        self._start_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setProperty("class", "danger")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_download)
        btn_row.addWidget(self._stop_btn)

        self._chrome_btn = QPushButton("Chrome starten")
        self._chrome_btn.setProperty("class", "secondary")
        self._chrome_btn.clicked.connect(self._launch_chrome)
        btn_row.addWidget(self._chrome_btn)

        self._scan_btn = QPushButton("Projekt scannen")
        self._scan_btn.setProperty("class", "secondary")
        self._scan_btn.clicked.connect(self._scan_project)
        btn_row.addWidget(self._scan_btn)

        self._cert_btn = QPushButton("Zertifikate laden")
        self._cert_btn.setProperty("class", "secondary")
        self._cert_btn.clicked.connect(self._start_cert_download)
        btn_row.addWidget(self._cert_btn)

        self._refresh_btn = QPushButton("Checks aktualisieren")
        self._refresh_btn.setProperty("class", "secondary")
        self._refresh_btn.clicked.connect(self._run_preflight)
        btn_row.addWidget(self._refresh_btn)

        btn_row.addStretch()
        cl.addLayout(btn_row)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("0 / 0 Songs")
        cl.addWidget(self._progress)

        # Current song label
        self._current_label = QLabel("Bereit")
        self._current_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        cl.addWidget(self._current_label)

        layout.addWidget(ctrl)

        # Statistics
        stats = QGroupBox("Statistik")
        sl = QHBoxLayout(stats)
        w, self._val_downloaded = self._stat_label("0", "Heruntergeladen", COLORS["success"])
        sl.addWidget(w)
        w, self._val_duplicates = self._stat_label("0", "Duplikate", COLORS["warning"])
        sl.addWidget(w)
        w, self._val_failures = self._stat_label("0", "Fehler", COLORS["error"])
        sl.addWidget(w)
        sl.addStretch()
        layout.addWidget(stats)

        # Log panel
        log_group = QGroupBox("Log")
        ll = QVBoxLayout(log_group)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(LOG_PANEL_STYLE)
        self._log.setMaximumBlockCount(2000)
        ll.addWidget(self._log)
        layout.addWidget(log_group)

    def _stat_label(self, value: str, label: str, color: str) -> tuple[QWidget, QLabel]:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 4, 8, 4)
        val = QLabel(value)
        val.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {color};")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(val)
        desc = QLabel(label)
        desc.setStyleSheet(f"font-size: 11px; color: {COLORS['text_muted']};")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vl.addWidget(desc)
        return w, val

    # ── Preflight ────────────────────────────────────────────────

    def _run_preflight(self) -> None:
        state = get_state()
        cfg = state.config

        # Display
        display = os.environ.get("DISPLAY", "")
        if display:
            self._set_check("display", True, f"Display: {display}")
        else:
            self._set_check("display", False, "$DISPLAY nicht gesetzt")

        # Monitor
        try:
            from ...screenshot import get_screen_size
            w, h = get_screen_size()
            self._set_check("monitor", True, f"Monitor: {w}x{h}")
        except Exception as e:
            self._set_check("monitor", False, f"Monitor-Erkennung fehlgeschlagen: {e}")

        # Templates
        found = sum(1 for t in REQUIRED_TEMPLATES if (TEMPLATES_DIR / t).exists())
        total = len(REQUIRED_TEMPLATES)
        self._set_check("templates", found == total,
                        f"Templates: {found}/{total}")

        # Chrome (check CDP port)
        try:
            import requests
            r = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
            if r.status_code == 200:
                self._set_check("chrome", True, "Chrome: läuft (CDP aktiv)")
            else:
                self._set_check("chrome", False, "Chrome: nicht gestartet")
        except Exception:
            self._set_check("chrome", False, "Chrome: nicht gestartet")

    def _set_check(self, key: str, ok: bool, text: str) -> None:
        icon = "✓" if ok else "✗"
        color = COLORS["success"] if ok else COLORS["error"]
        self._preflight_labels[key].setText(
            f'<span style="color:{color}; font-weight:bold;">{icon}</span> {text}'
        )

    # ── Chrome ───────────────────────────────────────────────────

    def _launch_chrome(self) -> None:
        cfg = get_state().config
        cache_dir = os.path.expanduser("~/.cache/cgc_tunee_download/chrome_profile")
        cmd = [
            "google-chrome",
            f"--user-data-dir={cache_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--window-size=1920,1080",
            "--remote-debugging-port=9222",
            "--remote-allow-origins=*",
            cfg.tunee_url,
        ]
        self._chrome_proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._append_log("[INFO] Chrome gestartet")
        # Refresh preflight after 3s
        QTimer.singleShot(3000, self._run_preflight)

    # ── Project Scan ─────────────────────────────────────────────

    def _scan_project(self) -> None:
        self._scan_btn.setEnabled(False)
        self._scan_worker = ScanWorker(self)
        self._scan_worker.log.connect(self._append_log)
        self._scan_worker.error.connect(lambda e: self._append_log(f"[ERROR] {e}"))
        self._scan_worker.scan_complete.connect(self._on_scan_complete)
        self._scan_worker.finished_work.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_scan_complete(self, status: list) -> None:
        complete = sum(1 for s in status if s["complete"])
        missing = len(status) - complete
        self._append_log(f"[INFO] Projekt bereit: {len(status)} Songs, "
                         f"{complete} fertig, {missing} fehlend")
        if self._songs_tab:
            self._songs_tab.refresh()

    def _on_scan_finished(self, success: bool, msg: str) -> None:
        self._scan_btn.setEnabled(True)

    # ── Download Worker ──────────────────────────────────────────

    def _start_download(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        state = get_state()
        state.downloaded = 0
        state.duplicates = 0
        state.failures = 0
        state.running = True

        self._update_stats()
        self._log.clear()

        self._worker = DownloadWorker()
        self._worker.log.connect(self._append_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.song_started.connect(self._on_song_started)
        self._worker.song_completed.connect(self._on_song_completed)
        self._worker.song_duplicate.connect(self._on_song_duplicate)
        self._worker.song_failed.connect(self._on_song_failed)
        self._worker.icons_found.connect(self._on_icons_found)
        self._worker.error.connect(self._on_error)
        self._worker.finished_work.connect(self._on_finished)
        self._worker.start()

        self._start_btn.setEnabled(False)
        self._cert_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._current_label.setText("Download läuft...")
        self._current_label.setStyleSheet(f"color: {COLORS['info']}; font-size: 12px;")

    def _stop_download(self) -> None:
        if self._worker:
            self._worker.request_stop()
        if self._cert_worker:
            self._cert_worker.request_stop()
        self._stop_btn.setEnabled(False)
        self._current_label.setText("Wird gestoppt...")

    # ── Certificate Worker ────────────────────────────────────────

    def _start_cert_download(self) -> None:
        if self._cert_worker and self._cert_worker.isRunning():
            return
        if self._worker and self._worker.isRunning():
            return

        # Preflight: check cert templates exist
        missing = [t for t in CERT_TEMPLATES if not (TEMPLATES_DIR / t).exists()]
        if missing:
            self._append_log(f"[FEHLER] Cert-Templates fehlen: {', '.join(missing)}")
            self._append_log("  Erstelle mit: python create_cert_templates.py")
            return

        state = get_state()
        state.downloaded = 0
        state.duplicates = 0
        state.failures = 0
        state.running = True

        self._update_stats()
        self._log.clear()

        self._cert_worker = CertWorker()
        self._cert_worker.log.connect(self._append_log)
        self._cert_worker.progress.connect(self._on_progress)
        self._cert_worker.song_started.connect(self._on_song_started)
        self._cert_worker.song_completed.connect(self._on_song_completed)
        self._cert_worker.song_failed.connect(self._on_song_failed)
        self._cert_worker.icons_found.connect(self._on_icons_found)
        self._cert_worker.error.connect(self._on_error)
        self._cert_worker.finished_work.connect(self._on_finished)
        self._cert_worker.start()

        self._start_btn.setEnabled(False)
        self._cert_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._current_label.setText("Zertifikate werden geladen...")
        self._current_label.setStyleSheet(f"color: {COLORS['info']}; font-size: 12px;")

    # ── Signal Handlers ──────────────────────────────────────────

    def _append_log(self, msg: str) -> None:
        clean = _ANSI_RE.sub("", msg)
        self._log.appendPlainText(clean)
        # Auto-scroll
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_progress(self, current: int, total: int) -> None:
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
            self._progress.setFormat(f"{current} / {total} Songs")

    def _on_song_started(self, num: int, x: int, y: int) -> None:
        self._current_label.setText(f"Song #{num} — icon bei ({x},{y})")
        self._current_label.setStyleSheet(f"color: {COLORS['info']}; font-size: 12px;")

    def _on_song_completed(self, num: int, folder: str) -> None:
        state = get_state()
        state.downloaded += 1
        self._update_stats()
        self._current_label.setText(f"Song #{num} — {folder}")
        self._current_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
        if self._songs_tab:
            self._songs_tab.refresh()

    def _on_song_duplicate(self, num: int, name: str, duration: str) -> None:
        state = get_state()
        state.duplicates += 1
        self._update_stats()
        self._current_label.setText(f"Song #{num} — Duplikat: {name} ({duration})")
        self._current_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")

    def _on_song_failed(self, num: int) -> None:
        state = get_state()
        state.failures += 1
        self._update_stats()

    def _on_icons_found(self, count: int, round_num: int) -> None:
        self._append_log(f"Runde {round_num}: {count} Download-Icons gefunden")

    def _on_error(self, msg: str) -> None:
        self._append_log(f"[FEHLER] {msg}")

    def _on_finished(self, success: bool, message: str) -> None:
        state = get_state()
        state.running = False
        self._start_btn.setEnabled(True)
        self._cert_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        if success:
            self._current_label.setText(f"Fertig — {message}")
            self._current_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
        else:
            self._current_label.setText(f"Beendet — {message}")
            self._current_label.setStyleSheet(f"color: {COLORS['warning']}; font-size: 12px;")

        self._run_preflight()

        # Final songs tab refresh
        parent = self.parent()
        if parent:
            tabs = parent.parent()
            if hasattr(tabs, "_songs_tab"):
                tabs._songs_tab.refresh()

    def _update_stats(self) -> None:
        state = get_state()
        self._val_downloaded.setText(str(state.downloaded))
        self._val_duplicates.setText(str(state.duplicates))
        self._val_failures.setText(str(state.failures))
