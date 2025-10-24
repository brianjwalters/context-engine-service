# GraphRAG Client Quick Reference

## Import & Initialization

```python
from src.clients.graphrag_client import create_graphrag_client

# Standard usage with context manager
async with create_graphrag_client() as client:
    result = await client.query_case_graph(...)

# Manual initialization
from src.clients.graphrag_client import GraphRAGClient
client = GraphRAGClient(
    base_url="http://10.10.0.87:8010",
    timeout=30.0,
    max_retries=3
)
```

## Case-Specific Operations (require case_id)

### Query Case Graph
```python
result = await client.query_case_graph(
    client_id="client-123",
    case_id="case-456",  # REQUIRED
    query="What are the key legal issues?",
    search_type="LOCAL"  # LOCAL | GLOBAL | HYBRID
)
```

### Get Case Entities
```python
entities = await client.get_case_entities(
    client_id="client-123",
    case_id="case-456",  # REQUIRED
    entity_type="CASE_CITATION",
    min_confidence=0.9,
    limit=100
)
```

### Get Case Relationships
```python
relationships = await client.get_case_relationships(
    case_id="case-456",  # REQUIRED
    relationship_type="CITES",
    min_confidence=0.8
)
```

### Get Case Communities
```python
communities = await client.get_case_communities(
    client_id="client-123",
    case_id="case-456",  # REQUIRED
    min_size=3
)
```

### Create Case Graph
```python
result = await client.create_case_graph(
    document_id="doc-123",
    case_id="case-456",  # REQUIRED
    client_id="client-789",
    markdown_content="Document text...",
    entities=[...],  # LurisEntityV2 format
    enable_community_detection=True
)
```

## Legal Research Operations (no case_id)

### Query Legal Research
```python
results = await client.query_legal_research(
    client_id="client-123",
    query="Find Second Amendment cases",
    jurisdiction="federal",
    search_type="GLOBAL"  # GLOBAL | HYBRID
)
```

### Find Similar Cases
```python
similar = await client.find_similar_cases(
    client_id="client-123",
    reference_case_id="case-rahimi",
    similarity_threshold=0.85,
    max_results=10
)
```

### Search Precedents
```python
precedents = await client.search_precedents(
    client_id="client-123",
    legal_issue="Second Amendment",
    jurisdiction="federal",
    court_level="supreme"
)
```

## Utility Operations

### Get Graph Statistics
```python
# Overall stats
stats = await client.get_graph_stats()

# Case-specific stats
stats = await client.get_graph_stats(
    case_id="case-456",
    client_id="client-123"
)
```

### Health Check
```python
health = await client.health_check()
if health["status"] == "ready":
    print("Service operational")
```

### Get Visualization Data
```python
viz_data = await client.get_visualization_data(
    client_id="client-123",
    case_id="case-456",
    max_nodes=50
)
```

## Response Models

### GraphEntity
```python
entity.entity_id          # str
entity.entity_text        # str
entity.entity_type        # str (uppercase)
entity.confidence_score   # float (0.0-1.0)
entity.document_ids       # List[str]
entity.case_id            # Optional[str]
entity.properties         # Dict[str, Any]
entity.metadata           # Dict[str, Any]
```

### GraphRelationship
```python
relationship.relationship_id     # str
relationship.source_entity_id    # str
relationship.target_entity_id    # str
relationship.relationship_type   # str
relationship.confidence          # float (0.0-1.0)
relationship.case_id             # Optional[str]
relationship.context             # Optional[str]
```

### GraphCommunity
```python
community.community_id      # str
community.title             # str
community.summary           # str
community.size              # int
community.entities          # List[str]
community.coherence_score   # float (0.0-1.0)
```

### GraphQueryResponse
```python
response.query              # str
response.search_type        # str
response.mode               # str
response.response           # str (AI-generated)
response.entities           # List[GraphEntity]
response.relationships      # List[GraphRelationship]
response.communities        # Optional[List[GraphCommunity]]
response.execution_time_ms  # int
```

## Error Handling

```python
import httpx

try:
    result = await client.query_case_graph(...)
except ValueError as e:
    # Missing required parameter
    print(f"Validation error: {e}")
except httpx.TimeoutException:
    # Timeout after retries
    print("Service timeout")
except httpx.HTTPStatusError as e:
    # HTTP error (4xx/5xx)
    print(f"HTTP {e.response.status_code}: {e.response.text}")
```

## Search Types

- **LOCAL**: Case-specific, entity neighborhoods (fast, focused)
- **GLOBAL**: Cross-case, community summaries (comprehensive)
- **HYBRID**: Combined local + global (balanced)

## Processing Modes

- **LAZY_GRAPHRAG**: Cost-optimized (default), 99.9% cost reduction
- **FULL_GRAPHRAG**: AI-generated summaries, maximum quality
- **HYBRID_MODE**: Intelligent mode selection

## Configuration

```python
client = GraphRAGClient(
    base_url="http://10.10.0.87:8010",  # Service URL
    timeout=30.0,                        # Request timeout (seconds)
    max_retries=3,                       # Retry attempts
    retry_delay=1.0                      # Initial delay (exponential backoff)
)
```

## Common Patterns

### Case Context Retrieval
```python
async def get_case_context(case_id: str, query: str):
    async with create_graphrag_client() as client:
        result = await client.query_case_graph(
            client_id="client-123",
            case_id=case_id,
            query=query,
            search_type="LOCAL"
        )
        return result.response, result.entities
```

### Precedent Research
```python
async def find_precedents(legal_issue: str):
    async with create_graphrag_client() as client:
        precedents = await client.search_precedents(
            client_id="client-123",
            legal_issue=legal_issue,
            jurisdiction="federal"
        )
        return [p.entity_text for p in precedents]
```

### Graph Construction
```python
async def build_case_graph(doc_id: str, case_id: str, entities: List):
    async with create_graphrag_client() as client:
        result = await client.create_case_graph(
            document_id=doc_id,
            case_id=case_id,
            client_id="client-123",
            markdown_content="...",
            entities=entities
        )
        return result.graph_id
```

## Testing

```bash
# Run all tests
cd /srv/luris/be/context-engine-service
source venv/bin/activate
pytest tests/unit/test_graphrag_client.py -v

# Run with coverage
pytest tests/unit/test_graphrag_client.py --cov=src/clients/graphrag_client
```

## Files

- **Implementation**: `src/clients/graphrag_client.py`
- **Tests**: `tests/unit/test_graphrag_client.py`
- **Full Documentation**: `src/clients/GRAPHRAG_CLIENT_README.md`
- **Examples**: `examples/graphrag_client_example.py`

## Service Info

- **Port**: 8010
- **Base URL**: http://10.10.0.87:8010
- **Health Check**: GET /api/v1/health/ready
- **Interactive Docs**: http://10.10.0.87:8010/docs
