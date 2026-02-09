"""Application entry point for the PySide6 GUI."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .window import MainWindow


def run_gui() -> int:
    """Launch the GUI and return exit code."""
    app = QApplication(sys.argv)
    app.setApplicationName("CGC Tunee Download")

    window = MainWindow()
    window.show()

    return app.exec()
