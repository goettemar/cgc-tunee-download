#!/usr/bin/env python3
"""
Tunee.ai Download Manager
GUI-Anwendung für Song- und Certificate-Downloads.
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.gui.main_window import MainWindow


def main():
    # High DPI Support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Tunee Download Manager")
    app.setOrganizationName("CGC")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
