# Context Engine Service - API Documentation

**Base URL:** `http://10.10.0.87:8015`
**Version:** 1.0.0
**Port:** 8015

---

## Table of Contents

- [Interactive Documentation](#interactive-documentation)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Root & Health Endpoints](#root--health-endpoints)
- [Context Retrieval API](#context-retrieval-api)
- [Dimension API](#dimension-api)
- [Cache Management API](#cache-management-api)
- [Monitoring & Metrics](#monitoring--metrics)
- [Code Examples](#code-examples)

---

## Interactive Documentation

- **Swagger UI**: http://10.10.0.87:8015/docs
- **ReDoc**: http://10.10.0.87:8015/redoc

---

## Authentication

**Current Status:** No authentication required (internal service)

**Future:** Will integrate with Auth Service for API key validation.

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Invalid parameters or missing required fields |
| 404 | Not Found | Case not found in database |
| 500 | Internal Server Error | Service error (check logs) |
| 503 | Service Unavailable | Dependent service (GraphRAG/DB) unavailable |

---

## Root & Health Endpoints

### GET /

Root endpoint providing service information.

**Request:**
```bash
curl http://10.10.0.87:8015/
```

**Response (200 OK):**
```json
{
  "service": "context-engine-service",
  "version": "1.0.0",
  "port": 8015,
  "status": "running",
  "description": "Case-centric context retrieval using WHO/WHAT/WHERE/WHEN/WHY framework",
  "endpoints": {
    "docs": "/docs",
    "redoc": "/redoc",
    "health": "/api/v1/health",
    "metrics": "/metrics"
  }
}
```

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://10.10.0.87:8015/")
    service_info = response.json()
    print(f"Service: {service_info['service']}")
    print(f"Version: {service_info['version']}")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/');
const serviceInfo = await response.json();
console.log(`Service: ${serviceInfo.service}`);
console.log(`Version: ${serviceInfo.version}`);
```

---

### GET /api/v1/health

Health check endpoint for monitoring.

**Request:**
```bash
curl http://10.10.0.87:8015/api/v1/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "context-engine",
  "port": 8015,
  "version": "1.0.0"
}
```

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://10.10.0.87:8015/api/v1/health")
    health = response.json()
    assert health["status"] == "healthy"
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/health');
const health = await response.json();
if (health.status !== 'healthy') {
    console.error('Service unhealthy!');
}
```

---

## Context Retrieval API

### POST /api/v1/context/retrieve

Build multi-dimensional context for a specific case using WHO/WHAT/WHERE/WHEN/WHY framework.

**Request Body:**
```json
{
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "scope": "comprehensive",
  "include_dimensions": null,
  "use_cache": true
}
```

**Parameters:**
- `client_id` (required): Client identifier for multi-tenant isolation
- `case_id` (required): Case identifier for case-scoped context
- `scope` (optional): Context scope - one of:
  - `minimal` - WHO + WHERE (parties, jurisdiction) - <100ms
  - `standard` - WHO + WHAT + WHERE + WHEN (adds legal issues, timeline) - 100-500ms
  - `comprehensive` - All 5 dimensions including WHY (precedents, reasoning) - 500-2000ms
- `include_dimensions` (optional): Explicit dimension list to override scope (e.g., ["WHO", "WHEN"])
- `use_cache` (optional, default: true): Whether to use cached context if available

**Response (200 OK):**
```json
{
  "query_id": "550e8400-e29b-41d4-a716-446655440000",
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "who": {
    "case_id": "case-xyz-456",
    "case_name": "Smith v. Jones",
    "parties": [
      {
        "id": "party-1",
        "name": "John Smith",
        "role": "plaintiff",
        "entity_type": "person",
        "case_id": "case-xyz-456",
        "metadata": {}
      }
    ],
    "judges": [
      {
        "id": "judge-1",
        "name": "Hon. Jane Doe",
        "court": "U.S. District Court",
        "case_id": "case-xyz-456",
        "assignment_date": "2024-01-15T00:00:00",
        "history_with_parties": {}
      }
    ],
    "attorneys": [],
    "witnesses": [],
    "party_relationships": {},
    "representation_map": {}
  },
  "what": {
    "case_id": "case-xyz-456",
    "case_name": "Smith v. Jones",
    "causes_of_action": [],
    "legal_issues": ["breach of contract", "negligence"],
    "doctrines": [],
    "statutes": [
      {
        "text": "28 U.S.C. § 1332",
        "type": "statute",
        "jurisdiction": "federal",
        "confidence": 0.95,
        "case_id": "case-xyz-456"
      }
    ],
    "case_citations": [],
    "primary_legal_theory": null,
    "issue_complexity": 0.7,
    "jurisdiction_type": "federal"
  },
  "where": {
    "case_id": "case-xyz-456",
    "case_name": "Smith v. Jones",
    "primary_jurisdiction": "federal",
    "court": "U.S. District Court",
    "venue": "Northern District of California",
    "judge_chambers": null,
    "local_rules": [],
    "filing_requirements": [],
    "related_proceedings": []
  },
  "when": {
    "case_id": "case-xyz-456",
    "case_name": "Smith v. Jones",
    "filing_date": "2024-01-15T00:00:00",
    "incident_date": null,
    "timeline": [],
    "upcoming_deadlines": [],
    "past_deadlines": [],
    "discovery_cutoff": null,
    "motion_deadline": null,
    "trial_date": null,
    "statute_of_limitations": null,
    "days_until_next_deadline": null,
    "urgency_score": 0.5,
    "case_age_days": 120
  },
  "why": {
    "case_id": "case-xyz-456",
    "case_name": "Smith v. Jones",
    "legal_theories": [],
    "argument_outline": [],
    "supporting_precedents": [],
    "opposing_precedents": [],
    "distinguishing_factors": [],
    "argument_strength": 0.75,
    "risk_factors": [],
    "mitigation_strategies": [],
    "similar_case_outcomes": {},
    "judge_ruling_patterns": {}
  },
  "context_score": 0.92,
  "is_complete": true,
  "cached": false,
  "execution_time_ms": 850,
  "timestamp": "2024-01-22T10:30:00"
}
```

**Performance:**
- Cached: <10ms
- Minimal (cache miss): 50-150ms
- Standard (cache miss): 200-600ms
- Comprehensive (cache miss): 800-2000ms

**HTTP Status Codes:**
- 200: Success
- 400: Invalid parameters (invalid scope, invalid dimension names)
- 404: Case not found
- 500: Service error

**Error Example (400):**
```json
{
  "detail": "Invalid scope: invalid_scope. Valid scopes: ['minimal', 'standard', 'comprehensive']"
}
```

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/context/retrieve",
        json={
            "client_id": "client-abc",
            "case_id": "case-123",
            "scope": "comprehensive",
            "use_cache": True
        }
    )
    context = response.json()

    # Access dimensions
    print(f"Parties: {len(context['who']['parties'])}")
    print(f"Statutes: {len(context['what']['statutes'])}")
    print(f"Quality Score: {context['context_score']}")
    print(f"Cache Hit: {context['cached']}")
```

**TypeScript Example:**
```typescript
interface ContextRetrievalRequest {
    client_id: string;
    case_id: string;
    scope?: 'minimal' | 'standard' | 'comprehensive';
    include_dimensions?: string[];
    use_cache?: boolean;
}

const request: ContextRetrievalRequest = {
    client_id: 'client-abc',
    case_id: 'case-123',
    scope: 'comprehensive',
    use_cache: true
};

const response = await fetch('http://10.10.0.87:8015/api/v1/context/retrieve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
});

const context = await response.json();
console.log(`Parties: ${context.who.parties.length}`);
console.log(`Quality Score: ${context.context_score}`);
```

---

### GET /api/v1/context/retrieve

Convenience GET endpoint with query parameters (same functionality as POST).

**Query Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier
- `scope` (optional, default: "comprehensive"): Context scope
- `use_cache` (optional, default: true): Whether to use cache

**Request:**
```bash
curl "http://10.10.0.87:8015/api/v1/context/retrieve?client_id=client-123&case_id=case-456&scope=standard"
```

**Response:** Same as POST /api/v1/context/retrieve

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://10.10.0.87:8015/api/v1/context/retrieve",
        params={
            "client_id": "client-abc",
            "case_id": "case-123",
            "scope": "standard"
        }
    )
    context = response.json()
```

**TypeScript Example:**
```typescript
const params = new URLSearchParams({
    client_id: 'client-abc',
    case_id: 'case-123',
    scope: 'standard'
});

const response = await fetch(`http://10.10.0.87:8015/api/v1/context/retrieve?${params}`);
const context = await response.json();
```

---

### POST /api/v1/context/refresh

Force refresh of case context (bypass cache).

**Query Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier
- `scope` (optional, default: "comprehensive"): Context scope to refresh

**Request:**
```bash
curl -X POST "http://10.10.0.87:8015/api/v1/context/refresh?client_id=client-123&case_id=case-456&scope=comprehensive"
```

**Response (200 OK):**
```json
{
  "message": "Context refreshed successfully",
  "case_id": "case-456",
  "scope": "comprehensive",
  "new_context_score": 0.92,
  "execution_time_ms": 1240
}
```

**Use Case:** Call after case data has been updated to regenerate context with latest information.

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/context/refresh",
        params={
            "client_id": "client-abc",
            "case_id": "case-123",
            "scope": "comprehensive"
        }
    )
    result = response.json()
    print(f"Refreshed in {result['execution_time_ms']}ms")
    print(f"New score: {result['new_context_score']}")
```

**TypeScript Example:**
```typescript
const params = new URLSearchParams({
    client_id: 'client-abc',
    case_id: 'case-123',
    scope: 'comprehensive'
});

const response = await fetch(
    `http://10.10.0.87:8015/api/v1/context/refresh?${params}`,
    { method: 'POST' }
);
const result = await response.json();
console.log(`Refreshed in ${result.execution_time_ms}ms`);
```

---

### POST /api/v1/context/batch/retrieve

Retrieve context for multiple cases in a single request.

**Request Body:**
```json
{
  "client_id": "client-abc-123",
  "case_ids": ["case-1", "case-2", "case-3"],
  "scope": "standard",
  "use_cache": true
}
```

**Response (200 OK):**
```json
{
  "total_cases": 3,
  "successful": 3,
  "failed": 0,
  "contexts": {
    "case-1": {
      "query_id": "...",
      "case_id": "case-1",
      "case_name": "Case 1",
      "who": { ... },
      "what": { ... },
      "context_score": 0.87
    },
    "case-2": { ... },
    "case-3": { ... }
  },
  "errors": {}
}
```

**Note:** For large batch sizes (>10 cases), this may take significant time. Consider using async task queue for very large batches.

**Python Example:**
```python
import httpx

async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/context/batch/retrieve",
        json={
            "client_id": "client-abc",
            "case_ids": ["case-1", "case-2", "case-3", "case-4"],
            "scope": "standard",
            "use_cache": True
        }
    )
    results = response.json()

    print(f"Success: {results['successful']}/{results['total_cases']}")

    for case_id, context in results["contexts"].items():
        print(f"{case_id}: score={context['context_score']:.2f}")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/context/batch/retrieve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        client_id: 'client-abc',
        case_ids: ['case-1', 'case-2', 'case-3'],
        scope: 'standard',
        use_cache: true
    })
});

const results = await response.json();
console.log(`Success: ${results.successful}/${results.total_cases}`);

for (const [caseId, context] of Object.entries(results.contexts)) {
    console.log(`${caseId}: score=${context.context_score}`);
}
```

---

## Dimension API

### POST /api/v1/context/dimension/retrieve

Retrieve a specific dimension for a case (faster than full context if you only need one dimension).

**Request Body:**
```json
{
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "dimension": "WHO"
}
```

**Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier
- `dimension` (required): Dimension name - one of: WHO, WHAT, WHERE, WHEN, WHY

**Response (200 OK):**
```json
{
  "case_id": "case-xyz-456",
  "dimension": "WHO",
  "data": {
    "case_id": "case-xyz-456",
    "case_name": "Smith v. Jones",
    "parties": [ ... ],
    "judges": [ ... ],
    "attorneys": [ ... ],
    "witnesses": [ ... ],
    "party_relationships": {},
    "representation_map": {}
  }
}
```

**HTTP Status Codes:**
- 200: Success
- 400: Invalid dimension name
- 404: Case not found
- 500: Service error

**Error Example (400):**
```json
{
  "detail": "Invalid dimension: INVALID. Valid dimensions: {'WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY'}"
}
```

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    # Retrieve only WHO dimension
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/context/dimension/retrieve",
        json={
            "client_id": "client-abc",
            "case_id": "case-123",
            "dimension": "WHO"
        }
    )

    result = response.json()
    who_data = result["data"]

    print(f"Parties: {len(who_data['parties'])}")
    print(f"Judges: {len(who_data['judges'])}")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/context/dimension/retrieve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        client_id: 'client-abc',
        case_id: 'case-123',
        dimension: 'WHO'
    })
});

const result = await response.json();
const whoData = result.data;
console.log(`Parties: ${whoData.parties.length}`);
```

---

### GET /api/v1/context/dimension/quality

Get quality metrics for a specific dimension.

**Query Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier
- `dimension` (required): Dimension name (WHO/WHAT/WHERE/WHEN/WHY)

**Request:**
```bash
curl "http://10.10.0.87:8015/api/v1/context/dimension/quality?client_id=client-123&case_id=case-456&dimension=WHO"
```

**Response (200 OK):**
```json
{
  "dimension_name": "WHO",
  "completeness_score": 0.87,
  "data_points": 12,
  "confidence_avg": 0.91,
  "is_sufficient": true
}
```

**Quality Scoring:**
- `completeness_score`: 0.0-1.0 (based on data points found vs. expected)
- `data_points`: Total number of entities extracted
- `confidence_avg`: Average confidence of extractions
- `is_sufficient`: true if completeness_score >= 0.85

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://10.10.0.87:8015/api/v1/context/dimension/quality",
        params={
            "client_id": "client-abc",
            "case_id": "case-123",
            "dimension": "WHO"
        }
    )

    quality = response.json()

    if quality["is_sufficient"]:
        print(f"✓ {quality['dimension_name']} dimension is complete")
    else:
        print(f"✗ {quality['dimension_name']} needs more data")

    print(f"  Score: {quality['completeness_score']:.2f}")
    print(f"  Data Points: {quality['data_points']}")
```

**TypeScript Example:**
```typescript
const params = new URLSearchParams({
    client_id: 'client-abc',
    case_id: 'case-123',
    dimension: 'WHO'
});

const response = await fetch(
    `http://10.10.0.87:8015/api/v1/context/dimension/quality?${params}`
);
const quality = await response.json();

console.log(`${quality.dimension_name}: ${quality.completeness_score}`);
console.log(`Sufficient: ${quality.is_sufficient}`);
```

---

## Cache Management API

### GET /api/v1/cache/stats

Get comprehensive cache statistics across all tiers.

**Request:**
```bash
curl http://10.10.0.87:8015/api/v1/cache/stats
```

**Response (200 OK):**
```json
{
  "memory_hits": 1523,
  "memory_misses": 347,
  "memory_hit_rate": 0.8145,
  "redis_hits": 245,
  "redis_misses": 102,
  "redis_hit_rate": 0.7060,
  "db_hits": 18,
  "db_misses": 84,
  "db_hit_rate": 0.1765,
  "total_sets": 449,
  "total_deletes": 23,
  "overall_hit_rate": 0.7821,
  "memory_cache": {
    "size": 847,
    "max_size": 1000,
    "utilization": 0.847,
    "total_hits": 1523,
    "expired_entries": 12,
    "default_ttl_seconds": 600
  }
}
```

**Cache Tiers:**
- **Memory Cache (Tier 1)**: 10-minute TTL, <10ms access
- **Redis Cache (Tier 2)**: 1-hour TTL (active cases), 24-hour TTL (closed cases)
- **Database Cache (Tier 3)**: Persistent storage

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://10.10.0.87:8015/api/v1/cache/stats")
    stats = response.json()

    print(f"Overall Hit Rate: {stats['overall_hit_rate']:.1%}")
    print(f"Memory Utilization: {stats['memory_cache']['utilization']:.1%}")
    print(f"Cache Size: {stats['memory_cache']['size']}/{stats['memory_cache']['max_size']}")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/cache/stats');
const stats = await response.json();

console.log(`Overall Hit Rate: ${(stats.overall_hit_rate * 100).toFixed(1)}%`);
console.log(`Memory Utilization: ${(stats.memory_cache.utilization * 100).toFixed(1)}%`);
```

---

### POST /api/v1/cache/stats/reset

Reset cache statistics counters to zero (useful for benchmarking).

**Request:**
```bash
curl -X POST http://10.10.0.87:8015/api/v1/cache/stats/reset
```

**Response (200 OK):**
```json
{
  "message": "Cache statistics reset successfully",
  "previous_stats": {
    "memory_hits": 1523,
    "memory_misses": 347,
    "overall_hit_rate": 0.8145
  },
  "new_stats": {
    "memory_hits": 0,
    "memory_misses": 0,
    "overall_hit_rate": 0.0
  }
}
```

**Note:** Does not clear cached data, only resets statistics counters.

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post("http://10.10.0.87:8015/api/v1/cache/stats/reset")
    result = response.json()

    print(f"Previous hit rate: {result['previous_stats']['overall_hit_rate']:.1%}")
    print(f"Stats reset successfully")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/cache/stats/reset', {
    method: 'POST'
});
const result = await response.json();
console.log(result.message);
```

---

### DELETE /api/v1/cache/invalidate

Invalidate cached context for a specific case.

**Query Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier to invalidate
- `scope` (optional): Specific scope to invalidate (minimal/standard/comprehensive)
  - If not specified, invalidates all scopes for the case

**Request:**
```bash
# Invalidate all scopes
curl -X DELETE "http://10.10.0.87:8015/api/v1/cache/invalidate?client_id=client-123&case_id=case-456"

# Invalidate specific scope
curl -X DELETE "http://10.10.0.87:8015/api/v1/cache/invalidate?client_id=client-123&case_id=case-456&scope=comprehensive"
```

**Response (200 OK):**
```json
{
  "message": "Cache invalidated successfully",
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "scope": "all",
  "entries_deleted": 3
}
```

**Use Case:** Call when case data has been updated and cached context should be regenerated. Invalidates across all cache tiers (memory, Redis, database).

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.delete(
        "http://10.10.0.87:8015/api/v1/cache/invalidate",
        params={
            "client_id": "client-abc",
            "case_id": "case-123"
        }
    )

    result = response.json()
    print(f"Deleted {result['entries_deleted']} cache entries")
```

**TypeScript Example:**
```typescript
const params = new URLSearchParams({
    client_id: 'client-abc',
    case_id: 'case-123',
    scope: 'comprehensive'
});

const response = await fetch(
    `http://10.10.0.87:8015/api/v1/cache/invalidate?${params}`,
    { method: 'DELETE' }
);
const result = await response.json();
console.log(`Deleted ${result.entries_deleted} entries`);
```

---

### POST /api/v1/cache/invalidate/case

Invalidate all cached contexts for a specific case (convenience endpoint).

**Query Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier

**Request:**
```bash
curl -X POST "http://10.10.0.87:8015/api/v1/cache/invalidate/case?client_id=client-123&case_id=case-456"
```

**Response (200 OK):**
```json
{
  "message": "All cache for case invalidated successfully",
  "case_id": "case-xyz-456",
  "entries_deleted": 15
}
```

**Note:** Equivalent to calling /invalidate without scope parameter (invalidates all scopes and dimensions).

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/cache/invalidate/case",
        params={
            "client_id": "client-abc",
            "case_id": "case-123"
        }
    )

    result = response.json()
    print(f"Invalidated all cache: {result['entries_deleted']} entries")
```

**TypeScript Example:**
```typescript
const params = new URLSearchParams({
    client_id: 'client-abc',
    case_id: 'case-123'
});

const response = await fetch(
    `http://10.10.0.87:8015/api/v1/cache/invalidate/case?${params}`,
    { method: 'POST' }
);
const result = await response.json();
console.log(`Invalidated ${result.entries_deleted} entries`);
```

---

### POST /api/v1/cache/warmup

Pre-warm cache for multiple cases.

**Request Body:**
```json
{
  "client_id": "client-abc-123",
  "case_ids": ["case-1", "case-2", "case-3"],
  "scope": "standard"
}
```

**Response (200 OK):**
```json
{
  "message": "Cache warmup completed",
  "total_cases": 3,
  "successful": 3,
  "failed": 0,
  "errors": {}
}
```

**Use Case:** Useful for preparing cache before high-traffic periods or after system restart. Builds and caches context for specified cases.

**Python Example:**
```python
import httpx

async with httpx.AsyncClient(timeout=60.0) as client:
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/cache/warmup",
        json={
            "client_id": "client-abc",
            "case_ids": ["case-1", "case-2", "case-3", "case-4", "case-5"],
            "scope": "standard"
        }
    )

    result = response.json()
    print(f"Warmed up {result['successful']}/{result['total_cases']} cases")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/cache/warmup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        client_id: 'client-abc',
        case_ids: ['case-1', 'case-2', 'case-3'],
        scope: 'standard'
    })
});

const result = await response.json();
console.log(`Warmed up ${result.successful}/${result.total_cases} cases`);
```

---

### GET /api/v1/cache/config

Get current cache configuration.

**Request:**
```bash
curl http://10.10.0.87:8015/api/v1/cache/config
```

**Response (200 OK):**
```json
{
  "tiers": {
    "memory": {
      "enabled": true,
      "ttl_seconds": 600,
      "max_size": 1000
    },
    "redis": {
      "enabled": false,
      "active_case_ttl_seconds": 3600,
      "closed_case_ttl_seconds": 86400
    },
    "database": {
      "enabled": false
    }
  },
  "ttl_strategy": {
    "memory": "10 minutes",
    "active_cases": "1 hour (Redis/DB)",
    "closed_cases": "24 hours (Redis/DB)"
  }
}
```

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://10.10.0.87:8015/api/v1/cache/config")
    config = response.json()

    print(f"Memory cache: {config['tiers']['memory']['enabled']}")
    print(f"Memory TTL: {config['tiers']['memory']['ttl_seconds']}s")
    print(f"Redis cache: {config['tiers']['redis']['enabled']}")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/cache/config');
const config = await response.json();

console.log(`Memory TTL: ${config.tiers.memory.ttl_seconds}s`);
console.log(`Redis enabled: ${config.tiers.redis.enabled}`);
```

---

### GET /api/v1/cache/health

Check cache system health.

**Request:**
```bash
curl http://10.10.0.87:8015/api/v1/cache/health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "tiers": {
    "memory": {
      "status": "healthy",
      "utilization": 0.847,
      "hit_rate": 0.8145
    },
    "redis": {
      "status": "disabled"
    },
    "database": {
      "status": "disabled"
    }
  },
  "overall_hit_rate": 0.8145
}
```

**Health Status:**
- `healthy`: Hit rate > 50%
- `degraded`: Hit rate <= 50%
- `disabled`: Tier not enabled

**Python Example:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://10.10.0.87:8015/api/v1/cache/health")
    health = response.json()

    if health["status"] == "healthy":
        print("✓ Cache system is healthy")
        print(f"  Hit rate: {health['overall_hit_rate']:.1%}")
    else:
        print("✗ Cache system is degraded")
```

**TypeScript Example:**
```typescript
const response = await fetch('http://10.10.0.87:8015/api/v1/cache/health');
const health = await response.json();

if (health.status === 'healthy') {
    console.log('✓ Cache system is healthy');
} else {
    console.log('✗ Cache system is degraded');
}
```

---

## Monitoring & Metrics

### GET /metrics

Prometheus metrics endpoint for monitoring.

**Request:**
```bash
curl http://10.10.0.87:8015/metrics
```

**Response (200 OK):**
```
# HELP context_engine_requests_total Total requests to Context Engine
# TYPE context_engine_requests_total counter
context_engine_requests_total{endpoint="/api/v1/context/retrieve",method="POST"} 1234.0

# HELP context_engine_request_latency_seconds Request latency in seconds
# TYPE context_engine_request_latency_seconds histogram
context_engine_request_latency_seconds_bucket{endpoint="/api/v1/context/retrieve",le="0.1"} 450.0
context_engine_request_latency_seconds_bucket{endpoint="/api/v1/context/retrieve",le="0.5"} 1150.0
context_engine_request_latency_seconds_bucket{endpoint="/api/v1/context/retrieve",le="1.0"} 1220.0
context_engine_request_latency_seconds_bucket{endpoint="/api/v1/context/retrieve",le="2.0"} 1234.0
```

**Metrics Tracked:**
- `context_engine_requests_total`: Request counts by endpoint and method
- `context_engine_request_latency_seconds`: Request latency histogram

**Python Example (Prometheus Client):**
```python
from prometheus_client.parser import text_string_to_metric_families
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://10.10.0.87:8015/metrics")
    metrics_text = response.text

    for family in text_string_to_metric_families(metrics_text):
        print(f"{family.name}: {family.type}")
        for sample in family.samples:
            print(f"  {sample.name}{sample.labels} = {sample.value}")
```

---

## Code Examples

### Complete Workflow Example (Python)

```python
import httpx
import asyncio

async def analyze_case_workflow():
    """Complete workflow: retrieve context, analyze quality, refresh if needed"""

    client_id = "client-abc"
    case_id = "case-123"

    async with httpx.AsyncClient() as client:
        # 1. Retrieve comprehensive context
        print("1. Retrieving context...")
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        context = response.json()

        print(f"   Quality Score: {context['context_score']:.2f}")
        print(f"   Complete: {context['is_complete']}")
        print(f"   Cache Hit: {context['cached']}")
        print(f"   Time: {context['execution_time_ms']}ms")

        # 2. Check individual dimension quality
        print("\n2. Checking dimension quality...")
        for dimension in ["WHO", "WHAT", "WHERE", "WHEN", "WHY"]:
            response = await client.get(
                "http://10.10.0.87:8015/api/v1/context/dimension/quality",
                params={
                    "client_id": client_id,
                    "case_id": case_id,
                    "dimension": dimension
                }
            )
            quality = response.json()

            status = "✓" if quality["is_sufficient"] else "✗"
            print(f"   {status} {dimension}: {quality['completeness_score']:.2f} ({quality['data_points']} points)")

        # 3. If quality is low, refresh context
        if context['context_score'] < 0.85:
            print("\n3. Quality below threshold, refreshing...")
            response = await client.post(
                "http://10.10.0.87:8015/api/v1/context/refresh",
                params={
                    "client_id": client_id,
                    "case_id": case_id,
                    "scope": "comprehensive"
                }
            )
            refresh_result = response.json()
            print(f"   New Score: {refresh_result['new_context_score']:.2f}")

        # 4. Check cache stats
        print("\n4. Cache statistics...")
        response = await client.get("http://10.10.0.87:8015/api/v1/cache/stats")
        stats = response.json()
        print(f"   Hit Rate: {stats['overall_hit_rate']:.1%}")
        print(f"   Memory Utilization: {stats['memory_cache']['utilization']:.1%}")

# Run workflow
asyncio.run(analyze_case_workflow())
```

### Complete Workflow Example (TypeScript)

```typescript
async function analyzeCaseWorkflow() {
    const clientId = 'client-abc';
    const caseId = 'case-123';
    const baseUrl = 'http://10.10.0.87:8015';

    // 1. Retrieve comprehensive context
    console.log('1. Retrieving context...');
    const contextResponse = await fetch(`${baseUrl}/api/v1/context/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            case_id: caseId,
            scope: 'comprehensive'
        })
    });
    const context = await contextResponse.json();

    console.log(`   Quality Score: ${context.context_score.toFixed(2)}`);
    console.log(`   Complete: ${context.is_complete}`);
    console.log(`   Cache Hit: ${context.cached}`);
    console.log(`   Time: ${context.execution_time_ms}ms`);

    // 2. Check individual dimension quality
    console.log('\n2. Checking dimension quality...');
    for (const dimension of ['WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY']) {
        const params = new URLSearchParams({
            client_id: clientId,
            case_id: caseId,
            dimension: dimension
        });

        const qualityResponse = await fetch(
            `${baseUrl}/api/v1/context/dimension/quality?${params}`
        );
        const quality = await qualityResponse.json();

        const status = quality.is_sufficient ? '✓' : '✗';
        console.log(`   ${status} ${dimension}: ${quality.completeness_score.toFixed(2)} (${quality.data_points} points)`);
    }

    // 3. If quality is low, refresh context
    if (context.context_score < 0.85) {
        console.log('\n3. Quality below threshold, refreshing...');
        const params = new URLSearchParams({
            client_id: clientId,
            case_id: caseId,
            scope: 'comprehensive'
        });

        const refreshResponse = await fetch(
            `${baseUrl}/api/v1/context/refresh?${params}`,
            { method: 'POST' }
        );
        const refreshResult = await refreshResponse.json();
        console.log(`   New Score: ${refreshResult.new_context_score.toFixed(2)}`);
    }

    // 4. Check cache stats
    console.log('\n4. Cache statistics...');
    const statsResponse = await fetch(`${baseUrl}/api/v1/cache/stats`);
    const stats = await statsResponse.json();
    console.log(`   Hit Rate: ${(stats.overall_hit_rate * 100).toFixed(1)}%`);
    console.log(`   Memory Utilization: ${(stats.memory_cache.utilization * 100).toFixed(1)}%`);
}

// Run workflow
analyzeCaseWorkflow();
```

---

## API Summary

### Context Retrieval Endpoints (6)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/context/retrieve | Build multi-dimensional context |
| GET | /api/v1/context/retrieve | Convenience GET with query params |
| POST | /api/v1/context/refresh | Force context refresh (bypass cache) |
| POST | /api/v1/context/batch/retrieve | Batch context retrieval |
| POST | /api/v1/context/dimension/retrieve | Retrieve single dimension |
| GET | /api/v1/context/dimension/quality | Get dimension quality metrics |

### Cache Management Endpoints (7)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/cache/stats | Get cache statistics |
| POST | /api/v1/cache/stats/reset | Reset statistics counters |
| DELETE | /api/v1/cache/invalidate | Invalidate specific cache |
| POST | /api/v1/cache/invalidate/case | Invalidate all cache for case |
| POST | /api/v1/cache/warmup | Pre-warm cache for cases |
| GET | /api/v1/cache/config | Get cache configuration |
| GET | /api/v1/cache/health | Check cache health |

### Monitoring Endpoints (3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Root service information |
| GET | /api/v1/health | Health check |
| GET | /metrics | Prometheus metrics |

**Total:** 16 endpoints (100% documented)

---

**API Version:** 1.0.0
**Last Updated:** 2025-01-22
**Documentation Coverage:** 100% (16/16 endpoints)

**For additional documentation:**
- Technical Specification: `/docs/technical-specification.md`
- Dimension Reference: `/DIMENSION_REFERENCE.md`
- Error Handling Guide: `/ERROR_HANDLING.md`
- Advanced Usage: `/ADVANCED_USAGE.md`
- Interactive Docs: http://10.10.0.87:8015/docs
