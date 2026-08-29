"""Design language for the overlay - Modern Glassmorphism."""

BG = "rgba(18, 20, 26, 0.88)"
BG_CARD = "rgba(255, 255, 255, 0.04)"
BG_CARD_HOVER = "rgba(255, 255, 255, 0.07)"
BORDER = "rgba(255, 255, 255, 0.10)"
BORDER_ACCENT = "rgba(110, 231, 183, 0.40)"

TEXT_PRIMARY = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
ACCENT = "#6EE7B7"
ACCENT_BG = "rgba(110, 231, 183, 0.12)"
WARN = "#FBBF24"
BLUE_CHEST = "#60A5FA"
GOLD_CHEST = "#FBBF24"

RADIUS = 16
PADDING = 18
FONT_FAMILY = "Segoe UI Variable, Segoe UI, -apple-system, sans-serif"

FONT_LABEL = f"8pt '{FONT_FAMILY}'"
FONT_VALUE = f"22pt '{FONT_FAMILY}'"
FONT_VALUE_SMALL = f"13pt '{FONT_FAMILY}'"
FONT_TITLE = f"9pt '{FONT_FAMILY}'"
FONT_TAB = f"9pt '{FONT_FAMILY}'"
FONT_TOGGLE = f"9.5pt '{FONT_FAMILY}'"
FONT_HISTORY = f"9pt '{FONT_FAMILY}'"

CARD_STYLE = f"""
QWidget#card {{
    background-color: {BG};
    border: 1px solid {BORDER};
    border-radius: {RADIUS}px;
}}
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel[role="label"] {{
    color: {TEXT_MUTED};
    font: {FONT_LABEL};
    font-weight: 600;
    letter-spacing: 1.2px;
}}
QLabel[role="value"] {{
    font: {FONT_VALUE};
    font-weight: 700;
    color: {ACCENT};
}}
QLabel[role="value-small"] {{
    font: {FONT_VALUE_SMALL};
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}
QLabel[role="title"] {{
    color: {TEXT_MUTED};
    font: {FONT_TITLE};
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel[role="accent"] {{
    color: {ACCENT};
}}
"""

TAB_STYLE = f"""
QPushButton[role="tab"] {{
    background: transparent;
    border: none;
    color: {TEXT_MUTED};
    font: {FONT_TAB};
    font-weight: 600;
    letter-spacing: 0.8px;
    padding: 5px 12px;
    border-radius: 8px;
}}
QPushButton[role="tab"][active="true"] {{
    color: {ACCENT};
    background: {ACCENT_BG};
    border: 1px solid {BORDER_ACCENT};
}}
QPushButton[role="tab"]:hover {{
    color: {TEXT_PRIMARY};
    background: rgba(255, 255, 255, 0.05);
}}
"""

TOGGLE_STYLE = f"""
QPushButton[role="toggle"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    color: {TEXT_MUTED};
    font: {FONT_TOGGLE};
    font-weight: 500;
    padding: 8px 14px;
    text-align: left;
}}
QPushButton[role="toggle"][checked="true"] {{
    color: {TEXT_PRIMARY};
    border-color: {BORDER_ACCENT};
    background: {ACCENT_BG};
}}
QPushButton[role="toggle"]:hover {{
    background: {BG_CARD_HOVER};
    border-color: rgba(255, 255, 255, 0.20);
}}
"""

HISTORY_CARD_STYLE = f"""
QWidget[role="history-card"] {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
QWidget[role="history-card"]:hover {{
    background: {BG_CARD_HOVER};
    border-color: rgba(255, 255, 255, 0.18);
}}
"""

NOTIFICATION_STYLE = f"""
QLabel[role="notification"] {{
    background: rgba(18, 20, 26, 0.95);
    border: 1px solid {BORDER_ACCENT};
    border-radius: 10px;
    color: {ACCENT};
    font: 10.5pt '{FONT_FAMILY}';
    font-weight: 600;
    padding: 8px 14px;
}}
"""

SCROLLBAR_STYLE = f"""
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.20);
    border-radius: 2.5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
