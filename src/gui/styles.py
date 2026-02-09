"""Zentrales Farbschema und Stylesheets – CGC Studio Design."""

COLORS = {
    # Primary
    "teal_dark": "#319795",
    "teal_mid": "#38B2AC",
    "teal_light": "#81E6D9",
    # Secondary
    "purple_dark": "#6B46C1",
    "purple_light": "#B794F4",
    # Neutral
    "bg_primary": "#f8f9fc",
    "bg_card": "#ffffff",
    "bg_sidebar": "#1a202c",
    "bg_sidebar_hover": "#2d3748",
    "bg_sidebar_active": "#319795",
    "text_primary": "#1c2321",
    "text_muted": "#718096",
    "text_sidebar": "#a0aec0",
    "text_sidebar_active": "#ffffff",
    "border": "#e2e8f0",
    "border_focus": "#319795",
    # Status
    "success": "#2ecc71",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "info": "#3498db",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS['bg_primary']};
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['bg_card']};
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {COLORS['border']};
    color: #4a5568;
    padding: 10px 20px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['teal_dark']};
    color: white;
}}

QTabBar::tab:hover:!selected {{
    background-color: #cbd5e0;
}}

/* ── Group Boxes ── */
QGroupBox {{
    font-weight: bold;
    font-size: 12px;
    color: {COLORS['teal_dark']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding: 16px 12px 12px 12px;
    background-color: {COLORS['bg_card']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    left: 12px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {COLORS['teal_dark']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
    font-size: 12px;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {COLORS['teal_mid']};
}}
QPushButton:pressed {{
    background-color: #2C7A7B;
}}
QPushButton:disabled {{
    background-color: #cbd5e0;
    color: #a0aec0;
}}

QPushButton[class="secondary"] {{
    background-color: {COLORS['border']};
    color: {COLORS['text_primary']};
}}
QPushButton[class="secondary"]:hover {{
    background-color: #cbd5e0;
}}

QPushButton[class="danger"] {{
    background-color: {COLORS['error']};
}}
QPushButton[class="danger"]:hover {{
    background-color: #c0392b;
}}

/* ── Inputs ── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    background-color: {COLORS['bg_card']};
    font-size: 12px;
    color: {COLORS['text_primary']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['border_focus']};
}}

/* ── ComboBox ── */
QComboBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    background-color: {COLORS['bg_card']};
    font-size: 12px;
    min-height: 20px;
}}
QComboBox:focus {{
    border-color: {COLORS['border_focus']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['teal_light']};
    selection-color: {COLORS['text_primary']};
}}

/* ── SpinBox / DoubleSpinBox ── */
QSpinBox, QDoubleSpinBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 10px;
    background-color: {COLORS['bg_card']};
    font-size: 12px;
    min-height: 20px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['border_focus']};
}}

/* ── Progress Bar ── */
QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    text-align: center;
    font-size: 11px;
    color: {COLORS['text_primary']};
    background-color: {COLORS['bg_primary']};
    min-height: 22px;
}}
QProgressBar::chunk {{
    background-color: {COLORS['teal_dark']};
    border-radius: 5px;
}}

/* ── Labels ── */
QLabel {{
    color: {COLORS['text_primary']};
    font-size: 12px;
}}

/* ── Scroll Area ── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}
QScrollBar:vertical {{
    width: 8px;
    background: transparent;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ── Table ── */
QTableWidget {{
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    gridline-color: {COLORS['border']};
    background-color: {COLORS['bg_card']};
    font-size: 12px;
    selection-background-color: {COLORS['teal_light']};
    selection-color: {COLORS['text_primary']};
}}
QTableWidget::item {{
    padding: 4px 8px;
}}
QHeaderView::section {{
    background-color: {COLORS['bg_primary']};
    color: {COLORS['text_primary']};
    font-weight: bold;
    font-size: 11px;
    padding: 6px 8px;
    border: none;
    border-bottom: 2px solid {COLORS['teal_dark']};
}}

/* ── CheckBox ── */
QCheckBox {{
    font-size: 12px;
    color: {COLORS['text_primary']};
    spacing: 8px;
}}

/* ── StatusBar ── */
QStatusBar {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_muted']};
    border-top: 1px solid {COLORS['border']};
    font-size: 11px;
}}
"""

LOG_PANEL_STYLE = f"""
    QPlainTextEdit {{
        background-color: #1a202c;
        color: #e2e8f0;
        font-family: monospace;
        font-size: 11px;
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 8px;
    }}
"""
