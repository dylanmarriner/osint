# OSINT Framework - Quick Start

## Installation (One-time)

```bash
cd /home/fubuntu/Documents/osint/osint-framework
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Start the Server

```bash
source venv/bin/activate
python3 main.py
```

Server runs on: **http://localhost:8000**

## Run Tests

```bash
source venv/bin/activate
python3 -m pytest tests/unit/ -v
```

Expected: **18 tests passing**

## Test the API

```bash
# Health check
curl http://localhost:8000/api/health | python3 -m json.tool

# Should return status: healthy
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `src/core/` | Pipeline components |
| `src/api/app.py` | API endpoints |
| `src/connectors/` | Data source connectors |
| `tests/unit/` | Unit tests |
| `DEBUG_REPORT.md` | Detailed debugging info |
| `TESTING_GUIDE.md` | Testing reference |

## Stop the Server

```bash
# Press Ctrl+C in the terminal running main.py
# Or in another terminal:
pkill -f "python3 main.py"
```

## Troubleshooting

**Port 8000 in use?**
```bash
pkill -f "python3 main.py"
```

**Import errors?**
```bash
# Ensure you're in the correct directory
cd /home/fubuntu/Documents/osint/osint-framework
source venv/bin/activate
```

**Tests not found?**
```bash
source venv/bin/activate
pip install pytest pytest-asyncio
```

## What's Implemented

✓ Core pipeline components (7 components)  
✓ API health check endpoint  
✓ Unit tests (18 passing)  
✓ Data models and validation  
✓ Async/await support  
✓ Error handling and logging  

## What's Needed Next

- Implement data source connectors
- Add investigation endpoints
- Implement WebSocket for real-time updates
- Add integration tests
- Implement report generation endpoints

## Components

1. **DiscoveryEngine** - Generates search queries
2. **FetchManager** - Executes queries with caching
3. **ParseEngine** - Extracts data from responses
4. **NormalizationEngine** - Standardizes data
5. **EntityResolver** - Deduplicates and merges entities
6. **ReportGenerator** - Creates investigation reports
7. **ConnectorRegistry** - Manages data source connectors
