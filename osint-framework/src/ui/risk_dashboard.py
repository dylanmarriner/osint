"""
Risk Dashboard - PyQt Desktop UI Component

Displays risk assessment metrics and vulnerabilities.
Replaces RiskDashboard.vue with native PyQt widgets.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush
from PyQt6.QtChart import QChart, QChartView, QPieSeries, QPieSlice
from PyQt6.QtCore import QTimer
from typing import List, Dict, Any
import logging


class RiskDashboard(QWidget):
    """Risk assessment dashboard widget."""
    
    analysis_refreshed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Data
        self.risk_assessment = None
        self.last_updated = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize dashboard UI."""
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Risk Assessment Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.refresh_button = QPushButton("Refresh Analysis")
        self.refresh_button.clicked.connect(self.refresh_analysis)
        self.last_updated_label = QLabel("Last updated: Never")
        self.last_updated_label.setStyleSheet("color: #666;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.last_updated_label)
        header.addWidget(self.refresh_button)
        layout.addLayout(header)
        
        # Overview metrics
        metrics_layout = QHBoxLayout()
        
        # Overall risk score
        self.overall_risk_card = self.create_metric_card(
            "Overall Risk Score",
            "65",
            "HIGH",
            QColor(220, 53, 69)  # Red
        )
        metrics_layout.addWidget(self.overall_risk_card)
        
        # Privacy score
        self.privacy_score_card = self.create_metric_card(
            "Privacy Exposure",
            "72",
            None,
            QColor(40, 167, 69)  # Green
        )
        metrics_layout.addWidget(self.privacy_score_card)
        
        # Security score
        self.security_score_card = self.create_metric_card(
            "Security Risk",
            "58",
            None,
            QColor(255, 193, 7)  # Yellow
        )
        metrics_layout.addWidget(self.security_score_card)
        
        # Identity theft risk
        self.identity_score_card = self.create_metric_card(
            "Identity Theft Risk",
            "55",
            None,
            QColor(255, 152, 0)  # Orange
        )
        metrics_layout.addWidget(self.identity_score_card)
        
        layout.addLayout(metrics_layout)
        
        # Main content - two columns
        content_layout = QHBoxLayout()
        
        # Left panel
        left_panel = QVBoxLayout()
        
        # Risk breakdown (pie chart)
        risk_group = QGroupBox("Risk Factor Breakdown")
        risk_layout = QVBoxLayout()
        self.pie_chart = self.create_pie_chart()
        risk_layout.addWidget(self.pie_chart)
        risk_group.setLayout(risk_layout)
        left_panel.addWidget(risk_group)
        
        # Vulnerabilities list
        vuln_group = QGroupBox("Critical Vulnerabilities")
        vuln_layout = QVBoxLayout()
        self.vuln_table = QTableWidget()
        self.vuln_table.setColumnCount(4)
        self.vuln_table.setHorizontalHeaderLabels(["Title", "Severity", "Affected", "Fix Effort"])
        self.vuln_table.horizontalHeader().setStretchLastSection(False)
        self.populate_vulnerabilities()
        vuln_layout.addWidget(self.vuln_table)
        vuln_group.setLayout(vuln_layout)
        left_panel.addWidget(vuln_group)
        
        # Right panel
        right_panel = QVBoxLayout()
        
        # Recommendations
        rec_group = QGroupBox("Top Recommendations")
        rec_layout = QVBoxLayout()
        self.rec_table = QTableWidget()
        self.rec_table.setColumnCount(4)
        self.rec_table.setHorizontalHeaderLabels(["Priority", "Action", "Impact", "Effort"])
        self.populate_recommendations()
        rec_layout.addWidget(self.rec_table)
        rec_group.setLayout(rec_layout)
        right_panel.addWidget(rec_group)
        
        content_layout.addLayout(left_panel, 1)
        content_layout.addLayout(right_panel, 1)
        layout.addLayout(content_layout)
        
        # Risk trend
        trend_group = QGroupBox("Risk Score Trend (Last 30 Days)")
        trend_layout = QVBoxLayout()
        trend_layout.addWidget(QLabel("Trend chart would render here"))
        trend_group.setLayout(trend_layout)
        layout.addWidget(trend_group)
        
        # Peer comparison table
        compare_group = QGroupBox("Comparative Risk Analysis")
        compare_layout = QVBoxLayout()
        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(4)
        self.compare_table.setHorizontalHeaderLabels(["Metric", "This Person", "Peer Average", "Status"])
        self.populate_peer_comparison()
        compare_layout.addWidget(self.compare_table)
        compare_group.setLayout(compare_layout)
        layout.addWidget(compare_group)
        
        self.setLayout(layout)
    
    def create_metric_card(self, label: str, value: str, level: str = None, color: QColor = None) -> QGroupBox:
        """Create a metric card widget."""
        card = QGroupBox()
        card.setStyleSheet(f"border: 2px solid {color.name() if color else '#ddd'}; border-radius: 4px;")
        layout = QVBoxLayout()
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"color: {color.name() if color else '#333'};")
        layout.addWidget(value_label)
        
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_widget.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(label_widget)
        
        if level:
            level_label = QLabel(level)
            level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            level_label.setStyleSheet(f"color: {color.name() if color else '#333'}; font-weight: bold;")
            layout.addWidget(level_label)
        
        progress = QProgressBar()
        progress.setValue(int(value))
        progress.setMaximum(100)
        layout.addWidget(progress)
        
        card.setLayout(layout)
        return card
    
    def create_pie_chart(self) -> QChartView:
        """Create pie chart for risk breakdown."""
        chart = QChart()
        chart.setTitle("Risk Factor Breakdown")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        series = QPieSeries()
        
        factors = [
            ("Privacy Exposure", 35, QColor(255, 107, 107)),
            ("Security Risk", 30, QColor(255, 165, 0)),
            ("Identity Theft", 20, QColor(255, 217, 61)),
            ("Network Risk", 15, QColor(107, 207, 228))
        ]
        
        for name, value, color in factors:
            slice_obj = QPieSlice(name, value)
            slice_obj.setColor(color)
            slice_obj.setLabelVisible(True)
            series.append(slice_obj)
        
        chart.addSeries(series)
        chart.legend().setVisible(True)
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(chart_view.RenderHint.Antialiasing)
        return chart_view
    
    def populate_vulnerabilities(self):
        """Populate vulnerabilities table."""
        vulnerabilities = [
            {
                "title": "Email Found in Breach Database",
                "severity": "CRITICAL",
                "affected": 1,
                "effort": "LOW"
            },
            {
                "title": "Weak Password Pattern",
                "severity": "HIGH",
                "affected": 3,
                "effort": "MEDIUM"
            },
            {
                "title": "Missing 2FA Protection",
                "severity": "HIGH",
                "affected": 2,
                "effort": "MEDIUM"
            }
        ]
        
        self.vuln_table.setRowCount(len(vulnerabilities))
        severity_colors = {
            "CRITICAL": QColor(198, 40, 40),
            "HIGH": QColor(230, 81, 0),
            "MEDIUM": QColor(245, 127, 23)
        }
        
        for row, vuln in enumerate(vulnerabilities):
            title_item = QTableWidgetItem(vuln["title"])
            severity_item = QTableWidgetItem(vuln["severity"])
            severity_item.setBackground(severity_colors.get(vuln["severity"], QColor(200, 200, 200)))
            severity_item.setForeground(QColor(255, 255, 255))
            affected_item = QTableWidgetItem(str(vuln["affected"]))
            effort_item = QTableWidgetItem(vuln["effort"])
            
            self.vuln_table.setItem(row, 0, title_item)
            self.vuln_table.setItem(row, 1, severity_item)
            self.vuln_table.setItem(row, 2, affected_item)
            self.vuln_table.setItem(row, 3, effort_item)
    
    def populate_recommendations(self):
        """Populate recommendations table."""
        recommendations = [
            {
                "priority": "CRITICAL",
                "action": "Change password for Adobe-affected accounts",
                "impact": "25%",
                "effort": "LOW"
            },
            {
                "priority": "HIGH",
                "action": "Enable two-factor authentication",
                "impact": "35%",
                "effort": "MEDIUM"
            },
            {
                "priority": "MEDIUM",
                "action": "Monitor credit reports",
                "impact": "15%",
                "effort": "LOW"
            }
        ]
        
        self.rec_table.setRowCount(len(recommendations))
        priority_colors = {
            "CRITICAL": QColor(198, 40, 40),
            "HIGH": QColor(230, 81, 0),
            "MEDIUM": QColor(245, 127, 23)
        }
        
        for row, rec in enumerate(recommendations):
            priority_item = QTableWidgetItem(rec["priority"])
            priority_item.setBackground(priority_colors.get(rec["priority"], QColor(200, 200, 200)))
            priority_item.setForeground(QColor(255, 255, 255))
            action_item = QTableWidgetItem(rec["action"])
            impact_item = QTableWidgetItem(rec["impact"])
            effort_item = QTableWidgetItem(rec["effort"])
            
            self.rec_table.setItem(row, 0, priority_item)
            self.rec_table.setItem(row, 1, action_item)
            self.rec_table.setItem(row, 2, impact_item)
            self.rec_table.setItem(row, 3, effort_item)
    
    def populate_peer_comparison(self):
        """Populate peer comparison table."""
        comparison = [
            {"metric": "Breaches Involved", "personal": "3", "average": "1.2", "status": "Above"},
            {"metric": "Accounts Exposed", "personal": "5", "average": "2.1", "status": "Above"},
            {"metric": "Data Types Exposed", "personal": "7", "average": "3.5", "status": "Above"},
            {"metric": "Last Breach", "personal": "2013", "average": "2018", "status": "Below"}
        ]
        
        self.compare_table.setRowCount(len(comparison))
        status_colors = {
            "Above": QColor(230, 81, 0),
            "Below": QColor(46, 125, 50),
            "Average": QColor(153, 153, 153)
        }
        
        for row, item in enumerate(comparison):
            metric_item = QTableWidgetItem(item["metric"])
            personal_item = QTableWidgetItem(item["personal"])
            average_item = QTableWidgetItem(item["average"])
            status_item = QTableWidgetItem(item["status"])
            status_item.setForeground(status_colors.get(item["status"], QColor(0, 0, 0)))
            
            self.compare_table.setItem(row, 0, metric_item)
            self.compare_table.setItem(row, 1, personal_item)
            self.compare_table.setItem(row, 2, average_item)
            self.compare_table.setItem(row, 3, status_item)
    
    def refresh_analysis(self):
        """Refresh risk analysis."""
        # In production, call API: /api/analysis/refresh
        self.logger.info("Refreshing risk analysis")
        self.analysis_refreshed.emit()
    
    def set_risk_assessment(self, assessment: Dict[str, Any]):
        """Update dashboard with new risk assessment."""
        self.risk_assessment = assessment
        # Update all metrics and tables
        self.logger.info("Updated risk assessment")
