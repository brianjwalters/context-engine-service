# Context Engine Service

**Port**: 8015

Case-centric context retrieval service providing WHO/WHAT/WHERE/WHEN/WHY dimensions for legal document drafting.

## Overview

The Context Engine Service is the central intelligence layer for the Luris document processing pipeline. It provides multi-dimensional context retrieval optimized for case-based legal work.

### Key Features

- **Case-Centric Architecture**: 99% of queries are case-specific (case_id + client_id)
- **Multi-Dimensional Framework**: WHO/WHAT/WHERE/WHEN/WHY context dimensions
- **Query Caching**: Case-aware caching with TTL (1hr active, 24hr closed)
- **Quality Scoring**: 5-dimension scoring system (>0.85 = complete context)
- **GraphRAG Integration**: Direct knowledge graph queries for entity relationships
- **Vector Search**: Semantic search across legal documents and precedents

## Architecture

### Context Dimensions

1. **WHO** - Parties, attorneys, judges, witnesses
2. **WHAT** - Legal issues, causes of action, claims, defenses
3. **WHERE** - Jurisdictions, venues, courts
4. **WHEN** - Timeline of events, filing dates, deadlines
5. **WHY** - Legal reasoning, precedents, statutory authority

### Case Context Model

```python
{
    "case_id": str,           # Primary case identifier
    "client_id": str,         # Multi-tenant isolation
    "who": {
        "parties": List[Entity],
        "attorneys": List[Entity],
        "judges": List[Entity],
        "witnesses": List[Entity]
    },
    "what": {
        "legal_issues": List[Entity],
        "claims": List[Entity],
        "defenses": List[Entity],
        "facts": List[Entity]
    },
    "where": {
        "jurisdiction": str,
        "venue": str,
        "court": str
    },
    "when": {
        "timeline": List[Event],
        "key_dates": List[Date],
        "deadlines": List[Deadline]
    },
    "why": {
        "precedents": List[Citation],
        "statutes": List[Citation],
        "reasoning": str
    }
}
```

## Quick Start

### Installation

```bash
# Navigate to service directory
cd /srv/luris/be/context-engine-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy `.env` file and configure service settings:

```bash
PORT=8015
SERVICE_NAME=context-engine-service
SERVICE_URL=http://10.10.0.87:8015
```

### Running the Service

```bash
# Activate virtual environment
source venv/bin/activate

# Run service
python run.py
```

Service will start on `http://0.0.0.0:8015`

## API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8015/docs
- **ReDoc**: http://localhost:8015/redoc

### Key Endpoints

#### Context Retrieval

```bash
# Get comprehensive case context
POST /api/v1/context/retrieve
{
    "case_id": "case-123",
    "client_id": "client-abc",
    "scope": "comprehensive"  # minimal | standard | comprehensive
}

# Get specific dimension
GET /api/v1/context/dimension/{dimension}?case_id=case-123&client_id=client-abc
```

#### Case Management

```bash
# Create case context
POST /api/v1/case/create
{
    "case_id": "case-123",
    "client_id": "client-abc",
    "metadata": {...}
}

# Update case context
PUT /api/v1/case/{case_id}
{
    "client_id": "client-abc",
    "updates": {...}
}
```

#### Research (No Case Required)

```bash
# Legal research without case context
POST /api/v1/research/query
{
    "query": "federal question jurisdiction",
    "jurisdiction": "federal",
    "include_precedents": true
}
```

## Integration

### Dependencies

The Context Engine integrates with multiple services:

- **GraphRAG Service** (8010): Knowledge graph queries and entity relationships
- **Entity Extraction Service** (8007): Real-time entity recognition
- **vLLM Instruct Service** (8080): Fast entity extraction and classification
- **vLLM Thinking Service** (8082): Complex legal reasoning
- **vLLM Embeddings Service** (8081): Vector search and similarity
- **Supabase**: Direct database access (law/client/graph schemas)

### Example Integration

```python
from openai import OpenAI
import httpx

# Initialize Context Engine client
context_client = httpx.AsyncClient(base_url="http://10.10.0.87:8015")

# Retrieve case context
response = await context_client.post(
    "/api/v1/context/retrieve",
    json={
        "case_id": "case-123",
        "client_id": "client-abc",
        "scope": "comprehensive"
    }
)

context = response.json()
print(f"Context quality score: {context['quality_score']}")
```

## Database Schema

The Context Engine uses all three Supabase schemas:

- **law schema**: Legal reference materials, precedents
- **client schema**: Client documents, cases, entities
- **graph schema**: Knowledge graph nodes, edges, communities

### Key Tables

- `client.client_cases`: Case metadata
- `client.entities`: Extracted entities with case_id
- `graph.nodes`: Knowledge graph entities
- `graph.edges`: Entity relationships
- `law.documents`: Legal reference documents

## Caching Strategy

### Case-Aware Caching

- **Active Cases**: 1-hour TTL (frequently updated)
- **Closed Cases**: 24-hour TTL (rarely updated)
- **Cache Key**: `{case_id}:{client_id}:{dimension}:{query_hash}`
- **Max Size**: 1,000 cached queries

### Cache Invalidation

```bash
# Clear specific case cache
DELETE /api/v1/cache/{case_id}?client_id=client-abc

# Clear all cache
DELETE /api/v1/cache/all
```

## Quality Scoring

Context quality is scored across 5 dimensions:

1. **Completeness** (0-1): All dimensions populated
2. **Freshness** (0-1): Recency of data
3. **Relevance** (0-1): Query-specific relevance
4. **Accuracy** (0-1): Entity confidence scores
5. **Coverage** (0-1): Document coverage

**Overall Quality Score**: Weighted average of dimension scores

- **>0.85**: Complete context (green)
- **0.70-0.85**: Good context (yellow)
- **<0.70**: Incomplete context (red)

## Testing

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Performance

### Expected Performance

- **Context Retrieval**: <200ms (cached), <2s (uncached)
- **Dimension Query**: <100ms (cached), <500ms (uncached)
- **Quality Scoring**: <50ms
- **Cache Hit Rate**: >80% for active cases

### Monitoring

- **Prometheus Metrics**: http://localhost:8015/metrics
- **Health Check**: http://localhost:8015/api/v1/health

## Development

### Project Structure

```
context-engine-service/
├── src/
│   ├── api/              # FastAPI routes
│   ├── core/             # Business logic
│   ├── clients/          # Service clients
│   ├── models/           # Pydantic models
│   └── utils/            # Utilities
├── tests/                # Test files
├── requirements.txt      # Dependencies
├── run.py               # Entry point
└── README.md            # This file
```

### Adding New Dimensions

To add a new context dimension:

1. Update `src/models/dimensions.py` with new dimension model
2. Implement dimension builder in `src/core/dimension_analyzer.py`
3. Add dimension endpoint in `src/api/routes/context.py`
4. Update quality scorer in `src/core/quality_scorer.py`
5. Add tests in `tests/unit/test_dimensions.py`

## Troubleshooting

### Common Issues

**Issue**: Import errors when running service

**Solution**: Ensure virtual environment is activated:
```bash
source venv/bin/activate
which python  # Should show venv path
```

**Issue**: Database connection errors

**Solution**: Verify Supabase configuration in `.env`:
```bash
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_KEY
```

**Issue**: GraphRAG integration failing

**Solution**: Check GraphRAG service is running:
```bash
curl http://10.10.0.87:8010/api/v1/health
```

## License

Copyright © 2025 Luris. All rights reserved.
