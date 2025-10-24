# Context Engine Service - Project Setup Complete

**Created**: 2025-10-22
**Port**: 8015
**Status**: Foundation Complete ✅

## Project Structure Created

```
context-engine-service/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              ✅ Basic FastAPI app with metrics
│   │   └── routes/
│   │       └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── clients/
│   │   ├── __init__.py
│   │   └── supabase_client.py   ✅ 2,359 lines (copied from graphrag-service)
│   ├── models/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   └── __init__.py
│   ├── integration/
│   │   └── __init__.py
│   └── fixtures/
│       ├── __init__.py
│       └── sample_cases.json    ✅ Sample case data
├── venv/                         ✅ Virtual environment created
├── .env                          ✅ Modified from graphrag-service (PORT=8015)
├── .gitignore                    ✅ Standard Python gitignore
├── requirements.txt              ✅ All dependencies listed
├── pyproject.toml               ✅ Pytest configuration
├── run.py                        ✅ Service entry point
├── api.md                        ✅ API documentation (placeholder)
└── README.md                     ✅ Comprehensive service documentation
```

## Files Created (24 total)

### Configuration Files (5)
- ✅ `.env` - Service configuration (PORT=8015)
- ✅ `.gitignore` - Standard Python exclusions
- ✅ `requirements.txt` - Dependencies
- ✅ `pyproject.toml` - Pytest configuration
- ✅ `run.py` - Service entry point

### Documentation Files (3)
- ✅ `README.md` - Comprehensive service documentation
- ✅ `api.md` - API documentation (placeholder)
- ✅ `PROJECT_SETUP.md` - This file

### Source Code (12 __init__.py + 2 implementation files)
- ✅ `src/__init__.py`
- ✅ `src/api/__init__.py`
- ✅ `src/api/main.py` - FastAPI app with Prometheus metrics
- ✅ `src/api/routes/__init__.py`
- ✅ `src/core/__init__.py`
- ✅ `src/clients/__init__.py`
- ✅ `src/clients/supabase_client.py` - 2,359 lines (copied from graphrag)
- ✅ `src/models/__init__.py`
- ✅ `src/utils/__init__.py`

### Test Files (4 __init__.py + 1 fixture)
- ✅ `tests/__init__.py`
- ✅ `tests/unit/__init__.py`
- ✅ `tests/integration/__init__.py`
- ✅ `tests/fixtures/__init__.py`
- ✅ `tests/fixtures/sample_cases.json`

### Virtual Environment
- ✅ `venv/` - Python virtual environment created

## Environment Configuration

### Modified from graphrag-service

```bash
# Service Configuration
PORT=8015                                    # Changed from 8010
SERVICE_NAME=context-engine-service         # Changed from graphrag-service
SERVICE_URL=http://10.10.0.87:8015         # Changed from 8010

# All other settings preserved (Supabase, LLM services, etc.)
```

### Added Cache Configuration
```bash
CACHE_TTL_ACTIVE_CASE=3600      # 1 hour for active cases
CACHE_TTL_CLOSED_CASE=86400     # 24 hours for closed cases
CACHE_MAX_SIZE=1000             # Maximum cached queries
```

## SupabaseClient Integration

**Source**: `/srv/luris/be/graphrag-service/src/clients/supabase_client.py`
**Destination**: `/srv/luris/be/context-engine-service/src/clients/supabase_client.py`
**Size**: 2,359 lines (89KB)

### Features Included
- ✅ Fluent API (schema().table() pattern)
- ✅ Connection pooling and semaphore management
- ✅ Retry logic with exponential backoff
- ✅ Circuit breaker pattern
- ✅ Prometheus metrics integration
- ✅ Dual-client support (anon + service_role)
- ✅ Schema-aware timeouts
- ✅ Comprehensive error handling

## Dependencies

### Core Framework
- fastapi==0.109.0
- uvicorn[standard]==0.27.0
- pydantic==2.5.3
- pydantic-settings==2.1.0

### Database
- supabase==2.3.0
- postgrest==0.13.0

### HTTP Clients
- httpx==0.26.0
- openai==1.10.0

### Testing
- pytest==7.4.4
- pytest-asyncio==0.23.3
- pytest-cov==4.1.0

### Monitoring
- prometheus-client==0.19.0

## Quick Start

```bash
# Navigate to service directory
cd /srv/luris/be/context-engine-service

# Activate virtual environment (already created)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run service
python run.py
```

## Service Endpoints

### Basic Endpoints (Implemented)
- `GET /` - Service information
- `GET /api/v1/health` - Health check
- `GET /metrics` - Prometheus metrics

### To Be Implemented
- `POST /api/v1/context/retrieve` - Case context retrieval
- `POST /api/v1/case/create` - Create case context
- `GET /api/v1/case/{case_id}` - Get case metadata
- `POST /api/v1/research/query` - Legal research (no case_id)
- `DELETE /api/v1/cache/{case_id}` - Cache management

## Next Steps

1. **Install Dependencies**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Implement Core Components**
   - [ ] `src/core/context_engine.py` - Main orchestration
   - [ ] `src/core/case_manager.py` - Case metadata management
   - [ ] `src/core/context_builder.py` - WHO/WHAT/WHERE/WHEN/WHY builder
   - [ ] `src/core/cache_manager.py` - Case-aware query cache
   - [ ] `src/core/quality_scorer.py` - Context quality metrics

3. **Implement Client Wrappers**
   - [ ] `src/clients/graphrag_client.py` - GraphRAG wrapper
   - [ ] `src/clients/entity_client.py` - Entity extraction wrapper
   - [ ] `src/clients/vllm_client.py` - vLLM services wrapper

4. **Implement Data Models**
   - [ ] `src/models/context.py` - Context data models
   - [ ] `src/models/case.py` - Case metadata models
   - [ ] `src/models/dimensions.py` - WHO/WHAT/WHERE/WHEN/WHY models
   - [ ] `src/models/enums.py` - Enums (context modes, query types)

5. **Implement API Routes**
   - [ ] `src/api/routes/context.py` - Context endpoints
   - [ ] `src/api/routes/case.py` - Case management
   - [ ] `src/api/routes/research.py` - Legal research
   - [ ] `src/api/routes/health.py` - Detailed health checks
   - [ ] `src/api/routes/cache.py` - Cache management

6. **Testing**
   - [ ] Unit tests for core components
   - [ ] Integration tests with GraphRAG
   - [ ] Performance benchmarks
   - [ ] Cache validation tests

7. **Documentation**
   - [ ] Complete api.md with all endpoints
   - [ ] Add architecture diagrams
   - [ ] Document context retrieval patterns
   - [ ] Add usage examples

## Architecture Notes

### Case-Centric Design
- 99% of queries include `case_id` + `client_id`
- Context caching is case-aware (1hr active, 24hr closed)
- All database operations use multi-tenant isolation

### WHO/WHAT/WHERE/WHEN/WHY Framework
- **WHO**: Parties, attorneys, judges, witnesses
- **WHAT**: Legal issues, claims, defenses, facts
- **WHERE**: Jurisdictions, venues, courts
- **WHEN**: Timeline, key dates, deadlines
- **WHY**: Precedents, statutes, reasoning

### Quality Scoring (5 Dimensions)
1. Completeness (0-1): All dimensions populated
2. Freshness (0-1): Recency of data
3. Relevance (0-1): Query-specific relevance
4. Accuracy (0-1): Entity confidence scores
5. Coverage (0-1): Document coverage

**Target**: >0.85 overall quality score

## Integration Points

### Direct Dependencies
- **GraphRAG Service** (8010): Knowledge graph queries
- **Entity Extraction Service** (8007): Real-time entity recognition
- **vLLM Instruct** (8080): Fast entity extraction
- **vLLM Thinking** (8082): Complex reasoning
- **vLLM Embeddings** (8081): Vector search
- **Supabase**: Direct database access (all schemas)

### Database Schemas Used
- **law schema**: Legal reference materials
- **client schema**: Client documents, cases, entities
- **graph schema**: Knowledge graph nodes, edges, communities

## Verification Checklist

- ✅ Directory structure created (12 directories)
- ✅ All __init__.py files created (12 files)
- ✅ SupabaseClient copied (2,359 lines)
- ✅ .env configured (PORT=8015)
- ✅ requirements.txt created
- ✅ pyproject.toml configured
- ✅ run.py entry point created
- ✅ src/api/main.py basic FastAPI app
- ✅ .gitignore configured
- ✅ README.md comprehensive documentation
- ✅ api.md placeholder created
- ✅ Virtual environment created
- ✅ Sample fixtures created

## Status: Foundation Complete ✅

The context-engine-service foundation is fully set up and ready for implementation.

**Total Files Created**: 24
**Total Lines of Code**: ~2,900 (including copied SupabaseClient)
**Time to Create**: ~5 minutes

All foundation files are in place. The service can now be developed incrementally
following the architecture outlined in the README.md.
