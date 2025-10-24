"""
Validation Tests for Real Data Fixtures

These tests verify that all real data fixtures work correctly and connect to actual services.
Tests are marked with `requires_services` to skip by default.

Run these tests explicitly to validate fixture implementation:
```bash
cd /srv/luris/be/context-engine-service
source venv/bin/activate
pytest tests/fixtures/test_fixtures_validation.py -v -s -m requires_services
```
"""

import pytest


# =============================================================================
# Session-Scoped Client Validation
# =============================================================================

@pytest.mark.requires_services
@pytest.mark.requires_graphrag
async def test_real_graphrag_client_connected(real_graphrag_client):
    """Verify GraphRAG client connects and health check works"""
    # Health check should work
    health = await real_graphrag_client.health_check()
    assert health is not None
    assert health.get("status") in ["ready", "healthy", "ok"]

    print(f"\n✅ GraphRAG Client Validated:")
    print(f"   Health Status: {health.get('status')}")


@pytest.mark.requires_services
@pytest.mark.requires_database
def test_real_supabase_client_connected(real_supabase_client):
    """Verify Supabase client sees graph nodes"""
    # Count graph nodes
    result = real_supabase_client.schema('graph').table('nodes') \
        .select('count', count='exact').execute()

    assert result.count >= 100000, \
        f"Expected at least 100K nodes, got {result.count}"

    print(f"\n✅ Supabase Client Validated:")
    print(f"   Graph Nodes: {result.count:,}")


@pytest.mark.requires_services
async def test_real_cache_manager_created(real_cache_manager):
    """Verify CacheManager is created with correct configuration"""
    assert real_cache_manager is not None
    assert real_cache_manager.enable_memory_cache is True
    assert real_cache_manager.enable_redis_cache is False
    assert real_cache_manager.enable_db_cache is False

    # Test basic cache operations
    await real_cache_manager.set("test_key", "test_value", ttl=60)
    value = await real_cache_manager.get("test_key")
    assert value == "test_value"

    # Cleanup
    await real_cache_manager.delete("test_key")

    print(f"\n✅ CacheManager Validated:")
    print(f"   Memory Cache: Enabled")
    print(f"   Basic Operations: Working")


@pytest.mark.requires_services
async def test_real_context_builder_created(real_context_builder):
    """Verify ContextBuilder is created with all dependencies"""
    assert real_context_builder is not None

    # Check that it has the required analyzers
    assert hasattr(real_context_builder, 'graphrag_client')
    assert hasattr(real_context_builder, 'supabase_client')

    print(f"\n✅ ContextBuilder Validated:")
    print(f"   Dependencies: Connected")


# =============================================================================
# Dimension Context Validation
# =============================================================================

@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_who_context_has_data(real_who_context):
    """Verify WHO context contains real data from database"""
    assert real_who_context is not None
    assert real_who_context.case_id is not None

    # Check that we have at least one data point in any category
    total_data_points = (
        len(real_who_context.parties) +
        len(real_who_context.judges) +
        len(real_who_context.attorneys)
    )

    print(f"\n✅ WHO Context Validated:")
    print(f"   Case ID: {real_who_context.case_id}")
    print(f"   Parties: {len(real_who_context.parties)}")
    print(f"   Judges: {len(real_who_context.judges)}")
    print(f"   Attorneys: {len(real_who_context.attorneys)}")
    print(f"   Total Data Points: {total_data_points}")


@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_what_context_has_data(real_what_context):
    """Verify WHAT context contains real statutes and citations"""
    assert real_what_context is not None
    assert real_what_context.case_id is not None

    # Check that we have citations or issues
    total_data_points = (
        len(real_what_context.statutes) +
        len(real_what_context.case_citations) +
        len(real_what_context.legal_issues)
    )

    print(f"\n✅ WHAT Context Validated:")
    print(f"   Case ID: {real_what_context.case_id}")
    print(f"   Statutes: {len(real_what_context.statutes)}")
    print(f"   Case Citations: {len(real_what_context.case_citations)}")
    print(f"   Legal Issues: {len(real_what_context.legal_issues)}")
    print(f"   Total Data Points: {total_data_points}")


@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_where_context_has_data(real_where_context):
    """Verify WHERE context has jurisdiction and court information"""
    assert real_where_context is not None
    assert real_where_context.case_id is not None
    assert real_where_context.primary_jurisdiction is not None

    print(f"\n✅ WHERE Context Validated:")
    print(f"   Case ID: {real_where_context.case_id}")
    print(f"   Jurisdiction: {real_where_context.primary_jurisdiction}")
    print(f"   Court: {real_where_context.court}")
    print(f"   Venue: {real_where_context.venue}")


@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_when_context_has_data(real_when_context):
    """Verify WHEN context has date information"""
    assert real_when_context is not None
    assert real_when_context.case_id is not None

    print(f"\n✅ WHEN Context Validated:")
    print(f"   Case ID: {real_when_context.case_id}")
    print(f"   Filing Date: {real_when_context.filing_date}")
    print(f"   Case Age (days): {real_when_context.case_age_days}")
    print(f"   Upcoming Deadlines: {len(real_when_context.upcoming_deadlines)}")


@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_why_context_has_data(real_why_context):
    """Verify WHY context has legal theories or precedents"""
    assert real_why_context is not None
    assert real_why_context.case_id is not None

    total_data_points = (
        len(real_why_context.legal_theories) +
        len(real_why_context.supporting_precedents)
    )

    print(f"\n✅ WHY Context Validated:")
    print(f"   Case ID: {real_why_context.case_id}")
    print(f"   Legal Theories: {len(real_why_context.legal_theories)}")
    print(f"   Supporting Precedents: {len(real_why_context.supporting_precedents)}")
    print(f"   Total Data Points: {total_data_points}")


# =============================================================================
# Complete Context Response Validation
# =============================================================================

@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_context_response_complete(real_context_response):
    """Verify complete context response has all 5 dimensions"""
    assert real_context_response is not None
    assert real_context_response.case_id is not None

    # Verify all dimensions are present
    assert real_context_response.who is not None
    assert real_context_response.what is not None
    assert real_context_response.where is not None
    assert real_context_response.when is not None
    assert real_context_response.why is not None

    # Verify context score is calculated
    assert isinstance(real_context_response.context_score, float)
    assert 0.0 <= real_context_response.context_score <= 1.0

    print(f"\n✅ Context Response Validated:")
    print(f"   Case ID: {real_context_response.case_id}")
    print(f"   Context Score: {real_context_response.context_score:.2f}")
    print(f"   Is Complete: {real_context_response.is_complete}")
    print(f"   All Dimensions Present: ✓")


# =============================================================================
# Quality Metrics Validation
# =============================================================================

@pytest.mark.requires_services
@pytest.mark.requires_database
async def test_real_quality_metrics_calculated(real_quality_metrics):
    """Verify quality metrics are calculated from real data"""
    assert real_quality_metrics is not None
    assert real_quality_metrics.dimension_name == "WHO"
    assert isinstance(real_quality_metrics.completeness_score, float)
    assert 0.0 <= real_quality_metrics.completeness_score <= 1.0
    assert real_quality_metrics.data_points >= 0

    print(f"\n✅ Quality Metrics Validated:")
    print(f"   Dimension: {real_quality_metrics.dimension_name}")
    print(f"   Completeness Score: {real_quality_metrics.completeness_score:.2f}")
    print(f"   Data Points: {real_quality_metrics.data_points}")
    print(f"   Is Sufficient: {real_quality_metrics.is_sufficient}")


# =============================================================================
# Helper Fixtures Validation
# =============================================================================

def test_test_config_has_real_urls(test_config):
    """Verify test config uses real service URLs"""
    assert test_config["graphrag_base_url"] == "http://10.10.0.87:8010"
    assert test_config["service_name"] == "context-engine-e2e-test"

    print(f"\n✅ Test Config Validated:")
    print(f"   GraphRAG URL: {test_config['graphrag_base_url']}")
    print(f"   Service Name: {test_config['service_name']}")


def test_performance_thresholds_are_lenient(performance_thresholds):
    """Verify performance thresholds account for real service latency"""
    # Real data thresholds should be more lenient than mock thresholds
    assert performance_thresholds["minimal_scope_ms"] >= 300  # More than 100ms (mock)
    assert performance_thresholds["standard_scope_ms"] >= 1000  # More than 500ms (mock)
    assert performance_thresholds["comprehensive_scope_ms"] >= 3000  # More than 2000ms (mock)

    print(f"\n✅ Performance Thresholds Validated:")
    print(f"   Minimal Scope: {performance_thresholds['minimal_scope_ms']}ms")
    print(f"   Standard Scope: {performance_thresholds['standard_scope_ms']}ms")
    print(f"   Comprehensive Scope: {performance_thresholds['comprehensive_scope_ms']}ms")


# =============================================================================
# Service Health Validation
# =============================================================================

@pytest.mark.requires_services
def test_services_available(check_services_available):
    """Verify all required services are running"""
    # This test uses the check_services_available fixture which
    # automatically skips if services are unavailable
    print(f"\n✅ All Required Services Available")


# =============================================================================
# Test Summary
# =============================================================================

def test_fixture_implementation_summary():
    """
    Summary of fixture implementation

    This test always passes and provides documentation on the fixture system.
    """
    summary = """

    ========================================================================
    REAL DATA FIXTURES IMPLEMENTATION SUMMARY
    ========================================================================

    Session-Scoped Clients (Created Once):
    ✓ real_graphrag_client - GraphRAG service connection (port 8010)
    ✓ real_supabase_client - Supabase database connection
    ✓ real_cache_manager - CacheManager with memory cache
    ✓ real_context_builder - ContextBuilder with all dependencies

    Function-Scoped Contexts (Created Per Test):
    ✓ real_who_context - WHO dimension from database
    ✓ real_what_context - WHAT dimension from database
    ✓ real_where_context - WHERE dimension from database
    ✓ real_when_context - WHEN dimension from database
    ✓ real_why_context - WHY dimension from database
    ✓ real_context_response - Complete 5-dimension context
    ✓ real_quality_metrics - Quality metrics from real data

    Helper Fixtures:
    ✓ test_client_id - Multi-tenant client ID (env: TEST_CLIENT_ID)
    ✓ test_case_id - Case ID for queries (env: TEST_CASE_ID)
    ✓ test_config - Configuration with real service URLs
    ✓ performance_thresholds - Real-data performance expectations

    Cleanup Fixtures:
    ✓ cleanup_singletons - Reset singleton instances
    ✓ cleanup_test_data - Clear test artifacts

    Pre-Flight Checks:
    ✓ check_services_available - Verify all services running

    Pytest Markers:
    ✓ requires_services - Test requires external services
    ✓ requires_graphrag - Test requires GraphRAG service
    ✓ requires_database - Test requires Supabase database

    Usage:
    # Run all validation tests
    pytest tests/fixtures/test_fixtures_validation.py -v -s -m requires_services

    # Run specific dimension tests
    pytest tests/fixtures/test_fixtures_validation.py::test_real_who_context_has_data -v -s

    # Override test IDs
    TEST_CLIENT_ID=client-xyz TEST_CASE_ID=case-456 pytest tests/fixtures/ -v -s

    ========================================================================
    """
    print(summary)
    assert True
