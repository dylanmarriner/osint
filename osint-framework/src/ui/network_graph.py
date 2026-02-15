"""
Network Graph - PyQt Desktop UI Component

Interactive network visualization with force-directed layout.
Replaces NetworkGraph.vue with PyQt + NetworkX + Matplotlib.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import networkx as nx
from typing import List, Dict, Any, Set
import logging


class NetworkGraphWidget(QWidget):
    """Network graph visualization widget."""
    
    node_selected = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Graph data
        self.nodes = []
        self.edges = []
        self.graph = nx.Graph()
        self.pos = {}
        self.selected_node = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Network Graph")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        
        # Controls
        self.physics_button = QPushButton("Physics: ON")
        self.physics_button.setCheckable(True)
        self.physics_button.setChecked(True)
        self.physics_button.clicked.connect(self.toggle_physics)
        
        self.export_button = QPushButton("Export as PNG")
        self.export_button.clicked.connect(self.export_graph)
        
        self.reset_button = QPushButton("Reset View")
        self.reset_button.clicked.connect(self.reset_view)
        
        size_label = QLabel("Node Size:")
        self.size_spinner = QSpinBox()
        self.size_spinner.setRange(50, 200)
        self.size_spinner.setValue(100)
        self.size_spinner.setMaximumWidth(80)
        self.size_spinner.valueChanged.connect(self.redraw_graph)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.physics_button)
        header.addWidget(self.export_button)
        header.addWidget(self.reset_button)
        header.addWidget(size_label)
        header.addWidget(self.size_spinner)
        layout.addLayout(header)
        
        # Canvas for graph
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        layout.addWidget(self.canvas)
        
        # Node details panel
        details_layout = QHBoxLayout()
        
        details_group = QGroupBox("Node Details")
        details_group_layout = QVBoxLayout()
        
        self.node_label = QLabel("No node selected")
        self.node_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        
        self.node_info_table = QTableWidget()
        self.node_info_table.setColumnCount(2)
        self.node_info_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.node_info_table.setMaximumHeight(200)
        
        self.connected_table = QTableWidget()
        self.connected_table.setColumnCount(3)
        self.connected_table.setHorizontalHeaderLabels(["Connected To", "Relationship", "Strength"])
        self.connected_table.setMaximumHeight(150)
        
        details_group_layout.addWidget(self.node_label)
        details_group_layout.addWidget(QLabel("Properties:"))
        details_group_layout.addWidget(self.node_info_table)
        details_group_layout.addWidget(QLabel("Connections:"))
        details_group_layout.addWidget(self.connected_table)
        
        details_group.setLayout(details_group_layout)
        details_layout.addWidget(details_group)
        
        # Legend
        legend_group = QGroupBox("Legend")
        legend_layout = QVBoxLayout()
        
        node_types = ["Person", "Company", "Domain", "Account", "Location"]
        for node_type in node_types:
            legend_layout.addWidget(QLabel(f"• {node_type}"))
        
        legend_group.setLayout(legend_layout)
        details_layout.addWidget(legend_group)
        
        # Stats
        stats_group = QGroupBox("Graph Statistics")
        stats_layout = QVBoxLayout()
        
        self.nodes_label = QLabel("Nodes: 0")
        self.edges_label = QLabel("Edges: 0")
        self.communities_label = QLabel("Communities: 0")
        self.avg_degree_label = QLabel("Avg. Degree: 0.0")
        
        stats_layout.addWidget(self.nodes_label)
        stats_layout.addWidget(self.edges_label)
        stats_layout.addWidget(self.communities_label)
        stats_layout.addWidget(self.avg_degree_label)
        
        stats_group.setLayout(stats_layout)
        details_layout.addWidget(stats_group)
        
        layout.addLayout(details_layout)
        
        self.setLayout(layout)
    
    def load_graph_data(self, nodes: List[Dict], edges: List[Dict]):
        """Load graph data and render."""
        self.nodes = nodes
        self.edges = edges
        
        # Build NetworkX graph
        self.graph = nx.Graph()
        
        for node in nodes:
            self.graph.add_node(
                node['id'],
                label=node.get('label', node['id']),
                type=node.get('type', 'Unknown'),
                metadata=node.get('metadata', {})
            )
        
        for edge in edges:
            self.graph.add_edge(
                edge['source'],
                edge['target'],
                relationship=edge.get('relationship', 'connected'),
                strength=edge.get('strength', 0.5)
            )
        
        # Compute layout
        self.compute_layout()
        
        # Draw
        self.redraw_graph()
        
        # Update stats
        self.update_stats()
    
    def compute_layout(self):
        """Compute force-directed layout."""
        if len(self.graph) == 0:
            return
        
        # Use spring layout for force-directed
        self.pos = nx.spring_layout(
            self.graph,
            k=2,
            iterations=50,
            seed=42
        )
    
    def redraw_graph(self):
        """Redraw the network graph."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        if len(self.graph) == 0:
            ax.text(0.5, 0.5, 'No graph data loaded',
                   ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            return
        
        # Node colors by type
        node_colors = {
            'Person': '#4285F4',
            'Company': '#34A853',
            'Domain': '#FBBC04',
            'Account': '#EA4335',
            'Location': '#9C27B0'
        }
        
        # Draw edges
        nx.draw_networkx_edges(
            self.graph,
            self.pos,
            ax=ax,
            edge_color='#cccccc',
            width=1,
            alpha=0.5
        )
        
        # Draw nodes
        node_types = {}
        for node in self.graph.nodes():
            node_type = self.graph.nodes[node].get('type', 'Unknown')
            if node_type not in node_types:
                node_types[node_type] = []
            node_types[node_type].append(node)
        
        node_size = self.size_spinner.value()
        for node_type, nodes_list in node_types.items():
            color = node_colors.get(node_type, '#999999')
            nx.draw_networkx_nodes(
                self.graph,
                self.pos,
                nodelist=nodes_list,
                ax=ax,
                node_color=color,
                node_size=node_size,
                label=node_type,
                alpha=0.8
            )
        
        # Draw labels
        labels = {node: self.graph.nodes[node].get('label', node) for node in self.graph.nodes()}
        nx.draw_networkx_labels(
            self.graph,
            self.pos,
            labels=labels,
            ax=ax,
            font_size=8
        )
        
        ax.set_title("Entity Relationship Network")
        ax.axis('off')
        ax.legend(scatterpoints=1, loc='upper left')
        
        self.canvas.draw()
    
    def update_stats(self):
        """Update graph statistics."""
        num_nodes = len(self.graph)
        num_edges = self.graph.number_of_edges()
        avg_degree = 2 * num_edges / max(num_nodes, 1)
        
        # Detect communities
        try:
            from networkx.algorithms import community
            communities = list(community.greedy_modularity_communities(self.graph))
            num_communities = len(communities)
        except:
            num_communities = 0
        
        self.nodes_label.setText(f"Nodes: {num_nodes}")
        self.edges_label.setText(f"Edges: {num_edges}")
        self.communities_label.setText(f"Communities: {num_communities}")
        self.avg_degree_label.setText(f"Avg. Degree: {avg_degree:.1f}")
    
    def on_canvas_click(self, event):
        """Handle canvas click for node selection."""
        if not event.inaxes:
            return
        
        # Find clicked node
        clicked_x, clicked_y = event.xdata, event.ydata
        min_dist = float('inf')
        closest_node = None
        
        for node, (x, y) in self.pos.items():
            dist = ((x - clicked_x) ** 2 + (y - clicked_y) ** 2) ** 0.5
            if dist < min_dist and dist < 0.05:
                min_dist = dist
                closest_node = node
        
        if closest_node:
            self.select_node(closest_node)
    
    def select_node(self, node_id: str):
        """Select a node and update details panel."""
        self.selected_node = node_id
        
        # Update label
        label = self.graph.nodes[node_id].get('label', node_id)
        self.node_label.setText(f"Selected: {label}")
        
        # Update node info
        self.node_info_table.setRowCount(0)
        node_data = self.graph.nodes[node_id]
        
        row = 0
        for key, value in node_data.items():
            if key != 'metadata':
                self.node_info_table.insertRow(row)
                self.node_info_table.setItem(row, 0, QTableWidgetItem(str(key)))
                self.node_info_table.setItem(row, 1, QTableWidgetItem(str(value)))
                row += 1
        
        # Update connected nodes
        self.connected_table.setRowCount(0)
        row = 0
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]
            neighbor_label = self.graph.nodes[neighbor].get('label', neighbor)
            relationship = edge_data.get('relationship', 'connected')
            strength = edge_data.get('strength', 0.5)
            
            self.connected_table.insertRow(row)
            self.connected_table.setItem(row, 0, QTableWidgetItem(neighbor_label))
            self.connected_table.setItem(row, 1, QTableWidgetItem(relationship))
            self.connected_table.setItem(row, 2, QTableWidgetItem(f"{strength:.2f}"))
            row += 1
        
        self.node_selected.emit({"id": node_id, "label": label})
    
    def toggle_physics(self):
        """Toggle physics simulation."""
        if self.physics_button.isChecked():
            self.physics_button.setText("Physics: ON")
            self.logger.info("Physics simulation enabled")
        else:
            self.physics_button.setText("Physics: OFF")
            self.logger.info("Physics simulation disabled")
    
    def export_graph(self):
        """Export graph as PNG."""
        try:
            self.figure.savefig('network_graph.png', dpi=300, bbox_inches='tight')
            self.logger.info("Graph exported to network_graph.png")
        except Exception as e:
            self.logger.error(f"Failed to export graph: {e}")
    
    def reset_view(self):
        """Reset view to default."""
        self.selected_node = None
        self.node_label.setText("No node selected")
        self.node_info_table.setRowCount(0)
        self.connected_table.setRowCount(0)
        self.compute_layout()
        self.redraw_graph()
