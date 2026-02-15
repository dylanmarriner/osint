# OSINT Framework Desktop - Quick Start

## Installation (5 minutes)

### 1. Install Dependencies

```bash
cd osint-framework
pip install -r requirements_ui.txt
```

### 2. Run Desktop Application

```bash
python osint_desktop.py
```

The application window will open.

---

## Quick Usage

### Start Investigation
1. Click **"New Investigation"** button
2. Follow the 5-step wizard:
   - Select entity type (Person, Company, Domain, etc.)
   - Search for entity
   - Select data sources
   - Choose analysis types
   - Configure report settings
3. Click **"Start Investigation"** to begin

### View Results
Results appear in multiple tabs:
- **Risk Assessment**: Risk scores, vulnerabilities, recommendations
- **Network Graph**: Entity relationships and connections
- **Timeline**: Chronological events and activities
- **Results**: Full investigation data

### Export Report
Click **"Export Report"** to save as PDF, HTML, JSON, or CSV

---

## Package as Executable

### Create Single .exe (Windows) / .app (macOS) / Binary (Linux)

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller osint_desktop.spec

# Find executable in:
# - Windows: dist/OSINTFramework.exe (~150MB)
# - macOS: dist/OSINTFramework.app
# - Linux: dist/OSINTFramework
```

### Distribution
- **Single File**: No installation required
- **Zero Dependencies**: Everything bundled
- **Native**: Looks and feels like native application
- **Works Offline**: No internet needed (with cached data)

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New Investigation |
| `Ctrl+O` | Load Results |
| `Ctrl+E` | Export Report |
| `Ctrl+Q` | Exit |

---

## Features

### Investigation Wizard
- ✅ 5-step guided process
- ✅ Entity search integration
- ✅ Multi-source selection
- ✅ Analysis configuration
- ✅ Report customization

### Risk Dashboard
- ✅ Risk score metrics
- ✅ Vulnerability list
- ✅ Recommendations
- ✅ Trend analysis
- ✅ Peer comparison

### Network Graph
- ✅ Force-directed layout
- ✅ Interactive node selection
- ✅ Relationship visualization
- ✅ Graph statistics
- ✅ Export to PNG

### Timeline
- ✅ Chronological visualization
- ✅ Color-coded event types
- ✅ Zoom controls
- ✅ Event filtering
- ✅ Details panel

---

## System Requirements

- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.8+ (if running from source)
- **RAM**: 512MB minimum (1GB+ recommended)
- **Disk**: 500MB for packaged executable

---

## Troubleshooting

**Application won't start:**
```bash
# Check dependencies
pip install -r requirements_ui.txt

# Run with verbose output
python -v osint_desktop.py
```

**Import errors on macOS:**
```bash
# May need to install system libraries
brew install qt6
```

**Linux display issues:**
```bash
# Set Qt platform
export QT_QPA_PLATFORM=xcb
python osint_desktop.py
```

---

## Backend Integration

The desktop app communicates with the FastAPI backend:

```bash
# Terminal 1: Start backend API
python main.py

# Terminal 2: Start desktop app
python osint_desktop.py
```

Backend should be running at `http://localhost:8000`

---

## Configuration

Optional: Create `config.ini` in app directory:

```ini
[api]
server = http://localhost:8000
timeout = 30

[ui]
theme = dark
window_width = 1400
window_height = 900
```

---

## Next Steps

1. **Investigate**: Use "New Investigation" to start
2. **Explore**: Click through tabs to view different data
3. **Export**: Save results in your preferred format
4. **Share**: Send reports securely

---

## Support

For issues or feature requests, check:
- `logs/osint.log` - Application log file
- Console output - For detailed error messages
- PYQT_DESKTOP_CONVERSION.md - Full documentation

---

**Ready?** Click "New Investigation" to begin!
