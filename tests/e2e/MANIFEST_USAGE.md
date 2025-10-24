# Data Manifest Usage Guide

## Quick Start

The data manifest provides real database statistics and recommended test queries for E2E testing.

### Generate Manifest

```bash
cd /srv/luris/be/context-engine-service
source venv/bin/activate
python tests/e2e/discover_data.py
```

### Use in Tests

```python
import json

# Load manifest
with open('tests/e2e/data_manifest.json', 'r') as f:
    manifest = json.load(f)

# Get sample entity
court = next(e for e in manifest['sample_entities'] if e['type'] == 'court')

# Use in test
result = await context_engine.retrieve_context(
    query=f"Find information about {court['text']}"
)
```

## Manifest Structure

```json
{
  "generated_at": "2025-10-23T17:54:37.319267+00:00",
  "database_summary": {
    "graph_nodes": 119838,
    "graph_edges": 119340,
    "law_entities": 59919,
    "law_documents": 15101
  },
  "entity_types_discovered": {
    "person": 1912,
    "case_citation": 1519,
    "court": 1509,
    ...
  },
  "relationship_types_discovered": {
    "cites": 1032,
    "references": 846,
    ...
  },
  "sample_entities": [
    {
      "text": "Court of Appeals",
      "type": "court",
      "node_id": "b0f1861e-0e94-4b44-ac51-6a4f771c7ee9"
    },
    ...
  ],
  "common_entities": [
    {
      "text": "Marbury v. Madison, 5 U.S. 137",
      "count": 132
    },
    ...
  ],
  "recommended_test_queries": [
    {
      "query": "What organizations are mentioned in the documents?",
      "expected_entity_type": "organization",
      "dimension": "WHO",
      "estimated_results": 1272,
      "reasoning": "organization entities represent WHO dimension..."
    },
    ...
  ],
  "test_data_coverage": {
    "who_dimension": ["organization", "judge", "attorney", ...],
    "what_dimension": ["regulation", "statute", ...],
    "where_dimension": ["jurisdiction", "court", ...],
    "when_dimension": ["date", "contract_term"],
    "why_dimension": ["citation", "case_citation"]
  }
}
```

## Common Patterns

### Pattern 1: Test Each Dimension

```python
def test_who_dimension(manifest):
    """Test WHO dimension with real data"""
    who_query = next(
        q for q in manifest['recommended_test_queries']
        if q['dimension'] == 'WHO'
    )

    result = await context_engine.retrieve_context(
        query=who_query['query'],
        scope="comprehensive"
    )

    assert 'who' in result
    assert len(result['who']) >= 1
```

### Pattern 2: Test Common Entities

```python
def test_common_entity(manifest):
    """Test with most frequently occurring entity"""
    most_common = manifest['common_entities'][0]

    result = await context_engine.retrieve_context(
        query=f"What is the context around '{most_common['text']}'?"
    )

    # Should have rich context for common entity
    assert result is not None
```

### Pattern 3: Test Entity Type Coverage

```python
def test_entity_type_coverage(manifest):
    """Ensure all entity types are discoverable"""
    for entity_type in manifest['entity_types_discovered'].keys():
        # Get sample entity of this type
        sample = next(
            (e for e in manifest['sample_entities'] if e['type'] == entity_type),
            None
        )

        if sample:
            result = await context_engine.retrieve_context(
                query=f"Find {entity_type} entities"
            )

            assert result is not None
```

### Pattern 4: Test Relationships

```python
def test_relationship_discovery(manifest):
    """Test relationship-based queries"""
    for rel_type in manifest['relationship_types_discovered'].keys():
        result = await context_engine.retrieve_context(
            query=f"What entities have '{rel_type}' relationships?"
        )

        # Should find entities connected by this relationship
        assert result is not None
```

## Real Data Statistics

### Database Size (as of 2025-10-23)
- **Graph Nodes**: 119,838
- **Graph Edges**: 119,340
- **Law Entities**: 59,919
- **Law Documents**: 15,101

### Top 10 Entity Types
1. person (1,912 - 12.7%)
2. case_citation (1,519 - 10.1%)
3. court (1,509 - 10.1%)
4. statute (1,298 - 8.7%)
5. organization (1,272 - 8.5%)
6. attorney (1,024 - 6.8%)
7. judge (982 - 6.5%)
8. plaintiff (688 - 4.6%)
9. defendant (636 - 4.2%)
10. regulation (613 - 4.1%)

### Top 5 Relationships
1. cites (1,032)
2. references (846)
3. related_to (626)
4. part_of (472)
5. represents (382)

### Most Common Entities
1. **Marbury v. Madison, 5 U.S. 137** (132 occurrences)
2. **Roe v. Wade, 410 U.S. 113** (119 occurrences)
3. **Miranda v. Arizona, 384 U.S. 436** (116 occurrences)
4. **Brown v. Board of Education, 347 U.S. 483** (116 occurrences)
5. **Michael Wilson** (79 occurrences)

## Recommended Test Queries

### Query 1: WHO Dimension
```
Query: "What organizations are mentioned in the documents?"
Entity Type: organization
Expected Results: ~1,272
Use Case: Test WHO dimension entity discovery
```

### Query 2: WHAT Dimension
```
Query: "Find all regulations in the legal corpus"
Entity Type: regulation
Expected Results: ~613
Use Case: Test WHAT dimension legal authority identification
```

### Query 3: WHERE Dimension
```
Query: "What court rules appear in the documents?"
Entity Type: court_rule
Expected Results: ~123
Use Case: Test WHERE dimension jurisdictional context
```

### Query 4: WHY Dimension
```
Query: "What entities have 'cites' relationships?"
Relationship: cites
Expected Results: ~1,032
Use Case: Test WHY dimension citation network
```

### Query 5: Multi-Entity
```
Query: "Find documents containing both court and agreement entities"
Entity Types: court, agreement
Expected Results: ~138
Use Case: Test cross-dimensional context retrieval
```

### Query 6: Common Entity
```
Query: "What is the context around 'Marbury v. Madison, 5 U.S. 137'?"
Entity Text: Marbury v. Madison, 5 U.S. 137
Expected Results: ~132
Use Case: Test comprehensive context for landmark case
```

## When to Regenerate

Regenerate the manifest when:

1. **New Data Added**: After processing significant new documents
2. **Entity Schema Changes**: When entity types or relationships change
3. **GraphRAG Updates**: After GraphRAG reprocessing
4. **Monthly**: Regular regeneration to track data growth

## Troubleshooting

### No manifest file
**Error**: `FileNotFoundError: data_manifest.json not found`

**Solution**:
```bash
python tests/e2e/discover_data.py
```

### Low entity counts
**Issue**: Manifest shows very few entities (<100)

**Possible Causes**:
- Entity extraction not yet run on documents
- GraphRAG processing incomplete
- Database connection using wrong schema

**Solution**:
1. Verify entity extraction has completed
2. Check GraphRAG service status
3. Run data quality checks

### Query timeout
**Issue**: discover_data.py times out

**Solution**:
Reduce batch sizes in the script or focus on specific schemas.

## Integration with CI/CD

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests with Manifest

on: [push, pull_request]

jobs:
  test:
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

      - name: Generate data manifest
        run: |
          source venv/bin/activate
          python tests/e2e/discover_data.py

      - name: Run manifest-based tests
        run: |
          source venv/bin/activate
          pytest tests/e2e/test_with_manifest.py -v
```

## Reference

- **Discovery Script**: `tests/e2e/discover_data.py`
- **Manifest File**: `tests/e2e/data_manifest.json`
- **Example Tests**: `tests/e2e/test_with_manifest.py`
- **E2E README**: `tests/e2e/README.md`
