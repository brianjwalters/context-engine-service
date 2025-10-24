# End-to-End Tests for Context Engine Service

This directory contains end-to-end (E2E) tests that verify the complete Context Engine pipeline with all service dependencies.

## Prerequisites

Before running E2E tests, ensure all required services are running:

### Required Services

1. **GraphRAG Service** (Port 8010)
   ```bash
   sudo systemctl status luris-graphrag
   ```

2. **Context Engine Service** (Port 8015)
   ```bash
   sudo systemctl status luris-context-engine
   ```

3. **Prompt Service** (Port 8003)
   ```bash
   sudo systemctl status luris-prompt
   ```

4. **Supabase Database**
   - Must be accessible via environment variables
   - Must contain graph data (nodes, edges, communities)
   - Must contain law data (entities)

### Optional Services (Enhanced Functionality)

5. **vLLM Instruct** (Port 8080)
   ```bash
   sudo systemctl status luris-vllm-instruct
   ```

6. **vLLM Thinking** (Port 8082)
   ```bash
   sudo systemctl status luris-vllm-thinking
   ```

7. **vLLM Embeddings** (Port 8081)
   ```bash
   sudo systemctl status luris-vllm-embeddings
   ```

## Service Health Check

Before running E2E tests, use the health check script to verify all services are operational:

```bash
# From context-engine-service directory
cd /srv/luris/be/context-engine-service

# Activate virtual environment
source venv/bin/activate

# Run health check
python tests/e2e/check_services.py

# Or make it executable and run directly
chmod +x tests/e2e/check_services.py
./tests/e2e/check_services.py
```

### Health Check Output

**All Services Healthy:**
```
✅ All required services are healthy!
Exit code: 0
```

**Critical Service Down:**
```
❌ One or more critical services are down!
Please start missing services before running tests:
   • GraphRAG Service: ❌ CRITICAL - Connection refused
Exit code: 1
```

**Optional Services Down:**
```
✅ All critical services are healthy!
⚠️  Some optional services are unavailable (tests may have limited functionality)
Exit code: 0
```

## Running E2E Tests

### Step 1: Verify Services

```bash
# Check all services are running
python tests/e2e/check_services.py
```

### Step 2: Run E2E Test Suite

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run with detailed output
pytest tests/e2e/ -vv

# Run specific test file
pytest tests/e2e/test_complete_pipeline.py -v

# Run with coverage
pytest tests/e2e/ --cov=src --cov-report=html
```

## Test Categories

### Basic Pipeline Tests
- Document upload and processing
- Entity extraction integration
- Graph construction integration
- Context retrieval

### Advanced Feature Tests
- Multi-dimensional context (WHO/WHAT/WHERE/WHEN/WHY)
- Precedent search
- Citation network analysis
- Legal reasoning queries

### Performance Tests
- Large document processing
- Concurrent query handling
- Response time benchmarks
- Memory usage profiling

## Service Status Table

| Service | Port | Required | Purpose |
|---------|------|----------|---------|
| GraphRAG | 8010 | ✅ Yes | Knowledge graph operations |
| Context Engine | 8015 | ✅ Yes | Context retrieval and construction |
| Prompt Service | 8003 | ✅ Yes | LLM prompt management |
| Supabase | N/A | ✅ Yes | Database operations |
| vLLM Instruct | 8080 | ⚠️  Optional | Entity extraction, fast tasks |
| vLLM Thinking | 8082 | ⚠️  Optional | Complex reasoning |
| vLLM Embeddings | 8081 | ⚠️  Optional | Vector similarity search |

## Troubleshooting

### Issue: Health Check Fails

**Symptom:**
```
❌ CRITICAL - Connection refused
```

**Solution:**
1. Check if service is running:
   ```bash
   sudo systemctl status luris-<service-name>
   ```

2. Start the service if stopped:
   ```bash
   sudo systemctl start luris-<service-name>
   ```

3. Check service logs:
   ```bash
   sudo journalctl -u luris-<service-name> -f
   ```

### Issue: Database Connection Fails

**Symptom:**
```
❌ CRITICAL - Supabase Database connection error
```

**Solution:**
1. Verify environment variables:
   ```bash
   cat .env | grep SUPABASE
   ```

2. Test database connectivity:
   ```bash
   python -c "from src.clients.supabase_client import create_supabase_client; client = create_supabase_client('test'); print('✅ Connected')"
   ```

### Issue: Graph Data Quality Warning

**Symptom:**
```
⚠️  109838 nodes missing client_id
```

**Impact:** Non-critical, but may affect multi-tenant data isolation.

**Solution:**
Run data migration to populate client_id fields (see GraphRAG Service documentation).

### Issue: vLLM Services Unavailable

**Symptom:**
```
⚠️  Optional - Connection refused
```

**Impact:** Some advanced features may be unavailable, but core tests will pass.

**Solution:**
1. Start vLLM services:
   ```bash
   sudo systemctl start luris-vllm-instruct
   sudo systemctl start luris-vllm-thinking
   sudo systemctl start luris-vllm-embeddings
   ```

2. Wait for model loading (30-45 seconds per service)

3. Verify with health check:
   ```bash
   curl http://localhost:8080/v1/models
   ```

## Exit Codes

The health check script uses standard exit codes:

| Exit Code | Meaning |
|-----------|---------|
| 0 | All required services healthy |
| 1 | One or more critical services down |
| 2 | Unexpected error during health check |
| 130 | User interrupted (Ctrl+C) |

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt

      - name: Check service health
        run: |
          source venv/bin/activate
          python tests/e2e/check_services.py

      - name: Run E2E tests
        run: |
          source venv/bin/activate
          pytest tests/e2e/ -v --cov=src
```

## Best Practices

1. **Always run health check first** before executing E2E tests
2. **Monitor service logs** during test execution for debugging
3. **Use appropriate test data** that represents production scenarios
4. **Clean up test data** after test completion
5. **Document failures** with service logs and error traces

## Reference Documentation

- **Context Engine API**: `/srv/luris/be/context-engine-service/api.md`
- **GraphRAG Service API**: `/srv/luris/be/graphrag-service/api.md`
- **Prompt Service API**: `/srv/luris/be/prompt-service/api.md`
- **Main Project Guide**: `/srv/luris/be/CLAUDE.md`

## Data Discovery Tool

### Purpose

The `discover_data.py` script analyzes the Luris graph database to generate a comprehensive test data manifest. This manifest provides:

1. **Real data statistics** - Actual counts of entities, relationships, and documents
2. **Common patterns** - Most frequently occurring entities and relationships
3. **Recommended test queries** - Suggested queries mapped to context dimensions
4. **Dimension coverage** - Entity types categorized by WHO/WHAT/WHERE/WHEN/WHY

### Usage

```bash
# Navigate to context-engine-service
cd /srv/luris/be/context-engine-service

# Activate virtual environment
source venv/bin/activate

# Run data discovery
python tests/e2e/discover_data.py
```

### Output

The script generates `data_manifest.json` with:

- **Database Summary**: Total nodes, edges, entities, documents
- **Entity Types**: All discovered types with occurrence counts
- **Relationship Types**: All relationship types with counts
- **Sample Entities**: Example entities for each type
- **Common Entities**: Top 20 most frequent entities
- **Recommended Queries**: Test query suggestions
- **Dimension Coverage**: Entities mapped to WHO/WHAT/WHERE/WHEN/WHY

### Current Statistics (as of 2025-10-23)

**Database Summary:**
- Graph Nodes: 119,838
- Graph Edges: 119,340
- Law Entities: 59,919
- Law Documents: 15,101

**Top Entity Types:**
1. person (1,912 - 12.7%)
2. case_citation (1,519 - 10.1%)
3. court (1,509 - 10.1%)
4. statute (1,298 - 8.7%)
5. organization (1,272 - 8.5%)

**Top Relationships:**
1. cites (1,032)
2. references (846)
3. related_to (626)
4. part_of (472)
5. represents (382)

**Most Common Entities:**
1. Marbury v. Madison, 5 U.S. 137 (132 occurrences)
2. Roe v. Wade, 410 U.S. 113 (119 occurrences)
3. Miranda v. Arizona, 384 U.S. 436 (116 occurrences)

### Recommended Test Queries

The manifest includes 6 recommended queries covering all dimensions:

1. **WHO Dimension**: "What organizations are mentioned in the documents?"
2. **WHAT Dimension**: "Find all regulations in the legal corpus"
3. **WHERE Dimension**: "What court rules appear in the documents?"
4. **WHY Dimension**: "What entities have 'cites' relationships?"
5. **Multi-Entity**: "Find documents containing both court and agreement entities"
6. **Common Entity**: "What is the context around 'Marbury v. Madison, 5 U.S. 137'?"

### Using the Manifest in Tests

```python
import json

# Load the manifest
with open('tests/e2e/data_manifest.json', 'r') as f:
    manifest = json.load(f)

# Get sample entity for testing
sample_court = next(
    e for e in manifest['sample_entities']
    if e['type'] == 'court'
)

# Use recommended query
query_spec = manifest['recommended_test_queries'][0]

async def test_who_dimension():
    """Test WHO dimension using real data"""
    result = await context_engine.retrieve_context(
        query=query_spec['query'],
        scope="comprehensive"
    )

    assert 'who' in result
    assert len(result['who']) > 0
```

### Re-generating the Manifest

Regenerate when:
- Significant new data is added to database
- Entity extraction patterns change
- GraphRAG processing completes on new documents

```bash
source venv/bin/activate
python tests/e2e/discover_data.py
```

## Contact

For issues or questions about E2E tests, see the main project documentation.
