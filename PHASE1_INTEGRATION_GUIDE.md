# Phase 1 Integration Guide

## Quick Start: Using Phase 1 Enhancements

### 1. Advanced Entity Matching

```python
from src.core.resolution.advanced_matching import AdvancedMatcher

matcher = AdvancedMatcher()

# Compare two entity records
entity1 = {
    'name': 'John Smith',
    'email': 'john.smith@techcorp.com',
    'phone': '+1-555-1234'
}

entity2 = {
    'name': 'Jon Smyth',
    'email': 'jon+work@gmail.com',
    'phone': '555-1234'
}

# Get match score
confidence, results = await matcher.match_entities(entity1, entity2)
print(f"Match confidence: {confidence:.1f}%")
# Output: Match confidence: 87.5%

# Get detailed results
for field, match_result in results.items():
    print(f"{field}: {match_result.confidence:.1f}% - {match_result.reasoning}")
```

### 2. Entity Graph Construction

```python
from src.core.graph.entity_graph import EntityGraph, RelationshipType

graph = EntityGraph()

# Add entities
person = graph.add_node(
    'john_smith_1',
    'person',
    {'name': 'John Smith', 'email': 'john@example.com'},
    confidence=0.95,
    sources=['LinkedIn']
)

company = graph.add_node(
    'techcorp_1',
    'company',
    {'name': 'TechCorp Inc', 'founded': 2015},
    confidence=0.90
)

# Add relationships
graph.add_edge(
    'john_smith_1',
    'techcorp_1',
    RelationshipType.WORKS_WITH,
    strength=0.8,
    confidence=0.85,
    metadata={'title': 'Senior Engineer', 'years': 5}
)

# Analyze network
ego_network = graph.get_ego_network('john_smith_1', depth=2)
print(f"Ego network size: {len(ego_network.nodes)} nodes")

pagerank = graph.compute_pagerank()
print(f"John's importance score: {pagerank['john_smith_1']:.3f}")

path = graph.find_shortest_path('john_smith_1', 'another_entity')
if path:
    print(f"Connection path: {' -> '.join(path)}")
```

### 3. Timeline Construction

```python
from src.core.timeline.timeline_engine import TimelineEngine, EventType
from datetime import datetime

timeline = TimelineEngine()

# Add life events
timeline.add_event(
    EventType.BIRTH,
    'john_smith_1',
    'Birth',
    date=datetime(1990, 5, 15),
    confidence=0.85,
    sources=['Official records']
)

timeline.add_event(
    EventType.UNIVERSITY_GRADUATION,
    'john_smith_1',
    'Graduated from State University',
    date=datetime(2012, 6, 1),
    confidence=0.90,
    sources=['LinkedIn']
)

timeline.add_event(
    EventType.JOB_START,
    'john_smith_1',
    'Started at TechCorp',
    date=datetime(2018, 1, 15),
    location='San Francisco, CA',
    confidence=0.95,
    sources=['LinkedIn', 'Company website']
)

# Get lifespan summary
summary = timeline.get_lifespan_summary('john_smith_1')
print(f"Age: {summary['estimated_age']} years old")
print(f"Major milestones: {len(summary['major_milestones'])}")

# Get activity patterns
activity = timeline.get_activity_timeline('john_smith_1', bucket='year')
print(f"Events by year: {activity}")

# Get most active periods
busy_periods = timeline.get_most_active_periods('john_smith_1', top_n=5)
print(f"Most active periods: {busy_periods}")
```

### 4. Breach Database Searches

```python
from src.connectors.breach.hibp import HAVEIBEENPWNEDConnector
from src.connectors.breach.dehashed import DehashededConnector

# HaveIBeenPwned search
hibp = HAVEIBEENPWNEDConnector(api_key='your_api_key')
result = await hibp.search({'email': 'john@example.com'})

if result.success and result.parsed_entities:
    for exposure in result.parsed_entities:
        if exposure['type'] == 'breach_exposure':
            print(f"Found in breach: {exposure['breach_name']} ({exposure['breach_date']})")
            print(f"Data exposed: {', '.join(exposure['data_classes'])}")

# Dehashed search (requires API credentials)
dehashed = DehashededConnector(
    api_key='your_dehashed_api_key',
    email='your_dehashed_email@example.com'
)

result = await dehashed.search({'email': 'john@example.com'})
if result.success:
    for leak in result.parsed_entities:
        if leak['type'] == 'credential_leak':
            print(f"Database: {leak['database_name']}")
            print(f"Username: {leak['username']}")
            print(f"Risk score: {leak['risk_score']:.2f}")
```

### 5. Historical Data from Wayback Machine

```python
from src.connectors.archives.wayback_machine import WaybackMachineConnector

wayback = WaybackMachineConnector()

# Get all snapshots of a domain
result = await wayback.search({
    'domain': 'example.com',
    'start_date': '2010-01-01',
    'end_date': '2023-12-31'
})

if result.success:
    snapshots = result.parsed_entities
    print(f"Found {len(snapshots)} snapshots")
    
    # Show oldest and newest
    oldest = min(snapshots, key=lambda s: s['snapshot_date'])
    newest = max(snapshots, key=lambda s: s['snapshot_date'])
    
    print(f"Oldest snapshot: {oldest['snapshot_date']} (Status: {oldest['http_status']})")
    print(f"Newest snapshot: {newest['snapshot_date']} (Status: {newest['http_status']})")
    print(f"Wayback URL: {oldest['wayback_url']}")
```

---

## Integration with Existing Pipeline

### In Your Investigation Workflow:

```python
from src import get_connector_registry, get_entity_resolver
from src.core.graph.entity_graph import EntityGraph
from src.core.timeline.timeline_engine import TimelineEngine
from src.core.resolution.advanced_matching import AdvancedMatcher

async def comprehensive_investigation(email):
    """Demonstrate full Phase 1 integration."""
    
    # 1. Get breach information
    registry = get_connector_registry()
    hibp = registry.get_connector("HaveIBeenPwned")
    breach_result = await hibp.search({'email': email})
    
    # 2. Create entity graph
    graph = EntityGraph()
    graph.add_node(f'email_{email}', 'email_address', {'email': email})
    
    # 3. Build timeline
    timeline = TimelineEngine()
    
    # 4. Use advanced matching
    matcher = AdvancedMatcher()
    
    # 5. Continue with other connectors
    github = registry.get_connector("GitHub")
    linkedin = registry.get_connector("LinkedIn")
    
    # Process and merge results
    all_entities = {}
    
    # Add breach contacts to graph
    for exposure in breach_result.parsed_entities:
        entity_id = f"breach_{exposure.get('breach_name')}"
        graph.add_node(
            entity_id,
            'breach_event',
            exposure,
            confidence=breach_result.parsed_entities[0].get('confidence', 0.85)
        )
    
    # Add historical data
    wayback = registry.get_connector("Wayback Machine")
    # ... process wayback data
    
    # Export results
    return {
        'graph': graph.to_dict(),
        'timeline': timeline.to_dict(f'email_{email}'),
        'breaches': breach_result.parsed_entities
    }
```

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# HaveIBeenPwned
HIBP_API_KEY=your_api_key_here

# Dehashed
DEHASHED_API_KEY=your_api_key_here
DEHASHED_EMAIL=your_email@example.com

# General
TIMELINE_RETENTION_DAYS=90
GRAPH_CACHE_SIZE=10000
MATCHER_CONFIDENCE_THRESHOLD=75.0
```

### Python Configuration

```python
from src.core.resolution.advanced_matching import AdvancedMatcher, MatchingAlgorithm

# Customize matcher weights
matcher = AdvancedMatcher()
custom_weights = {
    'name': 0.25,
    'email': 0.35,  # Higher weight for email
    'phone': 0.20,
    'username': 0.10,
    'biographical': 0.10
}

confidence, results = await matcher.match_entities(
    entity1, entity2,
    weights=custom_weights
)
```

---

## Performance Considerations

### Memory Usage:
- **Entity Graph**: ~1KB per node + edges
  - 10,000 nodes = ~10MB
  - 50,000 edges = ~50MB
- **Timeline**: ~500 bytes per event
  - 10,000 events = ~5MB
- **Matcher Cache**: Minimal (computed on demand)

### Query Performance:
- **Shortest path**: O(V+E), <100ms for 10K node graph
- **PageRank**: O(V+E) per iteration, 20 iterations default
- **Community detection**: O(V+E), <500ms for 10K nodes
- **Entity matching**: O(1) for exact match, O(n) for fuzzy match

### Rate Limiting:
- **HIBP**: 1,800 req/hr (30/min with key, 1/min without)
- **Dehashed**: 600 req/hr (10/min)
- **Wayback**: 1,200 req/hr (20/min)
- Connectors auto-respect limits via `_check_rate_limit()`

---

## Troubleshooting

### Issue: "API Key invalid" for HIBP
**Solution**: HIBP requires API key for reliability. Free-plan limited to 1 req/min.

### Issue: Wayback Machine no results
**Solution**: Not all domains have historical snapshots. Try major sites like github.com/example.com.

### Issue: Entity matching confidence too low
**Solution**: Adjust weights in `match_entities()` or lower confidence_threshold.

### Issue: Graph out of memory
**Solution**: Use `get_ego_network()` to extract subgraphs instead of entire graph.

---

## Next Steps

After Phase 1, you can:

1. **Add More Connectors** (Phase 2):
   - Shodan, Censys, OpenCorporates, SEC EDGAR
   - Estimated +4 connectors = 11 total

2. **Advanced Analytics**:
   - Behavioral pattern detection
   - Income/career prediction
   - Writing style analysis

3. **UI Enhancements**:
   - Interactive timeline viewer
   - Network visualization (D3.js)
   - Risk dashboard

4. **Performance**:
   - Implement Redis caching
   - Database indexing
   - Parallel processing

See `COMPREHENSIVE_OVERHAUL_PLAN.md` for the full roadmap.

