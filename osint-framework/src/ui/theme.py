"""
OSINT Framework — Premium Dark Theme System

Centralized theme with glassmorphism aesthetic, cyan/orange accent palette,
and consistent styling for all widgets.
"""

# === Color Palette ===
COLORS = {
    # Base
    "bg_darkest":    "#0a0e17",
    "bg_dark":       "#0f1923",
    "bg_medium":     "#162032",
    "bg_light":      "#1e2d42",
    "bg_lighter":    "#243447",
    
    # Surfaces
    "surface":       "#141e2b",
    "surface_hover": "#1a2738",
    "surface_active":"#1e3048",
    "card":          "#131c28",
    "card_border":   "#1e3048",
    
    # Text
    "text_primary":  "#e8edf3",
    "text_secondary":"#8899aa",
    "text_muted":    "#556677",
    "text_disabled": "#3a4a5a",
    
    # Accent — Cyan
    "accent":        "#00d4ff",
    "accent_hover":  "#33ddff",
    "accent_dim":    "#007a99",
    "accent_glow":   "rgba(0, 212, 255, 0.15)",
    "accent_border": "rgba(0, 212, 255, 0.3)",
    
    # Accent — Orange (secondary)
    "orange":        "#ff8c42",
    "orange_hover":  "#ffa366",
    "orange_dim":    "#cc6b2e",
    
    # Accent — Green (success)
    "green":         "#00e676",
    "green_dim":     "#00994d",
    
    # Accent — Red (danger)
    "red":           "#ff4757",
    "red_dim":       "#cc2233",
    
    # Accent — Yellow (warning)
    "yellow":        "#ffbe0b",
    "yellow_dim":    "#cc9800",
    
    # Accent — Purple
    "purple":        "#b24dff",
    "purple_dim":    "#7a1fbf",
    
    # Borders
    "border":        "#1e3048",
    "border_subtle": "#162032",
    "border_focus":  "#00d4ff",
}

# === Global Stylesheet ===
STYLESHEET = f"""
/* ===== GLOBAL RESET ===== */
QMainWindow, QWidget {{
    background-color: {COLORS['bg_darkest']};
    color: {COLORS['text_primary']};
    font-family: 'Inter', 'Segoe UI', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}}

/* ===== MENU BAR ===== */
QMenuBar {{
    background-color: {COLORS['bg_dark']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 2px 0px;
    color: {COLORS['text_secondary']};
    font-size: 12px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 4px;
    margin: 2px 2px;
}}
QMenuBar::item:selected {{
    background-color: {COLORS['surface_hover']};
    color: {COLORS['accent']};
}}
QMenu {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 30px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {COLORS['accent_glow']};
    color: {COLORS['accent']};
}}

/* ===== TAB WIDGET ===== */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    background-color: {COLORS['bg_dark']};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border_subtle']};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 22px;
    margin-right: 3px;
    font-weight: 500;
    font-size: 12px;
    min-width: 100px;
}}
QTabBar::tab:selected {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['accent']};
    border-color: {COLORS['accent_border']};
    border-bottom: 2px solid {COLORS['accent']};
}}
QTabBar::tab:hover:!selected {{
    background-color: {COLORS['surface_hover']};
    color: {COLORS['text_primary']};
}}

/* ===== BUTTONS ===== */
QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['accent_border']};
}}
QPushButton:pressed {{
    background-color: {COLORS['surface_active']};
}}
QPushButton:disabled {{
    color: {COLORS['text_disabled']};
    background-color: {COLORS['bg_medium']};
    border-color: {COLORS['border_subtle']};
}}
QPushButton#primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent_dim']}, stop:1 {COLORS['accent']});
    color: {COLORS['bg_darkest']};
    border: none;
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent']}, stop:1 {COLORS['accent_hover']});
}}
QPushButton#danger {{
    background: {COLORS['red_dim']};
    color: white;
    border: none;
}}
QPushButton#danger:hover {{
    background: {COLORS['red']};
}}

/* ===== INPUT FIELDS ===== */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    selection-background-color: {COLORS['accent_dim']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {COLORS['accent']};
    background-color: {COLORS['bg_light']};
}}
QLineEdit::placeholder {{
    color: {COLORS['text_muted']};
}}

/* ===== COMBO BOX ===== */
QComboBox {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px 14px;
    min-width: 120px;
}}
QComboBox:hover {{
    border-color: {COLORS['accent_border']};
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_dark']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    selection-background-color: {COLORS['accent_glow']};
    color: {COLORS['text_primary']};
}}

/* ===== SCROLL BARS ===== */
QScrollBar:vertical {{
    background: {COLORS['bg_darkest']};
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['bg_lighter']};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS['accent_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {COLORS['bg_darkest']};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['bg_lighter']};
    border-radius: 5px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLORS['accent_dim']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ===== TABLE / TREE VIEWS ===== */
QTableWidget, QTreeWidget, QListWidget {{
    background-color: {COLORS['bg_dark']};
    alternate-background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    gridline-color: {COLORS['border_subtle']};
    selection-background-color: {COLORS['accent_glow']};
    selection-color: {COLORS['accent']};
}}
QHeaderView::section {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['text_secondary']};
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px 12px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}}
QTableWidget::item, QTreeWidget::item, QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {COLORS['border_subtle']};
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    background-color: {COLORS['bg_medium']};
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: {COLORS['text_muted']};
    font-size: 10px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent_dim']}, stop:1 {COLORS['accent']});
    border-radius: 6px;
}}

/* ===== LABELS ===== */
QLabel#heading {{
    font-size: 20px;
    font-weight: 700;
    color: {COLORS['text_primary']};
}}
QLabel#subheading {{
    font-size: 14px;
    font-weight: 500;
    color: {COLORS['text_secondary']};
}}
QLabel#accent {{
    color: {COLORS['accent']};
    font-weight: 600;
}}
QLabel#muted {{
    color: {COLORS['text_muted']};
    font-size: 11px;
}}

/* ===== GROUP BOX ===== */
QGroupBox {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['card_border']};
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px;
    padding-top: 28px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 2px 10px;
    color: {COLORS['accent']};
    font-size: 12px;
}}

/* ===== SPLITTERS ===== */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {COLORS['bg_dark']};
    border-top: 1px solid {COLORS['border']};
    color: {COLORS['text_muted']};
    font-size: 11px;
}}
QStatusBar::item {{
    border: none;
}}

/* ===== TOOLTIPS ===== */
QToolTip {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['accent_border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}}

/* ===== CHECK/RADIO ===== */
QCheckBox {{
    color: {COLORS['text_primary']};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {COLORS['border']};
    background: {COLORS['bg_medium']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
QCheckBox::indicator:hover {{
    border-color: {COLORS['accent_dim']};
}}
"""

# === Card-style container helper ===
CARD_STYLE = f"""
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['card_border']};
    border-radius: 12px;
    padding: 16px;
"""

STAT_CARD_STYLE = f"""
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLORS['surface']}, stop:1 {COLORS['card']});
    border: 1px solid {COLORS['card_border']};
    border-radius: 12px;
    padding: 20px;
"""
