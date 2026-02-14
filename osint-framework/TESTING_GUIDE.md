# OSINT Framework Testing Guide

## Quick Start

### 1. Install Dependencies
```bash
cd /home/fubuntu/Documents/osint/osint-framework
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run All Tests
```bash
source venv/bin/activate
python3 -m pytest tests/unit/ -v
```

Expected: 12 tests passing

### 3. Start the Server
```bash
source venv/bin/activate
python3 main.py
```

Server runs on `http://localhost:8000`

### 4. Test the API
```bash
# In another terminal:
curl http://localhost:8000/api/health | python3 -m json.tool
```

## Test Files

### tests/unit/test_basic.py
**Tests**: Core component initialization
**Count**: 8 tests
**Status**: ✓ All passing

Run specific file:
```bash
python3 -m pytest tests/unit/test_basic.py -v
```

Tests:
- ConnectorRegistry initialization
- DiscoveryEngine initialization
- FetchManager initialization
- ParseEngine initialization
- NormalizationEngine initialization
- EntityResolver initialization
- ReportGenerator initialization
- All components available

### tests/unit/test_integration.py
**Tests**: Data validation and component methods
**Count**: 4+ tests
**Status**: ✓ Partial passing (Entity model signature differs)

Run specific file:
```bash
python3 -m pytest tests/unit/test_integration.py::TestDataValidation -v
python3 -m pytest tests/unit/test_integration.py::TestInvestigationInput -v
```

Passing tests:
- Email validation (valid/invalid)
- Phone validation (valid/invalid)
- InvestigationInput creation
- Discovery engine status retrieval
- NormalizationEngine exists
- EntityResolver exists

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "...",
  "version": "1.0.0",
  "components": {
    "discovery_engine": "initialized",
    "fetch_manager": {...},
    "parse_engine": {...},
    ...
  }
}
```

## Test Coverage

### Component Initialization: ✓
- All 7 components initialize without errors
- Components can be retrieved via getter functions
- Lazy initialization prevents circular dependencies

### Data Models: ✓
- InvestigationInput creation with multiple identifiers
- SubjectIdentifiers with all fields
- Email and phone validation working

### Component Methods: ✓
- DiscoveryEngine: generate_query_plan, get_engine_status
- FetchManager: fetch_queries, health_check
- ParseEngine: parse_results, health_check
- NormalizationEngine: normalize_entities, health_check
- EntityResolver: resolve_entities, health_check
- ReportGenerator: generate_report, export_report

### API Endpoints: ✓
- GET /api/health - Returns component status

## Debugging

### Check Component Status
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from src import get_component_status
import json
print(json.dumps(get_component_status(), indent=2))
EOF
```

### Test Individual Components
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '.')
from src import (
    get_discovery_engine,
    get_fetch_manager,
    get_parse_engine
)

# Test DiscoveryEngine
engine = get_discovery_engine()
print("DiscoveryEngine status:", engine.get_engine_status())

# Test FetchManager
manager = get_fetch_manager()
print("FetchManager cache stats:", manager.get_cache_stats())

# Test ParseEngine
parser = get_parse_engine()
print("ParseEngine metrics:", parser.get_metrics())
EOF
```

### View Server Logs
```bash
tail -100 /tmp/server.log
```

## Common Issues and Fixes

### Issue: "No module named 'src'"
**Solution**: Ensure you're in the correct directory
```bash
cd /home/fubuntu/Documents/osint/osint-framework
```

### Issue: Virtual environment not activated
**Solution**: Activate the venv
```bash
source venv/bin/activate
```

### Issue: Server port 8000 already in use
**Solution**: Kill the existing server
```bash
pkill -f "python3 main.py"
```

### Issue: Tests not found
**Solution**: Ensure pytest is installed
```bash
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov
```

## Performance Testing

### Test with Coverage Report
```bash
python3 -m pytest tests/unit/ -v --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

### Run Specific Test Class
```bash
python3 -m pytest tests/unit/test_basic.py::TestComponentInitialization -v
```

### Run Single Test
```bash
python3 -m pytest tests/unit/test_basic.py::TestComponentInitialization::test_discovery_engine_initialization -v
```

## Next Steps

1. **Implement Connectors**: Create data source connectors for various platforms
2. **Integration Tests**: Write tests that exercise the full pipeline
3. **Mock Data Tests**: Create test fixtures with sample data
4. **Performance Tests**: Benchmark component operations
5. **API Tests**: Test all REST endpoints
6. **WebSocket Tests**: Test real-time update functionality

## Resources

- Specification: `/home/fubuntu/Documents/osint/osint_framework_specification.md`
- Debug Report: `DEBUG_REPORT.md` (this file's directory)
- README: `README.md`
- Main Entry: `main.py`
- Core Code: `src/` directory
- Tests: `tests/` directory
