# OSINT Framework Connector Usage Guide

## Quick Start

### Initialize the Framework

```python
from src import get_connector_registry, get_discovery_engine, get_fetch_manager

# Get initialized connector registry (auto-initializes all connectors)
registry = get_connector_registry()

# List all available connectors
connectors = registry.list_connectors()
print(f"Available connectors: {connectors}")
```

## Using Individual Connectors

### Google Search Connector

```python
connector = registry.get_connector("Google Search")

# Search for a person
results = await connector.search("John Doe engineer")

# Search with parameters
results = await connector.search(
    "john.doe@example.com",
    params={'num_results': 20}
)
```

### GitHub Connector

```python
connector = registry.get_connector("GitHub")

# Search users
results = await connector.search(
    "johndoe",
    params={'search_type': 'users', 'num_results': 10}
)

# Search repositories
results = await connector.search(
    "security tools",
    params={'search_type': 'repos', 'num_results': 10}
)

# Search code
results = await connector.search(
    "API keys",
    params={'search_type': 'code', 'num_results': 10}
)
```

### LinkedIn Connector

```python
connector = registry.get_connector("LinkedIn")

results = await connector.search(
    "Jane Smith",
    params={'num_results': 10}
)
```

### Twitter/X Connector

```python
connector = registry.get_connector("Twitter/X")

# Search users
results = await connector.search(
    "johndoe",
    params={'search_type': 'users'}
)

# Search posts
results = await connector.search(
    "security breach",
    params={'search_type': 'posts', 'language': 'en'}
)
```

### Reddit Connector

```python
connector = registry.get_connector("Reddit")

# Search users
results = await connector.search(
    "cybersecurity",
    params={'search_type': 'users'}
)

# Search posts
results = await connector.search(
    "hacking tutorial",
    params={'search_type': 'posts', 'sort': 'relevance'}
)
```

### Stack Overflow Connector

```python
connector = registry.get_connector("Stack Overflow")

# Search users
results = await connector.search(
    "Alice Johnson",
    params={'search_type': 'users', 'num_results': 10}
)

# Search posts
results = await connector.search(
    "Python security",
    params={'search_type': 'posts', 'num_results': 10}
)
```

### WHOIS/RDAP Connector

```python
connector = registry.get_connector("WHOIS/RDAP")

# Query domain information
results = await connector.search(
    "example.com",
    params={'num_results': 10}
)
```

### Certificate Transparency Connector

```python
connector = registry.get_connector("Certificate Transparency")

# Find certificates for domain
results = await connector.search(
    "example.com",
    params={'num_results': 50}
)

# Returns all subdomains found in certificate logs
```

## Connector Information

### Get Connector Status

```python
connector = registry.get_connector("GitHub")
status = connector.get_status()

print(f"Status: {status['status']}")
print(f"Rate Limit: {status['rate_limit']}")
```

### Get Connector Details

```python
connector = registry.get_connector("GitHub")

# Basic information
print(f"Name: {connector.source_name}")
print(f"Type: {connector.source_type}")
print(f"Rate Limit: {connector.get_rate_limit()} req/hr")
print(f"Confidence: {connector.get_confidence_weight()}")
print(f"Entity Types: {connector.get_supported_entity_types()}")
```

## Batch Searching

### Search Multiple Connectors

```python
registry = get_connector_registry()

query = "john.doe@example.com"
entity_types = [EntityType.EMAIL_ADDRESS, EntityType.PERSON]

# Search all relevant connectors
results = await registry.search_all_connectors(
    query,
    params={'num_results': 10},
    entity_types=entity_types
)

# Results organized by connector
for connector_name, connector_results in results.items():
    print(f"\n{connector_name}: {len(connector_results)} results")
    for result in connector_results:
        print(f"  - {result.title}")
```

## Configuration

### Set API Credentials

```python
import os

# GitHub token
os.environ['GITHUB_TOKEN'] = 'your_github_token'

# Twitter bearer token
os.environ['TWITTER_BEARER_TOKEN'] = 'your_twitter_token'

# Reinitialize connectors
from src.connectors.manager import get_connector_manager
manager = get_connector_manager()
manager.reload_connectors()
```

### Custom Connector Configuration

```python
from src.connectors import GitHubConnector

# Create connector with custom config
config = {
    'github_token': 'your_token',
    'custom_setting': 'value'
}

connector = GitHubConnector(config)
```

## Result Processing

### Parse Search Results

```python
connector = registry.get_connector("Google Search")
results = await connector.search("john.doe")

# Each result is a SearchResult object
for result in results:
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Content: {result.content}")
    print(f"Confidence: {result.confidence}")
    print(f"Source: {result.source}")
    print(f"Retrieved: {result.retrieved_at}")
```

## Error Handling

```python
import asyncio

connector = registry.get_connector("GitHub")

try:
    results = await connector.search("invalid@query!@#")
except Exception as e:
    print(f"Search failed: {e}")

# Check connector status
if connector.status.value == "error":
    print("Connector encountered an error")
elif connector.status.value == "rate_limited":
    print("Rate limit exceeded, will retry later")
```

## Health Checks

### Monitor Connector Health

```python
# Check all connectors
health = await registry.health_check()

for connector_name, is_healthy in health.items():
    status = "✓ Healthy" if is_healthy else "✗ Unhealthy"
    print(f"{connector_name}: {status}")
```

### Get Registry Metrics

```python
# Get metrics from fetch manager
fetch_manager = get_fetch_manager()
metrics = fetch_manager.get_metrics()

print(f"Success Rate: {metrics['success_rate']:.1f}%")
print(f"Cache Hit Ratio: {metrics['cache_hit_ratio']:.1f}%")
print(f"Active Requests: {metrics['active_requests']}")
print(f"Queued Requests: {metrics['queued_requests']}")

# Per-connector metrics
for connector_name, connector_metrics in metrics['connector_metrics'].items():
    print(f"\n{connector_name}:")
    print(f"  Total: {connector_metrics['total']}")
    print(f"  Completed: {connector_metrics['completed']}")
    print(f"  Failed: {connector_metrics['failed']}")
```

## Integration with Pipeline

### Full Investigation Pipeline

```python
from src import (
    get_connector_registry, get_discovery_engine,
    get_fetch_manager, get_parse_engine,
    get_normalization_engine, get_entity_resolver,
    get_report_generator, InvestigationInput
)
from src.core.models.entities import SubjectIdentifiers

# 1. Create investigation input
subject = SubjectIdentifiers(
    full_name="John Doe",
    known_usernames=["johndoe"],
    email_addresses=["john@example.com"],
    geographic_hints={
        "city": "San Francisco",
        "region": "California"
    }
)

investigation = InvestigationInput(
    investigation_id="inv-001",
    subject_identifiers=subject
)

# 2. Generate queries
discovery = get_discovery_engine()
query_plan = discovery.generate_query_plan(investigation)

print(f"Generated {query_plan.total_queries} queries")

# 3. Execute searches
fetch = get_fetch_manager()
search_results = []

for query in query_plan.queries[:5]:  # First 5 queries
    for connector_name in query.target_connectors:
        connector = registry.get_connector(connector_name)
        if connector:
            results = await connector.search(
                query.query_string,
                query.parameters
            )
            search_results.extend(results)

# 4. Parse results
parser = get_parse_engine()
parse_results = await parser.parse_results(search_results)

# 5. Normalize entities
normalizer = get_normalization_engine()
normalized = await normalizer.normalize_entities(
    [pr.entities for pr in parse_results if pr.entities]
)

# 6. Resolve duplicates
resolver = get_entity_resolver()
resolved = await resolver.resolve_entities(
    [ne.normalized_entity for ne in normalized if ne.normalized_entity]
)

# 7. Generate report
reporter = get_report_generator()
report = reporter.generate_report(
    investigation,
    resolved.resolved_entities
)
```

## Performance Tips

1. **Use rate limits wisely**: Adjust `max_search_depth` in investigation constraints
2. **Enable caching**: Fetch manager caches results by default (TTL: 60 minutes)
3. **Parallel searches**: Multiple queries execute in parallel via asyncio
4. **Monitor metrics**: Track success rates and cache hit ratios
5. **Retry strategy**: Exponential backoff for failed requests (max 5 minutes)

## Troubleshooting

### Connector Not Initializing

```python
from src.connectors.manager import get_connector_manager

manager = get_connector_manager()
print(f"Initialized: {manager._initialized}")

# Try reinitializing
manager.reload_connectors()
```

### Rate Limiting Issues

```python
connector = registry.get_connector("GitHub")
print(f"Rate limit: {connector.rate_limit.requests_per_hour}")
print(f"Current: {connector.rate_limit.current_requests}")
print(f"Reset time: {connector.rate_limit.reset_time}")
```

### Authentication Failures

```python
connector = registry.get_connector("GitHub")
is_valid = await connector.validate_credentials()

if not is_valid:
    print("Invalid or missing credentials")
    print("Set GITHUB_TOKEN environment variable")
```

## See Also

- `osint_framework_specification.md` - Framework architecture
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `src/connectors/` - Connector source code
- `src/core/models/entities.py` - Data models
