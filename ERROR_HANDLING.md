# Context Engine Error Handling Guide

**Comprehensive Error Scenarios and Recovery Strategies**

---

## Table of Contents

- [Error Response Format](#error-response-format)
- [HTTP Status Codes](#http-status-codes)
- [Common Error Scenarios](#common-error-scenarios)
- [Service Dependency Errors](#service-dependency-errors)
- [Data Quality Errors](#data-quality-errors)
- [Performance Errors](#performance-errors)
- [Recovery Strategies](#recovery-strategies)
- [Error Logging](#error-logging)
- [Client Error Handling](#client-error-handling)

---

## Error Response Format

All errors follow a consistent JSON format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "MACHINE_READABLE_CODE",
  "additional_context": {
    "field": "value"
  }
}
```

**Example Error Response:**
```json
{
  "detail": "Case not found",
  "case_id": "invalid-case-123",
  "error_code": "CASE_NOT_FOUND"
}
```

---

## HTTP Status Codes

| Code | Name | When It Occurs | Recovery Action |
|------|------|----------------|-----------------|
| 200 | OK | Request successful | None - proceed with response |
| 400 | Bad Request | Invalid parameters | Fix request parameters |
| 404 | Not Found | Resource doesn't exist | Verify resource ID |
| 500 | Internal Server Error | Service error | Retry with backoff, contact support |
| 503 | Service Unavailable | Dependency unavailable | Wait and retry, check service status |

---

## Common Error Scenarios

### 1. Case Not Found (404)

**Cause**: Requested `case_id` doesn't exist in database.

**Error Response:**
```json
{
  "detail": "Case not found",
  "case_id": "invalid-case-123",
  "error_code": "CASE_NOT_FOUND"
}
```

**Recovery Strategy:**
```python
try:
    response = await client.post(
        "/api/v1/context/retrieve",
        json={"client_id": client_id, "case_id": case_id}
    )
    context = response.json()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        logger.error(f"Case {case_id} not found")

        # Recovery options:
        # 1. Verify case_id is correct
        # 2. Check if case exists in database
        # 3. Create case if it should exist

        # Verify in database
        case_exists = await verify_case_exists(case_id)
        if not case_exists:
            logger.info(f"Creating case {case_id}")
            await create_case(case_id)

            # Retry after creation
            response = await client.post(
                "/api/v1/context/retrieve",
                json={"client_id": client_id, "case_id": case_id}
            )
```

**Prevention:**
- Always verify case exists before requesting context
- Use batch operations to check multiple cases
- Implement case creation workflow

---

### 2. Invalid Scope Parameter (400)

**Cause**: Invalid value for `scope` parameter.

**Error Response:**
```json
{
  "detail": "Invalid scope: invalid_scope. Valid scopes: ['minimal', 'standard', 'comprehensive']",
  "error_code": "INVALID_SCOPE"
}
```

**Recovery Strategy:**
```python
VALID_SCOPES = ["minimal", "standard", "comprehensive"]

def get_context_with_validation(case_id: str, scope: str = "comprehensive"):
    # Validate scope before request
    if scope not in VALID_SCOPES:
        logger.warning(f"Invalid scope '{scope}', defaulting to 'comprehensive'")
        scope = "comprehensive"

    try:
        response = await client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": scope
            }
        )
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            error_detail = e.response.json()
            logger.error(f"Request error: {error_detail['detail']}")
            raise ValueError(f"Invalid request: {error_detail['detail']}")
```

**Prevention:**
- Use enums or constants for scope values
- Validate parameters before API calls
- Implement client-side validation

---

### 3. Invalid Dimension Name (400)

**Cause**: Invalid dimension name in dimension-specific request.

**Error Response:**
```json
{
  "detail": "Invalid dimension: INVALID. Valid dimensions: {'WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY'}",
  "error_code": "INVALID_DIMENSION"
}
```

**Recovery Strategy:**
```python
VALID_DIMENSIONS = {"WHO", "WHAT", "WHERE", "WHEN", "WHY"}

async def get_dimension_safe(case_id: str, dimension: str):
    # Normalize and validate dimension
    dimension = dimension.upper()

    if dimension not in VALID_DIMENSIONS:
        raise ValueError(
            f"Invalid dimension: {dimension}. "
            f"Valid dimensions: {VALID_DIMENSIONS}"
        )

    try:
        response = await client.post(
            "/api/v1/context/dimension/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "dimension": dimension
            }
        )
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            logger.error(f"Dimension request failed: {e.response.json()}")
            raise
```

**Prevention:**
- Use uppercase dimension names consistently
- Validate dimension names before requests
- Provide clear error messages to users

---

### 4. Missing Required Fields (400)

**Cause**: Required field(s) missing from request body.

**Error Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "client_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

**Recovery Strategy:**
```python
from pydantic import BaseModel, ValidationError

class ContextRequest(BaseModel):
    client_id: str
    case_id: str
    scope: str = "comprehensive"
    use_cache: bool = True

def make_context_request(client_id: str, case_id: str, **kwargs):
    try:
        # Validate request with Pydantic
        request = ContextRequest(
            client_id=client_id,
            case_id=case_id,
            **kwargs
        )

        response = await client.post(
            "/api/v1/context/retrieve",
            json=request.dict()
        )
        return response.json()

    except ValidationError as e:
        logger.error(f"Request validation failed: {e}")
        raise ValueError(f"Invalid request: {e}")
```

**Prevention:**
- Use Pydantic models for request validation
- Provide default values for optional fields
- Document all required fields clearly

---

## Service Dependency Errors

### 1. GraphRAG Service Unavailable (503)

**Cause**: GraphRAG service (port 8010) not responding.

**Error Response:**
```json
{
  "detail": "GraphRAG service unavailable",
  "service": "graphrag",
  "port": 8010,
  "error_code": "SERVICE_UNAVAILABLE"
}
```

**Impact**:
- **WHO dimension**: Partial - relationship data missing
- **WHAT dimension**: Partial - citation network unavailable
- **WHY dimension**: Severely impacted - precedent analysis fails

**Recovery Strategy:**
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def get_context_with_retry(case_id: str, fallback_to_partial: bool = True):
    try:
        # Attempt full context retrieval
        response = await client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            error_detail = e.response.json()

            if fallback_to_partial:
                logger.warning(
                    f"Service {error_detail.get('service')} unavailable, "
                    "falling back to partial context"
                )

                # Retry with minimal scope (doesn't require WHY dimension)
                response = await client.post(
                    "/api/v1/context/retrieve",
                    json={
                        "client_id": client_id,
                        "case_id": case_id,
                        "scope": "minimal"  # Only WHO + WHERE
                    }
                )
                return response.json()
            else:
                raise

# Usage
try:
    context = await get_context_with_retry(case_id)
    if context.get("why") is None:
        logger.warning("WHY dimension unavailable - precedent analysis skipped")
except Exception as e:
    logger.error(f"All retry attempts failed: {e}")
```

**Monitoring:**
```python
# Check service health before request
async def check_service_health():
    try:
        response = await client.get("http://10.10.0.87:8015/api/v1/health")
        health = response.json()

        if health["status"] != "healthy":
            logger.warning(f"Context Engine service degraded: {health}")
            return False

        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

# Use health check
if await check_service_health():
    context = await get_context(case_id)
else:
    logger.error("Service unhealthy - deferring context retrieval")
```

**Prevention:**
- Monitor service health endpoints
- Implement circuit breakers
- Use fallback strategies for degraded service

---

### 2. Supabase Database Connection Error (500)

**Cause**: Cannot connect to Supabase database.

**Error Response:**
```json
{
  "detail": "Database connection failed",
  "error_code": "DATABASE_CONNECTION_ERROR"
}
```

**Recovery Strategy:**
```python
async def get_context_with_db_fallback(case_id: str):
    try:
        response = await client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 500:
            error_detail = e.response.json()

            if "database" in error_detail.get("detail", "").lower():
                logger.error("Database connection failed")

                # Check if cache has stale data
                cached_context = await check_local_cache(case_id)
                if cached_context:
                    logger.info("Using stale cached context as fallback")
                    cached_context["_stale"] = True
                    return cached_context

                raise Exception("Database unavailable and no cached data")
```

---

## Data Quality Errors

### 1. Low Quality Context (< 0.85 threshold)

**Cause**: Insufficient data to build complete context.

**Response:**
```json
{
  "case_id": "case-123",
  "context_score": 0.67,
  "is_complete": false,
  "execution_time_ms": 1200
}
```

**Recovery Strategy:**
```python
async def ensure_quality_context(case_id: str, min_score: float = 0.85):
    # Retrieve context
    context = await get_context(case_id, scope="comprehensive")

    # Check quality
    if context["context_score"] < min_score:
        logger.warning(
            f"Low quality context: {context['context_score']:.2f} "
            f"(threshold: {min_score})"
        )

        # Diagnose which dimensions are insufficient
        insufficient_dimensions = []
        for dimension in ["WHO", "WHAT", "WHERE", "WHEN", "WHY"]:
            quality = await client.get(
                "/api/v1/context/dimension/quality",
                params={
                    "client_id": client_id,
                    "case_id": case_id,
                    "dimension": dimension
                }
            ).json()

            if not quality["is_sufficient"]:
                insufficient_dimensions.append({
                    "dimension": dimension,
                    "score": quality["completeness_score"],
                    "data_points": quality["data_points"]
                })

        logger.info(f"Insufficient dimensions: {insufficient_dimensions}")

        # Possible recovery actions:
        # 1. Extract more entities from documents
        await extract_additional_entities(case_id)

        # 2. Refresh context after additional extraction
        await client.post(
            "/api/v1/context/refresh",
            params={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )

        # 3. Retrieve updated context
        updated_context = await get_context(case_id, use_cache=False)

        if updated_context["context_score"] >= min_score:
            logger.info(
                f"Context quality improved: {updated_context['context_score']:.2f}"
            )
            return updated_context
        else:
            logger.warning(
                f"Context quality still below threshold after refresh: "
                f"{updated_context['context_score']:.2f}"
            )
            return updated_context

    return context
```

**Prevention:**
- Run entity extraction on all case documents
- Verify document quality before processing
- Implement data validation pipelines

---

### 2. Missing Critical Dimension

**Cause**: A required dimension failed to build.

**Response:**
```json
{
  "case_id": "case-123",
  "who": {...},
  "what": {...},
  "where": {...},
  "when": null,
  "why": {...},
  "context_score": 0.72,
  "is_complete": false
}
```

**Recovery Strategy:**
```python
async def handle_missing_dimension(context: dict, required_dimension: str):
    dimension_key = required_dimension.lower()

    if context.get(dimension_key) is None:
        logger.error(f"{required_dimension} dimension missing")

        # Try to retrieve just that dimension
        try:
            response = await client.post(
                "/api/v1/context/dimension/retrieve",
                json={
                    "client_id": client_id,
                    "case_id": context["case_id"],
                    "dimension": required_dimension
                }
            )

            dimension_data = response.json()["data"]

            if dimension_data:
                # Update context with recovered dimension
                context[dimension_key] = dimension_data
                logger.info(f"{required_dimension} dimension recovered")
            else:
                logger.warning(f"{required_dimension} dimension still unavailable")

        except Exception as e:
            logger.error(f"Failed to recover {required_dimension} dimension: {e}")

    return context

# Usage
context = await get_context(case_id)

# Ensure WHEN dimension is present
if context.get("when") is None:
    context = await handle_missing_dimension(context, "WHEN")

    if context.get("when") is None:
        raise ValueError("WHEN dimension required but unavailable")
```

---

## Performance Errors

### 1. Timeout Error

**Cause**: Request exceeded timeout limit.

**Recovery Strategy:**
```python
import httpx

async def get_context_with_timeout(
    case_id: str,
    timeout: float = 30.0,
    retry_with_minimal: bool = True
):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://10.10.0.87:8015/api/v1/context/retrieve",
                json={
                    "client_id": client_id,
                    "case_id": case_id,
                    "scope": "comprehensive"
                }
            )
            return response.json()

    except httpx.TimeoutException:
        logger.warning(f"Context retrieval timed out after {timeout}s")

        if retry_with_minimal:
            logger.info("Retrying with minimal scope")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "http://10.10.0.87:8015/api/v1/context/retrieve",
                    json={
                        "client_id": client_id,
                        "case_id": case_id,
                        "scope": "minimal"  # Faster scope
                    }
                )
                return response.json()
        else:
            raise
```

**Prevention:**
- Use appropriate scope for use case
- Warm cache for frequently accessed cases
- Monitor performance metrics

---

### 2. Cache Degradation

**Cause**: Cache hit rate below 50%.

**Detection:**
```python
async def monitor_cache_health():
    response = await client.get("http://10.10.0.87:8015/api/v1/cache/health")
    health = response.json()

    if health["status"] == "degraded":
        logger.warning(
            f"Cache degraded - hit rate: {health['overall_hit_rate']:.1%}"
        )

        # Get detailed stats
        stats_response = await client.get(
            "http://10.10.0.87:8015/api/v1/cache/stats"
        )
        stats = stats_response.json()

        logger.info(f"Memory utilization: {stats['memory_cache']['utilization']:.1%}")

        # Recovery action: warm cache
        if stats['memory_cache']['utilization'] < 0.5:
            logger.info("Cache underutilized - warming up frequently used cases")
            await warm_frequently_used_cases()
```

**Recovery:**
```python
async def warm_frequently_used_cases():
    # Get list of frequently accessed cases
    frequent_cases = await get_frequent_case_ids(limit=50)

    # Warm cache
    response = await client.post(
        "http://10.10.0.87:8015/api/v1/cache/warmup",
        json={
            "client_id": client_id,
            "case_ids": frequent_cases,
            "scope": "standard"
        }
    )

    result = response.json()
    logger.info(
        f"Cache warmup complete: {result['successful']}/{result['total_cases']}"
    )
```

---

## Recovery Strategies

### Retry with Exponential Backoff

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry_if_exception_type=httpx.HTTPStatusError),
    reraise=True
)
async def get_context_with_backoff(case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        response.raise_for_status()
        return response.json()
```

### Circuit Breaker Pattern

```python
from circuit_breaker import CircuitBreaker

context_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=httpx.HTTPStatusError
)

@context_breaker
async def get_context_with_circuit_breaker(case_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.10.0.87:8015/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": "comprehensive"
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
try:
    context = await get_context_with_circuit_breaker(case_id)
except CircuitBreakerError:
    logger.error("Circuit breaker open - service unavailable")
    # Use fallback or cached data
```

### Graceful Degradation

```python
async def get_context_with_degradation(case_id: str):
    # Try comprehensive first
    try:
        return await get_context(case_id, scope="comprehensive")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            logger.warning("Service degraded - trying standard scope")

            # Try standard scope
            try:
                return await get_context(case_id, scope="standard")
            except Exception:
                logger.warning("Service degraded - trying minimal scope")

                # Last resort: minimal scope
                return await get_context(case_id, scope="minimal")
        raise
```

---

## Error Logging

### Structured Logging

```python
import logging
import json

logger = logging.getLogger(__name__)

def log_context_error(
    error: Exception,
    case_id: str,
    scope: str,
    additional_context: dict = None
):
    error_log = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "case_id": case_id,
        "scope": scope,
        "timestamp": datetime.now().isoformat()
    }

    if additional_context:
        error_log.update(additional_context)

    logger.error(f"Context retrieval error: {json.dumps(error_log)}")

# Usage
try:
    context = await get_context(case_id, scope="comprehensive")
except httpx.HTTPStatusError as e:
    log_context_error(
        error=e,
        case_id=case_id,
        scope="comprehensive",
        additional_context={
            "status_code": e.response.status_code,
            "response_body": e.response.text
        }
    )
    raise
```

### Error Monitoring

```python
from prometheus_client import Counter, Histogram

context_errors = Counter(
    'context_engine_errors_total',
    'Total context retrieval errors',
    ['error_type', 'status_code']
)

context_latency = Histogram(
    'context_engine_latency_seconds',
    'Context retrieval latency',
    ['scope', 'cached']
)

async def get_context_with_metrics(case_id: str, scope: str = "comprehensive"):
    start_time = time.time()

    try:
        response = await client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": client_id,
                "case_id": case_id,
                "scope": scope
            }
        )

        context = response.json()

        # Record success metrics
        duration = time.time() - start_time
        context_latency.labels(
            scope=scope,
            cached=context.get("cached", False)
        ).observe(duration)

        return context

    except httpx.HTTPStatusError as e:
        # Record error metrics
        context_errors.labels(
            error_type=type(e).__name__,
            status_code=e.response.status_code
        ).inc()

        logger.error(f"Context retrieval failed: {e}")
        raise
```

---

## Client Error Handling

### Complete Error Handling Example

```python
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional

logger = logging.getLogger(__name__)

class ContextEngineClient:
    def __init__(self, base_url: str = "http://10.10.0.87:8015"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_context(
        self,
        client_id: str,
        case_id: str,
        scope: str = "comprehensive",
        use_cache: bool = True,
        fallback_to_minimal: bool = True
    ) -> dict:
        """
        Retrieve case context with comprehensive error handling.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Context scope (minimal/standard/comprehensive)
            use_cache: Whether to use cached context
            fallback_to_minimal: Fall back to minimal scope on error

        Returns:
            Context dictionary

        Raises:
            ValueError: Invalid parameters
            httpx.HTTPStatusError: API error after retries
        """
        # Validate parameters
        if scope not in ["minimal", "standard", "comprehensive"]:
            raise ValueError(f"Invalid scope: {scope}")

        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/context/retrieve",
                json={
                    "client_id": client_id,
                    "case_id": case_id,
                    "scope": scope,
                    "use_cache": use_cache
                }
            )

            response.raise_for_status()
            context = response.json()

            # Warn on low quality
            if context.get("context_score", 1.0) < 0.85:
                logger.warning(
                    f"Low quality context for {case_id}: "
                    f"{context['context_score']:.2f}"
                )

            return context

        except httpx.HTTPStatusError as e:
            error_detail = e.response.json() if e.response else {}

            # Handle specific errors
            if e.response.status_code == 404:
                logger.error(f"Case not found: {case_id}")
                raise ValueError(f"Case {case_id} not found")

            elif e.response.status_code == 400:
                logger.error(f"Invalid request: {error_detail.get('detail')}")
                raise ValueError(f"Invalid request: {error_detail.get('detail')}")

            elif e.response.status_code == 503:
                logger.warning("Service degraded")

                if fallback_to_minimal and scope != "minimal":
                    logger.info("Falling back to minimal scope")
                    return await self.get_context(
                        client_id=client_id,
                        case_id=case_id,
                        scope="minimal",
                        use_cache=use_cache,
                        fallback_to_minimal=False  # Prevent infinite loop
                    )

            # Re-raise for retry logic
            raise

    async def close(self):
        await self.client.aclose()

# Usage
async def main():
    client = ContextEngineClient()

    try:
        context = await client.get_context(
            client_id="client-abc",
            case_id="case-123",
            scope="comprehensive"
        )

        print(f"Context retrieved: quality={context['context_score']:.2f}")

    except ValueError as e:
        logger.error(f"Validation error: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"API error: {e}")
    finally:
        await client.close()
```

---

**Version**: 1.0.0
**Last Updated**: 2025-01-22
**Related Documentation**:
- [API Documentation](api.md)
- [Dimension Reference](DIMENSION_REFERENCE.md)
- [Advanced Usage](ADVANCED_USAGE.md)
