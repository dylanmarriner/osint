# OSINT Framework

A privacy-focused Open Source Intelligence (OSINT) investigation framework designed for digital risk assessment and identity protection.

## Features

- **Comprehensive Pipeline**: Discovery → Fetch → Parse → Normalize → Resolve → Report
- **Multi-Source Support**: Extensible connector system for various data sources
- **Real-time UI**: Web-based interface with WebSocket updates
- **Security-First Design**: Input validation, data redaction, and secure defaults
- **Production Ready**: Complete error handling, logging, and monitoring

## Quick Start

### Prerequisites

- Python 3.8+
- Required packages listed in `requirements.txt`

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd osint-framework

# Install dependencies
pip install -r requirements.txt

# Run the framework
python main.py
```

The web interface will be available at `http://localhost:8000`

## Architecture

### Core Components

1. **Discovery Engine**: Generates optimized search queries from seed identifiers
2. **Fetch Manager**: Executes queries with rate limiting and caching
3. **Parse Engine**: Extracts entities from HTML, JSON, XML, and text content
4. **Normalization Engine**: Standardizes data formats and applies quality scoring
5. **Entity Resolution**: Merges duplicate entities with confidence scoring
6. **Report Generator**: Creates comprehensive reports in multiple formats

### Data Flow

```
Input Validation → Query Generation → Parallel Fetching → 
Content Parsing → Data Normalization → Entity Resolution → 
Report Generation → Output
```

## Web Interface

- **Investigation Input**: Form-based investigation creation
- **Real-time Progress**: Live updates via WebSocket
- **Results Visualization**: Interactive entity cards with confidence scores
- **Report Export**: JSON, Markdown, and HTML formats
- **Activity Monitoring**: Real-time logs and metrics

## Security Features

- Input validation with comprehensive error handling
- Data redaction for sensitive information in logs
- Rate limiting and request throttling
- Security validation for malicious content
- Audit logging for all operations

## Configuration

The framework supports configuration through:

- Environment variables for sensitive settings
- Configuration files for connector settings
- Runtime parameters for investigation constraints

## Development

### Project Structure

```
osint-framework/
├── src/
│   ├── core/           # Core pipeline components
│   ├── connectors/      # Data source connectors
│   ├── api/           # Web interface
│   └── utils/          # Utility functions
├── tests/              # Test suite
├── config/             # Configuration files
├── docs/               # Documentation
└── requirements.txt     # Dependencies
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python -m pytest tests/test_discovery.py -v
```

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Monitoring

The framework includes comprehensive monitoring:

- Structured logging with correlation IDs
- Performance metrics for all pipeline stages
- Health checks for all components
- Error tracking and alerting

## License

This framework is designed for ethical OSINT investigations focused on privacy protection and security assessment.

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new features
3. Update documentation for any changes
4. Ensure all security measures are maintained

## Support

For issues and questions, please refer to the project documentation or create an issue in the repository.
