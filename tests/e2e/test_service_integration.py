"""
End-to-End Integration Tests for Context Engine Service

Tests the complete pipeline with all service dependencies.
"""

import pytest
import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.clients.supabase_client import create_supabase_client


@pytest.fixture(scope="session", autouse=True)
def verify_services_healthy():
    """
    Session-scoped fixture that verifies all services are healthy before running tests.

    This fixture runs automatically before any tests execute and fails fast if
    critical services are unavailable.
    """
    print("\n🔍 Verifying service health before running E2E tests...")

    # Run health check script
    check_script = Path(__file__).parent / "check_services.py"
    result = subprocess.run(
        [sys.executable, str(check_script)],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Print health check output
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Fail fast if critical services are down
    if result.returncode != 0:
        pytest.fail(
            "❌ Service health check failed! "
            "One or more critical services are unavailable. "
            "Please start all required services before running E2E tests. "
            f"Exit code: {result.returncode}"
        )

    print("✅ All required services verified healthy\n")
    yield


@pytest.fixture
def supabase_client():
    """Fixture providing a Supabase client for tests"""
    client = create_supabase_client(service_name="e2e-tests")
    yield client


class TestServiceIntegration:
    """Test suite for service integration"""

    @pytest.mark.asyncio
    async def test_database_connectivity(self, supabase_client):
        """Test basic database connectivity"""
        # Query graph nodes
        result = await supabase_client.schema('graph').table('nodes') \
            .select('count', count='exact') \
            .limit(1) \
            .execute()

        assert result.count is not None
        assert result.count >= 0

    @pytest.mark.asyncio
    async def test_graph_data_available(self, supabase_client):
        """Test that graph data exists in database"""
        # Check nodes
        nodes = await supabase_client.schema('graph').table('nodes') \
            .select('count', count='exact') \
            .execute()

        # Check edges
        edges = await supabase_client.schema('graph').table('edges') \
            .select('count', count='exact') \
            .execute()

        # Check communities (may be empty if Leiden clustering not yet run)
        communities = await supabase_client.schema('graph').table('communities') \
            .select('count', count='exact') \
            .execute()

        assert nodes.count > 0, "Graph should have nodes"
        assert edges.count > 0, "Graph should have edges"
        # Communities may be empty - just report count

        print(f"\nGraph Data Statistics:")
        print(f"  Nodes: {nodes.count:,}")
        print(f"  Edges: {edges.count:,}")
        print(f"  Communities: {communities.count:,}")
        if communities.count == 0:
            print("  ⚠️  Note: Communities table is empty (Leiden clustering not yet run)")

    @pytest.mark.asyncio
    async def test_law_entities_available(self, supabase_client):
        """Test that law entities exist in database"""
        result = await supabase_client.schema('law').table('entities') \
            .select('count', count='exact') \
            .execute()

        assert result.count > 0, "Law schema should have entities"
        print(f"\nLaw Entities: {result.count:,}")

    @pytest.mark.asyncio
    async def test_sample_entity_retrieval(self, supabase_client):
        """Test retrieving sample entities from law schema"""
        # Get a few sample entities
        result = await supabase_client.schema('law').table('entities') \
            .select('entity_type, entity_text, confidence_score') \
            .limit(5) \
            .execute()

        assert len(result.data) > 0, "Should retrieve sample entities"

        print(f"\nSample Entities:")
        for entity in result.data:
            entity_text = entity['entity_text'][:50] if entity['entity_text'] else 'N/A'
            print(f"  {entity['entity_type']}: {entity_text}... (confidence: {entity['confidence_score']})")

    @pytest.mark.asyncio
    async def test_graph_node_retrieval(self, supabase_client):
        """Test retrieving sample graph nodes"""
        result = await supabase_client.schema('graph').table('nodes') \
            .select('node_id, node_type, title, description') \
            .limit(5) \
            .execute()

        assert len(result.data) > 0, "Should retrieve sample nodes"

        print(f"\nSample Graph Nodes:")
        for node in result.data:
            title = (node.get('title') or 'N/A')[:50]
            print(f"  {node['node_id']}: {node['node_type']} - {title}")


class TestContextEngineAPI:
    """Test Context Engine API endpoints"""

    @pytest.mark.asyncio
    async def test_context_engine_health(self):
        """Test Context Engine health endpoint"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8015/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get('status') in ['healthy', 'ok']
        print(f"\nContext Engine Health: {data}")

    @pytest.mark.asyncio
    async def test_graphrag_health(self):
        """Test GraphRAG Service health endpoint"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8010/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get('status') in ['healthy', 'ok']
        print(f"\nGraphRAG Service Health: {data}")

    @pytest.mark.asyncio
    async def test_prompt_service_health(self):
        """Test Prompt Service health endpoint"""
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8003/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get('status') in ['healthy', 'ok']
        print(f"\nPrompt Service Health: {data}")


@pytest.mark.slow
class TestCompleteContextPipeline:
    """
    Complete end-to-end pipeline tests

    These tests verify the entire context retrieval flow from query to response.
    """

    @pytest.mark.asyncio
    async def test_basic_context_retrieval(self):
        """Test basic context retrieval with simple query"""
        import httpx

        query_data = {
            "query": "federal jurisdiction",
            "scope": "minimal",
            "max_results": 10
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8015/api/v1/context/retrieve",
                json=query_data
            )

        # Context Engine may not have this endpoint yet
        # This test documents expected behavior
        if response.status_code == 404:
            pytest.skip("Context retrieval endpoint not yet implemented")

        assert response.status_code == 200
        data = response.json()
        print(f"\nContext Retrieval Response: {data}")

    @pytest.mark.asyncio
    async def test_graphrag_query(self):
        """Test GraphRAG query functionality"""
        import httpx

        query_data = {
            "query": "What are the key legal concepts in this knowledge graph?",
            "max_results": 5
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8010/api/v1/graphrag/query",
                json=query_data
            )

        # May not be implemented yet
        if response.status_code == 404:
            pytest.skip("GraphRAG query endpoint not yet implemented")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            print(f"\nGraphRAG Query Response: {data}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "--tb=short"])
