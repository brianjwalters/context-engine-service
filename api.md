# Context Engine Service - API Documentation

**Base URL:** `http://10.10.0.87:8015`
**Version:** 1.0.0
**Port:** 8015

---

## Table of Contents

- [Interactive Documentation](#interactive-documentation)
- [Authentication](#authentication)
- [Error Handling](#error-handling)
- [Context Retrieval API](#context-retrieval-api)
- [Cache Management API](#cache-management-api)
- [Health & Monitoring](#health--monitoring)
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

## Context Retrieval API

### POST /api/v1/context/retrieve

Build multi-dimensional context for a specific case using WHO/WHAT/WHERE/WHEN/WHY framework.

**Request Body:**
```json
{
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "scope": "comprehensive",
  "use_cache": true
}
```

**Response (200 OK):** Full ContextResponse with all 5 dimensions

**Performance:**
- Cached: <10ms
- Minimal (cache miss): 50-150ms
- Standard (cache miss): 200-600ms
- Comprehensive (cache miss): 800-2000ms

---

### GET /api/v1/context/retrieve

Convenience GET endpoint with query parameters.

---

### POST /api/v1/context/dimension/retrieve

Retrieve a single dimension (faster than full context).

---

### GET /api/v1/context/dimension/quality

Get quality metrics for a specific dimension.

---

### POST /api/v1/context/refresh

Force context refresh (bypass cache).

---

### POST /api/v1/context/batch/retrieve

Retrieve context for multiple cases.

---

## Cache Management API

### GET /api/v1/cache/stats

Get comprehensive cache statistics.

---

### DELETE /api/v1/cache/invalidate

Invalidate cached context for a case.

---

### POST /api/v1/cache/warmup

Pre-warm cache for multiple cases.

---

### GET /api/v1/cache/config

Get cache configuration.

---

### GET /api/v1/cache/health

Check cache system health.

---

## Health & Monitoring

### GET /api/v1/health

Basic health check.

---

### GET /metrics

Prometheus metrics endpoint.

---

## Code Examples

### Python

```python
import httpx

async def get_case_context(client_id: str, case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        return response.json()
```

---

**For complete API documentation, see:**
- `/docs/technical-specification.md` - Full technical specification
- Interactive docs: http://10.10.0.87:8015/docs

**API Version:** 1.0.0
**Last Updated:** 2025-01-22
