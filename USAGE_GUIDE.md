# Context Engine - Usage Guide

**Service:** Context Engine Service
**Base URL:** `http://10.10.0.87:8015`
**Interactive Docs:** http://10.10.0.87:8015/docs
**Version:** 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [The WHO/WHAT/WHERE/WHEN/WHY Framework](#the-whowhatwherewhenwhy-framework)
3. [API Endpoints](#api-endpoints)
4. [Scope Levels](#scope-levels)
5. [Quick Start Examples](#quick-start-examples)
6. [Python Usage](#python-usage)
7. [Advanced Features](#advanced-features)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Context Engine provides **multi-dimensional legal context** for cases by analyzing and organizing information across five critical dimensions:

- **WHO**: Parties, attorneys, judges, courts
- **WHAT**: Legal issues, causes of action, statutes, claims
- **WHERE**: Jurisdiction, venue, court locations
- **WHEN**: Timeline of events, deadlines, filing dates
- **WHY**: Legal reasoning, precedents, supporting arguments

### Key Features

✅ Multi-dimensional context construction
✅ GraphRAG-powered precedent discovery
✅ Intelligent caching (70-80% hit rate)
✅ Sub-second response times (cached: <10ms)
✅ Quality scoring (0.0-1.0) for context completeness
✅ Flexible scope levels (minimal, standard, comprehensive)

---

## The WHO/WHAT/WHERE/WHEN/WHY Framework

```
┌─────────────────────────────────────────────────────────────┐
│          Context Engine - 5 Dimensions Framework            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  WHO    → Parties, Attorneys, Judges, Courts               │
│           "Who is involved in this case?"                   │
│           • Plaintiffs, Defendants, Third Parties          │
│           • Legal representation map                        │
│           • Presiding judges and judicial history          │
│                                                             │
│  WHAT   → Legal Issues, Causes of Action, Statutes         │
│           "What legal matters are at stake?"                │
│           • Primary and secondary legal issues             │
│           • Applicable statutes and regulations            │
│           • Causes of action and defenses                  │
│                                                             │
│  WHERE  → Jurisdiction, Venue, Court Locations              │
│           "Where is this case being heard?"                 │
│           • Federal vs. state jurisdiction                 │
│           • Specific court and division                    │
│           • Local rules and filing requirements            │
│                                                             │
│  WHEN   → Timeline, Deadlines, Filing Dates                 │
│           "When did events occur?"                          │
│           • Key dates (filing, hearings, rulings)          │
│           • Upcoming deadlines                             │
│           • Statute of limitations                         │
│                                                             │
│  WHY    → Legal Reasoning, Precedents, Arguments            │
│           "Why does the law support this position?"         │
│           • Relevant case law and precedents               │
│           • Legal standards and tests                      │
│           • Persuasive authority                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Query**: You provide a `client_id` and `case_id`
2. **Analysis**: Context Engine queries GraphRAG knowledge graph
3. **Construction**: Builds multi-dimensional context across 5 dimensions
4. **Scoring**: Calculates quality score based on completeness
5. **Caching**: Stores results for fast retrieval (TTL: 3600s)
6. **Response**: Returns structured JSON with all dimensions

---

## API Endpoints

### Primary Endpoint: POST /api/v1/context/retrieve

**Description:** Retrieve comprehensive multi-dimensional context for a case.

**Request:**
```json
{
  "client_id": "client-abc-123",      // REQUIRED: Client identifier
  "case_id": "case-xyz-456",          // REQUIRED: Case identifier
  "scope": "comprehensive",            // OPTIONAL: minimal | standard | comprehensive
  "use_cache": true                    // OPTIONAL: Enable caching (default: true)
}
```

**Response:**
```json
{
  "query_id": "uuid",                  // Unique query identifier
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",

  "who": {                             // WHO dimension
    "parties": [...],
    "judges": [...],
    "attorneys": [...]
  },

  "what": {                            // WHAT dimension
    "legal_issues": [...],
    "statutes": [...],
    "causes_of_action": [...]
  },

  "where": {                           // WHERE dimension
    "jurisdiction": "federal",
    "court": "U.S. District Court",
    "venue": "Northern District of California"
  },

  "when": {                            // WHEN dimension
    "filing_date": "2024-01-15",
    "key_dates": [...],
    "deadlines": [...]
  },

  "why": {                             // WHY dimension
    "precedents": [...],
    "legal_standards": [...],
    "reasoning": [...]
  },

  "context_score": 0.92,               // Quality score (0.0-1.0)
  "is_complete": true,                 // All dimensions populated?
  "cached": true,                      // Was this served from cache?
  "execution_time_ms": 8,              // Response time in milliseconds
  "timestamp": "2024-10-24T12:00:00Z"
}
```

### Additional Endpoints

#### GET /api/v1/context/retrieve

Convenience GET endpoint with query parameters:
```bash
GET /api/v1/context/retrieve?client_id=abc&case_id=xyz&scope=standard
```

#### POST /api/v1/context/dimension/retrieve

Retrieve a **single dimension** (faster than full context):
```json
{
  "client_id": "client-abc",
  "case_id": "case-xyz",
  "dimension": "who"  // who | what | where | when | why
}
```

Response time: 50-200ms (vs. 800-2000ms for comprehensive context)

#### GET /api/v1/context/dimension/quality

Get quality metrics for a specific dimension:
```bash
GET /api/v1/context/dimension/quality?dimension=who
```

Returns:
```json
{
  "dimension": "who",
  "quality_score": 0.95,
  "completeness": 0.90,
  "accuracy": 0.98,
  "sample_count": 1500
}
```

---

## Scope Levels

The Context Engine supports **3 scope levels** for balancing performance vs. completeness:

### 1. Minimal Scope

**Use Case:** Quick lookups, basic case information, UI previews

**Performance:**
- **Cache Hit:** <10ms
- **Cache Miss:** 50-150ms

**What's Included:**
- ✅ WHO: Basic party list, primary judge
- ⚠️ WHAT: Limited to primary legal issue
- ✅ WHERE: Jurisdiction and court
- ❌ WHEN: Only filing date
- ❌ WHY: Not included

**Example:**
```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{"client_id":"abc","case_id":"xyz","scope":"minimal"}'
```

---

### 2. Standard Scope (Default)

**Use Case:** General case analysis, document generation, research

**Performance:**
- **Cache Hit:** <10ms
- **Cache Miss:** 200-600ms

**What's Included:**
- ✅ WHO: All parties, attorneys, judges
- ✅ WHAT: All legal issues, primary statutes
- ✅ WHERE: Full jurisdiction details, venue, local rules
- ✅ WHEN: Timeline, key dates, upcoming deadlines
- ⚠️ WHY: Limited precedents (top 10)

**Example:**
```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{"client_id":"abc","case_id":"xyz","scope":"standard"}'
```

---

### 3. Comprehensive Scope

**Use Case:** Deep legal research, brief writing, case strategy

**Performance:**
- **Cache Hit:** <10ms
- **Cache Miss:** 800-2000ms

**What's Included:**
- ✅ WHO: All parties + relationships + organizational charts
- ✅ WHAT: All legal issues + statutes + regulations + defenses
- ✅ WHERE: Full jurisdiction + venue + local rules + procedures
- ✅ WHEN: Complete timeline + deadlines + statute of limitations
- ✅ WHY: **GraphRAG precedent discovery** (top 50 cases)

**Example:**
```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{"client_id":"abc","case_id":"xyz","scope":"comprehensive"}'
```

**🔥 Pro Tip:** Comprehensive scope leverages GraphRAG's Leiden community detection to discover non-obvious precedents through graph traversal, often finding relevant cases missed by traditional keyword search.

---

## Quick Start Examples

### Example 1: Basic Context Retrieval (curl)

```bash
# Retrieve standard context for a case
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client-abc-123",
    "case_id": "case-xyz-456",
    "scope": "standard",
    "use_cache": true
  }' | jq
```

### Example 2: Retrieve Just WHO Dimension

```bash
# Get only the WHO dimension (parties, attorneys, judges)
curl -X POST http://10.10.0.87:8015/api/v1/context/dimension/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client-abc-123",
    "case_id": "case-xyz-456",
    "dimension": "who"
  }' | jq
```

### Example 3: Check Dimension Quality

```bash
# Get quality metrics for the WHY dimension
curl -s http://10.10.0.87:8015/api/v1/context/dimension/quality?dimension=why | jq
```

### Example 4: Clear Cache for Case

```bash
# Clear cached context for a specific case
curl -X POST http://10.10.0.87:8015/api/v1/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"case_id": "case-xyz-456"}'
```

---

## Python Usage

### Installation

```bash
pip install httpx pydantic
```

### Basic Usage

```python
import httpx
from typing import Optional

class ContextEngineClient:
    """Client for Context Engine Service"""

    def __init__(self, base_url: str = "http://10.10.0.87:8015"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def retrieve_context(
        self,
        client_id: str,
        case_id: str,
        scope: str = "standard",
        use_cache: bool = True
    ) -> dict:
        """Retrieve multi-dimensional context for a case"""
        response = self.client.post(
            f"{self.base_url}/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": scope,
                "use_cache": use_cache
            }
        )
        response.raise_for_status()
        return response.json()

    def retrieve_dimension(
        self,
        client_id: str,
        case_id: str,
        dimension: str
    ) -> dict:
        """Retrieve a single dimension"""
        response = self.client.post(
            f"{self.base_url}/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": dimension
            }
        )
        response.raise_for_status()
        return response.json()

    def get_dimension_quality(self, dimension: str) -> dict:
        """Get quality metrics for a dimension"""
        response = self.client.get(
            f"{self.base_url}/api/v1/context/dimension/quality",
            params={"dimension": dimension}
        )
        response.raise_for_status()
        return response.json()

    def health_check(self) -> dict:
        """Check service health"""
        response = self.client.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()


# Usage Example
if __name__ == "__main__":
    # Create client
    client = ContextEngineClient()

    # Check health
    health = client.health_check()
    print(f"Service Status: {health['status']}")

    # Retrieve comprehensive context
    context = client.retrieve_context(
        client_id="client-abc-123",
        case_id="case-xyz-456",
        scope="comprehensive"
    )

    # Print results
    print(f"\nCase: {context['case_name']}")
    print(f"Context Score: {context['context_score']:.2f}")
    print(f"Complete: {context['is_complete']}")
    print(f"Cached: {context['cached']}")
    print(f"Response Time: {context['execution_time_ms']}ms")

    # Access dimensions
    who = context['who']
    print(f"\nParties: {len(who.get('parties', []))}")
    print(f"Attorneys: {len(who.get('attorneys', []))}")
    print(f"Judges: {len(who.get('judges', []))}")

    # Retrieve just WHY dimension (precedents)
    why = client.retrieve_dimension(
        client_id="client-abc-123",
        case_id="case-xyz-456",
        dimension="why"
    )
    print(f"\nPrecedents Found: {len(why.get('precedents', []))}")
```

### Async Usage (FastAPI Integration)

```python
import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI()

class AsyncContextEngineClient:
    """Async client for Context Engine Service"""

    def __init__(self, base_url: str = "http://10.10.0.87:8015"):
        self.base_url = base_url

    async def retrieve_context(
        self,
        client_id: str,
        case_id: str,
        scope: str = "standard"
    ) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/context/retrieve",
                json={
                    "client_id": client_id,
                    "case_id": case_id,
                    "scope": scope
                }
            )
            response.raise_for_status()
            return response.json()


# FastAPI endpoint
context_client = AsyncContextEngineClient()

@app.get("/case/{case_id}/context")
async def get_case_context(case_id: str, client_id: str, scope: str = "standard"):
    """Retrieve case context via FastAPI"""
    try:
        context = await context_client.retrieve_context(
            client_id=client_id,
            case_id=case_id,
            scope=scope
        )
        return context
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Advanced Features

### 1. GraphRAG Precedent Discovery (WHY Dimension)

The WHY dimension uses **GraphRAG** to discover precedents through graph traversal:

```python
# Retrieve comprehensive context with deep precedent analysis
context = client.retrieve_context(
    client_id="client-abc",
    case_id="case-xyz",
    scope="comprehensive"  # Required for GraphRAG precedent discovery
)

# Access precedents
why = context['why']
precedents = why.get('precedents', [])

for precedent in precedents:
    print(f"Case: {precedent['case_name']}")
    print(f"Citation: {precedent['citation']}")
    print(f"Relevance: {precedent['relevance_score']}")
    print(f"Summary: {precedent['summary']}")
    print("---")
```

**How It Works:**
1. GraphRAG builds knowledge graph with 119,838+ nodes
2. Leiden community detection groups related cases
3. Graph traversal finds precedents connected via legal concepts
4. Semantic similarity ranking (top 50 for comprehensive scope)

### 2. Intelligent Caching

Cache performance metrics:
- **Hit Rate:** 70-80% in production
- **TTL:** 3600 seconds (1 hour)
- **Eviction Policy:** LRU (Least Recently Used)
- **Cache Key:** `{client_id}:{case_id}:{scope}`

**Cache Control:**

```python
# Bypass cache (force fresh retrieval)
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    use_cache=False  # Bypass cache
)

# Clear cache for a case
response = httpx.post(
    "http://10.10.0.87:8015/api/v1/cache/clear",
    json={"case_id": "case-xyz-456"}
)

# Get cache statistics
stats = httpx.get("http://10.10.0.87:8015/api/v1/cache/stats").json()
print(f"Cache Hit Rate: {stats['hit_rate']:.2%}")
print(f"Cache Size: {stats['size']} entries")
```

### 3. Context Quality Scoring

The `context_score` (0.0-1.0) measures completeness:

```python
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"
)

score = context['context_score']

if score >= 0.9:
    print("✅ Excellent context (90%+ complete)")
elif score >= 0.7:
    print("✔️ Good context (70-89% complete)")
elif score >= 0.5:
    print("⚠️ Fair context (50-69% complete)")
else:
    print("❌ Poor context (<50% complete)")

# Check which dimensions are missing
is_complete = context['is_complete']
if not is_complete:
    missing = []
    if not context['who']: missing.append('WHO')
    if not context['what']: missing.append('WHAT')
    if not context['where']: missing.append('WHERE')
    if not context['when']: missing.append('WHEN')
    if not context['why']: missing.append('WHY')
    print(f"Missing dimensions: {', '.join(missing)}")
```

**Scoring Algorithm:**
```python
# Simplified version
score = (
    (0.2 if who else 0) +
    (0.2 if what else 0) +
    (0.2 if where else 0) +
    (0.2 if when else 0) +
    (0.2 if why else 0)
)
```

### 4. Dimension-Specific Retrieval

For performance optimization, retrieve only needed dimensions:

```python
# Only need parties and attorneys (WHO dimension)
who = client.retrieve_dimension(
    client_id="abc",
    case_id="xyz",
    dimension="who"
)
# Response time: 50-200ms (vs. 800-2000ms for full context)

# Only need precedents (WHY dimension)
why = client.retrieve_dimension(
    client_id="abc",
    case_id="xyz",
    dimension="why"
)
```

**Performance Comparison:**

| Retrieval Type | Cache Miss | Use Case |
|----------------|------------|----------|
| Full Context (comprehensive) | 800-2000ms | Complete case analysis |
| Full Context (standard) | 200-600ms | General research |
| Single Dimension | 50-200ms | Specific information lookup |
| Cached (any) | <10ms | All scenarios |

---

## Performance Optimization

### Best Practices

#### 1. **Use Appropriate Scope**

```python
# ❌ BAD: Always using comprehensive scope
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"  # 800-2000ms when not cached
)

# ✅ GOOD: Use minimal for UI previews
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="minimal"  # 50-150ms when not cached
)

# ✅ GOOD: Use standard for general analysis
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="standard"  # 200-600ms when not cached
)

# ✅ GOOD: Use comprehensive only for deep research
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"  # Worth 800-2000ms for GraphRAG precedents
)
```

#### 2. **Leverage Caching**

```python
# ✅ GOOD: Enable caching (default behavior)
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    use_cache=True  # <10ms on cache hit (70-80% hit rate)
)

# ❌ BAD: Disabling cache unnecessarily
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    use_cache=False  # Always slow
)

# ✅ GOOD: Bypass cache only when data has changed
# (e.g., after uploading new document)
response = upload_document(case_id="xyz", document=file)
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    use_cache=False  # Force refresh after data change
)
```

#### 3. **Retrieve Only Needed Dimensions**

```python
# ❌ BAD: Retrieving full context when only need parties
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"
)
parties = context['who']['parties']  # Wasteful

# ✅ GOOD: Retrieve just WHO dimension
who = client.retrieve_dimension(
    client_id="abc",
    case_id="xyz",
    dimension="who"
)
parties = who['parties']  # 4x faster
```

#### 4. **Parallel Retrieval for Multiple Cases**

```python
import asyncio
import httpx

async def get_contexts_parallel(case_ids: list[str]) -> list[dict]:
    """Retrieve context for multiple cases in parallel"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [
            client.post(
                "http://10.10.0.87:8015/api/v1/context/retrieve",
                json={
                    "client_id": "abc",
                    "case_id": case_id,
                    "scope": "standard"
                }
            )
            for case_id in case_ids
        ]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]

# Retrieve context for 10 cases in parallel
case_ids = [f"case-{i:03d}" for i in range(10)]
contexts = asyncio.run(get_contexts_parallel(case_ids))

# 10 cases in ~500ms (parallel) vs. ~5000ms (sequential)
```

### Performance Metrics

**Production SLA Targets:**
- P95 Latency: < 2 seconds
- Error Rate: < 1%
- Cache Hit Rate: > 70%
- Uptime: 99.9%

**Typical Response Times** (cache miss):

| Scope | P50 | P95 | P99 |
|-------|-----|-----|-----|
| Minimal | 80ms | 150ms | 250ms |
| Standard | 350ms | 600ms | 900ms |
| Comprehensive | 1200ms | 2000ms | 3000ms |

**Typical Response Times** (cache hit):

| Any Scope | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Cached | 5ms | 10ms | 20ms |

---

## Troubleshooting

### Common Issues

#### 1. **503 Service Unavailable**

**Cause:** Dependent services (GraphRAG, Supabase) unavailable

**Solution:**
```bash
# Check service health
curl http://10.10.0.87:8015/api/v1/health/dependencies

# Check GraphRAG service
curl http://10.10.0.87:8010/api/v1/health

# Check service status
sudo systemctl status luris-context-engine
sudo systemctl status luris-graphrag
```

#### 2. **Timeout Errors (>30s)**

**Cause:** Comprehensive scope on large cases without cache

**Solution:**
```python
# Increase timeout
client = httpx.Client(timeout=60.0)  # 60 second timeout

# Or use standard scope instead
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="standard"  # Faster than comprehensive
)
```

#### 3. **Empty Context (context_score = 0.0)**

**Cause:** Case has no data in database

**Solution:**
```python
# Check if case exists
response = httpx.get(
    f"http://10.10.0.87:8002/api/v1/cases/{case_id}"
)

if response.status_code == 404:
    print("Case not found - upload documents first")
else:
    # Case exists but has no processed data
    print("Upload and process documents for this case")
```

#### 4. **Low Context Score (<0.5)**

**Cause:** Incomplete data or missing dimensions

**Solution:**
```python
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"
)

# Check which dimensions are missing
missing_dimensions = []
if not context['who'] or len(context['who'].get('parties', [])) == 0:
    missing_dimensions.append('WHO - Upload party information')
if not context['what'] or len(context['what'].get('legal_issues', [])) == 0:
    missing_dimensions.append('WHAT - Extract legal issues from documents')
if not context['where']:
    missing_dimensions.append('WHERE - Set jurisdiction and venue')
if not context['when'] or not context['when'].get('filing_date'):
    missing_dimensions.append('WHEN - Add case timeline')
if not context['why'] or len(context['why'].get('precedents', [])) == 0:
    missing_dimensions.append('WHY - Upload legal briefs for precedent extraction')

print("Missing data:")
for dim in missing_dimensions:
    print(f"  - {dim}")
```

#### 5. **Cache Not Working (always slow)**

**Cause:** Cache disabled or case_id changing

**Solution:**
```python
# Check cache stats
stats = httpx.get("http://10.10.0.87:8015/api/v1/cache/stats").json()
print(f"Cache enabled: {stats['enabled']}")
print(f"Hit rate: {stats['hit_rate']:.2%}")

# Ensure case_id is consistent
context = client.retrieve_context(
    client_id="abc",
    case_id="case-123",  # Use same ID every time
    use_cache=True
)

# Check if response was cached
print(f"Cached: {context['cached']}")
print(f"Response time: {context['execution_time_ms']}ms")
```

### Debug Mode

Enable verbose logging:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Make request
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"
)

# Check execution time
print(f"Execution time: {context['execution_time_ms']}ms")
print(f"Cached: {context['cached']}")
```

### Health Checks

```bash
# Basic health check
curl http://10.10.0.87:8015/api/v1/health

# Detailed health with dependencies
curl http://10.10.0.87:8015/api/v1/health/dependencies

# Prometheus metrics
curl http://10.10.0.87:8015/metrics
```

---

## API Reference

### Complete Endpoint List

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/context/retrieve` | Retrieve full multi-dimensional context |
| GET | `/api/v1/context/retrieve` | Convenience GET with query params |
| POST | `/api/v1/context/dimension/retrieve` | Retrieve single dimension |
| GET | `/api/v1/context/dimension/quality` | Get dimension quality metrics |
| POST | `/api/v1/cache/clear` | Clear cache for a case |
| GET | `/api/v1/cache/stats` | Get cache statistics |
| GET | `/api/v1/health` | Basic health check |
| GET | `/api/v1/health/dependencies` | Health check with dependencies |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | Interactive API documentation |
| GET | `/redoc` | Alternative API documentation |

---

## Additional Resources

- **API Documentation**: http://10.10.0.87:8015/docs
- **Grafana Dashboard**: http://grafana:3000/d/context-engine-prod
- **Prometheus Metrics**: http://prometheus:9090
- **Service Logs**: `journalctl -u luris-context-engine -f`
- **Production Readiness**: `/srv/luris/be/context-engine-service/PRODUCTION_READINESS.md`

---

## Support

For issues or questions:
1. Check service health: `curl http://10.10.0.87:8015/api/v1/health`
2. Review logs: `journalctl -u luris-context-engine -n 100`
3. Check dependencies: `curl http://10.10.0.87:8015/api/v1/health/dependencies`
4. Consult troubleshooting section above

---

**Last Updated:** 2024-10-24
**Version:** 1.0.0
**Service Port:** 8015
