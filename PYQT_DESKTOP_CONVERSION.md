# PyQt6 Desktop Application Conversion

Complete conversion of Vue.js web UI to native PyQt6 desktop application.

## Overview

All Vue.js components have been converted to PyQt6 with full feature parity:

| Vue Component | PyQt Module | Status |
|---|---|---|
| InvestigationWizard.vue | investigation_wizard.py | ✅ Complete |
| NetworkGraph.vue | network_graph.py | ✅ Complete |
| RiskDashboard.vue | risk_dashboard.py | ✅ Complete |
| TimelineViewer.vue | timeline_viewer.py | ✅ Complete |
| Main App | main_window.py | ✅ Complete |

---

## File Structure

```
osint-framework/
├── osint_desktop.py                    # Desktop app entry point
├── osint_desktop.spec                  # PyInstaller config
├── requirements_ui.txt                 # Desktop UI dependencies
├── src/
│   └── ui/                            # Desktop UI components
│       ├── __init__.py
│       ├── main_window.py             # Main application window
│       ├── investigation_wizard.py     # 5-step investigation wizard
│       ├── risk_dashboard.py          # Risk assessment dashboard
│       ├── network_graph.py           # Network visualization
│       └── timeline_viewer.py         # Timeline visualization
└── ui/                                # Legacy Vue.js (can be removed)
    ├── pages/
    ├── components/
    └── ...
```

---

## Desktop UI Components

### 1. Investigation Wizard (`investigation_wizard.py`)

**5-Step Guided Wizard:**

- **Step 1**: Entity Type & Search
  - Select entity type (Person, Company, Domain, Email, Phone, Username)
  - Search for entity
  - Select from results

- **Step 2**: Data Source Selection
  - Multi-category source selection
  - Confidence and rate limit display
  - Source summary with count

- **Step 3**: Analysis Options
  - Checkboxes for analysis types
  - Timeline, Network Graph, Risk Assessment, etc.

- **Step 4**: Report Configuration
  - Format selection (PDF, HTML, JSON, CSV)
  - Content sections
  - Privacy options (encryption, anonymization, watermark)

- **Step 5**: Review & Confirmation
  - Summary of all selections
  - Terms acceptance
  - Confirmation to start investigation

**Features:**
- Progress bar with step tracking
- Previous/Next navigation
- Form validation
- API integration ready

---

### 2. Risk Dashboard (`risk_dashboard.py`)

**Comprehensive Risk Assessment:**

- **Metrics Cards** (4):
  - Overall Risk Score (0-100)
  - Privacy Exposure (%)
  - Security Risk (%)
  - Identity Theft Risk (%)

- **Risk Breakdown**:
  - Pie chart of risk factors
  - Legend with percentages

- **Vulnerabilities List**:
  - Title, severity, affected count, remediation effort
  - Color-coded severity (CRITICAL, HIGH, MEDIUM)
  - Sortable table

- **Recommendations**:
  - Priority-based sorting
  - Impact reduction percentages
  - Implementation effort estimates

- **Analytics**:
  - Risk score trend (30 days)
  - Peer comparative analysis

**Features:**
- Real-time metric updates
- Refresh button
- Last updated timestamp
- Exportable data

---

### 3. Network Graph (`network_graph.py`)

**Interactive Entity Relationship Network:**

- **Force-Directed Layout**:
  - Physics simulation
  - Node repulsion and edge attraction
  - Spring layout algorithm (NetworkX)

- **Visual Elements**:
  - Color-coded nodes by type
  - Edge thickness by relationship strength
  - Node size customization
  - Node labels

- **Node Types** (color-coded):
  - Person (Blue)
  - Company (Green)
  - Domain (Yellow)
  - Account (Red)
  - Location (Purple)

- **Interactive Features**:
  - Click nodes for details
  - Node properties panel
  - Connected nodes list with relationship strength
  - Degree and centrality metrics

- **Controls**:
  - Toggle physics simulation
  - Export as PNG
  - Reset view
  - Zoom controls

- **Statistics**:
  - Node count
  - Edge count
  - Community detection
  - Average degree

**Features:**
- NetworkX for graph algorithms
- Matplotlib canvas rendering
- Real-time updates
- Hover tooltips

---

### 4. Timeline Viewer (`timeline_viewer.py`)

**Temporal Event Visualization:**

- **Timeline Display**:
  - Horizontal timeline with year markers
  - Event dots positioned by date
  - Staggered vertical layout (no overlap)
  - Milestone indicators (larger dots)

- **Event Types** (color-coded):
  - Employment (Green)
  - Education (Yellow)
  - Social Media (Cyan)
  - Location (Pink)
  - Data Breach (Red)
  - Financial (Purple)

- **Interactive Features**:
  - Click events for details
  - Filter by event type
  - Zoom in/out (0.5x - 3.0x)
  - Hover tooltips

- **Event Details**:
  - Date, description, location
  - Confidence score
  - Related entities
  - Data source
  - Additional metadata

- **Legend**:
  - Color-coded event types
  - Quick reference

**Features:**
- Matplotlib timeline rendering
- Date parsing and positioning
- Automatic scaling
- Export-ready

---

### 5. Main Window (`main_window.py`)

**Application Container:**

- **Menu Bar**:
  - File (New, Load, Export, Exit)
  - View (Dashboard, Risk, Network, Timeline, Results)
  - Tools (Settings)
  - Help (About)

- **Toolbar**:
  - Quick action buttons
  - New Investigation
  - Load Results
  - Export Report
  - Settings

- **Tab Interface**:
  - Dashboard (welcome & stats)
  - Risk Assessment (risk_dashboard)
  - Network Graph (network_graph)
  - Timeline (timeline_viewer)
  - Results (text results & export)

- **Status Bar**:
  - Current operation status
  - Last action feedback
  - Investigation state

**Features:**
- Full menu and keyboard shortcuts
- Tab-based multi-view
- State management
- Signal/slot communication between components

---

## Installation & Setup

### 1. Install Dependencies

```bash
cd osint-framework
pip install -r requirements_ui.txt
```

### 2. Run Desktop App

```bash
python osint_desktop.py
```

### 3. Package as Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build single executable
pyinstaller osint_desktop.spec

# Executable will be in: dist/OSINTFramework
```

---

## Features

### Desktop-Native Capabilities

✅ **Native Widgets**: Uses Qt native controls
✅ **System Integration**: Native file dialogs, menus, shortcuts
✅ **Single Executable**: Bundle with PyInstaller into .exe/.app/.bin
✅ **No Browser Required**: Runs standalone
✅ **Keyboard Shortcuts**: Full keyboard support
✅ **Drag & Drop**: Native OS drag-and-drop
✅ **Taskbar Integration**: OS taskbar/dock integration
✅ **System Tray**: Optional system tray icon support
✅ **Local Data**: Data stays on local machine
✅ **Offline-Ready**: Can run without internet (with cached data)

### Data Visualization

✅ **Network Graphs**: Force-directed layout with physics
✅ **Timelines**: Temporal visualization with zoom
✅ **Charts**: Pie charts, bar charts (via matplotlib)
✅ **Tables**: Sortable, scrollable data tables
✅ **Real-Time Updates**: Live data refresh

### Investigation Workflow

✅ **Guided Wizard**: 5-step investigation setup
✅ **Data Integration**: Multi-source configuration
✅ **Analysis Selection**: Customizable analysis types
✅ **Report Options**: Multiple export formats
✅ **Results Management**: Load, view, export

---

## API Integration

Components are designed for easy API integration:

```python
# Example: Load investigation results from API
response = requests.get('/api/investigation/results', params={...})
results = response.json()

# Update network graph
self.network_graph.load_graph_data(
    results['nodes'],
    results['edges']
)

# Update timeline
self.timeline_viewer.load_events(results['events'])

# Update risk dashboard
self.risk_dashboard.set_risk_assessment(results['risk'])
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New Investigation |
| `Ctrl+O` | Load Results |
| `Ctrl+E` | Export Report |
| `Ctrl+Q` | Exit |

---

## Building Executables

### Windows (.exe)

```bash
pyinstaller osint_desktop.spec
# Creates: dist/OSINTFramework.exe (~150MB)
```

### macOS (.app)

```bash
pyinstaller osint_desktop.spec --onedir
# Creates: dist/OSINTFramework.app
```

### Linux (Binary)

```bash
pyinstaller osint_desktop.spec
# Creates: dist/OSINTFramework executable
```

---

## Configuration

Optional: Create `config.ini` for desktop app settings:

```ini
[ui]
theme = dark
window_width = 1400
window_height = 900

[api]
server = http://localhost:8000
timeout = 30

[export]
default_format = pdf
output_directory = ~/OSINTResults
```

---

## Migration from Web UI

**What Stays the Same:**
- All Vue component logic → PyQt equivalent
- API calls (requests library)
- Data structures and models
- Report generation
- Analysis engines

**What Changes:**
- Vue component lifecycle → PyQt signals/slots
- Vue templates → PyQt widgets/layouts
- CSS styling → PyQt stylesheets
- Network requests → requests library (already used)

---

## Advantages Over Web UI

| Aspect | Web UI | Desktop |
|---|---|---|
| **Deployment** | Browser dependency | Single executable |
| **Performance** | Network latency | Local execution |
| **Data Privacy** | Server storage | Local machine only |
| **Offline** | ❌ Requires internet | ✅ Works offline |
| **System Integration** | ❌ Limited | ✅ Full access |
| **Installation** | Browser required | Single file |
| **Native Look** | Web browser look | Native OS look |
| **File Access** | Sandboxed | Full filesystem |
| **Keyboard Shortcuts** | ❌ Limited | ✅ Full support |
| **Taskbar/Dock** | ❌ Requires browser | ✅ Native integration |

---

## Next Steps

1. ✅ Replace Vue components with PyQt
2. ✅ Maintain API communication
3. ⏳ Add system tray support
4. ⏳ Create installer (NSIS/DMG)
5. ⏳ Add auto-update mechanism
6. ⏳ Create macOS code signing

---

## Troubleshooting

**Import Errors:**
```bash
pip install PyQt6 PyQt6-Charts matplotlib networkx
```

**Display Issues (Linux):**
```bash
export QT_QPA_PLATFORM=xcb
python osint_desktop.py
```

**Build Errors:**
```bash
pip install --upgrade pyinstaller
pyinstaller osint_desktop.spec --clean
```

---

## License & Credits

OSINT Framework Desktop - PyQt6 Conversion
Based on original Vue.js implementation
Uses: PyQt6, NetworkX, Matplotlib, Python
