# Context Engine Service - Technical Specification

**Version:** 1.0.0
**Port:** 8015
**Status:** Production Ready
**Last Updated:** 2025-01-22

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [API Reference](#api-reference)
5. [Performance Characteristics](#performance-characteristics)
6. [Caching Strategy](#caching-strategy)
7. [Database Schema](#database-schema)
8. [Service Dependencies](#service-dependencies)
9. [Deployment Guide](#deployment-guide)
10. [Monitoring & Metrics](#monitoring--metrics)

---

## Executive Summary

The **Context Engine Service** is a specialized microservice designed to construct comprehensive, multi-dimensional legal context for case-centric workflows. It implements the WHO/WHAT/WHERE/WHEN/WHY framework to provide rich contextual understanding of legal cases through intelligent orchestration of knowledge graph queries, entity extraction, and precedent analysis.

### Key Features

- ✅ **Multi-Dimensional Context**: WHO, WHAT, WHERE, WHEN, WHY framework
- ✅ **Case-Centric Architecture**: 99% of queries are case-specific with composite indexes
- ✅ **Multi-Tier Caching**: In-memory (10min), Redis (1-24hr), Database (persistent)
- ✅ **Parallel Execution**: Dimensions analyzed concurrently for optimal performance
- ✅ **Quality Scoring**: Automated completeness and confidence metrics
- ✅ **GraphRAG Integration**: Microsoft GraphRAG with Leiden community detection
- ✅ **REST API**: 20 endpoints for context retrieval and cache management

### Target Performance

| Context Scope | Target Latency | Dimensions | Use Case |
|--------------|----------------|------------|----------|
| **Minimal** | <100ms | WHO + WHERE | Quick party/jurisdiction lookup |
| **Standard** | 100-500ms | WHO + WHAT + WHERE + WHEN | Most common queries |
| **Comprehensive** | 500-2000ms | All 5 dimensions | Deep legal analysis |

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Context Engine Service                     │
│                        (Port 8015)                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   FastAPI    │  │   Context    │  │    Cache     │     │
│  │     App      │  │   Builder    │  │   Manager    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         │   ┌──────────────▼──────────────┐  │              │
│         │   │   Dimension Analyzers       │  │              │
│         │   ├─────────────────────────────┤  │              │
│         │   │ • WhoAnalyzer               │  │              │
│         │   │ • WhatAnalyzer              │  │              │
│         │   │ • WhereAnalyzer             │  │              │
│         │   │ • WhenAnalyzer              │  │              │
│         │   │ • WhyAnalyzer               │  │              │
│         │   └─────────────┬───────────────┘  │              │
│         │                 │                   │              │
│         │   ┌─────────────▼───────────────┐  │              │
│         │   │   Multi-Tier Cache          │◄─┘              │
│         │   ├─────────────────────────────┤                 │
│         │   │ Tier 1: LRU Memory (10min)  │                 │
│         │   │ Tier 2: Redis (1-24hr)      │ (placeholder)   │
│         │   │ Tier 3: Database            │ (placeholder)   │
│         │   └─────────────┬───────────────┘                 │
└─────────────────────────────┼───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   GraphRAG   │    │   Supabase   │    │    vLLM      │
│   Service    │    │   Database   │    │   Services   │
│  (Port 8010) │    │              │    │ (8080/8082)  │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Data Flow

1. **Request Reception**: Client sends context retrieval request with `case_id`
2. **Cache Check**: CacheManager checks all tiers (memory → Redis → DB)
3. **Parallel Execution**: If cache miss, ContextBuilder executes dimension analyzers in parallel
4. **Dimension Analysis**: Each analyzer queries GraphRAG and Supabase for case-specific data
5. **Quality Scoring**: Overall context quality calculated from dimension completeness
6. **Cache Storage**: Complete context cached with TTL based on case status
7. **Response**: ContextResponse returned with all dimensions and metadata

---

## Core Components

### 1. Context Builder (`context_builder.py` - 661 lines)

**Purpose**: Orchestrates multi-dimensional context construction

**Key Features**:
- Parallel dimension execution using `asyncio.gather()`
- Configurable scopes: minimal, standard, comprehensive
- Quality scoring algorithm (0.0-1.0 scale)
- Cache integration for performance
- Graceful degradation on analyzer failures

**Quality Score Algorithm**:
```python
context_score = (dimension_scores_avg) * (successful_dimensions / total_dimensions)

# Threshold for completeness: 0.85
# Example: 4/5 dimensions at 0.9 each = 0.9 * 0.8 = 0.72 (incomplete)
#          5/5 dimensions at 0.9 each = 0.9 * 1.0 = 0.90 (complete)
```

**Scope Definitions**:
```python
SCOPES = {
    'minimal': ['WHO', 'WHERE'],           # 2 dimensions
    'standard': ['WHO', 'WHAT', 'WHERE', 'WHEN'],  # 4 dimensions
    'comprehensive': ['WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY']  # All 5
}
```

### 2. Dimension Analyzers (`dimension_analyzer.py` - 922 lines)

**Purpose**: Extract specific context dimensions for legal cases

#### WhoAnalyzer
- **Entities**: Parties, Judges, Attorneys, Witnesses
- **Data Sources**:
  - GraphRAG: `query()` for entity relationships
  - Supabase: `graph.nodes` table filtered by `entity_type IN ('PARTY', 'JUDGE', 'ATTORNEY', 'WITNESS')`
- **Output**: `WhoContext` with party relationships and representation map

#### WhatAnalyzer
- **Entities**: Causes of Action, Legal Issues, Statutes, Case Citations, Doctrines
- **Data Sources**:
  - GraphRAG: Legal concept queries
  - Supabase: `graph.nodes` table filtered by `entity_type IN ('STATUTE_CITATION', 'CASE_CITATION', 'LEGAL_PRINCIPLE')`
- **Output**: `WhatContext` with issue complexity score

#### WhereAnalyzer
- **Entities**: Jurisdiction, Court, Venue, Local Rules
- **Data Sources**:
  - Supabase: `client.client_cases` table
- **Output**: `WhereContext` with court hierarchy information

#### WhenAnalyzer
- **Entities**: Filing Date, Timeline Events, Deadlines, Statute of Limitations
- **Data Sources**:
  - Supabase: `client.client_cases` table, deadlines table (future)
- **Metrics**: Case age (days), days until next deadline, urgency score
- **Output**: `WhenContext` with urgency calculation

#### WhyAnalyzer
- **Entities**: Legal Theories, Precedents, Argument Analysis
- **Data Sources**:
  - GraphRAG: `GLOBAL` search for precedent cases
  - Supabase: Legal theory nodes
- **Metrics**: Argument strength (supporting vs opposing precedents)
- **Output**: `WhyContext` with precedent categorization

### 3. Cache Manager (`cache_manager.py` - 634 lines)

**Purpose**: Multi-tier caching system for context queries

#### Tier 1: In-Memory LRU Cache
- **Implementation**: `OrderedDict` with TTL and LRU eviction
- **Capacity**: 1,000 entries (configurable)
- **TTL**: 10 minutes
- **Eviction**: Least Recently Used (LRU)
- **Scope**: Per-process (not shared across instances)
- **Hit Tracking**: Records hit count and last access time

#### Tier 2: Redis Cache (Placeholder)
- **TTL Strategy**:
  - Active cases: 1 hour
  - Closed cases: 24 hours
- **Scope**: Shared across all service instances
- **Status**: Implementation pending

#### Tier 3: Database Cache (Placeholder)
- **Table**: `context.cached_contexts`
- **TTL**: Permanent (manual invalidation)
- **Scope**: Persistent storage
- **Status**: Implementation pending

**Cache Key Format**:
```
context:{client_id}:{case_id}:{scope}:{hash}
Example: context:client-abc:case-123:comprehensive:a3f5b2c1
```

**TTL Configuration**:
```python
MEMORY_TTL = 600        # 10 minutes
ACTIVE_CASE_TTL = 3600  # 1 hour (Redis/DB)
CLOSED_CASE_TTL = 86400 # 24 hours (Redis/DB)
```

### 4. GraphRAG Client (`graphrag_client.py` - 1,000+ lines)

**Purpose**: Case-aware wrapper for GraphRAG Service queries

**Key Features**:
- Automatic `case_id` filtering for all queries
- Circuit breaker pattern (5 failures → 60s recovery)
- Retry logic with exponential backoff (max 3 retries)
- Request/response validation
- Connection pooling

**Query Types**:
- `LOCAL`: Community-based search (parties, local entities)
- `GLOBAL`: Cross-community search (precedents, broader concepts)
- `HYBRID`: Combined local + global

---

## API Reference

### Base URL
```
http://10.10.0.87:8015/api/v1
```

### Context Retrieval Endpoints

#### POST /context/retrieve
Build multi-dimensional context for a case.

**Request Body**:
```json
{
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "scope": "comprehensive",
  "include_dimensions": null,
  "use_cache": true
}
```

**Response** (200 OK):
```json
{
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
        "case_id": "case-xyz-456"
      }
    ],
    "judges": [...],
    "attorneys": [...],
    "witnesses": []
  },
  "what": {
    "causes_of_action": [...],
    "legal_issues": [...],
    "statutes": [...],
    "case_citations": [...],
    "primary_legal_theory": "Breach of Contract",
    "issue_complexity": 0.65
  },
  "where": {
    "primary_jurisdiction": "federal",
    "court": "U.S. District Court, Northern District of California",
    "venue": "San Francisco"
  },
  "when": {
    "filing_date": "2024-01-15T00:00:00Z",
    "case_age_days": 120,
    "urgency_score": 0.7
  },
  "why": {
    "legal_theories": [...],
    "supporting_precedents": [...],
    "opposing_precedents": [...],
    "argument_strength": 0.75
  },
  "context_score": 0.92,
  "is_complete": true,
  "cached": false,
  "execution_time_ms": 850,
  "timestamp": "2025-01-22T10:30:00Z"
}
```

**Performance**:
- Minimal scope: <100ms (cache hit), 50-150ms (cache miss)
- Standard scope: <100ms (cache hit), 200-600ms (cache miss)
- Comprehensive scope: <100ms (cache hit), 800-2500ms (cache miss)

#### GET /context/retrieve
Convenience GET endpoint with query parameters.

**Query Parameters**:
- `client_id` (required): Client identifier
- `case_id` (required): Case identifier
- `scope` (optional): minimal | standard | comprehensive (default: comprehensive)
- `use_cache` (optional): boolean (default: true)

#### POST /context/dimension/retrieve
Retrieve a single dimension for a case.

**Request Body**:
```json
{
  "client_id": "client-abc-123",
  "case_id": "case-xyz-456",
  "dimension": "WHO"
}
```

**Response** (200 OK):
```json
{
  "case_id": "case-xyz-456",
  "dimension": "WHO",
  "data": {
    "case_id": "case-xyz-456",
    "parties": [...],
    "judges": [...],
    "attorneys": [...]
  }
}
```

#### GET /context/dimension/quality
Get quality metrics for a specific dimension.

**Query Parameters**:
- `client_id` (required)
- `case_id` (required)
- `dimension` (required): WHO | WHAT | WHERE | WHEN | WHY

**Response** (200 OK):
```json
{
  "dimension_name": "WHO",
  "completeness_score": 0.87,
  "data_points": 12,
  "confidence_avg": 0.91,
  "is_sufficient": true
}
```

#### POST /context/refresh
Force context refresh (bypass cache).

**Query Parameters**:
- `client_id` (required)
- `case_id` (required)
- `scope` (optional): default comprehensive

#### POST /context/batch/retrieve
Retrieve context for multiple cases.

**Request Body**:
```json
{
  "client_id": "client-abc-123",
  "case_ids": ["case-1", "case-2", "case-3"],
  "scope": "standard",
  "use_cache": true
}
```

**Response** (200 OK):
```json
{
  "total_cases": 3,
  "successful": 3,
  "failed": 0,
  "contexts": {
    "case-1": {...},
    "case-2": {...},
    "case-3": {...}
  },
  "errors": {}
}
```

### Cache Management Endpoints

#### GET /cache/stats
Get comprehensive cache statistics.

**Response** (200 OK):
```json
{
  "memory_hits": 1523,
  "memory_misses": 347,
  "memory_hit_rate": 0.8145,
  "redis_hits": 0,
  "redis_misses": 0,
  "db_hits": 0,
  "db_misses": 0,
  "total_sets": 449,
  "total_deletes": 23,
  "overall_hit_rate": 0.8145,
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

#### DELETE /cache/invalidate
Invalidate cached context.

**Query Parameters**:
- `client_id` (required)
- `case_id` (required)
- `scope` (optional): specific scope or all

#### POST /cache/warmup
Pre-warm cache for multiple cases.

**Request Body**:
```json
{
  "client_id": "client-abc-123",
  "case_ids": ["case-1", "case-2", "case-3"],
  "scope": "standard"
}
```

#### GET /cache/config
Get cache configuration.

#### GET /cache/health
Check cache system health.

---

## Performance Characteristics

### Latency Targets

| Operation | Target P50 | Target P95 | Target P99 |
|-----------|-----------|-----------|-----------|
| Cache hit (any scope) | <10ms | <20ms | <50ms |
| Minimal scope (cache miss) | 75ms | 150ms | 250ms |
| Standard scope (cache miss) | 350ms | 600ms | 1000ms |
| Comprehensive scope (cache miss) | 1200ms | 2000ms | 3000ms |

### Throughput

- **Sustained**: 100 requests/second (with 80% cache hit rate)
- **Peak**: 200 requests/second (burst capacity)
- **Concurrent Connections**: 50 (configurable)

### Resource Usage

- **Memory**:
  - Base: 200MB
  - With full cache (1000 entries): 500MB
  - Peak: 800MB
- **CPU**: 1-2 cores (parallel dimension execution benefits from multi-core)
- **Disk I/O**: Minimal (database queries via Supabase client)

### Scalability

- **Horizontal**: Fully stateless (except in-memory cache which is per-instance)
- **Vertical**: Linear scaling up to 4 cores, diminishing returns beyond
- **Database**: PostgreSQL with composite indexes on (client_id, case_id)

---

## Caching Strategy

### Cache Hit Scenarios

**Scenario 1: Repeat Query (Same Scope)**
```
Request 1: comprehensive context for case-123
  → Cache MISS → Build context (1500ms) → Cache SET
Request 2: comprehensive context for case-123 (within 10 min)
  → Cache HIT (memory) → Return cached (5ms)
```

**Scenario 2: Different Scope**
```
Request 1: minimal context for case-123
  → Cache MISS → Build WHO+WHERE (100ms) → Cache SET
Request 2: comprehensive context for case-123
  → Cache MISS (different scope) → Build all 5 (1500ms) → Cache SET
```

**Scenario 3: Active vs Closed Cases**
```
Active Case (status="active"):
  → Memory: 10 min TTL
  → Redis: 1 hour TTL
  → Expect frequent updates, shorter cache lifetime

Closed Case (status="closed"):
  → Memory: 10 min TTL
  → Redis: 24 hour TTL
  → Stable data, longer cache lifetime
```

### Cache Invalidation Strategy

**Automatic Invalidation**:
- TTL expiration (memory: 10min, Redis: 1-24hr)
- LRU eviction (memory cache when > 1000 entries)

**Manual Invalidation** (via API):
- `/cache/invalidate` - Invalidate specific case/scope
- `/cache/invalidate/case` - Invalidate all scopes for case

**When to Invalidate**:
- Case data updated (new documents, entities, relationships)
- Graph structure changes (new communities, precedent links)
- Manual refresh requested by user

---

## Database Schema

### Context Schema Tables

#### cached_contexts (Placeholder - Tier 3 Cache)

```sql
CREATE TABLE context.cached_contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cache_key TEXT NOT NULL UNIQUE,
    client_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    context_data JSONB NOT NULL,
    case_status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    accessed_at TIMESTAMP DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    expires_at TIMESTAMP,

    CONSTRAINT cached_contexts_scope_check
        CHECK (scope IN ('minimal', 'standard', 'comprehensive'))
);

CREATE INDEX idx_cached_contexts_case
    ON context.cached_contexts(client_id, case_id);
CREATE INDEX idx_cached_contexts_key
    ON context.cached_contexts(cache_key);
CREATE INDEX idx_cached_contexts_expires
    ON context.cached_contexts(expires_at)
    WHERE expires_at IS NOT NULL;
```

### Graph Schema Tables (Used by Dimension Analyzers)

- **graph.nodes**: Entity nodes with `case_id` filtering
- **graph.edges**: Relationships between entities
- **graph.communities**: Leiden algorithm community assignments
- **graph.chunks**: Enhanced contextual chunks with embeddings

### Client Schema Tables (Used by Dimension Analyzers)

- **client.client_cases**: Case metadata (jurisdiction, court, dates)
- **client.client_documents**: Document metadata
- **client.client_entities**: Extracted entities (LurisEntityV2 schema)

---

## Service Dependencies

### Required Services

#### 1. GraphRAG Service (Port 8010)
- **Purpose**: Knowledge graph queries and precedent discovery
- **Health Check**: `GET http://10.10.0.87:8010/api/v1/health`
- **Critical Endpoints**:
  - `POST /api/v1/graphrag/query` - Natural language graph queries
  - `POST /api/v1/graph/create` - Build graph from entities

#### 2. Supabase Database
- **Purpose**: Persistent storage for entities, cases, graph data
- **Schemas Used**: client, graph, context
- **Connection**: Via SupabaseClient fluent API
- **Required Tables**: See Database Schema section

#### 3. vLLM Services (Indirect via GraphRAG)
- **vLLM Instruct** (Port 8080): Entity extraction, structured queries
- **vLLM Thinking** (Port 8082): Complex reasoning, precedent analysis
- **vLLM Embeddings** (Port 8081): Vector embeddings for graph

### Optional Services

#### 4. Redis (Future - Tier 2 Cache)
- **Purpose**: Distributed caching across service instances
- **Configuration**: TBD

#### 5. Prometheus (Monitoring)
- **Purpose**: Metrics collection
- **Endpoint**: `GET http://10.10.0.87:8015/metrics`

---

## Deployment Guide

### Prerequisites

- Python 3.12+
- Virtual environment with dependencies installed
- Access to GraphRAG Service (port 8010)
- Access to Supabase database
- Environment variables configured

### Environment Variables

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Service Configuration
CONTEXT_ENGINE_PORT=8015
GRAPHRAG_SERVICE_URL=http://10.10.0.87:8010

# Cache Configuration (optional)
CACHE_MEMORY_ENABLED=true
CACHE_REDIS_ENABLED=false
CACHE_DB_ENABLED=false
CACHE_MEMORY_SIZE=1000
CACHE_MEMORY_TTL=600
```

### Installation Steps

```bash
# 1. Navigate to service directory
cd /srv/luris/be/context-engine-service

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt

# 4. Verify environment
python -c "from src.api.main import app; print('✅ App initialized')"

# 5. Run service
python run.py
```

### Verification

```bash
# Health check
curl http://localhost:8015/api/v1/health

# Expected response:
{
  "status": "healthy",
  "service": "context-engine",
  "port": 8015,
  "version": "1.0.0"
}

# Test context retrieval
curl -X POST http://localhost:8015/api/v1/context/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "test-client",
    "case_id": "test-case",
    "scope": "minimal"
  }'
```

---

## Monitoring & Metrics

### Prometheus Metrics

Available at: `GET http://10.10.0.87:8015/metrics`

#### Application Metrics

```
# Request metrics
context_engine_requests_total{endpoint="/api/v1/context/retrieve",method="POST"} 1523
context_engine_request_latency_seconds{endpoint="/api/v1/context/retrieve"} 0.850

# Custom metrics (to be implemented)
context_engine_cache_hits_total{tier="memory"} 1523
context_engine_cache_misses_total{tier="memory"} 347
context_engine_dimension_execution_seconds{dimension="WHO"} 0.120
context_engine_context_quality_score 0.92
```

### Health Endpoints

#### Service Health
```bash
GET /api/v1/health
```

#### Cache Health
```bash
GET /api/v1/cache/health
```

### Logging

**Log Levels**:
- `INFO`: Normal operations, cache hits/misses, context builds
- `WARNING`: Cache failures, degraded quality scores
- `ERROR`: Dimension analyzer failures, API errors
- `DEBUG`: Detailed execution traces

**Log Format**:
```
2025-01-22 10:30:00 [INFO] Context retrieval request: case=case-123, scope=comprehensive, cache=true
2025-01-22 10:30:00 [DEBUG] Memory cache HIT: context:client-abc:case-123:comprehensive:a3f5b2c1
2025-01-22 10:30:01 [INFO] Context built: case=case-123, score=0.92, time=850ms, cached=false
```

---

## Appendix

### Error Codes

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Invalid Request | Missing required fields or invalid parameters |
| 404 | Case Not Found | Specified case_id does not exist |
| 500 | Context Build Failed | Internal error during context construction |
| 503 | Service Unavailable | GraphRAG or database service unavailable |

### Future Enhancements

1. **Redis Cache Integration** - Enable Tier 2 distributed caching
2. **Database Cache** - Implement Tier 3 persistent cache
3. **WebSocket Support** - Real-time context updates
4. **Batch Optimization** - Parallel batch processing for large case sets
5. **Advanced Quality Metrics** - ML-based quality prediction
6. **Custom Dimension Plugins** - Extensible dimension framework
7. **GraphQL API** - Alternative query interface

---

**Document Version:** 1.0.0
**Last Updated:** 2025-01-22
**Maintainer:** Luris Development Team
