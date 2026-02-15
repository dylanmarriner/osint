"""
Investigation Wizard - PyQt Desktop UI Component

Multi-step wizard for configuring and starting OSINT investigations.
Replaces InvestigationWizard.vue with native PyQt widgets.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QButtonGroup, QRadioButton, QCheckBox, QLineEdit, QComboBox,
    QProgressBar, QListWidget, QListWidgetItem, QScrollArea, QWidget,
    QMessageBox, QSpinBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from typing import List, Dict, Any
import logging


class InvestigationWizard(QDialog):
    """Multi-step investigation configuration wizard."""
    
    investigation_started = pyqtSignal(dict)  # Emits investigation config
    
    ENTITY_TYPES = ["Person", "Company", "Domain", "Email", "Phone", "Username"]
    
    DATA_SOURCES = {
        "Search Engines": [
            {"id": "google", "name": "Google", "confidence": 85, "rate_limit": 100},
            {"id": "bing", "name": "Bing", "confidence": 75, "rate_limit": 100},
        ],
        "Social Media": [
            {"id": "facebook", "name": "Facebook", "confidence": 90, "rate_limit": 50},
            {"id": "twitter", "name": "Twitter", "confidence": 85, "rate_limit": 450},
            {"id": "instagram", "name": "Instagram", "confidence": 80, "rate_limit": 200},
        ],
        "People Search": [
            {"id": "linkedin", "name": "LinkedIn", "confidence": 92, "rate_limit": 100},
            {"id": "pipl", "name": "Pipl", "confidence": 88, "rate_limit": 60},
        ],
        "Public Records": [
            {"id": "pacer", "name": "PACER (Court Records)", "confidence": 95, "rate_limit": 200},
            {"id": "sec", "name": "SEC EDGAR", "confidence": 99, "rate_limit": 1000},
        ],
        "Domain/IP": [
            {"id": "whois", "name": "WHOIS", "confidence": 98, "rate_limit": 1000},
            {"id": "dns", "name": "DNS Records", "confidence": 100, "rate_limit": 1000},
        ],
    }
    
    ANALYSIS_OPTIONS = {
        "timeline": "Timeline Construction",
        "networkGraph": "Network Graph Analysis",
        "riskAssessment": "Risk Assessment",
        "behavioralAnalysis": "Behavioral Analysis",
        "predictiveInsights": "Predictive Insights",
        "trendAnalysis": "Trend Analysis"
    }
    
    REPORT_FORMATS = ["PDF", "HTML", "JSON", "CSV"]
    REPORT_SECTIONS = ["Executive Summary", "Detailed Findings", "Timeline", "Network Graph", "Risk Assessment"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OSINT Investigation Wizard")
        self.setGeometry(100, 100, 800, 700)
        self.setModal(True)
        
        self.logger = logging.getLogger(__name__)
        
        # Wizard state
        self.current_step = 1
        self.total_steps = 5
        self.selected_entity_type = self.ENTITY_TYPES[0]
        self.selected_entity = None
        self.search_results = []
        self.selected_sources = []
        self.analysis_options = {key: False for key in self.ANALYSIS_OPTIONS}
        self.report_format = "PDF"
        self.report_contents = []
        self.report_options = {"encrypt": False, "anonymize": False, "watermark": False}
        self.accepted_terms = False
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize wizard UI."""
        layout = QVBoxLayout()
        
        # Header with progress
        header_layout = QHBoxLayout()
        self.progress_label = QLabel(f"Step {self.current_step} of {self.total_steps}")
        self.progress_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(int((self.current_step / self.total_steps) * 100))
        header_layout.addWidget(QLabel("Investigation Wizard"))
        header_layout.addStretch()
        header_layout.addWidget(self.progress_label)
        layout.addLayout(header_layout)
        layout.addWidget(self.progress_bar)
        
        # Step container (will swap steps)
        self.step_container = QWidget()
        self.step_layout = QVBoxLayout(self.step_container)
        layout.addWidget(self.step_container)
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        self.prev_button = QPushButton("< Previous")
        self.prev_button.clicked.connect(self.previous_step)
        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(self.next_step)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.prev_button)
        button_layout.addStretch()
        button_layout.addWidget(self.next_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.show_step(1)
    
    def show_step(self, step_num: int):
        """Display specific wizard step."""
        # Clear current step
        while self.step_layout.count():
            self.step_layout.takeAt(0).widget().deleteLater()
        
        self.current_step = step_num
        self.progress_label.setText(f"Step {step_num} of {self.total_steps}")
        self.progress_bar.setValue(int((step_num / self.total_steps) * 100))
        
        # Update button states
        self.prev_button.setEnabled(step_num > 1)
        self.next_button.setText("Start Investigation" if step_num == self.total_steps else "Next >")
        
        if step_num == 1:
            self.show_step_1()
        elif step_num == 2:
            self.show_step_2()
        elif step_num == 3:
            self.show_step_3()
        elif step_num == 4:
            self.show_step_4()
        elif step_num == 5:
            self.show_step_5()
    
    def show_step_1(self):
        """Entity Type & Search Selection."""
        title = QLabel("Who are you investigating?")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.step_layout.addWidget(title)
        
        # Entity type buttons
        type_group = QGroupBox("Select Entity Type")
        type_layout = QHBoxLayout()
        self.entity_button_group = QButtonGroup()
        for i, entity_type in enumerate(self.ENTITY_TYPES):
            btn = QPushButton(entity_type)
            btn.setCheckable(True)
            if entity_type == self.selected_entity_type:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, et=entity_type: self.select_entity_type(et))
            type_layout.addWidget(btn)
            self.entity_button_group.addButton(btn, i)
        type_group.setLayout(type_layout)
        self.step_layout.addWidget(type_group)
        
        # Search form
        search_group = QGroupBox(f"Search for {self.selected_entity_type.lower()}")
        search_layout = QVBoxLayout()
        
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel(f"Enter {self.selected_entity_type.lower()}:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(f"e.g., name, email, username, etc.")
        self.search_input.returnPressed.connect(self.search_entity)
        search_input_layout.addWidget(self.search_input)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_entity)
        search_input_layout.addWidget(self.search_button)
        search_layout.addLayout(search_input_layout)
        
        # Search results
        self.results_list = QListWidget()
        self.results_list.itemSelectionChanged.connect(self.on_result_selected)
        search_layout.addWidget(QLabel("Results:"))
        search_layout.addWidget(self.results_list)
        
        search_group.setLayout(search_layout)
        self.step_layout.addWidget(search_group)
        self.step_layout.addStretch()
    
    def show_step_2(self):
        """Data Source Selection."""
        title = QLabel("Which data sources to query?")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.step_layout.addWidget(title)
        
        self.step_layout.addWidget(QLabel("Select data sources to search (more sources = more comprehensive results)"))
        
        # Scrollable source list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout()
        
        self.source_checkboxes = {}
        for category, sources in self.DATA_SOURCES.items():
            category_group = QGroupBox(category)
            category_layout = QVBoxLayout()
            for source in sources:
                checkbox_layout = QHBoxLayout()
                checkbox = QCheckBox(source["name"])
                checkbox.setChecked(source["id"] in self.selected_sources)
                checkbox.stateChanged.connect(
                    lambda state, sid=source["id"]: self.toggle_source(sid, state)
                )
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.addWidget(QLabel(f"{source['confidence']}% | {source['rate_limit']}/hr"))
                checkbox_layout.addStretch()
                category_layout.addLayout(checkbox_layout)
                self.source_checkboxes[source["id"]] = checkbox
            category_group.setLayout(category_layout)
            container_layout.addWidget(category_group)
        
        container.setLayout(container_layout)
        scroll.setWidget(container)
        self.step_layout.addWidget(scroll)
        
        # Summary
        self.source_summary = QLabel(f"{len(self.selected_sources)} source(s) selected")
        self.step_layout.addWidget(self.source_summary)
    
    def show_step_3(self):
        """Analysis Options."""
        title = QLabel("What analysis to perform?")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.step_layout.addWidget(title)
        
        self.analysis_checkboxes = {}
        for key, name in self.ANALYSIS_OPTIONS.items():
            checkbox = QCheckBox(name)
            checkbox.setChecked(self.analysis_options.get(key, False))
            checkbox.stateChanged.connect(
                lambda state, k=key: self.toggle_analysis(k, state)
            )
            self.step_layout.addWidget(checkbox)
            self.analysis_checkboxes[key] = checkbox
        
        self.step_layout.addStretch()
    
    def show_step_4(self):
        """Report Configuration."""
        title = QLabel("Report Generation Options")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.step_layout.addWidget(title)
        
        # Format selection
        format_group = QGroupBox("Report Format")
        format_layout = QVBoxLayout()
        self.format_buttons = {}
        for fmt in self.REPORT_FORMATS:
            radio = QRadioButton(fmt)
            radio.setChecked(fmt == self.report_format)
            radio.toggled.connect(lambda checked, f=fmt: setattr(self, 'report_format', f) if checked else None)
            format_layout.addWidget(radio)
            self.format_buttons[fmt] = radio
        format_group.setLayout(format_layout)
        self.step_layout.addWidget(format_group)
        
        # Contents selection
        contents_group = QGroupBox("Report Contents")
        contents_layout = QVBoxLayout()
        self.content_checkboxes = {}
        for section in self.REPORT_SECTIONS:
            checkbox = QCheckBox(section)
            checkbox.stateChanged.connect(
                lambda state, s=section: self.toggle_report_content(s, state)
            )
            contents_layout.addWidget(checkbox)
            self.content_checkboxes[section] = checkbox
        contents_group.setLayout(contents_layout)
        self.step_layout.addWidget(contents_group)
        
        # Privacy options
        privacy_group = QGroupBox("Privacy & Security")
        privacy_layout = QVBoxLayout()
        self.encrypt_checkbox = QCheckBox("Encrypt report (password-protected PDF)")
        self.anonymize_checkbox = QCheckBox("Anonymize sensitive data")
        self.watermark_checkbox = QCheckBox("Add watermark to prevent copying")
        privacy_layout.addWidget(self.encrypt_checkbox)
        privacy_layout.addWidget(self.anonymize_checkbox)
        privacy_layout.addWidget(self.watermark_checkbox)
        privacy_group.setLayout(privacy_layout)
        self.step_layout.addWidget(privacy_group)
        
        self.step_layout.addStretch()
    
    def show_step_5(self):
        """Review and Confirmation."""
        title = QLabel("Review and Confirm")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.step_layout.addWidget(title)
        
        # Entity info
        entity_group = QGroupBox("Entity")
        entity_layout = QVBoxLayout()
        entity_layout.addWidget(QLabel(f"Type: {self.selected_entity_type}"))
        entity_layout.addWidget(QLabel(f"Target: {self.selected_entity or 'N/A'}"))
        entity_group.setLayout(entity_layout)
        self.step_layout.addWidget(entity_group)
        
        # Sources
        sources_group = QGroupBox(f"Data Sources ({len(self.selected_sources)})")
        sources_layout = QVBoxLayout()
        source_names = []
        for category, sources in self.DATA_SOURCES.items():
            for source in sources:
                if source["id"] in self.selected_sources:
                    source_names.append(source["name"])
        sources_layout.addWidget(QLabel(", ".join(source_names) or "None selected"))
        sources_group.setLayout(sources_layout)
        self.step_layout.addWidget(sources_group)
        
        # Analysis
        analysis_group = QGroupBox("Analysis Types")
        analysis_layout = QVBoxLayout()
        for key, name in self.ANALYSIS_OPTIONS.items():
            if self.analysis_options.get(key, False):
                analysis_layout.addWidget(QLabel(f"• {name}"))
        analysis_group.setLayout(analysis_layout)
        self.step_layout.addWidget(analysis_group)
        
        # Report settings
        report_group = QGroupBox("Report Settings")
        report_layout = QVBoxLayout()
        report_layout.addWidget(QLabel(f"Format: {self.report_format}"))
        report_layout.addWidget(QLabel(f"Encryption: {'Yes' if self.encrypt_checkbox.isChecked() else 'No'}"))
        report_group.setLayout(report_layout)
        self.step_layout.addWidget(report_group)
        
        # Terms acceptance
        self.terms_checkbox = QCheckBox(
            "I acknowledge that I have lawful authorization to investigate this entity"
        )
        self.terms_checkbox.stateChanged.connect(self.update_button_states)
        self.step_layout.addWidget(self.terms_checkbox)
        
        self.step_layout.addStretch()
    
    def select_entity_type(self, entity_type: str):
        """Select entity type."""
        self.selected_entity_type = entity_type
    
    def search_entity(self):
        """Perform entity search via API."""
        query = self.search_input.text().strip()
        if not query:
            return
        
        # For now, mock search results
        # In production, call API: /api/search
        self.search_results = [
            {
                "id": query,
                "name": query,
                "type": self.selected_entity_type,
                "details": f"{self.selected_entity_type} - Found in 3 data sources",
                "confidence": 0.85
            }
        ]
        
        self.results_list.clear()
        for result in self.search_results:
            item = QListWidgetItem(f"{result['name']} ({result['confidence']*100:.0f}%)")
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.results_list.addItem(item)
    
    def on_result_selected(self):
        """Handle result selection."""
        if self.results_list.selectedItems():
            item = self.results_list.selectedItems()[0]
            result = item.data(Qt.ItemDataRole.UserRole)
            self.selected_entity = result["id"]
    
    def toggle_source(self, source_id: str, state):
        """Toggle data source selection."""
        if state == Qt.CheckState.Checked.value:
            if source_id not in self.selected_sources:
                self.selected_sources.append(source_id)
        else:
            if source_id in self.selected_sources:
                self.selected_sources.remove(source_id)
        self.source_summary.setText(f"{len(self.selected_sources)} source(s) selected")
    
    def toggle_analysis(self, key: str, state):
        """Toggle analysis option."""
        self.analysis_options[key] = state == Qt.CheckState.Checked.value
    
    def toggle_report_content(self, section: str, state):
        """Toggle report content section."""
        if state == Qt.CheckState.Checked.value:
            if section not in self.report_contents:
                self.report_contents.append(section)
        else:
            if section in self.report_contents:
                self.report_contents.remove(section)
    
    def update_button_states(self):
        """Update button states based on wizard state."""
        can_proceed = self.current_step < self.total_steps
        if self.current_step == 1:
            can_proceed = bool(self.selected_entity)
        elif self.current_step == 2:
            can_proceed = len(self.selected_sources) > 0
        elif self.current_step == 5:
            can_proceed = self.terms_checkbox.isChecked()
        self.next_button.setEnabled(can_proceed)
    
    def next_step(self):
        """Move to next step or start investigation."""
        if self.current_step < self.total_steps:
            self.show_step(self.current_step + 1)
        else:
            self.start_investigation()
    
    def previous_step(self):
        """Move to previous step."""
        if self.current_step > 1:
            self.show_step(self.current_step - 1)
    
    def start_investigation(self):
        """Start the investigation with configured parameters."""
        if not self.accepted_terms and not self.terms_checkbox.isChecked():
            QMessageBox.warning(self, "Terms Not Accepted", 
                              "Please accept the terms to proceed")
            return
        
        config = {
            "entity_type": self.selected_entity_type,
            "entity_id": self.selected_entity,
            "sources": self.selected_sources,
            "analysis": self.analysis_options,
            "report": {
                "format": self.report_format,
                "contents": self.report_contents,
                "encrypt": self.encrypt_checkbox.isChecked(),
                "anonymize": self.anonymize_checkbox.isChecked(),
                "watermark": self.watermark_checkbox.isChecked()
            }
        }
        
        self.investigation_started.emit(config)
        self.accept()
