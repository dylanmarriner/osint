"""
Main Application Window - PyQt Desktop OSINT Framework

Desktop application bundling all UI components.
Replaces Vue SPA with native PyQt desktop application.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction
import sys
import logging
from typing import Dict, Any

from .investigation_wizard import InvestigationWizard
from .risk_dashboard import RiskDashboard
from .network_graph import NetworkGraphWidget
from .timeline_viewer import TimelineViewer


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OSINT Framework")
        self.setGeometry(100, 100, 1400, 900)
        
        self.logger = logging.getLogger(__name__)
        
        # Investigation state
        self.current_investigation = None
        self.investigation_results = None
        
        self.init_ui()
        self.init_menu()
        self.init_status_bar()
    
    def init_ui(self):
        """Initialize main UI."""
        # Central widget with tabs
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar/Quick Actions
        toolbar_layout = QHBoxLayout()
        
        self.new_investigation_button = self.create_button(
            "New Investigation",
            self.start_new_investigation
        )
        self.load_results_button = self.create_button(
            "Load Results",
            self.load_investigation_results
        )
        self.export_button = self.create_button(
            "Export Report",
            self.export_results
        )
        self.settings_button = self.create_button(
            "Settings",
            self.open_settings
        )
        
        toolbar_layout.addWidget(self.new_investigation_button)
        toolbar_layout.addWidget(self.load_results_button)
        toolbar_layout.addWidget(self.export_button)
        toolbar_layout.addWidget(self.settings_button)
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # Tab widget for different views
        self.tabs = QTabWidget()
        
        # Tab 1: Dashboard (initial view)
        self.dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout()
        
        welcome_label = QFont()
        welcome_label = "Welcome to OSINT Framework"
        
        dashboard_widget = QWidget()
        dashboard_widget_layout = QVBoxLayout()
        
        from PyQt6.QtWidgets import QLabel
        welcome = QLabel("Welcome to OSINT Framework Desktop")
        welcome.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        dashboard_widget_layout.addWidget(welcome)
        
        instructions = QLabel(
            "Click 'New Investigation' to start an investigation, or load previous results."
        )
        dashboard_widget_layout.addWidget(instructions)
        dashboard_widget_layout.addStretch()
        
        dashboard_widget.setLayout(dashboard_widget_layout)
        dashboard_layout.addWidget(dashboard_widget)
        self.dashboard_tab.setLayout(dashboard_layout)
        
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        
        # Tab 2: Risk Assessment
        self.risk_dashboard = RiskDashboard()
        self.tabs.addTab(self.risk_dashboard, "Risk Assessment")
        
        # Tab 3: Network Graph
        self.network_graph = NetworkGraphWidget()
        self.network_graph.node_selected.connect(self.on_node_selected)
        self.tabs.addTab(self.network_graph, "Network Graph")
        
        # Tab 4: Timeline
        self.timeline_viewer = TimelineViewer()
        self.timeline_viewer.event_selected.connect(self.on_event_selected)
        self.tabs.addTab(self.timeline_viewer, "Timeline")
        
        # Tab 5: Results/Export
        self.results_tab = QWidget()
        results_layout = QVBoxLayout()
        from PyQt6.QtWidgets import QTextEdit
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(QLabel("Investigation Results"))
        results_layout.addWidget(self.results_text)
        self.results_tab.setLayout(results_layout)
        self.tabs.addTab(self.results_tab, "Results")
        
        layout.addWidget(self.tabs)
        
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    
    def init_menu(self):
        """Initialize menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Investigation", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.start_new_investigation)
        file_menu.addAction(new_action)
        
        load_action = QAction("Load Results", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_investigation_results)
        file_menu.addAction(load_action)
        
        export_action = QAction("Export Report", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        dashboard_action = QAction("Dashboard", self)
        dashboard_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        view_menu.addAction(dashboard_action)
        
        risk_action = QAction("Risk Assessment", self)
        risk_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        view_menu.addAction(risk_action)
        
        network_action = QAction("Network Graph", self)
        network_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        view_menu.addAction(network_action)
        
        timeline_action = QAction("Timeline", self)
        timeline_action.triggered.connect(lambda: self.tabs.setCurrentIndex(3))
        view_menu.addAction(timeline_action)
        
        results_action = QAction("Results", self)
        results_action.triggered.connect(lambda: self.tabs.setCurrentIndex(4))
        view_menu.addAction(results_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_status_bar(self):
        """Initialize status bar."""
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
    
    def create_button(self, text: str, callback):
        """Helper to create styled button."""
        from PyQt6.QtWidgets import QPushButton
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button
    
    def start_new_investigation(self):
        """Start new investigation wizard."""
        wizard = InvestigationWizard(self)
        wizard.investigation_started.connect(self.on_investigation_started)
        wizard.exec()
    
    def on_investigation_started(self, config: Dict[str, Any]):
        """Handle investigation started."""
        self.current_investigation = config
        self.status.showMessage(
            f"Investigation started: {config['entity_type']} - {config['entity_id']}"
        )
        
        # In production, would call API to run investigation
        # For now, show mock results
        self.show_mock_results()
    
    def show_mock_results(self):
        """Display mock results (in production, would load from API)."""
        # Load mock data into components
        mock_nodes = [
            {"id": "1", "label": "John Doe", "type": "Person", "metadata": {"age": 35}},
            {"id": "2", "label": "ACME Corp", "type": "Company", "metadata": {"industry": "Tech"}},
            {"id": "3", "label": "example.com", "type": "Domain", "metadata": {}},
            {"id": "4", "label": "@johndoe", "type": "Account", "metadata": {"platform": "Twitter"}},
            {"id": "5", "label": "San Francisco, CA", "type": "Location", "metadata": {}}
        ]
        
        mock_edges = [
            {"source": "1", "target": "2", "relationship": "works_at", "strength": 0.9},
            {"source": "1", "target": "4", "relationship": "owns", "strength": 0.95},
            {"source": "2", "target": "3", "relationship": "operates", "strength": 0.85},
            {"source": "1", "target": "5", "relationship": "located_in", "strength": 0.7},
        ]
        
        self.network_graph.load_graph_data(mock_nodes, mock_edges)
        
        # Load mock timeline
        from datetime import datetime, timedelta
        mock_events = [
            {
                "event_id": "1",
                "event_type": "employment",
                "date": (datetime.now() - timedelta(days=365*5)).isoformat(),
                "description": "Joined ACME Corp as Engineer",
                "location": "San Francisco, CA",
                "confidence": 0.95,
                "source": "LinkedIn",
                "is_milestone": True,
                "entities": ["John Doe", "ACME Corp"]
            },
            {
                "event_id": "2",
                "event_type": "social",
                "date": (datetime.now() - timedelta(days=180)).isoformat(),
                "description": "Created Twitter account @johndoe",
                "confidence": 0.90,
                "source": "Twitter API",
                "entities": ["John Doe"]
            },
            {
                "event_id": "3",
                "event_type": "breach",
                "date": (datetime.now() - timedelta(days=90)).isoformat(),
                "description": "Included in Marriott data breach",
                "confidence": 0.98,
                "source": "HaveIBeenPwned",
                "entities": ["John Doe"]
            }
        ]
        
        self.timeline_viewer.load_events(mock_events)
        
        # Update results text
        results_text = "Investigation Results\n" + "="*50 + "\n\n"
        results_text += f"Entity: {self.current_investigation['entity_type']} - {self.current_investigation['entity_id']}\n"
        results_text += f"Sources: {len(self.current_investigation['sources'])} selected\n"
        results_text += f"Nodes Found: {len(mock_nodes)}\n"
        results_text += f"Relationships: {len(mock_edges)}\n"
        results_text += f"Events: {len(mock_events)}\n"
        
        self.results_text.setText(results_text)
        
        # Switch to results tab
        self.tabs.setCurrentIndex(4)
    
    def on_node_selected(self, node_data: Dict):
        """Handle node selection from network graph."""
        self.status.showMessage(f"Selected node: {node_data.get('label', 'Unknown')}")
    
    def on_event_selected(self, event_data: Dict):
        """Handle event selection from timeline."""
        self.status.showMessage(f"Selected event: {event_data.get('event_type', 'Unknown')}")
    
    def load_investigation_results(self):
        """Load previous investigation results."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Investigation Results",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            self.status.showMessage(f"Loaded: {filename}")
            # In production, would parse and load results
    
    def export_results(self):
        """Export investigation results."""
        if not self.current_investigation:
            QMessageBox.warning(self, "No Results", "No investigation results to export")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results",
            "investigation_results.pdf",
            "PDF Files (*.pdf);;JSON Files (*.json);;HTML Files (*.html)"
        )
        
        if filename:
            self.status.showMessage(f"Exported to: {filename}")
            # In production, would generate and save report
    
    def open_settings(self):
        """Open settings dialog."""
        QMessageBox.information(self, "Settings", "Settings dialog would open here")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.information(
            self,
            "About OSINT Framework",
            "OSINT Framework v1.0\n\n"
            "Desktop application for comprehensive open-source intelligence gathering.\n\n"
            "© 2024"
        )


def main():
    """Entry point for desktop application."""
    app = QtWidgets.QApplication(sys.argv)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import QtWidgets
    main()
