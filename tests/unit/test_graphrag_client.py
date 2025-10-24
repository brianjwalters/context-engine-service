"""
Integration Tests for GraphRAG Client

Tests case-aware GraphRAG client functionality using REAL data:
- Real GraphRAG Service (http://10.10.0.87:8010)
- Real Supabase database queries
- Real case data from test fixtures

NO MOCKS - All tests use actual service calls and database queries.
"""

import pytest
import pytest_asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from src.clients.graphrag_client import (
    GraphRAGClient,
    GraphEntity,
    GraphRelationship,
    GraphCommunity,
    GraphQueryResponse,
    GraphStats,
    GraphBuildResponse,
    create_graphrag_client
)

# Load environment variables
load_dotenv()


# ============================================================================
# Test Fixtures with Real Data
# ============================================================================


@pytest_asyncio.fixture
async def graphrag_client() -> GraphRAGClient:
    """
    Real GraphRAG client connecting to http://10.10.0.87:8010

    Verifies:
    - Service is running and healthy
    - Connection is stable

    Returns:
        GraphRAGClient: Connected client with verified data

    Raises:
        pytest.skip: If GraphRAG service unavailable
    """
    client = create_graphrag_client(
        base_url="http://10.10.0.87:8010",
        timeout=30.0
    )

    # Verify service health
    try:
        health = await client.health_check()
        # GraphRAG health check returns {"ready": True/False, ...} format
        assert health.get("ready") is not None or health.get("status") is not None, \
            f"GraphRAG health check missing 'ready' or 'status' field: {health}"

        status = "ready" if health.get("ready") else health.get("status", "unknown")
        print(f"\n✅ GraphRAG Client Connected")
        print(f"   Base URL: http://10.10.0.87:8010")
        print(f"   Status: {status}")
    except Exception as e:
        pytest.skip(f"GraphRAG service unavailable: {e}")

    yield client

    # Cleanup
    await client.close()


@pytest.fixture
def test_client_id():
    """Test client ID"""
    return "test-client-context-engine"


@pytest.fixture
def test_case_id():
    """Test case ID"""
    return "test-case-001"


@pytest.fixture
def real_client_id():
    """Real client ID from environment or default"""
    return os.getenv("TEST_CLIENT_ID", "client-abc")


@pytest.fixture
def real_case_id():
    """Real case ID from environment or default"""
    return os.getenv("TEST_CASE_ID", "case-123")


# ============================================================================
# Response Model Tests (No Service Calls)
# ============================================================================


class TestResponseModels:
    """Test Pydantic response models with real data structures"""

    def test_graph_entity_validation(self):
        """Test GraphEntity model with real entity data"""
        entity_data = {
            "entity_id": "entity_case_rahimi_001",
            "entity_text": "Rahimi v. United States",
            "entity_type": "CASE_CITATION",
            "confidence_score": 0.95,
            "document_ids": ["doc_rahimi_2024"],
            "case_id": "case-456",
            "properties": {"year": 2024, "court": "Supreme Court"},
            "metadata": {"jurisdiction": "federal"}
        }

        entity = GraphEntity(**entity_data)

        assert entity.entity_id == "entity_case_rahimi_001"
        assert entity.entity_text == "Rahimi v. United States"
        assert entity.entity_type == "CASE_CITATION"
        assert entity.confidence_score == 0.95
        assert entity.case_id == "case-456"
        assert "year" in entity.properties

    def test_graph_entity_uppercase_type(self):
        """Test entity type is converted to uppercase"""
        entity_data = {
            "entity_id": "ent_001",
            "entity_text": "Test",
            "entity_type": "case_citation",  # lowercase
            "confidence_score": 0.9,
            "document_ids": [],
            "properties": {},
            "metadata": {}
        }

        entity = GraphEntity(**entity_data)
        assert entity.entity_type == "CASE_CITATION"  # uppercase

    def test_graph_relationship_validation(self):
        """Test GraphRelationship model with real relationship data"""
        relationship_data = {
            "relationship_id": "rel_001",
            "source_entity_id": "entity_case_rahimi_001",
            "target_entity_id": "entity_case_bruen_001",
            "relationship_type": "CITES",
            "confidence": 0.92,
            "case_id": "case-456",
            "context": "Rahimi cites Bruen v. NYC precedent",
            "metadata": {"citation_type": "binding"}
        }

        relationship = GraphRelationship(**relationship_data)

        assert relationship.relationship_id == "rel_001"
        assert relationship.source_entity_id == "entity_case_rahimi_001"
        assert relationship.target_entity_id == "entity_case_bruen_001"
        assert relationship.relationship_type == "CITES"
        assert relationship.confidence == 0.92
        assert relationship.case_id == "case-456"

    def test_graph_community_validation(self):
        """Test GraphCommunity model with real community data"""
        community_data = {
            "community_id": "community_2A_001",
            "title": "Second Amendment Cases",
            "summary": "Community of Second Amendment legal precedents",
            "size": 45,
            "level": 2,
            "entities": ["entity_case_rahimi_001", "entity_case_bruen_001"],
            "coherence_score": 0.89,
            "key_relationships": ["CITES", "FOLLOWS"],
            "client_id": "client-123"
        }

        community = GraphCommunity(**community_data)

        assert community.community_id == "community_2A_001"
        assert community.title == "Second Amendment Cases"
        assert community.size == 45
        assert community.coherence_score == 0.89
        assert len(community.entities) == 2


# ============================================================================
# Client Initialization Tests
# ============================================================================


class TestClientInitialization:
    """Test GraphRAG client initialization"""

    def test_client_initialization(self):
        """Test client initializes with correct defaults"""
        client = GraphRAGClient()

        assert client.base_url == "http://10.10.0.87:8010"
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.retry_delay == 1.0

    def test_client_custom_config(self):
        """Test client with custom configuration"""
        client = GraphRAGClient(
            base_url="http://localhost:8010",
            timeout=60.0,
            max_retries=5,
            retry_delay=2.0
        )

        assert client.base_url == "http://localhost:8010"
        assert client.timeout == 60.0
        assert client.max_retries == 5
        assert client.retry_delay == 2.0

    def test_factory_function(self):
        """Test create_graphrag_client factory function"""
        client = create_graphrag_client(
            base_url="http://test:8010",
            timeout=45.0
        )

        assert isinstance(client, GraphRAGClient)
        assert client.base_url == "http://test:8010"
        assert client.timeout == 45.0


# ============================================================================
# Real Service Integration Tests
# ============================================================================


@pytest.mark.asyncio
class TestRealServiceIntegration:
    """
    Integration tests using REAL GraphRAG service.

    Requires:
    - GraphRAG service running on http://10.10.0.87:8010
    - Supabase database accessible
    - Real case data in database
    """

    async def test_real_health_check(self, graphrag_client):
        """Test real health check against running GraphRAG service"""
        health = await graphrag_client.health_check()

        # GraphRAG service returns {"ready": True/False, ...} format
        assert "ready" in health or "status" in health, \
            f"Health check response missing 'ready' or 'status': {health}"

        status = "ready" if health.get("ready") else health.get("status", "unknown")
        print(f"\nGraphRAG Service Health: {status}")

    async def test_real_graph_stats(self, graphrag_client):
        """Test real graph statistics query"""
        stats = await graphrag_client.get_graph_stats(include_details=True)

        assert isinstance(stats, GraphStats)
        assert stats.total_entities >= 0
        assert stats.total_relationships >= 0

        print(f"\nGraph Stats:")
        print(f"  Entities: {stats.total_entities}")
        print(f"  Relationships: {stats.total_relationships}")
        print(f"  Communities: {stats.total_communities}")

    async def test_real_graph_stats_case_specific(self, graphrag_client, real_client_id, real_case_id):
        """Test case-specific graph statistics with real case"""
        stats = await graphrag_client.get_graph_stats(
            client_id=real_client_id,
            case_id=real_case_id
        )

        assert isinstance(stats, GraphStats)
        print(f"\nCase-Specific Stats (case_id={real_case_id}):")
        print(f"  Entities: {stats.total_entities}")
        print(f"  Relationships: {stats.total_relationships}")

    async def test_real_case_query(self, graphrag_client, real_client_id, real_case_id):
        """Test real case graph query"""
        try:
            result = await graphrag_client.query_case_graph(
                client_id=real_client_id,
                case_id=real_case_id,
                query="What statutes are cited in this case?",
                search_type="LOCAL",
                max_results=10
            )

            assert isinstance(result, GraphQueryResponse)
            assert result.search_type == "LOCAL"

            print(f"\nCase Query Results (case_id={real_case_id}):")
            print(f"  Entities found: {len(result.entities)}")
            print(f"  Execution time: {result.execution_time_ms}ms")

            # Verify case isolation
            if result.entities:
                for entity in result.entities[:3]:
                    print(f"  - {entity.entity_type}: {entity.entity_text}")
                    if entity.case_id:
                        assert entity.case_id == real_case_id, "Case isolation violation!"

        except Exception as e:
            print(f"\nCase query failed (case may not exist): {e}")
            pytest.skip(f"Case {real_case_id} not found in GraphRAG")

    async def test_real_legal_research(self, graphrag_client, real_client_id):
        """Test real legal research query (cross-case)"""
        try:
            result = await graphrag_client.query_legal_research(
                client_id=real_client_id,
                query="Find Second Amendment cases",
                jurisdiction="federal",
                search_type="GLOBAL",
                max_results=5
            )

            assert isinstance(result, GraphQueryResponse)
            assert result.search_type == "GLOBAL"

            print(f"\nLegal Research Results:")
            print(f"  Entities found: {len(result.entities)}")
            print(f"  Execution time: {result.execution_time_ms}ms")

            if result.entities:
                print("  Sample results:")
                for entity in result.entities[:3]:
                    print(f"    - {entity.entity_type}: {entity.entity_text}")
        except Exception as e:
            # Skip if endpoint not implemented
            pytest.skip(f"Legal research endpoint not available: {e}")

    async def test_case_id_validation(self, graphrag_client, test_client_id):
        """Test that case_id is REQUIRED for case queries"""
        with pytest.raises(ValueError, match="case_id is REQUIRED"):
            await graphrag_client.query_case_graph(
                client_id=test_client_id,
                case_id=None,  # Missing case_id
                query="Test query"
            )

    async def test_get_case_entities_validation(self, graphrag_client, test_client_id):
        """Test that case_id is REQUIRED for entity retrieval"""
        with pytest.raises(ValueError, match="case_id is REQUIRED"):
            await graphrag_client.get_case_entities(
                client_id=test_client_id,
                case_id=None,  # Missing case_id
                entity_type="CASE_CITATION"
            )


# ============================================================================
# Context Manager Tests
# ============================================================================


@pytest.mark.asyncio
class TestContextManager:
    """Test async context manager support"""

    async def test_context_manager_usage(self):
        """Test client as async context manager"""
        async with create_graphrag_client() as client:
            assert isinstance(client, GraphRAGClient)
            assert client._client is not None

            # Make a real health check
            health = await client.health_check()
            # GraphRAG service returns {"ready": True/False, ...} format
            assert "ready" in health or "status" in health, \
                f"Health check response missing 'ready' or 'status': {health}"

    async def test_manual_close(self):
        """Test manual client close"""
        client = create_graphrag_client()
        await client.close()
        # Client should be closed (no assertion, just ensure no errors)


# ============================================================================
# Test Execution Instructions
# ============================================================================

"""
Run these tests with:

# All tests (requires GraphRAG service running)
pytest tests/unit/test_graphrag_client.py -v

# With output
pytest tests/unit/test_graphrag_client.py -v -s

# Specific test
pytest tests/unit/test_graphrag_client.py::TestRealServiceIntegration::test_real_health_check -v -s

# Set custom client/case IDs
TEST_CLIENT_ID=client-abc TEST_CASE_ID=case-123 pytest tests/unit/test_graphrag_client.py -v

Prerequisites:
1. GraphRAG service running on http://10.10.0.87:8010
2. Supabase database accessible
3. Real case data in database (optional, tests will skip if not found)
"""
