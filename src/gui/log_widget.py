"""Log-Ausgabe Widget."""

from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Slot
from PySide6.QtGui import QTextCursor


class LogWidget(QTextEdit):
    """Widget zur Anzeige von Log-Nachrichten."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)

    @Slot(str)
    def append_log(self, message: str):
        """Fügt eine Log-Nachricht hinzu."""
        self.append(message)
        self.moveCursor(QTextCursor.MoveOperation.End)

    @Slot(str)
    def append_success(self, message: str):
        """Fügt eine Erfolgsmeldung (grün) hinzu."""
        self.append(f'<span style="color: #4ec9b0;">{message}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)

    @Slot(str)
    def append_error(self, message: str):
        """Fügt eine Fehlermeldung (rot) hinzu."""
        self.append(f'<span style="color: #f14c4c;">{message}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)

    @Slot(str)
    def append_warning(self, message: str):
        """Fügt eine Warnung (gelb) hinzu."""
        self.append(f'<span style="color: #cca700;">{message}</span>')
        self.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        """Löscht alle Log-Nachrichten."""
        self.clear()
