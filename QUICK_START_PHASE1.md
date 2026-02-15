# Quick Start - Phase 1 Enhancements

## Installation

The new modules are already in your codebase. No additional dependencies needed beyond existing requirements.

### Optional API Keys (for full functionality):

```bash
# Add to .env file:
HIBP_API_KEY=your_haveibeenpwned_api_key
DEHASHED_API_KEY=your_dehashed_api_key  
DEHASHED_EMAIL=your_email_for_dehashed
```

---

## 30-Second Tutorial

### Search for Breached Email:

```python
import asyncio
from src.connectors.breach.hibp import HAVEIBEENPWNEDConnector

async def check_breaches():
    hibp = HAVEIBEENPWNEDConnector(api_key='your_key')
    result = await hibp.search({'email': 'target@example.com'})
    
    for breach in result.parsed_entities:
        print(f"Found in {breach['breach_name']}: {breach['breach_date']}")
        print(f"Data exposed: {breach['data_classes']}")

asyncio.run(check_breaches())
```

### Build Entity Graph:

```python
from src.core.graph.entity_graph import EntityGraph, RelationshipType

graph = EntityGraph()

# Add people
graph.add_node('alice_1', 'person', {'name': 'Alice'}, confidence=0.9)
graph.add_node('bob_1', 'person', {'name': 'Bob'}, confidence=0.9)
graph.add_node('techcorp', 'company', {'name': 'TechCorp'}, confidence=0.95)

# Connect them
graph.add_edge('alice_1', 'techcorp', RelationshipType.WORKS_WITH, strength=0.85)
graph.add_edge('bob_1', 'techcorp', RelationshipType.WORKS_WITH, strength=0.90)
graph.add_edge('alice_1', 'bob_1', RelationshipType.KNOWS, strength=0.75)

# Find who's important
ranks = graph.compute_pagerank()
print(f"TechCorp importance: {ranks['techcorp']:.3f}")

# Find shortest connection
path = graph.find_shortest_path('alice_1', 'bob_1')
print(f"Alice to Bob: {' -> '.join(path)}")  # ['alice_1', 'techcorp', 'bob_1']
```

### Build Timeline:

```python
from src.core.timeline.timeline_engine import TimelineEngine, EventType
from datetime import datetime

timeline = TimelineEngine()

# Add events
timeline.add_event(
    EventType.JOB_START,
    'alice_1',
    'Started at TechCorp',
    date=datetime(2020, 1, 15),
    sources=['LinkedIn']
)

timeline.add_event(
    EventType.JOB_END,
    'alice_1',
    'Left TechCorp',
    date=datetime(2023, 6, 30),
    sources=['LinkedIn']
)

# Get summary
summary = timeline.get_lifespan_summary('alice_1')
print(f"Total events: {summary['total_events']}")
print(f"Time span: {summary['timespan_years']} years")
```

### Match Entities:

```python
from src.core.resolution.advanced_matching import AdvancedMatcher

matcher = AdvancedMatcher()

entity1 = {
    'name': 'John Smith',
    'email': 'john@company.com',
    'phone': '+1-555-0123'
}

entity2 = {
    'name': 'Jon Smyth',
    'email': 'jon+personal@gmail.com',
    'phone': '555-0123'
}

confidence, results = await matcher.match_entities(entity1, entity2)
print(f"Match confidence: {confidence:.1f}%")  # Usually 85-92%
```

---

## Common Use Cases

### Use Case 1: Check if Email was Breached

```python
async def check_email_security(email):
    hibp = HAVEIBEENPWNEDConnector()
    dehashed = DehashededConnector()
    
    hibp_result = await hibp.search({'email': email})
    dehashed_result = await dehashed.search({'email': email})
    
    print(f"HIBP breaches: {len(hibp_result.parsed_entities)}")
    print(f"Dehashed leaks: {len(dehashed_result.parsed_entities)}")
    
    # Calculate risk
    total_risk = len(hibp_result.parsed_entities) + len(dehashed_result.parsed_entities)
    print(f"Risk level: {'HIGH' if total_risk > 5 else 'MEDIUM' if total_risk > 2 else 'LOW'}")
```

### Use Case 2: Map Someone's Network

```python
async def map_network():
    graph = EntityGraph()
    
    # Add target
    graph.add_node('target', 'person', {'name': 'Target Person'})
    
    # Add connections (from your investigation)
    connections = [
        ('coworker1', 'company', 'TechCorp'),
        ('coworker2', 'company', 'TechCorp'),
        ('friend1', 'person', 'Friend'),
    ]
    
    for entity_id, entity_type, name in connections:
        graph.add_node(entity_id, entity_type, {'name': name})
        graph.add_edge('target', entity_id, RelationshipType.KNOWS)
    
    # Analyze network
    ego = graph.get_ego_network('target', depth=2)
    stats = ego.get_statistics()
    print(f"Network size: {stats['node_count']} people")
    print(f"Network density: {stats['density']:.2%}")
```

### Use Case 3: Reconstruct Someone's Life

```python
async def reconstruct_life(person_id):
    timeline = TimelineEngine()
    
    # Add discovered events
    timeline.add_event(EventType.BIRTH, person_id, "Born", 
        date=datetime(1990, 5, 15), sources=['Official'])
    
    timeline.add_event(EventType.SCHOOL_GRADUATION, person_id, "HS Graduation",
        date=datetime(2008, 6, 1), sources=['Yearbook'])
    
    timeline.add_event(EventType.UNIVERSITY_GRADUATION, person_id, "College Graduation",
        date=datetime(2012, 5, 20), sources=['LinkedIn'])
    
    timeline.add_event(EventType.JOB_START, person_id, "First Job",
        date=datetime(2012, 7, 15), sources=['LinkedIn'])
    
    # Get complete summary
    summary = timeline.get_lifespan_summary(person_id)
    print(f"Age: {summary['estimated_age']}")
    print(f"Career length: {(datetime.now() - summary['major_milestones'][3]['date']).days / 365:.1f} years")
    
    # Show timeline
    for milestone in summary['major_milestones']:
        print(f"- {milestone['title']} ({milestone['date']})")
```

### Use Case 4: Historical Research

```python
async def research_domain_history():
    wayback = WaybackMachineConnector()
    
    result = await wayback.search({
        'domain': 'example.com',
        'start_date': '2010-01-01',
        'end_date': '2023-12-31'
    })
    
    # Get oldest and newest snapshots
    snapshots = result.parsed_entities
    oldest = min(snapshots, key=lambda s: s['timestamp'])
    newest = max(snapshots, key=lambda s: s['timestamp'])
    
    print(f"First snapshot: {oldest['snapshot_date']}")
    print(f"Last snapshot: {newest['snapshot_date']}")
    print(f"Total snapshots: {len(snapshots)}")
    
    # Show status code history
    status_timeline = {}
    for snap in snapshots:
        year = snap['timestamp'][:4]
        status = snap['http_status']
        status_timeline[year] = status_timeline.get(year, 0) + 1
    
    print("Status codes by year:")
    for year in sorted(status_timeline.keys()):
        print(f"  {year}: {status_timeline[year]} snapshots")
```

---

## API Quick Reference

### AdvancedMatcher

```python
matcher = AdvancedMatcher()

# Methods
matcher.levenshtein_ratio(s1, s2)        # 0-1 similarity
matcher.jaro_winkler_similarity(s1, s2)  # 0-1 similarity
matcher.soundex(name)                    # 4-char code
matcher.normalize_email(email)           # Canonical form
matcher.normalize_phone(phone)           # E.164 format
await matcher.match_entities(e1, e2, weights={...})  # Full match
await matcher.link_cross_platform_identities([entities])  # Clusters
```

### EntityGraph

```python
graph = EntityGraph()

# Nodes
graph.add_node(id, type, attrs, confidence=0.5, sources=[])
graph.get_node(id)
graph.remove_node(id)
graph.get_nodes_by_type(type)

# Edges
graph.add_edge(src, tgt, rel_type, strength=0.5, confidence=0.5)
graph.get_edges_from(id)
graph.get_edges_to(id)
graph.remove_edge(edge_id)

# Analysis
graph.get_ego_network(id, depth=2)
graph.find_shortest_path(src, tgt)
graph.compute_pagerank()               # Returns dict of scores
graph.compute_degree_centrality()      # In/out degree
graph.compute_betweenness_centrality() # Bridge importance
graph.community_detection()            # Returns list of clusters
graph.get_statistics()                 # Dict of metrics

# Export
graph.to_dict()    # JSON-serializable dict
graph.to_graphml() # GraphML for visualization
```

### TimelineEngine

```python
timeline = TimelineEngine()

# Events
timeline.add_event(type, subject_id, title, date=None, 
                  date_precision=DatePrecision.EXACT_DATE,
                  location=None, confidence=0.5, 
                  sources=[], urls=[], metadata={})

timeline.get_event(id)
timeline.get_events_for_subject(id, start_date=None, 
                               end_date=None, event_types=None)
timeline.merge_duplicate_events(id1, id2)

# Analysis
timeline.detect_milestones(id)         # Major life events
timeline.estimate_age(id, as_of_date=None)
timeline.get_lifespan_summary(id)      # Complete summary dict
timeline.get_activity_timeline(id, bucket='month')  # Frequency
timeline.get_most_active_periods(id, top_n=5)

# Export
timeline.to_dict(id)  # JSON export
```

### Breach Connectors

```python
# HaveIBeenPwned
hibp = HAVEIBEENPWNEDConnector(api_key='...')
result = await hibp.search({'email': 'test@example.com'})

# Dehashed
dehashed = DehashededConnector(api_key='...', email='...')
result = await dehashed.search({'email': 'test@example.com'})
result = await dehashed.search({'username': 'john_smith'})

# Both return SearchResult with:
# - success: bool
# - parsed_entities: list of dicts
# - error_message: str if failed
```

### Archive Connectors

```python
# Wayback Machine
wayback = WaybackMachineConnector()
result = await wayback.search({
    'domain': 'example.com',
    'start_date': '2010-01-01',  # Optional
    'end_date': '2023-12-31'     # Optional
})

# Returns snapshots with:
# - timestamp: YYYYMMDDHHMMSS
# - snapshot_date: ISO datetime
# - http_status: 200, 404, etc.
# - wayback_url: Direct link to snapshot
```

---

## Debugging Tips

### Enable Verbose Logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now you'll see detailed logs from all modules
```

### Check Entity Graph Size:

```python
stats = graph.get_statistics()
print(f"Nodes: {stats['node_count']}")
print(f"Edges: {stats['edge_count']}")
print(f"Density: {stats['density']:.4f}")
print(f"Communities: {stats['communities']}")
```

### Test Entity Matching:

```python
# Test with identical entities (should be ~100%)
confidence, _ = await matcher.match_entities(
    {'name': 'John Smith', 'email': 'john@example.com'},
    {'name': 'John Smith', 'email': 'john@example.com'}
)
# Should return ~100%

# Test with typos (should be ~85%)
confidence, _ = await matcher.match_entities(
    {'name': 'John Smith'},
    {'name': 'Jon Smyth'}
)
# Should return ~85%
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| "Missing API key" | HIBP needs key | Get from https://haveibeenpwned.com/api/key |
| "Rate limited" | Too many requests | Wait, connectors auto-backoff |
| "No snapshots" | Domain not archived | Try example.com, github.com |
| "Memory error" | Graph too large | Use `get_ego_network()` for subgraph |
| "No breaches found" | Email never leaked | Good news! Probably safe |

---

## What's Next?

1. **Explore the code**: Check `PHASE1_INTEGRATION_GUIDE.md` for detailed examples
2. **Run tests**: Create test cases in `tests/` directory
3. **Add more connectors**: Follow patterns in `src/connectors/breach/` and `archives/`
4. **Build UI**: Use graph/timeline JSON output for visualization
5. **Scale up**: See optimization tips in `COMPREHENSIVE_OVERHAUL_PLAN.md`

---

## Resources

- **Detailed Guide**: `PHASE1_INTEGRATION_GUIDE.md`
- **Full Status**: `OVERHAUL_STATUS.md`
- **Architecture**: `COMPREHENSIVE_OVERHAUL_PLAN.md`
- **Implementation Details**: `PHASE1_IMPLEMENTATION_SUMMARY.md`

