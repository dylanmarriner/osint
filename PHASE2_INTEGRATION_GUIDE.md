# Phase 2 Integration Guide

## Quick Start - Integrating New Components

### 1. Register New Connectors

In `src/connectors/__init__.py` or your connector manager:

```python
from src.connectors.advanced.greynoise import GreyNoiseConnector
from src.connectors.records.opencorporates import OpenCorporatesConnector
from src.connectors.records.uspto import USPTOConnector
from src.connectors.funding.crunchbase import CrunchbaseConnector

# Register connectors
registry.register(GreyNoiseConnector(api_key=GREYNOISE_KEY))
registry.register(OpenCorporatesConnector(api_token=OPENCORP_TOKEN))
registry.register(USPTOConnector())
registry.register(CrunchbaseConnector(api_key=CRUNCHBASE_KEY))
```

### 2. Initialize Caching

In your FastAPI app startup:

```python
from src.utils.cache import get_cache, shutdown_cache

@app.on_event("startup")
async def startup_event():
    cache = await get_cache()
    await cache.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await shutdown_cache()
```

### 3. Add Analytics Endpoints

```python
from src.core.analytics.predictive import PredictiveAnalytics
from src.core.analytics.trends import TrendAnalyzer

@app.post("/api/analysis/predict-location")
async def predict_location(entity_id: str, timeline_events: List[Dict]):
    predictor = PredictiveAnalytics()
    result = await predictor.predict_location(entity, historical_locs, timeline_events)
    return result

@app.post("/api/analysis/track-sentiment")
async def track_sentiment(entity_id: str, posts: List[Dict]):
    analyzer = TrendAnalyzer()
    trend = await analyzer.track_sentiment(entity_id, posts)
    return trend
```

### 4. Integrate UI Components

In your Vue.js app (`main.js` or app initialization):

```javascript
import TimelineViewer from '@/components/TimelineViewer.vue'
import NetworkGraph from '@/components/NetworkGraph.vue'
import RiskDashboard from '@/pages/RiskDashboard.vue'
import InvestigationWizard from '@/pages/InvestigationWizard.vue'

// Register components globally or in specific routes
export default {
  components: {
    TimelineViewer,
    NetworkGraph,
    RiskDashboard,
    InvestigationWizard
  }
}
```

---

## Connector Configuration

### Environment Variables

Create `.env` file with:

```bash
# GreyNoise
GREYNOISE_API_KEY=your_api_key

# OpenCorporates
OPENCORPORATES_API_TOKEN=your_token

# Crunchbase
CRUNCHBASE_API_KEY=your_api_key

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### API Key Management

```python
from src.config import Config

# Load from environment
greynoise = GreyNoiseConnector(api_key=Config.GREYNOISE_API_KEY)
crunchbase = CrunchbaseConnector(api_key=Config.CRUNCHBASE_API_KEY)
```

---

## API Endpoints (New)

### Predictive Analytics

```
POST /api/analysis/predict-location
{
  "entity_id": "john_doe",
  "historical_locations": [...],
  "timeline_events": [...]
}
Response:
{
  "prediction_id": "uuid",
  "location": "San Francisco, CA",
  "confidence": 0.75,
  "reasoning": [...]
}
```

```
POST /api/analysis/predict-career
{
  "entity_id": "john_doe",
  "employment_history": [...],
  "education": [...],
  "skills": [...]
}
Response:
{
  "current_role": "Senior Engineer",
  "predicted_next_roles": ["Tech Lead", "Engineering Manager"],
  "timeline": "24 months"
}
```

```
POST /api/analysis/estimate-income
{
  "entity_id": "john_doe",
  "employment_history": [...],
  "education": [...],
  "location": "San Francisco"
}
Response:
{
  "estimated_income": 165000,
  "income_range": [132000, 198000],
  "confidence": 0.55
}
```

### Trend Analysis

```
POST /api/analysis/track-sentiment
{
  "entity_id": "john_doe",
  "posts": [...],
  "lookback_days": 365
}
Response:
{
  "trend_id": "uuid",
  "overall_trend": "increasing",
  "current_value": 0.65,
  "volatility": 0.15
}
```

```
POST /api/analysis/extract-topics
{
  "entity_id": "john_doe",
  "content_timeline": [...],
  "lookback_days": 365
}
Response:
[
  {
    "topic": "AI/ML",
    "introduction_date": "2022-01-15",
    "engagement_trend": "growing",
    "current_interest": 0.85
  }
]
```

```
POST /api/analysis/network-growth-rate
{
  "entity_id": "john_doe",
  "graph_snapshots": [["2023-01-01", 100], ["2023-02-01", 150]]
}
Response:
{
  "growth_rate_monthly": 3.2,
  "growth_acceleration": 0.8,
  "confidence": 0.70
}
```

### Connector Operations

```
POST /api/connectors/greynoise/lookup
{
  "ip": "8.8.8.8"
}

GET /api/connectors/opencorporates/search
?company_name=Apple&jurisdiction=us_ca

POST /api/connectors/uspto/search
{
  "inventor": "John Smith"
}

POST /api/connectors/crunchbase/search
{
  "company_name": "Stripe"
}
```

### Cache Management

```
GET /api/cache/stats
Response:
{
  "hits": 1234,
  "misses": 567,
  "hit_rate": 0.685,
  "total_requests": 1801
}

POST /api/cache/clear
Response: { "status": "cleared" }

GET /api/cache/cleanup
Response: { "removed": 23 }
```

---

## Database Queries

### Store Investigation Results

```python
# In your database models
class Investigation(Base):
    id = Column(String, primary_key=True)
    entity_id = Column(String)
    entity_type = Column(String)
    created_at = Column(DateTime)
    
    # Results
    timeline_data = Column(JSON)
    graph_data = Column(JSON)
    risk_assessment = Column(JSON)
    
    # Analytics
    predictions = Column(JSON)
    trends = Column(JSON)
    
    # Report
    report_path = Column(String)
    generated_at = Column(DateTime)
```

### Query Results

```python
# Get investigation
investigation = db.query(Investigation).filter(
    Investigation.id == investigation_id
).first()

# Get latest risk assessment
latest_risk = investigation.risk_assessment

# Get trend data
trends = investigation.trends
```

---

## Testing Guide

### Test Connectors

```python
import pytest
from src.connectors.advanced.greynoise import GreyNoiseConnector

@pytest.mark.asyncio
async def test_greynoise_lookup_ip():
    connector = GreyNoiseConnector(api_key="test_key")
    result = await connector._lookup_ip("8.8.8.8")
    assert result is not None
    assert "ip" in result
    assert "classification" in result

@pytest.mark.asyncio
async def test_opencorporates_search():
    connector = OpenCorporatesConnector()
    result = await connector._search_companies("Apple Inc")
    assert len(result) > 0
    assert "name" in result[0]
```

### Test Analytics

```python
@pytest.mark.asyncio
async def test_predict_location():
    predictor = PredictiveAnalytics()
    entity = Entity(entity_id="test", name="Test")
    
    locations = [
        {"location": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
        {"location": "San Francisco", "latitude": 37.7749, "longitude": -122.4194}
    ]
    
    events = [
        {"date": "2024-02-01", "location": "San Francisco"}
    ]
    
    result = await predictor.predict_location(entity, locations, events)
    assert result.location == "San Francisco"
    assert result.confidence > 0.5

@pytest.mark.asyncio
async def test_track_sentiment():
    analyzer = TrendAnalyzer()
    posts = [
        {"date": "2024-01-01", "content": "I love this amazing project"},
        {"date": "2024-01-15", "content": "This is terrible, completely broken"}
    ]
    
    trend = await analyzer.track_sentiment("entity", posts)
    assert len(trend.time_periods) > 0
    assert trend.overall_trend in ["increasing", "decreasing", "stable"]
```

### Test Caching

```python
@pytest.mark.asyncio
async def test_cache_connector_result():
    cache = RedisCache()
    
    result = {"data": "test"}
    await cache.set_connector_result("hibp", "test@example.com", result)
    
    cached = await cache.get_connector_result("hibp", "test@example.com")
    assert cached == result

@pytest.mark.asyncio
async def test_cache_expiration():
    cache = RedisCache()
    await cache.set("test_key", "value", ttl_seconds=1)
    
    cached = await cache.get("test_key")
    assert cached == "value"
    
    await asyncio.sleep(2)
    expired = await cache.get("test_key")
    assert expired is None
```

### Test UI Components

```javascript
// Vue component test
import { mount } from '@vue/test-utils'
import TimelineViewer from '@/components/TimelineViewer.vue'

describe('TimelineViewer', () => {
  it('renders timeline events', () => {
    const events = [
      {
        event_id: '1',
        event_type: 'employment',
        date: '2023-01-01',
        description: 'Started job',
        confidence: 0.95
      }
    ]
    
    const wrapper = mount(TimelineViewer, {
      props: { events }
    })
    
    expect(wrapper.find('.timeline-event').exists()).toBe(true)
  })

  it('filters events by type', async () => {
    const wrapper = mount(TimelineViewer, {
      props: { events: [...] }
    })
    
    await wrapper.vm.filterEvents()
    expect(wrapper.vm.filteredEvents.length).toBeLessThan(events.length)
  })
})
```

---

## Performance Optimization Tips

### 1. Cache Strategy

```python
# Cache frequently accessed results
async def get_entity_risk(entity_id):
    # Try cache first
    cached = await cache.get_analytics_result(entity_id, "risk_assessment")
    if cached:
        return cached
    
    # Compute if not cached
    assessment = await risk_engine.calculate_overall_risk(entity_data)
    
    # Cache for 24 hours
    await cache.set_analytics_result(entity_id, "risk_assessment", assessment)
    return assessment
```

### 2. Batch Operations

```python
# Process multiple entities in parallel
async def batch_predict_locations(entities):
    tasks = [
        predictor.predict_location(e, locs, timeline)
        for e, locs, timeline in entities
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 3. Query Optimization

```python
# Use indexes
CREATE INDEX idx_entity_created ON investigations(entity_id, created_at)
CREATE INDEX idx_investigation_risk ON investigations(risk_score)

# Limit result sets
investigation = db.query(Investigation)\
    .filter(Investigation.entity_id == entity_id)\
    .limit(10)\
    .all()
```

### 4. Connector Optimization

```python
# Reuse connector instances
class ConnectorPool:
    def __init__(self):
        self.connectors = {}
    
    def get(self, name):
        if name not in self.connectors:
            self.connectors[name] = self._create_connector(name)
        return self.connectors[name]
```

---

## Troubleshooting

### Redis Connection Issues

```python
# Check Redis connection
import aioredis

async def check_redis():
    try:
        redis = await aioredis.create_redis_pool('redis://localhost:6379')
        await redis.ping()
        print("Redis connected")
    except Exception as e:
        print(f"Redis error: {e}")
        # Falls back to in-memory cache automatically
```

### Connector Rate Limiting

```python
# Check connector status
status = connector.get_status()
print(f"Status: {status['status']}")
print(f"Requests: {status['rate_limit']['current_requests']}")
print(f"Limit: {status['rate_limit']['requests_per_hour']}")

# Wait for rate limit reset
if status['status'] == 'rate_limited':
    reset_time = status['rate_limit']['reset_time']
    print(f"Wait until: {reset_time}")
```

### Analytics Errors

```python
# Graceful error handling
try:
    prediction = await predictor.predict_location(entity, locations, events)
except Exception as e:
    logger.error(f"Prediction failed: {e}")
    # Return default/partial result
    prediction = LocationPrediction(
        location="Unknown",
        confidence=0.0,
        reasoning=["Error computing prediction"]
    )
```

---

## Deployment Checklist

- [ ] All environment variables set
- [ ] Redis server running (or using in-memory fallback)
- [ ] Database migrations applied
- [ ] Connectors registered with API keys
- [ ] Vue components integrated into routes
- [ ] API endpoints tested
- [ ] Cache statistics monitored
- [ ] Rate limits verified
- [ ] Analytics engines working
- [ ] UI components rendering
- [ ] Investigation wizard complete workflow
- [ ] Risk dashboard metrics accurate
- [ ] Timeline viewer interactive
- [ ] Network graph visualization
- [ ] Report generation tested
- [ ] Performance benchmarks acceptable

---

## Success Metrics

### System Health
- **Connector Success Rate**: > 95%
- **Analytics Accuracy**: > 80%
- **Cache Hit Rate**: > 70%
- **API Response Time**: < 2s (90th percentile)

### User Experience
- **Investigation Time**: < 5 minutes for 10 sources
- **UI Load Time**: < 2s
- **Report Generation**: < 30s
- **Wizard Completion**: < 10 minutes

### Data Quality
- **Entity Resolution**: > 90% accuracy
- **Timeline Completeness**: > 85% coverage
- **Risk Assessment**: > 85% relevant vulnerabilities
- **Predictions**: > 65% confidence

---

## Support & Documentation

- API Docs: `/docs` (auto-generated by FastAPI)
- Component Storybook: Setup with Storybook.js
- Architecture: See `PHASE2_COMPLETION_SUMMARY.md`
- Specifications: See `osint_framework_specification.md`

---

## Next Integration Steps

1. **Week 1**: Register connectors, test basic functionality
2. **Week 2**: Integrate analytics engines, test predictions
3. **Week 3**: Deploy UI components, test workflow
4. **Week 4**: Full system testing, performance optimization
5. **Week 5**: Production deployment and monitoring

---

End of Integration Guide
