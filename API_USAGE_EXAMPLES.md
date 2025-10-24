# Context Engine API - Usage Examples

**Last Updated:** 2024-10-24
**Service:** Context Engine
**Base URL:** http://10.10.0.87:8015
**Interactive Docs:** http://10.10.0.87:8015/docs

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Endpoints](#api-endpoints)
3. [Scope Levels](#scope-levels)
4. [curl Examples](#curl-examples)
5. [Python Examples](#python-examples)
6. [Response Structure](#response-structure)
7. [Error Handling](#error-handling)
8. [Performance Tips](#performance-tips)

---

## Quick Start

### Health Check

```bash
# Check if service is running
curl http://10.10.0.87:8015/api/v1/health

# Response:
# {
#   "status": "healthy",
#   "service": "context-engine",
#   "port": 8015,
#   "version": "1.0.0"
# }
```

### Basic Context Retrieval

```bash
# Retrieve context for a case
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client-abc-123",
    "case_id": "case-xyz-456",
    "scope": "standard",
    "use_cache": true
  }'
```

---

## API Endpoints

### 1. POST /api/v1/context/retrieve

**Primary endpoint for retrieving multi-dimensional context**

**Request Body:**
```json
{
  "client_id": "client-abc-123",      // REQUIRED
  "case_id": "case-xyz-456",          // REQUIRED
  "scope": "standard",                 // OPTIONAL: minimal | standard | comprehensive
  "use_cache": true                    // OPTIONAL: default true
}
```

**Response:**
```json
{
  "query_id": "uuid",
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "who": { /* WHO dimension */ },
  "what": { /* WHAT dimension */ },
  "where": { /* WHERE dimension */ },
  "when": { /* WHEN dimension */ },
  "why": { /* WHY dimension */ },
  "context_score": 0.92,
  "is_complete": true,
  "cached": true,
  "execution_time_ms": 8,
  "timestamp": "2024-10-24T12:00:00Z"
}
```

---

### 2. GET /api/v1/context/retrieve

**Convenience GET endpoint with query parameters**

```bash
curl "http://10.10.0.87:8015/api/v1/context/retrieve?client_id=abc&case_id=xyz&scope=standard"
```

**Query Parameters:**
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier
- `scope` (optional): minimal | standard | comprehensive (default: standard)
- `use_cache` (optional): true | false (default: true)

---

### 3. POST /api/v1/context/dimension/retrieve

**Retrieve a single dimension (faster than full context)**

**Request Body:**
```json
{
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "dimension": "who"                   // who | what | where | when | why
}
```

**Response:**
```json
{
  "dimension": "who",
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "parties": [
    {
      "name": "John Smith",
      "role": "plaintiff",
      "entity_type": "individual"
    }
  ],
  "judges": [...],
  "attorneys": [...],
  "execution_time_ms": 125
}
```

---

### 4. GET /api/v1/context/dimension/quality

**Get quality metrics for a dimension**

```bash
curl "http://10.10.0.87:8015/api/v1/context/dimension/quality?dimension=who"
```

**Response:**
```json
{
  "dimension": "who",
  "quality_score": 0.95,
  "completeness": 0.90,
  "accuracy": 0.98,
  "sample_count": 1500,
  "metrics": {
    "avg_parties_per_case": 3.2,
    "avg_attorneys_per_case": 2.5,
    "cases_with_judges": 1450
  }
}
```

---

### 5. POST /api/v1/cache/clear

**Clear cached context for a case**

**Request Body:**
```json
{
  "case_id": "case-xyz-456"
}
```

**Response:**
```json
{
  "status": "success",
  "case_id": "case-xyz-456",
  "entries_cleared": 3
}
```

---

### 6. GET /api/v1/cache/stats

**Get cache performance statistics**

```bash
curl http://10.10.0.87:8015/api/v1/cache/stats
```

**Response:**
```json
{
  "enabled": true,
  "size": 1247,
  "max_size": 10000,
  "hit_rate": 0.78,
  "total_hits": 8542,
  "total_misses": 2401,
  "total_requests": 10943,
  "utilization": 0.1247
}
```

---

## Scope Levels

The Context Engine supports 3 scope levels:

### Minimal Scope

**Use Case:** Quick lookups, UI previews, basic info
**Performance:** 50-150ms (cache miss), <10ms (cache hit)

```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "abc",
    "case_id": "xyz",
    "scope": "minimal"
  }'
```

**What's Included:**
- ✅ WHO: Basic party list, primary judge
- ⚠️ WHAT: Limited to primary legal issue
- ✅ WHERE: Jurisdiction and court
- ⚠️ WHEN: Only filing date
- ❌ WHY: Not included

---

### Standard Scope (Default)

**Use Case:** General case analysis, document generation
**Performance:** 200-600ms (cache miss), <10ms (cache hit)

```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "abc",
    "case_id": "xyz",
    "scope": "standard"
  }'
```

**What's Included:**
- ✅ WHO: All parties, attorneys, judges
- ✅ WHAT: All legal issues, primary statutes
- ✅ WHERE: Full jurisdiction details, venue, local rules
- ✅ WHEN: Timeline, key dates, deadlines
- ⚠️ WHY: Limited precedents (top 10)

---

### Comprehensive Scope

**Use Case:** Deep research, brief writing, case strategy
**Performance:** 800-2000ms (cache miss), <10ms (cache hit)

```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "abc",
    "case_id": "xyz",
    "scope": "comprehensive"
  }'
```

**What's Included:**
- ✅ WHO: All parties + relationships + org charts
- ✅ WHAT: All legal issues + statutes + regulations
- ✅ WHERE: Full jurisdiction + venue + rules + procedures
- ✅ WHEN: Complete timeline + deadlines + SOL
- ✅ WHY: **GraphRAG precedent discovery** (top 50 cases)

---

## curl Examples

### Example 1: Retrieve Comprehensive Context

```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client-abc-123",
    "case_id": "case-xyz-456",
    "scope": "comprehensive",
    "use_cache": true
  }' | jq
```

**Tip:** Use `jq` to pretty-print JSON responses

---

### Example 2: Get Only WHO Dimension

```bash
curl -X POST http://10.10.0.87:8015/api/v1/context/dimension/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client-abc-123",
    "case_id": "case-xyz-456",
    "dimension": "who"
  }' | jq '.parties'
```

**Performance:** ~75ms vs. 800-2000ms for full comprehensive context

---

### Example 3: Extract Specific Fields

```bash
# Get only parties and attorneys
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "abc",
    "case_id": "xyz",
    "scope": "minimal"
  }' | jq '{
    case_name,
    parties: .who.parties,
    attorneys: .who.attorneys,
    cached,
    execution_time_ms
  }'
```

---

### Example 4: Check Cache Performance

```bash
# Get cache statistics
curl http://10.10.0.87:8015/api/v1/cache/stats | jq '{
  hit_rate,
  size,
  utilization
}'
```

---

### Example 5: Clear Cache After Document Upload

```bash
# After uploading new documents, clear cache to force refresh
curl -X POST http://10.10.0.87:8015/api/v1/cache/clear \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "case-xyz-456"
  }'

# Then retrieve fresh context
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "abc",
    "case_id": "case-xyz-456",
    "scope": "standard",
    "use_cache": false
  }'
```

---

### Example 6: GET Request (Query Parameters)

```bash
# Simpler GET syntax for basic queries
curl "http://10.10.0.87:8015/api/v1/context/retrieve?client_id=abc&case_id=xyz&scope=minimal" | jq
```

---

### Example 7: Dimension Quality Check

```bash
# Check quality of WHO dimension
curl "http://10.10.0.87:8015/api/v1/context/dimension/quality?dimension=who" | jq

# Check all dimensions
for dim in who what where when why; do
  echo "=== $dim Dimension ==="
  curl -s "http://10.10.0.87:8015/api/v1/context/dimension/quality?dimension=$dim" | jq '.quality_score'
done
```

---

## Python Examples

### Example 1: Basic Client

```python
import httpx
from typing import Optional

class ContextEngineClient:
    """Simple Context Engine client"""

    def __init__(self, base_url: str = "http://10.10.0.87:8015"):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)

    def health_check(self) -> dict:
        """Check service health"""
        response = self.client.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()

    def retrieve_context(
        self,
        client_id: str,
        case_id: str,
        scope: str = "standard",
        use_cache: bool = True
    ) -> dict:
        """Retrieve multi-dimensional context"""
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
        """Retrieve single dimension"""
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

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        response = self.client.get(f"{self.base_url}/api/v1/cache/stats")
        response.raise_for_status()
        return response.json()

    def clear_cache(self, case_id: str) -> dict:
        """Clear cache for a case"""
        response = self.client.post(
            f"{self.base_url}/api/v1/cache/clear",
            json={"case_id": case_id}
        )
        response.raise_for_status()
        return response.json()


# Usage
if __name__ == "__main__":
    client = ContextEngineClient()

    # Health check
    health = client.health_check()
    print(f"Service Status: {health['status']}")

    # Retrieve context
    context = client.retrieve_context(
        client_id="client-abc-123",
        case_id="case-xyz-456",
        scope="comprehensive"
    )

    print(f"\nCase: {context['case_name']}")
    print(f"Context Score: {context['context_score']:.2f}")
    print(f"Cached: {context['cached']}")
    print(f"Response Time: {context['execution_time_ms']}ms")

    # Access dimensions
    who = context['who']
    print(f"\nParties: {len(who['parties'])}")
    print(f"Attorneys: {len(who['attorneys'])}")
    print(f"Judges: {len(who['judges'])}")
```

---

### Example 2: Async Client

```python
import httpx
import asyncio

class AsyncContextEngineClient:
    """Async Context Engine client for high-performance applications"""

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

    async def retrieve_multiple_cases(
        self,
        client_id: str,
        case_ids: list[str],
        scope: str = "standard"
    ) -> list[dict]:
        """Retrieve context for multiple cases in parallel"""
        tasks = [
            self.retrieve_context(client_id, case_id, scope)
            for case_id in case_ids
        ]
        return await asyncio.gather(*tasks)


# Usage
async def main():
    client = AsyncContextEngineClient()

    # Retrieve multiple cases in parallel
    case_ids = ["case-001", "case-002", "case-003"]
    contexts = await client.retrieve_multiple_cases(
        client_id="client-abc",
        case_ids=case_ids,
        scope="standard"
    )

    for ctx in contexts:
        print(f"Case: {ctx['case_name']}, Score: {ctx['context_score']:.2f}")

# Run
asyncio.run(main())
```

---

### Example 3: Dimension-Specific Retrieval

```python
def analyze_case_parties(client_id: str, case_id: str):
    """Retrieve and analyze WHO dimension only"""
    client = ContextEngineClient()

    # Get only WHO dimension (faster)
    who = client.retrieve_dimension(
        client_id=client_id,
        case_id=case_id,
        dimension="who"
    )

    # Analyze parties
    print(f"Case: {who['case_name']}")
    print(f"\n=== Parties ===")
    for party in who['parties']:
        print(f"- {party['name']} ({party['role']})")

    print(f"\n=== Attorneys ===")
    for attorney in who['attorneys']:
        print(f"- {attorney['name']} representing {attorney['represents']}")

    print(f"\n=== Judges ===")
    for judge in who['judges']:
        print(f"- {judge['name']} ({judge['court']})")


# Usage
analyze_case_parties(
    client_id="client-abc-123",
    case_id="case-xyz-456"
)
```

---

### Example 4: Error Handling

```python
import httpx

def safe_context_retrieval(client_id: str, case_id: str):
    """Retrieve context with comprehensive error handling"""
    client = ContextEngineClient()

    try:
        context = client.retrieve_context(
            client_id=client_id,
            case_id=case_id,
            scope="comprehensive"
        )
        return context

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"Case {case_id} not found")
        elif e.response.status_code == 503:
            print("Service unavailable - check dependencies")
        else:
            print(f"HTTP error: {e.response.status_code}")
        return None

    except httpx.TimeoutException:
        print("Request timed out - try minimal scope")
        # Retry with minimal scope
        try:
            return client.retrieve_context(
                client_id=client_id,
                case_id=case_id,
                scope="minimal"
            )
        except Exception as e:
            print(f"Retry failed: {e}")
            return None

    except httpx.RequestError as e:
        print(f"Network error: {e}")
        return None

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

---

### Example 5: Cache Management

```python
def smart_cache_usage(client_id: str, case_id: str, force_refresh: bool = False):
    """Intelligent cache usage pattern"""
    client = ContextEngineClient()

    if force_refresh:
        # Clear cache first
        print("Clearing cache...")
        client.clear_cache(case_id)

    # Retrieve context
    context = client.retrieve_context(
        client_id=client_id,
        case_id=case_id,
        scope="comprehensive",
        use_cache=not force_refresh
    )

    # Check if cached
    if context['cached']:
        print(f"✅ Served from cache: {context['execution_time_ms']}ms")
    else:
        print(f"⚠️ Cache miss: {context['execution_time_ms']}ms")

    return context


# Usage
# First call - cache miss
context1 = smart_cache_usage("client-abc", "case-xyz")

# Second call - cache hit (<10ms)
context2 = smart_cache_usage("client-abc", "case-xyz")

# Force refresh after document upload
context3 = smart_cache_usage("client-abc", "case-xyz", force_refresh=True)
```

---

## Response Structure

### WHO Dimension

```json
{
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "parties": [
    {
      "id": "party-001",
      "name": "John Smith",
      "role": "plaintiff",
      "entity_type": "individual",
      "contact": {...}
    }
  ],
  "judges": [
    {
      "id": "judge-001",
      "name": "Hon. Jane Doe",
      "court": "U.S. District Court",
      "preferences": {...}
    }
  ],
  "attorneys": [
    {
      "id": "attorney-001",
      "name": "Robert Johnson",
      "firm": "Johnson & Associates",
      "represents": "plaintiff",
      "bar_number": "CA-12345"
    }
  ],
  "witnesses": [...],
  "party_relationships": {
    "plaintiff-defendant": "adversarial",
    "co-defendants": "joint_defense"
  },
  "representation_map": {
    "party-001": ["attorney-001"],
    "party-002": ["attorney-002", "attorney-003"]
  }
}
```

### WHAT Dimension

```json
{
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "legal_issues": [
    {
      "issue": "subject_matter_jurisdiction",
      "description": "Federal question jurisdiction under 28 U.S.C. § 1331",
      "primary": true
    }
  ],
  "statutes": [
    {
      "citation": "28 U.S.C. § 1331",
      "title": "Federal Question Jurisdiction",
      "relevance": "primary"
    }
  ],
  "causes_of_action": [
    {
      "claim": "breach_of_contract",
      "elements": [...],
      "status": "pending"
    }
  ],
  "defenses": [...],
  "legal_standards": [...]
}
```

### WHERE Dimension

```json
{
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "primary_jurisdiction": "federal",
  "court": "U.S. District Court, Northern District of California",
  "venue": "San Francisco",
  "judge_chambers": "450 Golden Gate Ave, San Francisco, CA",
  "local_rules": [
    {
      "rule": "Civil L.R. 7-1",
      "description": "Motion practice requirements",
      "url": "https://..."
    }
  ],
  "filing_requirements": [
    {
      "type": "motion",
      "format": "PDF",
      "page_limit": 25,
      "font": "Times New Roman 12pt"
    }
  ],
  "related_proceedings": []
}
```

### WHEN Dimension

```json
{
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "filing_date": "2024-09-15",
  "key_dates": [
    {
      "date": "2024-10-01",
      "event": "Initial Case Management Conference",
      "status": "scheduled"
    }
  ],
  "deadlines": [
    {
      "date": "2024-10-15",
      "description": "Defendant's response to complaint",
      "priority": "high"
    }
  ],
  "timeline": [
    {
      "date": "2024-08-01",
      "event": "Alleged breach occurred"
    },
    {
      "date": "2024-09-15",
      "event": "Complaint filed"
    }
  ],
  "statute_of_limitations": {
    "claim_type": "breach_of_contract",
    "period": "4 years",
    "expires": "2028-08-01"
  }
}
```

### WHY Dimension

```json
{
  "case_id": "case-xyz-456",
  "case_name": "Smith v. Jones",
  "precedents": [
    {
      "case_name": "United States v. Johnson",
      "citation": "123 F.3d 456 (9th Cir. 2020)",
      "relevance_score": 0.95,
      "holding": "Federal question jurisdiction requires...",
      "reasoning": "The court held that...",
      "similarity_metrics": {
        "legal_issue_match": 0.98,
        "fact_pattern_similarity": 0.85
      }
    }
  ],
  "legal_standards": [
    {
      "standard": "Federal Question Test",
      "description": "Arises under federal law",
      "authority": "28 U.S.C. § 1331"
    }
  ],
  "reasoning": [
    {
      "argument": "Federal question jurisdiction exists",
      "support": [
        "Complaint alleges constitutional violation",
        "Federal statute provides cause of action"
      ],
      "precedents": ["case-001", "case-002"]
    }
  ]
}
```

---

## Error Handling

### Common HTTP Status Codes

| Code | Meaning | Cause |
|------|---------|-------|
| 200 | Success | Request processed successfully |
| 400 | Bad Request | Invalid parameters or missing required fields |
| 404 | Not Found | Case not found in database |
| 500 | Internal Server Error | Service error (check logs) |
| 503 | Service Unavailable | Dependent service (GraphRAG/DB) unavailable |

### Error Response Format

```json
{
  "detail": "Case not found: case-xyz-456"
}
```

### Handling Errors in Python

```python
try:
    context = client.retrieve_context(
        client_id="abc",
        case_id="xyz",
        scope="comprehensive"
    )
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        print(f"Case not found: {e.response.json()['detail']}")
    elif e.response.status_code == 503:
        print("Service unavailable - check dependencies")
    else:
        print(f"Error: {e.response.status_code}")
except httpx.TimeoutException:
    print("Request timed out")
```

---

## Performance Tips

### 1. Use Appropriate Scope

```python
# ❌ BAD: Always using comprehensive (slow)
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"  # 800-2000ms
)

# ✅ GOOD: Use minimal for quick lookups
context = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="minimal"  # 50-150ms
)
```

### 2. Leverage Caching

```python
# First call: cache miss (800ms)
context1 = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"
)

# Second call: cache hit (<10ms)
context2 = client.retrieve_context(
    client_id="abc",
    case_id="xyz",
    scope="comprehensive"
)
```

### 3. Retrieve Only Needed Dimensions

```python
# ❌ BAD: Retrieve full context when only need parties
context = client.retrieve_context(...)
parties = context['who']['parties']  # Wasteful

# ✅ GOOD: Retrieve just WHO dimension
who = client.retrieve_dimension(
    client_id="abc",
    case_id="xyz",
    dimension="who"
)
parties = who['parties']  # 4x faster
```

### 4. Parallel Retrieval

```python
import asyncio

async def get_multiple_contexts(case_ids):
    client = AsyncContextEngineClient()
    tasks = [
        client.retrieve_context("abc", case_id, "standard")
        for case_id in case_ids
    ]
    return await asyncio.gather(*tasks)

# 10 cases in ~500ms (parallel) vs. ~5000ms (sequential)
contexts = asyncio.run(get_multiple_contexts([
    "case-001", "case-002", ..., "case-010"
]))
```

### 5. Monitor Cache Performance

```python
stats = client.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")

if stats['hit_rate'] < 0.5:
    print("⚠️ Low cache hit rate - consider increasing TTL")
```

---

## Additional Resources

- **Interactive API Docs**: http://10.10.0.87:8015/docs
- **Full Usage Guide**: `/srv/luris/be/context-engine-service/USAGE_GUIDE.md`
- **Production Readiness**: `/srv/luris/be/context-engine-service/PRODUCTION_READINESS.md`
- **Service Logs**: `journalctl -u luris-context-engine -f`

---

## Quick Command Reference

```bash
# Health check
curl http://10.10.0.87:8015/api/v1/health

# Retrieve context
curl -X POST http://10.10.0.87:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{"client_id":"abc","case_id":"xyz","scope":"standard"}'

# Get single dimension
curl -X POST http://10.10.0.87:8015/api/v1/context/dimension/retrieve \
  -H "Content-Type: application/json" \
  -d '{"client_id":"abc","case_id":"xyz","dimension":"who"}'

# Cache stats
curl http://10.10.0.87:8015/api/v1/cache/stats

# Clear cache
curl -X POST http://10.10.0.87:8015/api/v1/cache/clear \
  -H "Content-Type: application/json" \
  -d '{"case_id":"xyz"}'
```

---

**Last Updated:** 2024-10-24
**Version:** 1.0.0
