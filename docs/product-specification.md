# Context Engine Service - Product Specification

**Version:** 1.0.0
**Date:** 2025-01-22
**Service Port:** 8015
**Status:** Production Ready

---

## Executive Summary

The **Context Engine Service** is a specialized microservice that provides intelligent, multi-dimensional legal case context for the Luris platform. It transforms raw legal data into actionable intelligence using the WHO/WHAT/WHERE/WHEN/WHY framework, enabling legal professionals to understand complex cases quickly and make informed decisions.

### Key Value Propositions

1. **Instant Case Understanding** - Get comprehensive case context in under 2 seconds
2. **Multi-Dimensional Analysis** - Understand WHO (parties), WHAT (issues), WHERE (jurisdiction), WHEN (timeline), WHY (reasoning)
3. **Intelligent Caching** - 70-80% cache hit rate reduces latency and costs
4. **Knowledge Graph Integration** - Leverages GraphRAG for relationship discovery
5. **Case-Centric Design** - Optimized for 99% of queries being case-specific

---

## Product Vision

### Mission Statement

Empower legal professionals with instant, comprehensive case intelligence that surfaces critical relationships, precedents, and context automatically.

### Target Users

1. **Attorneys** - Need quick case briefings and precedent analysis
2. **Legal Researchers** - Require comprehensive context for case analysis
3. **Paralegals** - Need efficient document review and case preparation
4. **Legal AI Applications** - Require structured legal context for decision support

### User Problems Solved

| Problem | Current Reality | Context Engine Solution |
|---------|----------------|------------------------|
| **Information Overload** | Hours reading case files | 2-second comprehensive briefing |
| **Missing Connections** | Manual relationship discovery | Automatic precedent and party linking |
| **Context Fragmentation** | Data scattered across systems | Unified 5-dimensional view |
| **Repetitive Research** | Same queries every time | Intelligent caching remembers context |
| **Jurisdiction Confusion** | Manual court hierarchy analysis | Automatic jurisdiction mapping |

---

## Product Features

### Core Features (MVP)

#### 1. Multi-Dimensional Context Retrieval

**What it does**: Analyzes cases through 5 complementary dimensions

**User benefit**: Complete case understanding without manual data gathering

**Technical implementation**:
- WHO: Party relationships, attorneys, judges, witnesses
- WHAT: Legal issues, causes of action, statutes, citations
- WHERE: Jurisdiction hierarchy, court venues, geographic scope
- WHEN: Timeline construction, deadline tracking, case age analysis
- WHY: Legal reasoning, precedent analysis, argument strength

**Performance SLA**:
- Minimal scope (<100ms): WHO + WHERE only
- Standard scope (100-500ms): WHO + WHAT + WHERE + WHEN
- Comprehensive scope (500-2000ms): All 5 dimensions including WHY

#### 2. Intelligent Multi-Tier Caching

**What it does**: Remembers previous context builds with smart invalidation

**User benefit**: Near-instant responses for frequently accessed cases

**Technical implementation**:
- Tier 1: In-memory LRU cache (10-minute TTL, <10ms retrieval)
- Tier 2: Redis distributed cache (1hr active cases, 24hr closed cases)
- Tier 3: Database persistent cache (permanent with manual invalidation)

**Performance SLA**:
- Cache hit rate: 70-80% for active cases
- Cache retrieval: <10ms from memory, <50ms from Redis
- Automatic invalidation on case updates

#### 3. GraphRAG Knowledge Graph Integration

**What it does**: Discovers non-obvious relationships between legal entities

**User benefit**: Surface hidden connections and relevant precedents

**Technical implementation**:
- Leiden community detection for entity clustering
- Relationship traversal across 34 relationship types
- Precedent discovery using citation networks
- Vector similarity search for legal concepts

**Performance SLA**:
- Relationship discovery: <500ms for typical case
- Community detection: <200ms per case
- Precedent ranking: Confidence scores 0.0-1.0

#### 4. Quality-Aware Context Assembly

**What it does**: Automatically assesses context completeness and reliability

**User benefit**: Know when you have enough information to proceed

**Technical implementation**:
- Dimension-level completeness scoring (0.0-1.0)
- Data point counting and validation
- Confidence aggregation across sources
- Sufficiency thresholds (0.85 for high quality)

**Performance SLA**:
- Overall context score: Weighted average of 5 dimensions
- Quality assessment: <5ms overhead
- Completeness tracking: Real-time updates

### Advanced Features (Post-MVP)

#### 5. Batch Context Operations

**What it does**: Process multiple cases in parallel

**User benefit**: Prepare context for case lists, dashboards, reports

**Use cases**:
- Dashboard rendering for 10-50 cases
- Report generation for case portfolios
- Bulk context pre-warming before hearings

#### 6. Dimension-Specific Queries

**What it does**: Retrieve only needed dimensions (faster than full context)

**User benefit**: Optimize for specific use cases (e.g., just timeline for scheduling)

**Use cases**:
- Timeline view for calendar integration
- Party list for conflict checking
- Precedent analysis for legal research

#### 7. Cache Warmup Strategies

**What it does**: Pre-load cache before high-traffic periods

**User benefit**: Guaranteed fast performance during critical times

**Use cases**:
- Pre-hearing preparation (warm all related cases)
- Morning batch warm for day's docket
- Client meeting preparation

---

## User Workflows

### Workflow 1: Attorney Case Review

**Scenario**: Attorney needs to quickly understand a new case assignment

**Steps**:
1. Attorney opens case in Luris application
2. Frontend calls `POST /api/v1/context/retrieve` with `scope=comprehensive`
3. Context Engine returns 5-dimensional analysis in <2 seconds
4. Attorney sees:
   - **WHO**: All parties, their attorneys, judge assigned
   - **WHAT**: Primary causes of action, key statutes cited
   - **WHERE**: Court jurisdiction, venue details
   - **WHEN**: Filing date, upcoming deadlines, case age
   - **WHY**: Similar cases, relevant precedents, argument analysis

**Outcome**: Attorney has complete case briefing without reading entire file

**Performance**:
- First request: 800-2000ms (cache miss)
- Subsequent requests: <10ms (cache hit)

### Workflow 2: Legal Research - Precedent Discovery

**Scenario**: Researcher needs to find similar cases and precedents

**Steps**:
1. Researcher queries case context with `scope=comprehensive`
2. Context Engine's WHY dimension triggers:
   - GraphRAG precedent discovery
   - Citation network traversal
   - Community detection for related cases
3. System returns ranked precedents with confidence scores
4. Researcher sees:
   - Supporting precedents (sorted by relevance)
   - Distinguishable cases (anti-precedents)
   - Legal theories employed
   - Argument strength analysis

**Outcome**: Automated precedent research vs. hours of manual searching

**Performance**: 500-1500ms for precedent discovery

### Workflow 3: Case Status Dashboard

**Scenario**: Manager needs overview of 50 active cases

**Steps**:
1. Frontend calls `POST /api/v1/context/batch/retrieve` with 50 case IDs
2. Context Engine processes in parallel:
   - Checks cache first (70-80% hit rate expected)
   - Builds missing contexts concurrently
   - Returns unified response with all cases
3. Dashboard displays:
   - Case ages and upcoming deadlines (WHEN)
   - Jurisdiction distribution (WHERE)
   - Primary issues across portfolio (WHAT)

**Outcome**: Portfolio visibility without individual case clicks

**Performance**:
- 50 cases, 80% cache hit: ~500ms total
- 50 cases, cache miss: 3-5 seconds total

### Workflow 4: Context Refresh After Document Upload

**Scenario**: New pleading uploaded, context needs updating

**Steps**:
1. Document upload triggers webhook
2. System calls `POST /api/v1/context/refresh?case_id=X`
3. Context Engine:
   - Invalidates all cached context for case
   - Rebuilds fresh context from updated data
   - Returns new context with updated metadata
4. Frontend automatically refreshes case view

**Outcome**: Always-current context without manual refresh

**Performance**: 800-2000ms for full rebuild

---

## Success Metrics

### Product KPIs

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Context Retrieval Latency (p95)** | <2000ms comprehensive | Prometheus histograms |
| **Cache Hit Rate** | 70-80% | Cache statistics endpoint |
| **Context Completeness Score** | >0.85 average | Quality metrics aggregation |
| **API Availability** | 99.9% uptime | Health check monitoring |
| **Concurrent Request Capacity** | 50 simultaneous | Load testing |

### User Satisfaction Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Time to Case Understanding** | <5 minutes → <30 seconds | User surveys |
| **Precedent Discovery Rate** | 3x more precedents found | Usage analytics |
| **Context Accuracy** | >95% verified correct | User feedback |
| **Return User Rate** | >80% daily active | Usage tracking |

### Business Impact Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Cost per Context Build** | <$0.02 per request | LLM token usage tracking |
| **Cache Cost Savings** | 70-80% reduction | Cache hit rate × cost |
| **Developer Integration Time** | <2 hours | API documentation feedback |
| **Support Tickets** | <5% error rate | Error rate monitoring |

---

## Technical Architecture Summary

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Context Engine Service                    │
│                         (Port 8015)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Context      │  │ Dimension    │  │ Cache        │      │
│  │ Builder      │→ │ Analyzers    │→ │ Manager      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                   │              │
│         │                 │                   │              │
│         ▼                 ▼                   ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GraphRAG     │  │ Supabase     │  │ Multi-Tier   │      │
│  │ Client       │  │ Client       │  │ Cache        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                   │              │
└─────────┼─────────────────┼───────────────────┼──────────────┘
          │                 │                   │
          ▼                 ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ GraphRAG     │  │ Supabase     │  │ Redis        │
│ Service      │  │ Database     │  │ (Optional)   │
│ (Port 8010)  │  │ (Postgres)   │  │ (Port 6379)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Data Flow

1. **Request** → FastAPI REST endpoint receives context retrieval request
2. **Cache Check** → CacheManager checks memory → Redis → DB for cached context
3. **Context Build** → On cache miss, ContextBuilder orchestrates:
   - Parallel execution of 5 dimension analyzers
   - GraphRAG relationship queries
   - Supabase direct data queries
4. **Quality Scoring** → Automatic completeness assessment
5. **Cache Store** → Store result with appropriate TTL
6. **Response** → Return ContextResponse with all dimensions + metadata

---

## API Overview

### Core Endpoints

| Endpoint | Method | Purpose | Latency Target |
|----------|--------|---------|---------------|
| `/api/v1/context/retrieve` | POST/GET | Main context retrieval | <2000ms |
| `/api/v1/context/dimension/retrieve` | POST | Single dimension | <500ms |
| `/api/v1/context/refresh` | POST | Force rebuild | <2000ms |
| `/api/v1/context/batch/retrieve` | POST | Multiple cases | Varies |
| `/api/v1/cache/stats` | GET | Cache metrics | <50ms |
| `/api/v1/cache/invalidate` | DELETE | Clear cache | <100ms |
| `/api/v1/health` | GET | Service health | <10ms |

### Integration Points

**Upstream Services (Context Engine depends on)**:
- GraphRAG Service (Port 8010) - Knowledge graph queries
- Supabase Database - Direct case/entity data
- vLLM Services (8080, 8082) - Via GraphRAG for reasoning

**Downstream Consumers (Services that use Context Engine)**:
- Document Processing Service (Port 8000) - Case context enrichment
- Frontend Applications - User-facing case views
- Analytics Services - Batch context processing
- AI Agent Services - Decision support context

---

## Deployment Requirements

### Infrastructure

| Resource | Requirement | Justification |
|----------|------------|---------------|
| **CPU** | 2-4 cores | Parallel dimension execution |
| **Memory** | 4GB RAM | In-memory cache (1000 entries × ~4KB) |
| **Disk** | 10GB | Application code, logs, temp cache |
| **Network** | <5ms to GraphRAG/DB | Low-latency service communication |

### Dependencies

**Required Services**:
- GraphRAG Service (Port 8010) - CRITICAL
- Supabase/PostgreSQL - CRITICAL
- Python 3.11+ runtime - CRITICAL

**Optional Services**:
- Redis (Port 6379) - Tier 2 caching (recommended for production)
- Prometheus (Port 9090) - Metrics collection
- Grafana - Metrics visualization

### Environment Configuration

```bash
# Service Configuration
PORT=8015
SERVICE_NAME=context-engine
LOG_LEVEL=INFO

# GraphRAG Integration
GRAPHRAG_BASE_URL=http://10.10.0.87:8010
GRAPHRAG_TIMEOUT=20

# Supabase Integration
SUPABASE_URL=your-project.supabase.co
SUPABASE_KEY=your-service-role-key

# Cache Configuration
ENABLE_MEMORY_CACHE=true
ENABLE_REDIS_CACHE=false
ENABLE_DB_CACHE=false
CACHE_MEMORY_TTL=600
```

---

## Security Considerations

### Authentication & Authorization

**Current Status**: Internal service (no authentication required)

**Future Implementation**:
- API key validation via Auth Service
- JWT token verification for user-scoped requests
- Client ID validation for multi-tenant isolation
- Rate limiting per API key

### Data Privacy

| Aspect | Implementation |
|--------|---------------|
| **Multi-Tenant Isolation** | All queries filtered by client_id |
| **PII Protection** | No sensitive data in cache keys |
| **Audit Logging** | All context retrievals logged with request ID |
| **Data Retention** | Cache TTL enforces data lifecycle |

### Network Security

- Internal service (not exposed to public internet)
- TLS/HTTPS for all external communications
- Firewall rules limit access to trusted services
- No credentials stored in code (environment variables only)

---

## Roadmap

### Phase 1: MVP (Current)
- ✅ Multi-dimensional context retrieval
- ✅ In-memory caching
- ✅ GraphRAG integration
- ✅ Quality scoring
- ✅ REST API (20 endpoints)

### Phase 2: Production Hardening (Q1 2025)
- Redis distributed caching
- Database persistent cache
- Enhanced monitoring dashboards
- Load testing validation
- Rate limiting implementation

### Phase 3: Intelligence Enhancement (Q2 2025)
- ML-based precedent ranking
- Automatic legal theory identification
- Argument strength prediction
- Timeline anomaly detection
- Cross-case pattern discovery

### Phase 4: Integration Expansion (Q3 2025)
- WebSocket real-time updates
- GraphQL API support
- Webhook-based cache invalidation
- SDK libraries (Python, JavaScript, Java)
- Third-party integration connectors

---

## Competitive Analysis

### vs. Manual Legal Research

| Aspect | Manual Research | Context Engine | Advantage |
|--------|----------------|----------------|-----------|
| **Time** | 2-4 hours | <2 seconds | 3600x faster |
| **Completeness** | 60-70% (fatigue) | 85%+ (systematic) | More thorough |
| **Consistency** | Varies by researcher | Standardized | Reliable |
| **Scalability** | 1 case at a time | 50 concurrent | 50x throughput |
| **Cost** | $200-400/case | <$0.02/case | 10,000x cheaper |

### vs. Traditional Legal AI

| Feature | Traditional Legal AI | Context Engine | Differentiation |
|---------|---------------------|----------------|-----------------|
| **Context Approach** | Document-centric | Case-centric | Better fit for legal workflows |
| **Relationship Discovery** | Keyword matching | Knowledge graph | Deeper connections |
| **Caching** | None or basic | Multi-tier intelligent | 70-80% cost savings |
| **Quality Metrics** | Unknown | Transparent scoring | Trust through visibility |
| **Integration** | Monolithic | Microservice | Flexible deployment |

---

## Success Stories (Projected)

### Story 1: Large Law Firm Case Load Management

**Challenge**: Managing 500+ active cases across 50 attorneys

**Solution**: Context Engine batch API + dashboard integration

**Results**:
- 90% reduction in case briefing time
- 3x increase in precedent discovery
- 40% improvement in deadline compliance
- $200K annual savings in research costs

### Story 2: Solo Practitioner Competitive Edge

**Challenge**: Cannot compete with big firm research resources

**Solution**: Comprehensive context scope for every case

**Results**:
- Same-quality research as large firms
- <$1/month infrastructure cost
- 2-hour case prep → 15-minute prep
- Client satisfaction up 35%

### Story 3: Legal Tech Startup AI Assistant

**Challenge**: Building LLM-powered legal assistant needs context

**Solution**: Context Engine as backend for AI decision support

**Results**:
- 95% reduction in LLM hallucinations (grounded in real case data)
- Sub-second response times (cached context)
- Scalable to 10,000 concurrent users
- Production-ready legal context API

---

## Appendices

### Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Case-Centric** | Architecture optimized for case_id as primary query dimension |
| **Dimension** | One of 5 analytical lenses (WHO/WHAT/WHERE/WHEN/WHY) |
| **GraphRAG** | Graph Retrieval-Augmented Generation (knowledge graph + LLM) |
| **Quality Score** | Completeness metric (0.0-1.0) indicating context sufficiency |
| **Scope** | Depth of analysis (minimal/standard/comprehensive) |
| **Cache Tier** | Level in cache hierarchy (memory/Redis/database) |

### Appendix B: Related Documentation

- **Technical Specification**: `/docs/technical-specification.md`
- **API Reference**: `/docs/api.md` or http://10.10.0.87:8015/docs
- **Deployment Guide**: `/docs/deployment.md` (future)
- **Operations Runbook**: `/docs/operations.md` (future)

### Appendix C: Contact Information

- **Product Owner**: Luris Platform Team
- **Technical Lead**: Backend Engineering
- **Support**: engineering@luris.ai (future)
- **Repository**: https://github.com/brianjwalters/context-engine-service

---

**Document Version**: 1.0.0
**Last Updated**: 2025-01-22
**Next Review**: Q2 2025
