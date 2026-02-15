# OSINT Framework - No External API Keys Required

## Overview

This is a **completely self-contained OSINT framework** that operates without requiring any external API keys. It leverages open-source intelligence techniques, web scraping, local machine learning models, and public data sources to provide professional-grade OSINT capabilities.

## 🚀 Key Features

### **No API Keys Required**
- **Web Scraping**: Advanced scraping with Selenium, Playwright, and BeautifulSoup
- **Public Data Sources**: Uses publicly available information only
- **Local ML Models**: All machine learning runs locally
- **Open Source Intelligence**: Leverages public databases and archives

### **Advanced Capabilities**
- **Multi-Source Intelligence**: Google, Bing, GitHub, LinkedIn (public data)
- **Entity Extraction**: Advanced NLP with spaCy and NLTK
- **Behavioral Analysis**: Pattern recognition and anomaly detection
- **Threat Intelligence**: MITRE ATT&CK framework integration
- **Professional Reporting**: Interactive visualizations and compliance reports

### **Enterprise Features**
- **Advanced Caching**: Memory and file-based caching systems
- **Circuit Breakers**: Automatic failover and reliability
- **Performance Monitoring**: Comprehensive metrics and health checks
- **Security Analysis**: Local threat detection and risk assessment

## 📦 Installation

### **Quick Start**
```bash
# Clone the repository
git clone https://github.com/your-org/osint-framework.git
cd osint-framework

# Install dependencies (no API keys version)
pip install -r requirements_no_api.py

# Start the framework
python main.py
```

### **Docker Setup**
```bash
# Build the no-API-keys image
docker build -f Dockerfile.no-api -t osint-framework:no-api .

# Run the container
docker run -p 8000:8000 osint-framework:no-api
```

## 🔧 Configuration

### **Environment Variables**
```bash
# No API keys required - just basic configuration
export OSINT_FRAMEWORK_DEBUG=false
export OSINT_FRAMEWORK_CACHE_DIR=./cache
export OSINT_FRAMEWORK_LOG_LEVEL=INFO
export OSINT_FRAMEWORK_MAX_CONCURRENT_REQUESTS=10
```

### **Configuration File**
```yaml
# config/no_api_config.yaml
framework:
  name: "OSINT Framework"
  version: "2.0.0"
  mode: "no_api_keys"
  
cache:
  backend: "memory"
  ttl: 3600
  max_size: 10000
  
scraping:
  user_agent: "OSINT-Framework/2.0 (No API Keys)"
  delay_between_requests: 2
  max_retries: 3
  
sources:
  google:
    enabled: true
    type: "scraping"
  bing:
    enabled: true
    type: "scraping"
  github:
    enabled: true
    type: "public_api"
  linkedin:
    enabled: true
    type: "scraping"
```

## 🎯 Usage Examples

### **Basic Investigation**
```python
from src.core.pipeline.enhanced_discovery import EnhancedDiscoveryEngine
from src.core.pipeline.enhanced_fetch_no_api import EnhancedFetchManager
from src.core.pipeline.enhanced_parse import EnhancedParseEngine
from src.core.pipeline.enhanced_resolve import EnhancedEntityResolver
from src.core.pipeline.enhanced_report import EnhancedReportGenerator

# Initialize components
discovery = EnhancedDiscoveryEngine()
fetch_manager = EnhancedFetchManager()
parser = EnhancedParseEngine()
resolver = EnhancedEntityResolver()
reporter = EnhancedReportGenerator()

# Create investigation input
investigation_input = InvestigationInput(
    investigation_id="example-001",
    subject_identifiers=SubjectIdentifiers(
        full_name="John Doe",
        known_usernames=["johndoe", "john_doe"],
        email_addresses=["john.doe@example.com"],
        phone_numbers=["+1-555-0123"]
    )
)

# Run investigation
query_plan = await discovery.generate_enhanced_query_plan(investigation_input)
results = await fetch_manager.fetch_batch(query_plan.queries)
parsed_results = await parser.parse_entities_batch(results)
resolved_entities = await resolver.resolve_entities_enhanced(parsed_results)
report = await reporter.generate_enhanced_report(resolved_entities, investigation_input.investigation_id)

# Export report
html_report = await reporter.export_enhanced_report(report, ReportFormat.HTML)
with open("investigation_report.html", "w") as f:
    f.write(html_report)
```

### **Web Interface**
```bash
# Start the web interface
python main.py

# Access the UI
open http://localhost:8000
```

### **Command Line Interface**
```bash
# Quick investigation
python -m src.cli investigate --name "John Doe" --email "john.doe@example.com"

# Batch processing
python -m src.cli batch --input investigations.csv --output results/

# Configuration management
python -m src.cli config --show
python -m src.cli config --set scraping.delay=3
```

## 🔍 Data Sources

### **Search Engines**
- **Google**: Advanced search operators and scraping
- **Bing**: Microsoft Bing search with scraping
- **DuckDuckGo**: Privacy-focused search
- **Startpage**: Meta search engine

### **Social Networks**
- **LinkedIn**: Public profile scraping
- **Twitter**: Public tweet analysis
- **Instagram**: Public post analysis
- **Facebook**: Public information scraping

### **Code Repositories**
- **GitHub**: Public repository analysis
- **GitLab**: Public project information
- **Bitbucket**: Public code analysis

### **Professional Networks**
- **LinkedIn**: Professional profile analysis
- **Xing**: European professional network
- **Viadeo**: Professional networking

### **Public Records**
- **Company Registries**: Business information
- **Court Records**: Legal proceedings
- **Property Records**: Real estate information
- **Voter Registration**: Public voter data

## 🛡️ Security Features

### **Local Processing**
- **No External Dependencies**: All processing happens locally
- **Data Privacy**: No data sent to external services
- **Offline Capability**: Works without internet connection for cached data

### **Advanced Security**
- **Input Validation**: Comprehensive input sanitization
- **Output Redaction**: Automatic sensitive data redaction
- **Audit Trails**: Complete operation logging
- **Access Control**: Role-based access management

### **Compliance**
- **GDPR Ready**: Built-in compliance features
- **Data Minimization**: Only collect necessary data
- **Retention Policies**: Automatic data cleanup
- **Consent Management**: User consent tracking

## 📊 Advanced Analytics

### **Behavioral Analysis**
- **Pattern Recognition**: Identify behavioral patterns
- **Anomaly Detection**: Detect unusual behavior
- **Temporal Analysis**: Time-based pattern analysis
- **Network Analysis**: Relationship mapping

### **Threat Intelligence**
- **MITRE ATT&CK**: Attack framework integration
- **IOC Extraction**: Indicator of compromise identification
- **Risk Scoring**: Automated risk assessment
- **Threat Modeling**: Comprehensive threat analysis

### **Predictive Analytics**
- **Risk Prediction**: Future risk assessment
- **Behavior Forecasting**: Predict behavior patterns
- **Trend Analysis**: Identify emerging trends
- **Early Warning**: Proactive threat detection

## 📈 Performance

### **Optimization Features**
- **Intelligent Caching**: Multi-level caching system
- **Circuit Breakers**: Automatic failover protection
- **Rate Limiting**: Respectful source interaction
- **Concurrent Processing**: Parallel data collection

### **Monitoring**
- **Real-time Metrics**: Performance monitoring
- **Health Checks**: System health monitoring
- **Alert System**: Automated alerting
- **Resource Tracking**: Resource usage monitoring

## 🔧 Customization

### **Adding New Sources**
```python
from src.connectors.base import BaseConnector

class CustomConnector(BaseConnector):
    async def search(self, query: str, metadata: dict) -> List[SearchResult]:
        # Implement custom search logic
        pass
    
    def get_rate_limit(self) -> int:
        return 100  # Requests per hour

# Register the connector
from src.core.registry import connector_registry
connector_registry.register("custom", CustomConnector())
```

### **Custom Parsers**
```python
from src.core.pipeline.enhanced_parse import EnhancedParseEngine

class CustomParser(EnhancedParseEngine):
    async def parse_custom_format(self, content: str) -> List[Entity]:
        # Implement custom parsing logic
        pass
```

### **Custom Reports**
```python
from src.core.pipeline.enhanced_report import EnhancedReportGenerator

class CustomReporter(EnhancedReportGenerator):
    async def generate_custom_report(self, entities: List[Entity]) -> str:
        # Implement custom report generation
        pass
```

## 🚀 Deployment

### **Production Deployment**
```bash
# Using Docker Compose
docker-compose -f docker-compose.no-api.yml up -d

# Using Kubernetes
kubectl apply -f k8s/no-api-deployment.yaml
```

### **Scaling**
```yaml
# docker-compose.no-api.yml
version: '3.8'
services:
  osint-framework:
    image: osint-framework:no-api
    deploy:
      replicas: 3
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

## 📚 Documentation

### **API Documentation**
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Spec**: `http://localhost:8000/openapi.json`

### **User Guide**
- [Getting Started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [Data Sources](docs/data-sources.md)
- [Security](docs/security.md)

### **Developer Guide**
- [Architecture](docs/architecture.md)
- [Extending](docs/extending.md)
- [Contributing](docs/contributing.md)
- [API Reference](docs/api-reference.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### **Development Setup**
```bash
# Clone the repository
git clone https://github.com/your-org/osint-framework.git
cd osint-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements_no_api.py
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linting
black src/
flake8 src/
mypy src/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Important Notes

### **Legal and Ethical Use**
- **Compliance Only**: Use only for legal and ethical purposes
- **Consent Required**: Ensure proper consent for data collection
- **Respect Privacy**: Follow privacy laws and regulations
- **Terms of Service**: Respect website terms of service

### **No API Keys Required**
- **Public Data Only**: Uses only publicly available information
- **Rate Limiting**: Respects website rate limits
- **Polite Scraping**: Implements delays between requests
- **Local Processing**: All data processing happens locally

### **Disclaimer**
This framework is designed for legitimate OSINT purposes only. Users are responsible for ensuring compliance with applicable laws and regulations. The authors are not responsible for misuse of this software.

## 🆘 Support

- **Documentation**: [Full Documentation](https://osint-framework.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/your-org/osint-framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/osint-framework/discussions)
- **Security**: [Security Policy](https://github.com/your-org/osint-framework/security)

## 🎯 Roadmap

### **Version 2.1**
- [ ] Enhanced dark web analysis
- [ ] Mobile app support
- [ ] Advanced geospatial analysis
- [ ] Machine learning model training

### **Version 2.2**
- [ ] Distributed processing
- [ ] Advanced visualization
- [ ] Real-time collaboration
- [ ] Mobile forensic integration

### **Version 3.0**
- [ ] AI-powered investigation assistant
- [ ] Automated report generation
- [ ] Advanced threat modeling
- [ ] Integration with security tools

---

**OSINT Framework - Professional Intelligence Without API Keys**

Built with ❤️ for the OSINT community
