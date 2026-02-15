"""
OSINT Framework — Premium Desktop Main Window

Tabbed investigation dashboard with real-time progress,
entity graph, timeline, recon panel, and risk dashboard.
Connected directly to InvestigationOrchestrator via QThread workers.
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QLineEdit, QComboBox, QProgressBar,
    QTextEdit, QStatusBar, QMenuBar, QMenu, QGroupBox,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QSplitter, QFrame, QCheckBox, QFileDialog, QMessageBox,
    QHeaderView, QApplication, QGridLayout, QScrollArea, QSpacerItem,
    QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QSize, QTimer, QPropertyAnimation,
    QEasingCurve
)
from PyQt6.QtGui import (
    QFont, QIcon, QPalette, QColor, QAction, QPainter, QPen,
    QBrush, QLinearGradient, QPixmap
)

from src.ui.theme import STYLESHEET, COLORS, CARD_STYLE, STAT_CARD_STYLE
from src.core.orchestrator import (
    InvestigationOrchestrator, InvestigationConfig, InvestigationResult,
    InvestigationStage, EntityType
)

logger = logging.getLogger(__name__)


class InvestigationWorker(QThread):
    """Background worker that runs investigations without blocking the UI."""
    progress = pyqtSignal(str, int)      # message, percentage
    stage_changed = pyqtSignal(str, str) # stage_name, status
    finished = pyqtSignal(object)        # InvestigationResult
    error = pyqtSignal(str)

    def __init__(self, config: InvestigationConfig):
        super().__init__()
        self.config = config
        self.orchestrator = InvestigationOrchestrator()

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.orchestrator.run_investigation(
                    self.config,
                    progress_callback=lambda msg, pct: self.progress.emit(msg, pct),
                    stage_callback=lambda stage, status: self.stage_changed.emit(stage.value, status),
                )
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            loop.close()

    def cancel(self):
        self.orchestrator.cancel()


class StatCard(QFrame):
    """Styled card widget for statistics display."""
    def __init__(self, title: str, value: str = "—", subtitle: str = "",
                 accent_color: str = COLORS['accent'], parent=None):
        super().__init__(parent)
        self.setStyleSheet(STAT_CARD_STYLE)
        self.setMinimumSize(180, 100)
        self.setMaximumHeight(120)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 12, 16, 12)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; text-transform: uppercase; border: none;")
        layout.addWidget(title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {accent_color}; font-size: 28px; font-weight: 700; border: none;")
        layout.addWidget(self.value_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px; border: none;")
        layout.addWidget(self.subtitle_label)

    def update_value(self, value: str, subtitle: str = ""):
        self.value_label.setText(value)
        if subtitle:
            self.subtitle_label.setText(subtitle)


class MainWindow(QMainWindow):
    """OSINT Framework — Premium Investigation Dashboard"""

    def __init__(self):
        super().__init__()
        self.current_result: Optional[InvestigationResult] = None
        self.worker: Optional[InvestigationWorker] = None
        self.investigation_history: list = []

        self.setWindowTitle("⚡ OSINT Framework — Intelligence Platform")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        self.setStyleSheet(STYLESHEET)

        self._init_ui()
        self._init_menu()
        self._init_statusbar()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        header = self._build_header()
        main_layout.addWidget(header)

        # Main tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        main_layout.addWidget(self.tabs)

        # Build tabs
        self.tabs.addTab(self._build_dashboard_tab(), "🏠 Dashboard")
        self.tabs.addTab(self._build_investigation_tab(), "🔍 Investigation")
        self.tabs.addTab(self._build_recon_tab(), "🛡️ Recon Results")
        self.tabs.addTab(self._build_graph_tab(), "🕸️ Entity Graph")
        self.tabs.addTab(self._build_timeline_tab(), "📅 Timeline")
        self.tabs.addTab(self._build_report_tab(), "📊 Report")

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {COLORS['bg_dark']}, stop:0.5 {COLORS['surface']}, stop:1 {COLORS['bg_dark']});
            border-bottom: 1px solid {COLORS['border']};
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(8)

        # Logo and title
        title = QLabel("⚡ OSINT FRAMEWORK")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-size: 16px; font-weight: 800; letter-spacing: 2px; border: none;")
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # Search type selector (always visible in header)
        type_label = QLabel("Type:")
        type_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: 600; border: none;")
        layout.addWidget(type_label)

        self.header_type_combo = QComboBox()
        self.header_type_combo.addItems(["Domain", "IP Address", "Email", "Username", "Person"])
        self.header_type_combo.setFixedWidth(130)
        self.header_type_combo.setFixedHeight(34)
        self.header_type_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: 13px; font-weight: 600;
                padding: 4px 10px;
                background-color: {COLORS['bg_light']};
                border: 1px solid {COLORS['accent_dim']};
                border-radius: 6px;
                color: {COLORS['accent']};
            }}
            QComboBox:hover {{ border-color: {COLORS['accent']}; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border']};
                color: {COLORS['text_primary']};
            }}
        """)
        layout.addWidget(self.header_type_combo)

        # Quick search
        self.quick_search = QLineEdit()
        self.quick_search.setPlaceholderText("Quick scan: domain, IP, email, or name...")
        self.quick_search.setFixedWidth(350)
        self.quick_search.returnPressed.connect(self._quick_scan)
        layout.addWidget(self.quick_search)

        quick_btn = QPushButton("⚡ Scan")
        quick_btn.setObjectName("primary")
        quick_btn.setFixedWidth(90)
        quick_btn.clicked.connect(self._quick_scan)
        layout.addWidget(quick_btn)

        # Person search shortcut button
        person_btn = QPushButton("👤 Person Search")
        person_btn.setFixedWidth(140)
        person_btn.setFixedHeight(34)
        person_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['orange_dim']};
                color: white; border: none; border-radius: 6px;
                font-weight: 600; font-size: 12px; padding: 6px 12px;
            }}
            QPushButton:hover {{ background: {COLORS['orange']}; }}
        """)
        person_btn.clicked.connect(self._open_person_search)
        layout.addWidget(person_btn)

        return header

    def _build_dashboard_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self.stat_investigations = StatCard("Total Investigations", "0", "investigations run")
        self.stat_entities = StatCard("Entities Discovered", "0", "unique entities", COLORS['green'])
        self.stat_risk = StatCard("Avg Risk Score", "—", "across targets", COLORS['orange'])
        self.stat_ports = StatCard("Open Ports Found", "0", "across all scans", COLORS['red'])
        stats_layout.addWidget(self.stat_investigations)
        stats_layout.addWidget(self.stat_entities)
        stats_layout.addWidget(self.stat_risk)
        stats_layout.addWidget(self.stat_ports)
        layout.addLayout(stats_layout)

        # Recent investigations
        recent_group = QGroupBox("Recent Investigations")
        recent_layout = QVBoxLayout(recent_group)
        self.recent_table = QTableWidget(0, 5)
        self.recent_table.setHorizontalHeaderLabels(["Target", "Type", "Risk", "Entities", "Date"])
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recent_table.doubleClicked.connect(self._load_selected_investigation)
        recent_layout.addWidget(self.recent_table)
        layout.addWidget(recent_group)

        # Welcome message (shown when no investigations)
        self.welcome_label = QLabel(
            "🔍 No investigations yet. Enter a target in the search bar above or go to the Investigation tab to begin.\n\n"
            "Supported targets:\n"
            "  • Domains — example.com\n"
            "  • IP addresses — 192.168.1.1\n"
            "  • Email addresses — user@example.com\n"
            "  • Usernames — @johndoe\n"
            "  • People — search by full name, DOB, and location"
        )
        self.welcome_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 14px;
            padding: 40px;
            background: {COLORS['card']};
            border: 1px dashed {COLORS['border']};
            border-radius: 12px;
        """)
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.welcome_label)

        return tab

    def _build_investigation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Configuration panel
        config_group = QGroupBox("Investigation Configuration")
        config_layout = QGridLayout(config_group)
        config_layout.setSpacing(12)
        config_layout.setContentsMargins(16, 28, 16, 16)

        # Field label style
        label_style = f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; border: none;"

        # Row 0 — Target
        lbl_target = QLabel("Target:")
        lbl_target.setStyleSheet(label_style)
        config_layout.addWidget(lbl_target, 0, 0)
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Enter domain, IP, email, or username...")
        self.target_input.setMinimumHeight(38)
        config_layout.addWidget(self.target_input, 0, 1, 1, 3)

        # Row 1 — Entity Type (highly visible)
        lbl_type = QLabel("⚡ Entity Type:")
        lbl_type.setStyleSheet(f"color: {COLORS['accent']}; font-size: 14px; font-weight: 700; border: none;")
        config_layout.addWidget(lbl_type, 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Domain", "IP Address", "Email", "Username", "Person", "Organization"])
        self.type_combo.setMinimumHeight(40)
        self.type_combo.setStyleSheet(f"""
            QComboBox {{
                font-size: 14px;
                font-weight: 600;
                padding: 8px 16px;
                min-width: 160px;
                background-color: {COLORS['bg_light']};
                border: 2px solid {COLORS['accent_dim']};
                border-radius: 8px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['accent']};
            }}
        """)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        config_layout.addWidget(self.type_combo, 1, 1)

        # Row 1 — Case Name
        lbl_case = QLabel("Case Name:")
        lbl_case.setStyleSheet(label_style)
        config_layout.addWidget(lbl_case, 1, 2)
        self.case_input = QLineEdit()
        self.case_input.setPlaceholderText("Optional case name...")
        self.case_input.setMinimumHeight(38)
        config_layout.addWidget(self.case_input, 1, 3)

        # Person search fields (shown when type is Person)
        self.person_fields_group = QGroupBox("👤 Person Search Details")
        person_layout = QGridLayout(self.person_fields_group)
        person_layout.setSpacing(10)

        lbl_name = QLabel("Full Name:")
        lbl_name.setStyleSheet(label_style)
        person_layout.addWidget(lbl_name, 0, 0)
        self.person_name_input = QLineEdit()
        self.person_name_input.setPlaceholderText("e.g. John Michael Smith")
        self.person_name_input.setMinimumHeight(38)
        person_layout.addWidget(self.person_name_input, 0, 1, 1, 3)

        lbl_dob = QLabel("Date of Birth:")
        lbl_dob.setStyleSheet(label_style)
        person_layout.addWidget(lbl_dob, 1, 0)
        self.person_dob_input = QLineEdit()
        self.person_dob_input.setPlaceholderText("e.g. 1990-01-15 or 15/01/1990")
        self.person_dob_input.setMinimumHeight(38)
        person_layout.addWidget(self.person_dob_input, 1, 1)

        lbl_loc = QLabel("Location:")
        lbl_loc.setStyleSheet(label_style)
        person_layout.addWidget(lbl_loc, 1, 2)
        self.person_location_input = QLineEdit()
        self.person_location_input.setPlaceholderText("e.g. Auckland, New Zealand")
        self.person_location_input.setMinimumHeight(38)
        person_layout.addWidget(self.person_location_input, 1, 3)

        self.person_fields_group.hide()  # Hidden by default

        layout.addWidget(config_group)
        layout.addWidget(self.person_fields_group)

        # Module toggles
        modules_group = QGroupBox("Modules")
        modules_layout = QGridLayout(modules_group)
        modules_layout.setSpacing(10)

        self.chk_dns = QCheckBox("DNS Recon")
        self.chk_dns.setChecked(True)
        self.chk_whois = QCheckBox("WHOIS Lookup")
        self.chk_whois.setChecked(True)
        self.chk_ports = QCheckBox("Port Scan")
        self.chk_ports.setChecked(True)
        self.chk_certs = QCheckBox("Cert Transparency")
        self.chk_certs.setChecked(True)
        self.chk_web = QCheckBox("Web Analysis")
        self.chk_web.setChecked(True)
        self.chk_emails = QCheckBox("Email Harvesting")
        self.chk_emails.setChecked(True)
        self.chk_usernames = QCheckBox("Username Search")
        self.chk_usernames.setChecked(False)
        self.chk_quick_ports = QCheckBox("Quick Port Scan (top 20)")
        self.chk_quick_ports.setChecked(True)
        self.chk_subdomains = QCheckBox("Subdomain Brute-force")
        self.chk_subdomains.setChecked(True)

        self.chk_person_search = QCheckBox("Person Search")
        self.chk_person_search.setChecked(True)

        col = 0
        for i, chk in enumerate([self.chk_dns, self.chk_whois, self.chk_ports,
                                   self.chk_certs, self.chk_web, self.chk_emails,
                                   self.chk_usernames, self.chk_quick_ports, self.chk_subdomains,
                                   self.chk_person_search]):
            modules_layout.addWidget(chk, i // 3, i % 3)

        layout.addWidget(modules_group)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.btn_start = QPushButton("⚡ START INVESTIGATION")
        self.btn_start.setObjectName("primary")
        self.btn_start.setFixedSize(250, 48)
        self.btn_start.clicked.connect(self._start_investigation)
        btn_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("✕ Cancel")
        self.btn_cancel.setObjectName("danger")
        self.btn_cancel.setFixedSize(120, 48)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_investigation)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

        # Progress area
        progress_group = QGroupBox("Investigation Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% — %v")
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready to investigate.")
        self.progress_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)

        # Stage status list
        self.stage_list = QTreeWidget()
        self.stage_list.setHeaderLabels(["Stage", "Status", "Duration"])
        self.stage_list.setAlternatingRowColors(True)
        self.stage_list.setMaximumHeight(200)
        progress_layout.addWidget(self.stage_list)

        layout.addWidget(progress_group)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        return tab

    def _build_recon_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel — category tree
        left = QFrame()
        left.setStyleSheet(CARD_STYLE)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)

        cat_label = QLabel("📂 Categories")
        cat_label.setObjectName("subheading")
        left_layout.addWidget(cat_label)

        self.recon_tree = QTreeWidget()
        self.recon_tree.setHeaderHidden(True)
        self.recon_tree.itemClicked.connect(self._recon_category_selected)
        left_layout.addWidget(self.recon_tree)
        splitter.addWidget(left)

        # Right panel — details
        right = QFrame()
        right.setStyleSheet(CARD_STYLE)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        self.recon_detail_label = QLabel("Select a category to view details")
        self.recon_detail_label.setObjectName("subheading")
        right_layout.addWidget(self.recon_detail_label)

        self.recon_table = QTableWidget()
        self.recon_table.setAlternatingRowColors(True)
        self.recon_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.recon_table)

        self.recon_detail_text = QTextEdit()
        self.recon_detail_text.setReadOnly(True)
        self.recon_detail_text.setMaximumHeight(200)
        self.recon_detail_text.setStyleSheet(f"font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px;")
        right_layout.addWidget(self.recon_detail_text)

        splitter.addWidget(right)
        splitter.setSizes([300, 900])

        layout.addWidget(splitter)
        return tab

    def _build_graph_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Graph toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("🕸️ Entity Relationship Graph"))
        toolbar.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        btn_export = QPushButton("📷 Export PNG")
        btn_export.clicked.connect(self._export_graph)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # Graph widget (using matplotlib for now, can be upgraded to QGraphicsScene)
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure
            import networkx as nx

            self.graph_figure = Figure(facecolor=COLORS['bg_darkest'])
            self.graph_canvas = FigureCanvas(self.graph_figure)
            layout.addWidget(self.graph_canvas)
            self._has_graph = True
        except ImportError:
            placeholder = QLabel("📦 Install matplotlib and networkx for graph visualization:\npip install matplotlib networkx")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px; padding: 60px;")
            layout.addWidget(placeholder)
            self._has_graph = False

        # Entity list below graph
        self.entity_table = QTableWidget(0, 4)
        self.entity_table.setHorizontalHeaderLabels(["Type", "Value", "Connections", "Source"])
        self.entity_table.horizontalHeader().setStretchLastSection(True)
        self.entity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.entity_table.setMaximumHeight(200)
        self.entity_table.setAlternatingRowColors(True)
        layout.addWidget(self.entity_table)

        return tab

    def _build_timeline_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        header = QHBoxLayout()
        header.addWidget(QLabel("📅 Investigation Timeline"))
        header.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addLayout(header)

        self.timeline_table = QTableWidget(0, 4)
        self.timeline_table.setHorizontalHeaderLabels(["Date", "Event", "Category", "Source"])
        self.timeline_table.horizontalHeader().setStretchLastSection(True)
        self.timeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.timeline_table.setAlternatingRowColors(True)
        layout.addWidget(self.timeline_table)

        return tab

    def _build_report_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Report header
        header = QHBoxLayout()
        header.addWidget(QLabel("📊 Investigation Report"))
        header.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        btn_json = QPushButton("💾 Export JSON")
        btn_json.clicked.connect(self._export_json)
        header.addWidget(btn_json)

        btn_html = QPushButton("🌐 Export HTML")
        btn_html.clicked.connect(self._export_html)
        header.addWidget(btn_html)

        layout.addLayout(header)

        # Risk score card
        risk_frame = QFrame()
        risk_frame.setStyleSheet(CARD_STYLE)
        risk_layout = QHBoxLayout(risk_frame)

        self.risk_score_label = QLabel("—")
        self.risk_score_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 48px; font-weight: 800; border: none;")
        risk_layout.addWidget(self.risk_score_label)

        risk_detail = QVBoxLayout()
        self.risk_grade_label = QLabel("Risk Score")
        self.risk_grade_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; border: none;")
        risk_detail.addWidget(self.risk_grade_label)
        self.risk_factors_label = QLabel("No investigation data")
        self.risk_factors_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; border: none;")
        self.risk_factors_label.setWordWrap(True)
        risk_detail.addWidget(self.risk_factors_label)
        risk_layout.addLayout(risk_detail)

        risk_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(risk_frame)

        # Summary text
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet(f"font-family: 'JetBrains Mono', monospace; font-size: 13px; background: {COLORS['card']}; border: 1px solid {COLORS['card_border']}; border-radius: 8px; padding: 16px;")
        layout.addWidget(self.report_text)

        return tab

    def _init_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        open_act = QAction("Open Investigation...", self)
        open_act.triggered.connect(self._load_investigation)
        file_menu.addAction(open_act)

        save_act = QAction("Save Investigation...", self)
        save_act.triggered.connect(self._save_investigation)
        file_menu.addAction(save_act)

        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        for label, handler in [
            ("Quick DNS Lookup", self._tool_dns),
            ("Quick Port Scan", self._tool_ports),
            ("Username Search", self._tool_username),
            ("WHOIS Lookup", self._tool_whois),
        ]:
            act = QAction(label, self)
            act.triggered.connect(handler)
            tools_menu.addAction(act)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _init_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {COLORS['accent']}; font-weight: 600;")
        self.status_bar.addWidget(self.status_label)

        self.status_modules = QLabel("Modules: 8 active")
        self.status_modules.setStyleSheet(f"color: {COLORS['text_muted']};")
        self.status_bar.addPermanentWidget(self.status_modules)

    # ==================== INVESTIGATION LOGIC ====================

    def _open_person_search(self):
        """Switch to investigation tab with Person type pre-selected."""
        self.tabs.setCurrentIndex(1)  # Switch to Investigation tab
        self.type_combo.setCurrentText("Person")
        self.header_type_combo.setCurrentText("Person")
        self.person_name_input.setFocus()

    def _on_type_changed(self, type_text: str):
        """Show/hide person-specific fields based on the selected entity type."""
        is_person = type_text in ("Person", "Organization")
        self.person_fields_group.setVisible(is_person)

        # Sync header combo with investigation tab combo
        if self.header_type_combo.currentText() != type_text:
            self.header_type_combo.blockSignals(True)
            self.header_type_combo.setCurrentText(type_text)
            self.header_type_combo.blockSignals(False)

        if is_person:
            self.target_input.setPlaceholderText("Full name or identifier (can also fill in fields below)...")
            self.quick_search.setPlaceholderText("Quick scan: enter a person's name...")
            self.chk_person_search.setChecked(True)
            self.chk_usernames.setChecked(True)
            self.chk_dns.setChecked(False)
            self.chk_whois.setChecked(False)
            self.chk_ports.setChecked(False)
            self.chk_certs.setChecked(False)
            self.chk_web.setChecked(False)
            self.chk_emails.setChecked(False)
        else:
            self.target_input.setPlaceholderText("Enter domain, IP, email, or username...")
            self.quick_search.setPlaceholderText("Quick scan: domain, IP, email, or name...")
            if type_text == "Domain":
                self.chk_dns.setChecked(True)
                self.chk_whois.setChecked(True)
                self.chk_ports.setChecked(True)
                self.chk_certs.setChecked(True)
                self.chk_web.setChecked(True)
                self.chk_emails.setChecked(True)

    def _quick_scan(self):
        target = self.quick_search.text().strip()
        if not target:
            return
        self.target_input.setText(target)

        # Use header type combo if set to Person, otherwise auto-detect
        header_type = self.header_type_combo.currentText()
        if header_type == "Person":
            self.type_combo.setCurrentText("Person")
            self.person_name_input.setText(target)
        elif "@" in target:
            self.type_combo.setCurrentText("Email")
        elif target.replace(".", "").isdigit() or ":" in target:
            self.type_combo.setCurrentText("IP Address")
        elif "." in target:
            self.type_combo.setCurrentText("Domain")
        elif " " in target:
            # Name-like input (has spaces) → person search
            self.type_combo.setCurrentText("Person")
            self.person_name_input.setText(target)
        else:
            self.type_combo.setCurrentText("Username")

        self.tabs.setCurrentIndex(1)  # Switch to investigation tab
        self._start_investigation()

    def _start_investigation(self):
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Error", "Please enter a target to investigate.")
            return

        # Build config
        type_map = {
            "Domain": EntityType.DOMAIN,
            "IP Address": EntityType.IP,
            "Email": EntityType.EMAIL,
            "Username": EntityType.USERNAME,
            "Person": EntityType.PERSON,
            "Organization": EntityType.ORGANIZATION,
        }

        entity_type = type_map.get(self.type_combo.currentText(), EntityType.DOMAIN)

        # Use person name as target if person search and name is provided
        person_name = self.person_name_input.text().strip()
        if entity_type in (EntityType.PERSON, EntityType.ORGANIZATION) and person_name:
            target = person_name

        config = InvestigationConfig(
            target=target,
            entity_type=entity_type,
            run_dns=self.chk_dns.isChecked(),
            run_whois=self.chk_whois.isChecked(),
            run_ports=self.chk_ports.isChecked(),
            run_certs=self.chk_certs.isChecked(),
            run_web=self.chk_web.isChecked(),
            run_emails=self.chk_emails.isChecked(),
            run_usernames=self.chk_usernames.isChecked(),
            run_person_search=self.chk_person_search.isChecked(),
            port_scan_quick=self.chk_quick_ports.isChecked(),
            subdomain_scan=self.chk_subdomains.isChecked(),
            case_name=self.case_input.text().strip(),
            person_name=person_name,
            date_of_birth=self.person_dob_input.text().strip(),
            location=self.person_location_input.text().strip(),
        )

        # UI state
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.stage_list.clear()
        self.status_label.setText(f"Investigating {target}...")

        # Start worker
        self.worker = InvestigationWorker(config)
        self.worker.progress.connect(self._on_progress)
        self.worker.stage_changed.connect(self._on_stage_changed)
        self.worker.finished.connect(self._on_investigation_complete)
        self.worker.error.connect(self._on_investigation_error)
        self.worker.start()

    def _cancel_investigation(self):
        if self.worker:
            self.worker.cancel()
            self.progress_label.setText("Cancelling...")
            self.btn_cancel.setEnabled(False)

    def _on_progress(self, message: str, percent: int):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def _on_stage_changed(self, stage: str, status: str):
        stage_names = {
            "dns_recon": "🌐 DNS Reconnaissance",
            "whois_lookup": "📋 WHOIS Lookup",
            "port_scan": "🔌 Port Scanning",
            "cert_transparency": "🔒 Cert Transparency",
            "web_analysis": "🕸️ Web Analysis",
            "email_harvest": "📧 Email Harvesting",
            "username_check": "👤 Username Search",
            "person_search": "👤 Person Search",
            "entity_resolution": "🔗 Entity Resolution",
            "risk_scoring": "⚠️ Risk Scoring",
            "report_generation": "📊 Report Generation",
            "complete": "✅ Complete",
        }

        display_name = stage_names.get(stage, stage)
        status_icon = "🟢" if status == "complete" else "🔵" if status == "running" else "⚪"

        # Update or add to stage list
        found = False
        for i in range(self.stage_list.topLevelItemCount()):
            item = self.stage_list.topLevelItem(i)
            if item.text(0) == display_name:
                item.setText(1, f"{status_icon} {status}")
                found = True
                break
        if not found:
            item = QTreeWidgetItem([display_name, f"{status_icon} {status}", ""])
            self.stage_list.addTopLevelItem(item)

    def _on_investigation_complete(self, result: InvestigationResult):
        self.current_result = result
        self.investigation_history.append(result)
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Investigation complete — {result.duration_seconds:.1f}s")
        self.status_label.setText(f"✅ Complete: {result.target}")

        # Update all tabs
        self._populate_recon_tab(result)
        self._populate_graph_tab(result)
        self._populate_timeline_tab(result)
        self._populate_report_tab(result)
        self._update_dashboard(result)

        # Switch to recon tab
        self.tabs.setCurrentIndex(2)

    def _on_investigation_error(self, error: str):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_label.setText(f"Error: {error}")
        self.status_label.setText("❌ Investigation failed")
        QMessageBox.critical(self, "Investigation Error", f"Investigation failed:\n{error}")

    # ==================== TAB POPULATION ====================

    def _update_dashboard(self, result: InvestigationResult):
        count = len(self.investigation_history)
        self.stat_investigations.update_value(str(count))
        self.stat_entities.update_value(str(len(result.entities)))
        self.stat_risk.update_value(f"{result.risk_score:.0f}", "/100")
        open_ports = result.ports.get("open_port_count", 0)
        self.stat_ports.update_value(str(open_ports))

        # Add to recent table
        row = self.recent_table.rowCount()
        self.recent_table.insertRow(row)
        self.recent_table.setItem(row, 0, QTableWidgetItem(result.target))
        self.recent_table.setItem(row, 1, QTableWidgetItem(result.entity_type))
        risk_item = QTableWidgetItem(f"{result.risk_score:.0f}/100")
        self.recent_table.setItem(row, 2, risk_item)
        self.recent_table.setItem(row, 3, QTableWidgetItem(str(len(result.entities))))
        self.recent_table.setItem(row, 4, QTableWidgetItem(datetime.now().strftime("%Y-%m-%d %H:%M")))

        # Hide welcome message
        self.welcome_label.hide()

    def _populate_recon_tab(self, result: InvestigationResult):
        self.recon_tree.clear()

        categories = {
            "🌐 DNS Records": ("dns", result.dns),
            "📋 WHOIS Data": ("whois", result.whois),
            "🌍 IP Information": ("ip_info", result.ip_info),
            "🔌 Open Ports": ("ports", result.ports),
            "🔒 Certificates": ("certificates", result.certificates),
            "🕸️ Web Analysis": ("web", result.web),
            "📧 Emails": ("emails", result.emails),
            "👤 Usernames": ("usernames", result.usernames),
            "🧑 Person Data": ("person_data", result.person_data),
        }

        for label, (key, data) in categories.items():
            if data:
                item = QTreeWidgetItem([label])
                item.setData(0, Qt.ItemDataRole.UserRole, (key, data))
                self.recon_tree.addTopLevelItem(item)

                # Add sub-items for quick reference
                if key == "dns":
                    for sub_key in ["ip_addresses", "nameservers", "mail_servers", "subdomains"]:
                        items = data.get(sub_key, [])
                        if items:
                            child = QTreeWidgetItem([f"  {sub_key} ({len(items)})"])
                            item.addChild(child)
                elif key == "ports":
                    count = data.get("open_port_count", 0)
                    child = QTreeWidgetItem([f"  {count} open ports"])
                    item.addChild(child)
                elif key == "web":
                    techs = data.get("technologies", [])
                    if techs:
                        child = QTreeWidgetItem([f"  Technologies: {', '.join(techs[:5])}"])
                        item.addChild(child)

        self.recon_tree.expandAll()

    def _recon_category_selected(self, item: QTreeWidgetItem, column: int):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            # Check parent
            parent = item.parent()
            if parent:
                data = parent.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        key, content = data
        self.recon_detail_label.setText(item.text(0))

        # Show as table for structured data
        if key == "ports":
            open_ports = content.get("open_ports", [])
            self.recon_table.setColumnCount(5)
            self.recon_table.setHorizontalHeaderLabels(["Port", "Service", "State", "Banner", "Response (ms)"])
            self.recon_table.setRowCount(len(open_ports))
            for i, port in enumerate(open_ports):
                self.recon_table.setItem(i, 0, QTableWidgetItem(str(port.get("port", ""))))
                self.recon_table.setItem(i, 1, QTableWidgetItem(port.get("service", "")))
                self.recon_table.setItem(i, 2, QTableWidgetItem(port.get("state", "")))
                self.recon_table.setItem(i, 3, QTableWidgetItem(port.get("banner", "")[:80]))
                self.recon_table.setItem(i, 4, QTableWidgetItem(str(port.get("response_time_ms", ""))))
        elif key in ("dns",):
            records = content.get("records", [])
            self.recon_table.setColumnCount(4)
            self.recon_table.setHorizontalHeaderLabels(["Type", "Name", "Value", "TTL"])
            self.recon_table.setRowCount(len(records))
            for i, rec in enumerate(records):
                self.recon_table.setItem(i, 0, QTableWidgetItem(rec.get("type", "")))
                self.recon_table.setItem(i, 1, QTableWidgetItem(rec.get("name", "")))
                self.recon_table.setItem(i, 2, QTableWidgetItem(rec.get("value", "")))
                self.recon_table.setItem(i, 3, QTableWidgetItem(str(rec.get("ttl", ""))))
        else:
            self.recon_table.setRowCount(0)
            self.recon_table.setColumnCount(0)

        # Always show raw JSON
        self.recon_detail_text.setText(json.dumps(content, indent=2, default=str))

    def _populate_graph_tab(self, result: InvestigationResult):
        if not self._has_graph or not result.entities:
            return

        try:
            import networkx as nx

            G = nx.Graph()

            # Color mapping
            type_colors = {
                "domain": COLORS['accent'], "ip": COLORS['orange'],
                "email": COLORS['green'], "nameserver": COLORS['purple'],
                "mail_server": COLORS['yellow'], "subdomain": "#66bbff",
                "service": COLORS['red'], "social_profile": "#ff66cc",
                "registrar": "#aaaaaa", "organization": COLORS['orange'],
                "username": COLORS['accent'],
            }

            for entity in result.entities:
                G.add_node(entity["id"], label=entity.get("label", str(entity["id"])),
                          type=entity.get("type", "unknown"))

            for rel in result.relationships:
                G.add_edge(rel["source"], rel["target"], label=rel.get("type", ""))

            # Draw
            self.graph_figure.clear()
            ax = self.graph_figure.add_subplot(111)
            ax.set_facecolor(COLORS['bg_darkest'])

            if len(G.nodes()) > 0:
                pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
                node_colors = [type_colors.get(G.nodes[n].get("type", ""), COLORS['text_muted']) for n in G.nodes()]
                labels = {n: G.nodes[n].get("label", str(n))[:20] for n in G.nodes()}

                nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=300, alpha=0.9)
                nx.draw_networkx_edges(G, pos, ax=ax, edge_color=COLORS['border'], alpha=0.4, width=1)
                nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=7, font_color=COLORS['text_primary'])

            ax.set_xlim(ax.get_xlim()[0] - 0.1, ax.get_xlim()[1] + 0.1)
            ax.set_ylim(ax.get_ylim()[0] - 0.1, ax.get_ylim()[1] + 0.1)
            ax.axis("off")
            self.graph_figure.tight_layout()
            self.graph_canvas.draw()

            # Entity table
            self.entity_table.setRowCount(len(result.entities))
            for i, entity in enumerate(result.entities):
                self.entity_table.setItem(i, 0, QTableWidgetItem(entity.get("type", "")))
                self.entity_table.setItem(i, 1, QTableWidgetItem(entity.get("value", "")))
                connections = sum(1 for r in result.relationships if r["source"] == entity["id"] or r["target"] == entity["id"])
                self.entity_table.setItem(i, 2, QTableWidgetItem(str(connections)))
                self.entity_table.setItem(i, 3, QTableWidgetItem("primary" if entity.get("is_target") else "derived"))

        except Exception as e:
            logger.error(f"Graph render failed: {e}")

    def _populate_timeline_tab(self, result: InvestigationResult):
        self.timeline_table.setRowCount(len(result.timeline))
        for i, event in enumerate(result.timeline):
            self.timeline_table.setItem(i, 0, QTableWidgetItem(event.get("date", "")))
            self.timeline_table.setItem(i, 1, QTableWidgetItem(event.get("event", "")))
            self.timeline_table.setItem(i, 2, QTableWidgetItem(event.get("category", "")))
            self.timeline_table.setItem(i, 3, QTableWidgetItem(event.get("source", "")))

    def _populate_report_tab(self, result: InvestigationResult):
        # Risk score
        score = result.risk_score
        color = COLORS['green'] if score < 30 else COLORS['yellow'] if score < 60 else COLORS['orange'] if score < 80 else COLORS['red']
        self.risk_score_label.setText(f"{score:.0f}")
        self.risk_score_label.setStyleSheet(f"color: {color}; font-size: 48px; font-weight: 800; border: none;")

        grade = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH" if score < 80 else "CRITICAL"
        self.risk_grade_label.setText(f"Risk Level: {grade}")

        factors_text = "\n".join(f"⚠ {f['factor']}: {f.get('detail', '')}" for f in result.risk_factors)
        self.risk_factors_label.setText(factors_text or "No significant risk factors found.")

        # Summary
        self.report_text.setText(result.summary)

    # ==================== EXPORT ====================

    def _export_json(self):
        if not self.current_result:
            QMessageBox.warning(self, "No Data", "Run an investigation first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", f"osint_{self.current_result.target}.json", "JSON (*.json)")
        if path:
            with open(path, "w") as f:
                f.write(self.current_result.to_json())
            self.status_label.setText(f"Exported to {path}")

    def _export_html(self):
        if not self.current_result:
            QMessageBox.warning(self, "No Data", "Run an investigation first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML", f"osint_{self.current_result.target}.html", "HTML (*.html)")
        if path:
            html = self._generate_html_report(self.current_result)
            with open(path, "w") as f:
                f.write(html)
            self.status_label.setText(f"Exported to {path}")

    def _export_graph(self):
        if self._has_graph:
            path, _ = QFileDialog.getSaveFileName(self, "Export Graph", "entity_graph.png", "PNG (*.png)")
            if path:
                self.graph_figure.savefig(path, dpi=150, facecolor=COLORS['bg_darkest'])
                self.status_label.setText(f"Graph exported to {path}")

    def _generate_html_report(self, result: InvestigationResult) -> str:
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>OSINT Report — {result.target}</title>
    <style>
        body {{ font-family: Inter, sans-serif; background: #0a0e17; color: #e8edf3; padding: 40px; }}
        h1 {{ color: #00d4ff; }} h2 {{ color: #8899aa; border-bottom: 1px solid #1e3048; padding-bottom: 8px; }}
        .card {{ background: #131c28; border: 1px solid #1e3048; border-radius: 12px; padding: 20px; margin: 16px 0; }}
        .risk {{ font-size: 48px; font-weight: 800; }}
        .risk.low {{ color: #00e676; }} .risk.medium {{ color: #ffbe0b; }}
        .risk.high {{ color: #ff8c42; }} .risk.critical {{ color: #ff4757; }}
        table {{ width: 100%; border-collapse: collapse; }} th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #1e3048; }}
        th {{ color: #8899aa; font-size: 11px; text-transform: uppercase; }}
        pre {{ background: #0f1923; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 12px; }}
    </style>
</head>
<body>
    <h1>⚡ OSINT Report: {result.target}</h1>
    <div class="card">
        <span class="risk {'low' if result.risk_score < 30 else 'medium' if result.risk_score < 60 else 'high' if result.risk_score < 80 else 'critical'}">{result.risk_score:.0f}</span>
        <span>/100 Risk Score</span>
    </div>
    <h2>Summary</h2>
    <pre>{result.summary}</pre>
    <h2>Entities ({len(result.entities)})</h2>
    <table><tr><th>Type</th><th>Value</th></tr>
    {''.join(f"<tr><td>{e.get('type','')}</td><td>{e.get('value','')}</td></tr>" for e in result.entities[:50])}
    </table>
    <h2>Full Data</h2>
    <pre>{json.dumps(result.to_dict(), indent=2, default=str)[:50000]}</pre>
</body>
</html>"""

    # ==================== SAVE/LOAD ====================

    def _save_investigation(self):
        if not self.current_result:
            QMessageBox.warning(self, "No Data", "Run an investigation first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Investigation", f"case_{self.current_result.target}.osint", "OSINT Files (*.osint)")
        if path:
            with open(path, "w") as f:
                json.dump(self.current_result.to_dict(), f, indent=2, default=str)
            self.status_label.setText(f"Investigation saved to {path}")

    def _load_investigation(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Investigation", "", "OSINT Files (*.osint);;JSON (*.json)")
        if path:
            with open(path, "r") as f:
                data = json.load(f)
            self.current_result = InvestigationResult(**{k: v for k, v in data.items() if k in InvestigationResult.__dataclass_fields__})
            self._populate_recon_tab(self.current_result)
            self._populate_graph_tab(self.current_result)
            self._populate_timeline_tab(self.current_result)
            self._populate_report_tab(self.current_result)
            self._update_dashboard(self.current_result)
            self.status_label.setText(f"Loaded investigation: {self.current_result.target}")
            self.tabs.setCurrentIndex(2)

    def _load_selected_investigation(self, index):
        row = index.row()
        if row < len(self.investigation_history):
            result = self.investigation_history[row]
            self.current_result = result
            self._populate_recon_tab(result)
            self._populate_graph_tab(result)
            self._populate_timeline_tab(result)
            self._populate_report_tab(result)
            self.tabs.setCurrentIndex(2)

    # ==================== QUICK TOOLS ====================

    def _tool_dns(self):
        self.target_input.setText(self.quick_search.text().strip())
        self.type_combo.setCurrentText("Domain")
        # Only enable DNS
        for chk in [self.chk_dns, self.chk_whois, self.chk_ports, self.chk_certs,
                     self.chk_web, self.chk_emails, self.chk_usernames]:
            chk.setChecked(False)
        self.chk_dns.setChecked(True)
        self.tabs.setCurrentIndex(1)

    def _tool_ports(self):
        self.target_input.setText(self.quick_search.text().strip())
        for chk in [self.chk_dns, self.chk_whois, self.chk_ports, self.chk_certs,
                     self.chk_web, self.chk_emails, self.chk_usernames]:
            chk.setChecked(False)
        self.chk_ports.setChecked(True)
        self.tabs.setCurrentIndex(1)

    def _tool_username(self):
        self.target_input.setText(self.quick_search.text().strip())
        self.type_combo.setCurrentText("Username")
        for chk in [self.chk_dns, self.chk_whois, self.chk_ports, self.chk_certs,
                     self.chk_web, self.chk_emails, self.chk_usernames]:
            chk.setChecked(False)
        self.chk_usernames.setChecked(True)
        self.tabs.setCurrentIndex(1)

    def _tool_whois(self):
        self.target_input.setText(self.quick_search.text().strip())
        for chk in [self.chk_dns, self.chk_whois, self.chk_ports, self.chk_certs,
                     self.chk_web, self.chk_emails, self.chk_usernames]:
            chk.setChecked(False)
        self.chk_whois.setChecked(True)
        self.tabs.setCurrentIndex(1)

    def _show_about(self):
        QMessageBox.about(self, "About OSINT Framework",
            "⚡ OSINT Framework v2.0\n\n"
            "Self-contained intelligence platform.\n"
            "All recon modules use free, public data sources.\n"
            "No API keys required.\n\n"
            "Modules:\n"
            "  • DNS Intelligence\n"
            "  • WHOIS & IP Geolocation\n"
            "  • Port Scanning & Banner Grabbing\n"
            "  • Certificate Transparency\n"
            "  • Web Technology Fingerprinting\n"
            "  • Email Harvesting\n"
            "  • Username Enumeration\n"
            "  • Entity Graph Visualization\n"
        )
