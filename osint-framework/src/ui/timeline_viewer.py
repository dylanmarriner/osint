"""
Timeline Viewer - PyQt Desktop UI Component

Interactive timeline visualization of events.
Replaces TimelineViewer.vue with native PyQt widgets.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QSpinBox, QSlider,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime
from typing import List, Dict, Any
import logging


class TimelineViewer(QWidget):
    """Timeline visualization widget."""
    
    event_selected = pyqtSignal(dict)
    filter_changed = pyqtSignal(str)
    
    EVENT_TYPES = {
        "employment": ("Employment", QColor(40, 167, 69)),
        "education": ("Education", QColor(255, 193, 7)),
        "social": ("Social Media", QColor(23, 162, 184)),
        "location": ("Location", QColor(232, 62, 140)),
        "breach": ("Data Breach", QColor(220, 53, 69)),
        "financial": ("Financial", QColor(111, 66, 193))
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Data
        self.events = []
        self.filtered_events = []
        self.selected_event = None
        self.selected_event_type = ""
        self.zoom_level = 1.0
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Timeline View")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        # Controls
        filter_label = QLabel("Filter by Event Type:")
        self.event_type_combo = QComboBox()
        self.event_type_combo.addItem("All Events", "")
        for event_id, (event_name, _) in self.EVENT_TYPES.items():
            self.event_type_combo.addItem(event_name, event_id)
        self.event_type_combo.currentDataChanged.connect(self.on_filter_changed)
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setMaximumWidth(40)
        self.zoom_in_button.clicked.connect(self.zoom_in)
        
        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setMaximumWidth(40)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        
        self.zoom_display = QLabel("1.0x")
        self.zoom_display.setMaximumWidth(40)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(filter_label)
        header.addWidget(self.event_type_combo)
        header.addWidget(zoom_label)
        header.addWidget(self.zoom_in_button)
        header.addWidget(self.zoom_out_button)
        header.addWidget(self.zoom_display)
        layout.addLayout(header)
        
        # Timeline canvas
        self.figure = Figure(figsize=(12, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.mpl_connect('button_press_event', self.on_event_click)
        layout.addWidget(self.canvas)
        
        # Event details
        details_group = QGroupBox("Event Details")
        details_layout = QVBoxLayout()
        
        self.event_title = QLabel("No event selected")
        self.event_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        details_layout.addWidget(self.event_title)
        
        self.event_details_table = QTableWidget()
        self.event_details_table.setColumnCount(2)
        self.event_details_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.event_details_table.setMaximumHeight(200)
        details_layout.addWidget(self.event_details_table)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)
        
        # Legend
        legend_group = QGroupBox("Legend")
        legend_layout = QHBoxLayout()
        
        for event_id, (event_name, color) in self.EVENT_TYPES.items():
            label = QLabel(f"● {event_name}")
            label.setStyleSheet(f"color: {color.name()};")
            legend_layout.addWidget(label)
        
        legend_layout.addStretch()
        legend_group.setLayout(legend_layout)
        layout.addWidget(legend_group)
        
        self.setLayout(layout)
    
    def load_events(self, events: List[Dict[str, Any]]):
        """Load events and render timeline."""
        self.events = events
        self.filtered_events = events
        self.draw_timeline()
    
    def on_filter_changed(self):
        """Handle filter change."""
        selected_type = self.event_type_combo.currentData()
        self.selected_event_type = selected_type
        
        if selected_type:
            self.filtered_events = [e for e in self.events if e.get('event_type') == selected_type]
        else:
            self.filtered_events = self.events
        
        self.draw_timeline()
        self.filter_changed.emit(selected_type)
    
    def draw_timeline(self):
        """Draw timeline visualization."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if not self.filtered_events:
            ax.text(0.5, 0.5, 'No events to display',
                   ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            return
        
        # Parse dates
        try:
            dates = [datetime.fromisoformat(e.get('date', datetime.now().isoformat())) 
                    for e in self.filtered_events]
        except:
            dates = [datetime.now()] * len(self.filtered_events)
        
        # Draw horizontal timeline
        min_date = min(dates)
        max_date = max(dates)
        
        # Y position for events (staggered to avoid overlap)
        y_positions = []
        for i in range(len(self.filtered_events)):
            y_positions.append((i % 3) + 1)  # Stagger vertically
        
        # Plot events
        for event, date, y_pos in zip(self.filtered_events, dates, y_positions):
            event_type = event.get('event_type', 'unknown')
            event_name, color = self.EVENT_TYPES.get(event_type, ("Unknown", QColor(150, 150, 150)))
            
            is_milestone = event.get('is_milestone', False)
            marker_size = 150 if is_milestone else 100
            
            ax.scatter(date, y_pos, s=marker_size, c=[color.name()], 
                      alpha=0.8, picker=True, zorder=3)
            
            # Add label below
            ax.text(date, y_pos - 0.3, event.get('event_type', ''), 
                   ha='center', fontsize=8, rotation=45)
        
        # Draw baseline
        ax.axhline(y=0.5, color='gray', linestyle='-', linewidth=1, alpha=0.3)
        
        # Format axes
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.set_ylim(0, 4)
        ax.set_ylabel('')
        ax.set_title(f"Timeline ({len(self.filtered_events)} events)")
        ax.grid(True, alpha=0.2)
        
        self.figure.autofmt_xdate(rotation=45)
        self.figure.tight_layout()
        self.canvas.draw()
    
    def on_event_click(self, event):
        """Handle event click."""
        if not event.inaxes or event.xdata is None:
            return
        
        # Find clicked event
        try:
            click_date = mdates.num2date(event.xdata)
        except:
            return
        
        # Find closest event
        min_dist = float('inf')
        closest_event = None
        
        for evt in self.filtered_events:
            try:
                evt_date = datetime.fromisoformat(evt.get('date', datetime.now().isoformat()))
                dist = abs((evt_date - click_date).total_seconds())
                if dist < min_dist and dist < 86400:  # Within 1 day
                    min_dist = dist
                    closest_event = evt
            except:
                pass
        
        if closest_event:
            self.select_event(closest_event)
    
    def select_event(self, event: Dict[str, Any]):
        """Select and display event details."""
        self.selected_event = event
        
        # Update title
        self.event_title.setText(f"{event.get('event_type', 'Unknown').title()} - {event.get('description', 'N/A')}")
        
        # Update details table
        self.event_details_table.setRowCount(0)
        
        display_fields = ['date', 'description', 'location', 'confidence', 'source']
        row = 0
        for field in display_fields:
            if field in event:
                self.event_details_table.insertRow(row)
                self.event_details_table.setItem(row, 0, QTableWidgetItem(field.title()))
                
                value = event[field]
                if field == 'confidence' and isinstance(value, float):
                    value = f"{value*100:.0f}%"
                
                self.event_details_table.setItem(row, 1, QTableWidgetItem(str(value)))
                row += 1
        
        # Add entities if available
        if 'entities' in event:
            self.event_details_table.insertRow(row)
            self.event_details_table.setItem(row, 0, QTableWidgetItem("Related Entities"))
            self.event_details_table.setItem(row, 1, QTableWidgetItem(", ".join(event['entities'])))
        
        self.event_selected.emit(event)
    
    def zoom_in(self):
        """Zoom in timeline."""
        if self.zoom_level < 3.0:
            self.zoom_level += 0.5
            self.zoom_display.setText(f"{self.zoom_level:.1f}x")
            self.draw_timeline()
    
    def zoom_out(self):
        """Zoom out timeline."""
        if self.zoom_level > 0.5:
            self.zoom_level -= 0.5
            self.zoom_display.setText(f"{self.zoom_level:.1f}x")
            self.draw_timeline()
