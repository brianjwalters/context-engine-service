# Context Engine E2E Test Suite - Usage Guide

## Quick Start

### 1. Check Service Health

Before running any tests, verify all required services are healthy:

```bash
cd /srv/luris/be/context-engine-service
source venv/bin/activate
python tests/e2e/check_services.py
```

**Expected Output:**
```
✅ All required services are healthy!
Exit code: 0
```

### 2. Run E2E Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run specific test class
pytest tests/e2e/test_service_integration.py::TestServiceIntegration -v

# Run with coverage
pytest tests/e2e/ -v --cov=src --cov-report=html
```

## Test Suite Structure

### `/srv/luris/be/context-engine-service/tests/e2e/`

```
e2e/
├── __init__.py                      # Package marker
├── check_services.py                # Health check script (run first!)
├── test_service_integration.py      # Integration tests
├── README.md                        # Comprehensive documentation
└── USAGE.md                         # This file (quick reference)
```

## Health Check Script

### Features

✅ **Concurrent Health Checks** - All services checked in parallel for speed
✅ **Rich Console Output** - Color-coded status table with detailed information
✅ **Database Verification** - Tests Supabase connectivity and data availability
✅ **Data Quality Checks** - Verifies multi-tenant compliance (client_id)
✅ **Optional Services** - vLLM services warn but don't fail tests
✅ **Clear Exit Codes** - 0=success, 1=critical failure, 2=error

### Services Checked

| Service | Port | Status | Required |
|---------|------|--------|----------|
| GraphRAG Service | 8010 | ✅ Healthy | Yes |
| Context Engine | 8015 | ✅ Healthy | Yes |
| Prompt Service | 8003 | ✅ Healthy | Yes |
| Supabase Database | N/A | ✅ Connected (119,838 nodes, 59,919 entities) | Yes |
| Graph Data Quality | N/A | ⚠️  109838 nodes missing client_id | Info only |
| vLLM Instruct | 8080 | ✅ Healthy (qwen3-vl-instruct-384k) | Optional |
| vLLM Thinking | 8082 | ✅ Healthy (qwen3-vl-thinking-256k) | Optional |
| vLLM Embeddings | 8081 | ✅ Healthy (jina-embeddings-v4) | Optional |

### Exit Codes

```bash
# Check exit code after running
python tests/e2e/check_services.py
echo $?

# Exit codes:
# 0 = All critical services healthy
# 1 = One or more critical services down
# 2 = Unexpected error
# 130 = User interrupted (Ctrl+C)
```

## Test Classes

### TestServiceIntegration (5 tests)

Basic integration tests for service connectivity and data availability.

**Status: ✅ All Passing**

```bash
# Run only integration tests
pytest tests/e2e/test_service_integration.py::TestServiceIntegration -v
```

**Tests:**
1. `test_database_connectivity` - Basic database connection test
2. `test_graph_data_available` - Verifies graph nodes/edges exist
3. `test_law_entities_available` - Verifies law entities exist
4. `test_sample_entity_retrieval` - Retrieves sample legal entities
5. `test_graph_node_retrieval` - Retrieves sample graph nodes

### TestContextEngineAPI (3 tests)

API health endpoint verification.

**Status: ✅ All Passing**

```bash
# Run only API tests
pytest tests/e2e/test_service_integration.py::TestContextEngineAPI -v
```

**Tests:**
1. `test_context_engine_health` - Context Engine health check
2. `test_graphrag_health` - GraphRAG Service health check
3. `test_prompt_service_health` - Prompt Service health check

### TestCompleteContextPipeline (2 tests)

End-to-end pipeline tests for complete workflows.

**Status: ⚠️  1 Failing, 1 Skipped**

```bash
# Run pipeline tests
pytest tests/e2e/test_service_integration.py::TestCompleteContextPipeline -v
```

**Tests:**
1. `test_basic_context_retrieval` - ❌ Fails (endpoint returns 422)
2. `test_graphrag_query` - ⏭️  Skipped (endpoint not implemented)

**Note:** These tests document expected behavior for future API implementations.

## Test Results Summary

**Latest Run:**
```
============= 8 passed, 1 skipped, 1 failed in 6.45s ==============
```

**Breakdown:**
- ✅ **8 passed** - Core integration and health checks working
- ⏭️  **1 skipped** - GraphRAG query endpoint not yet implemented
- ❌ **1 failed** - Context retrieval endpoint needs implementation

## Common Workflows

### Before Starting Work

```bash
# 1. Check all services
python tests/e2e/check_services.py

# 2. Start any missing services
sudo systemctl start luris-graphrag
sudo systemctl start luris-context-engine
sudo systemctl start luris-prompt

# 3. Verify health again
python tests/e2e/check_services.py
```

### During Development

```bash
# Run tests after code changes
pytest tests/e2e/ -v --tb=short

# Run specific test during debugging
pytest tests/e2e/test_service_integration.py::TestServiceIntegration::test_database_connectivity -v
```

### Pre-Commit

```bash
# Full test suite with coverage
pytest tests/e2e/ -v --cov=src --cov-report=term-missing

# Verify no critical services down
python tests/e2e/check_services.py || exit 1
```

## Troubleshooting

### Health Check Shows Services Down

```bash
# Check service status
sudo systemctl status luris-graphrag
sudo systemctl status luris-context-engine
sudo systemctl status luris-prompt

# View service logs
sudo journalctl -u luris-graphrag -f
sudo journalctl -u luris-context-engine -f

# Restart service if needed
sudo systemctl restart luris-context-engine
```

### Database Connection Errors

```bash
# Test Supabase connectivity directly
python -c "
from src.clients.supabase_client import create_supabase_client
client = create_supabase_client('test')
print('✅ Connected')
"

# Check environment variables
cat .env | grep SUPABASE
```

### Import Errors

```bash
# Ensure venv is activated
which python  # Should show: .../venv/bin/python
source venv/bin/activate

# Verify project root in path
python -c "import sys; print(sys.path)"
```

### Test Failures

```bash
# Run with full traceback
pytest tests/e2e/ -vv --tb=long

# Run with debug output
pytest tests/e2e/ -vv -s

# Check for schema mismatches
python -c "
import asyncio
from src.clients.supabase_client import create_supabase_client

async def check():
    client = create_supabase_client('test')
    result = await client.schema('law').table('entities').select('*').limit(1).execute()
    print(f'Columns: {list(result.data[0].keys())}')

asyncio.run(check())
"
```

## Advanced Usage

### Running Health Check in Scripts

```bash
#!/bin/bash
set -e

# Run health check and capture exit code
if python tests/e2e/check_services.py; then
    echo "✅ All services healthy - running tests..."
    pytest tests/e2e/ -v
else
    echo "❌ Service health check failed - aborting"
    exit 1
fi
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Check service health
  run: |
    cd /srv/luris/be/context-engine-service
    source venv/bin/activate
    python tests/e2e/check_services.py

- name: Run E2E tests
  run: |
    source venv/bin/activate
    pytest tests/e2e/ -v --cov=src --cov-report=xml
```

### Custom Service Checks

```python
# Add custom checks to check_services.py
from check_services import ServiceHealthChecker

async def custom_check():
    checker = ServiceHealthChecker()

    # Add custom service check
    checker.check_http_service(
        "My Custom Service",
        "http://localhost:9999/health",
        required=True
    )

    return await checker.run_checks()
```

## Performance Notes

- **Health check execution time:** ~2-3 seconds (concurrent checks)
- **Full E2E test suite:** ~6-7 seconds
- **Database query tests:** ~100-200ms each
- **API health checks:** ~50-100ms each

## Test Data Requirements

### Minimum Data for Tests to Pass

- **Graph Schema:**
  - `graph.nodes`: At least 1 node required
  - `graph.edges`: At least 1 edge required
  - `graph.communities`: May be empty (Leiden clustering optional)

- **Law Schema:**
  - `law.entities`: At least 1 entity required

### Data Quality Warnings

The health check script reports data quality issues but doesn't fail:

- Missing `client_id` in graph.nodes (multi-tenant compliance)
- Empty communities table (Leiden clustering not run)
- Low entity counts (may indicate incomplete data load)

## Additional Resources

- **Full Documentation:** `/srv/luris/be/context-engine-service/tests/e2e/README.md`
- **Context Engine API:** `/srv/luris/be/context-engine-service/api.md`
- **GraphRAG API:** `/srv/luris/be/graphrag-service/api.md`
- **Database Schemas:**
  - Law: `/srv/luris/be/docs/database/law-schema.md`
  - Graph: `/srv/luris/be/docs/database/graph-schema.md`
  - Client: `/srv/luris/be/docs/database/client-schema.md`

## Contact

For issues or questions about E2E tests, consult the main project documentation at `/srv/luris/be/CLAUDE.md`.
