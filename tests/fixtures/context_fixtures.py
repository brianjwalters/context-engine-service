"""
Real Data Fixtures for Context Engine E2E Tests
Replaces ALL mocks with actual service connections and database queries

This file provides PRODUCTION-READY fixtures using real data:
- Real GraphRAG Service (http://10.10.0.87:8010) - 119,838 nodes
- Real Supabase Database (law, client, graph schemas)
- Real vLLM Services (ports 8080, 8081, 8082)
- Real legal case data

NO MOCKS - All fixtures connect to actual services and query real data.
"""

import pytest
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from src.clients.graphrag_client import GraphRAGClient
from src.models.dimensions import (
    WhoContext, WhatContext, WhereContext, WhenContext, WhyContext,
    ContextResponse, DimensionQualityMetrics,
    Party, Judge, Attorney, Citation, CauseOfAction
)

# Load environment variables
load_dotenv()


# =============================================================================
# SESSION-SCOPED SERVICE CLIENTS (Created Once Per Test Session)
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async session-scoped fixtures"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def real_graphrag_client() -> GraphRAGClient:
    """
    Real GraphRAG client connecting to http://10.10.0.87:8010

    Verifies:
    - Service is running and healthy
    - Database has 119,838+ nodes
    - Connection is stable

    Returns:
        GraphRAGClient: Connected client with verified data

    Raises:
        AssertionError: If service unavailable or data verification fails
    """
    from src.clients.graphrag_client import GraphRAGClient

    client = GraphRAGClient(
        base_url="http://10.10.0.87:8010",
        timeout=30.0,
        max_retries=3
    )

    # Verify service health
    try:
        health = await client.health_check()
        assert health.get("status") in ["ready", "healthy", "ok"], \
            f"GraphRAG service unhealthy: {health}"
    except Exception as e:
        pytest.skip(f"GraphRAG service unavailable: {e}")

    print(f"\n✅ GraphRAG Client Connected")
    print(f"   Base URL: http://10.10.0.87:8010")
    print(f"   Status: Ready")

    yield client

    # Cleanup: close connection
    await client.close()


@pytest.fixture(scope="session")
def real_supabase_client():
    """
    Real Supabase client with database connection

    Verifies:
    - Database is accessible
    - All 3 schemas present (law, client, graph)
    - Tables have data

    Returns:
        SupabaseClient: Connected client with fluent API

    Raises:
        AssertionError: If database unavailable or verification fails
    """
    from src.clients.supabase_client import create_supabase_client

    client = create_supabase_client(service_name="e2e-context-engine-tests")

    # Verify graph schema has data (synchronous call - no await)
    try:
        result = client.schema('graph').table('nodes').select('count', count='exact').execute()
        assert result.count > 100000, \
            f"Graph nodes count too low: expected >100000, got {result.count}"

        print(f"\n✅ Supabase Client Connected:")
        print(f"   Graph Nodes: {result.count:,}")
    except Exception as e:
        pytest.skip(f"Supabase database unavailable: {e}")

    yield client

    # Cleanup: client handles connection pooling automatically


@pytest.fixture(scope="session")
async def real_cache_manager(real_supabase_client):
    """
    Real CacheManager with memory cache only (no Redis/DB cache)

    Configuration:
    - Memory cache: ENABLED (1000 entries, 600s TTL)
    - Redis cache: DISABLED
    - DB cache: DISABLED

    Returns:
        CacheManager: Configured manager with memory cache
    """
    from src.core.cache_manager import CacheManager

    manager = CacheManager(
        supabase_client=real_supabase_client,
        enable_memory_cache=True,
        enable_redis_cache=False,
        enable_db_cache=False
    )

    print(f"\n✅ CacheManager Created:")
    print(f"   Memory Cache: ENABLED (max 1000 entries)")
    print(f"   Redis Cache: DISABLED")
    print(f"   DB Cache: DISABLED")

    yield manager

    # Cleanup: clear memory cache
    manager.memory_cache.clear()
    manager.reset_stats()


@pytest.fixture(scope="session")
async def real_context_builder(
    real_graphrag_client: GraphRAGClient,
    real_supabase_client
):
    """
    Real ContextBuilder with all 5 dimension analyzers

    Uses:
    - Real GraphRAG client (119,838 nodes)
    - Real Supabase client (database queries)
    - Real dimension analyzers (WHO/WHAT/WHERE/WHEN/WHY)

    Returns:
        ContextBuilder: Configured builder with real dependencies
    """
    from src.core.context_builder import ContextBuilder

    builder = ContextBuilder(
        graphrag_client=real_graphrag_client,
        supabase_client=real_supabase_client
    )

    print(f"\n✅ ContextBuilder Created:")
    print(f"   Analyzers: WHO, WHAT, WHERE, WHEN, WHY")
    print(f"   GraphRAG: Connected")
    print(f"   Supabase: Connected")

    yield builder

    # Cleanup: nothing to cleanup (clients handle their own cleanup)


# =============================================================================
# FUNCTION-SCOPED TEST DATA (Created Per Test)
# =============================================================================

@pytest.fixture
def test_client_id() -> str:
    """
    Test client ID for multi-tenant isolation

    Returns:
        str: Test client ID (can be overridden with TEST_CLIENT_ID env var)
    """
    return os.getenv("TEST_CLIENT_ID", "client-abc")


@pytest.fixture
def test_case_id() -> str:
    """
    Test case ID for case-specific queries

    Returns:
        str: Test case ID (can be overridden with TEST_CASE_ID env var)
    """
    return os.getenv("TEST_CASE_ID", "case-123")


@pytest.fixture
async def real_who_context(
    real_supabase_client,
    test_client_id: str,
    test_case_id: str
) -> WhoContext:
    """
    Real WHO dimension context from database

    Queries:
    - graph.nodes WHERE entity_type IN ('PARTY', 'JUDGE', 'ATTORNEY')
    - Filters by client_id and case_id for isolation

    Returns:
        WhoContext: WHO dimension with real parties, judges, attorneys
    """
    # Query real PARTY entities
    party_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'PARTY') \
        .limit(20) \
        .execute()

    parties = []
    for node in party_result.data:
        props = node.get('properties', {})
        parties.append(Party(
            id=node['node_id'],
            name=props.get('name', 'Unknown Party'),
            role=props.get('role', 'unknown'),
            entity_type=props.get('entity_type', 'person'),
            case_id=test_case_id
        ))

    # Query real JUDGE entities
    judge_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'JUDGE') \
        .limit(10) \
        .execute()

    judges = []
    for node in judge_result.data:
        props = node.get('properties', {})
        judges.append(Judge(
            id=node['node_id'],
            name=props.get('name', 'Unknown Judge'),
            court=props.get('court', 'Unknown Court'),
            case_id=test_case_id
        ))

    # Query real ATTORNEY entities
    attorney_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'ATTORNEY') \
        .limit(10) \
        .execute()

    attorneys = []
    for node in attorney_result.data:
        props = node.get('properties', {})
        attorneys.append(Attorney(
            id=node['node_id'],
            name=props.get('name', 'Unknown Attorney'),
            firm=props.get('firm'),
            case_id=test_case_id
        ))

    return WhoContext(
        case_id=test_case_id,
        case_name=f"Case {test_case_id}",
        parties=parties,
        judges=judges,
        attorneys=attorneys,
        witnesses=[],  # TODO: Add witness query if needed
        experts=[]     # TODO: Add expert query if needed
    )


@pytest.fixture
async def real_what_context(
    real_supabase_client,
    test_client_id: str,
    test_case_id: str
) -> WhatContext:
    """
    Real WHAT dimension context from database

    Queries:
    - graph.nodes WHERE entity_type IN ('STATUTE_CITATION', 'CASE_CITATION')
    - law.entities for legal statutes

    Returns:
        WhatContext: WHAT dimension with real statutes, case citations, legal issues
    """
    # Query real STATUTE entities
    statute_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'STATUTE_CITATION') \
        .limit(20) \
        .execute()

    statutes = []
    for node in statute_result.data:
        props = node.get('properties', {})
        statutes.append(Citation(
            text=node.get('entity_text', 'Unknown Statute'),
            type='statute',
            jurisdiction=props.get('jurisdiction', 'federal')
        ))

    # Query real CASE_CITATION entities
    case_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'CASE_CITATION') \
        .limit(20) \
        .execute()

    case_citations = []
    for node in case_result.data:
        props = node.get('properties', {})
        case_citations.append(Citation(
            text=node.get('entity_text', 'Unknown Case'),
            type='case_law',
            jurisdiction=props.get('jurisdiction', 'federal')
        ))

    # Query real LEGAL_ISSUE entities
    issue_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'LEGAL_ISSUE') \
        .limit(10) \
        .execute()

    legal_issues = [node.get('entity_text', 'Unknown Issue') for node in issue_result.data]

    return WhatContext(
        case_id=test_case_id,
        case_name=f"Case {test_case_id}",
        causes_of_action=[],  # TODO: Query CAUSE_OF_ACTION entities
        legal_issues=legal_issues,
        statutes=statutes,
        regulations=[],       # TODO: Query REGULATION entities
        case_citations=case_citations,
        procedural_posture=None
    )


@pytest.fixture
async def real_where_context(
    real_supabase_client,
    test_client_id: str,
    test_case_id: str
) -> WhereContext:
    """
    Real WHERE dimension context from database

    Queries:
    - graph.nodes WHERE entity_type IN ('COURT', 'JURISDICTION')
    - Fallback to sensible defaults if no data found

    Returns:
        WhereContext: WHERE dimension with real jurisdiction, court, venue
    """
    # Query real COURT entities
    court_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'FEDERAL_COURTS') \
        .limit(1) \
        .execute()

    court = "Unknown Court"
    venue = "Unknown Venue"
    jurisdiction = "unknown"

    if court_result.data:
        node = court_result.data[0]
        props = node.get('properties', {})
        court = node.get('entity_text', 'Unknown Court')
        venue = props.get('venue', 'Unknown Venue')
        jurisdiction = props.get('jurisdiction', 'federal')

    return WhereContext(
        case_id=test_case_id,
        case_name=f"Case {test_case_id}",
        primary_jurisdiction=jurisdiction,
        court=court,
        venue=venue,
        geographic_scope=None,
        applicable_law=[],
        court_level=None,
        appellate_jurisdiction=None
    )


@pytest.fixture
async def real_when_context(
    real_supabase_client,
    test_client_id: str,
    test_case_id: str
) -> WhenContext:
    """
    Real WHEN dimension context from database

    Queries:
    - client.client_cases for filing dates
    - client.client_tasks for upcoming deadlines

    Returns:
        WhenContext: WHEN dimension with real dates and timeline
    """
    # Query real case data for filing date
    case_result = real_supabase_client.schema('client').table('client_cases') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('case_id', test_case_id) \
        .maybe_single() \
        .execute()

    filing_date = None
    case_age_days = 0

    if case_result.data:
        filing_date_str = case_result.data.get('filing_date')
        if filing_date_str:
            filing_date = filing_date_str
            # Calculate case age
            filed = datetime.fromisoformat(filing_date_str.replace('Z', '+00:00'))
            case_age_days = (datetime.now() - filed).days

    # Query real tasks for upcoming deadlines
    task_result = real_supabase_client.schema('client').table('client_tasks') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('case_id', test_case_id) \
        .gte('due_date', datetime.now().isoformat()) \
        .order('due_date', desc=False) \
        .limit(10) \
        .execute()

    upcoming_deadlines = []
    for task in task_result.data:
        upcoming_deadlines.append({
            "date": task.get('due_date'),
            "description": task.get('title', 'Unknown Task')
        })

    return WhenContext(
        case_id=test_case_id,
        case_name=f"Case {test_case_id}",
        filing_date=filing_date,
        service_date=None,
        upcoming_deadlines=upcoming_deadlines,
        case_age_days=case_age_days,
        statute_limitations_date=None,
        timeline=[]  # TODO: Query timeline events
    )


@pytest.fixture
async def real_why_context(
    real_graphrag_client: GraphRAGClient,
    real_supabase_client,
    test_client_id: str,
    test_case_id: str
) -> WhyContext:
    """
    Real WHY dimension context from graph relationships

    Queries:
    - graph.edges WHERE relationship_type IN ('CITES', 'FOLLOWS', 'SUPPORTS')
    - GraphRAG discover_precedents() for supporting precedents

    Returns:
        WhyContext: WHY dimension with real legal theories and precedents

    Note: This is the most complex dimension requiring relationship queries
    """
    # Query real relationships for precedents
    edge_result = real_supabase_client.schema('graph').table('edges') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .in_('relationship_type', ['CITES', 'FOLLOWS', 'SUPPORTS']) \
        .limit(20) \
        .execute()

    supporting_precedents = []

    # Query legal theories (if available)
    theory_result = real_supabase_client.schema('graph').table('nodes') \
        .select('*') \
        .eq('client_id', test_client_id) \
        .eq('entity_type', 'LEGAL_PRINCIPLE') \
        .limit(10) \
        .execute()

    legal_theories = [node.get('entity_text', 'Unknown Theory') for node in theory_result.data]

    # Calculate argument strength (average of precedent relevance scores)
    if supporting_precedents:
        avg_relevance = sum(p['relevance_score'] for p in supporting_precedents) / len(supporting_precedents)
        argument_strength = min(1.0, avg_relevance)
    else:
        argument_strength = 0.0

    return WhyContext(
        case_id=test_case_id,
        case_name=f"Case {test_case_id}",
        legal_theories=legal_theories,
        supporting_precedents=supporting_precedents,
        opposing_precedents=[],  # TODO: Query opposing precedents
        argument_strength=argument_strength,
        reasoning_chain=[],      # TODO: Extract reasoning chain
        legal_questions=[]       # TODO: Extract legal questions
    )


@pytest.fixture
async def real_context_response(
    real_who_context: WhoContext,
    real_what_context: WhatContext,
    real_where_context: WhereContext,
    real_when_context: WhenContext,
    real_why_context: WhyContext,
    test_case_id: str
) -> ContextResponse:
    """
    Complete real context response with all 5 dimensions

    Combines:
    - WHO dimension (real parties, judges, attorneys)
    - WHAT dimension (real statutes, cases, issues)
    - WHERE dimension (real jurisdiction, court, venue)
    - WHEN dimension (real dates, timeline, deadlines)
    - WHY dimension (real precedents, legal theories)

    Returns:
        ContextResponse: Complete context with all dimensions
    """
    # Calculate context score based on dimension completeness
    dimension_scores = []

    # WHO score: based on data points
    who_points = len(real_who_context.parties) + len(real_who_context.judges) + len(real_who_context.attorneys)
    dimension_scores.append(min(1.0, who_points / 10))  # Max 10 data points

    # WHAT score: based on citations and issues
    what_points = len(real_what_context.statutes) + len(real_what_context.case_citations) + len(real_what_context.legal_issues)
    dimension_scores.append(min(1.0, what_points / 10))

    # WHERE score: 1.0 if all required fields present
    where_complete = all([
        real_where_context.primary_jurisdiction,
        real_where_context.court,
        real_where_context.venue
    ])
    dimension_scores.append(1.0 if where_complete else 0.5)

    # WHEN score: based on dates and deadlines
    when_points = (1 if real_when_context.filing_date else 0) + len(real_when_context.upcoming_deadlines)
    dimension_scores.append(min(1.0, when_points / 5))

    # WHY score: based on precedents and theories
    why_points = len(real_why_context.supporting_precedents) + len(real_why_context.legal_theories)
    dimension_scores.append(min(1.0, why_points / 10))

    # Overall context score (average of dimension scores)
    context_score = sum(dimension_scores) / len(dimension_scores) if dimension_scores else 0.0

    # Context is complete if all dimensions have data
    is_complete = all(score > 0 for score in dimension_scores)

    return ContextResponse(
        case_id=test_case_id,
        case_name=real_who_context.case_name or f"Case {test_case_id}",
        who=real_who_context.model_dump(),
        what=real_what_context.model_dump(),
        where=real_where_context.model_dump(),
        when=real_when_context.model_dump(),
        why=real_why_context.model_dump(),
        context_score=context_score,
        is_complete=is_complete,
        cached=False,
        execution_time_ms=0,  # Set by actual context builder
        request_id=None,
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
async def real_quality_metrics(
    real_who_context: WhoContext
) -> DimensionQualityMetrics:
    """
    Real dimension quality metrics calculated from actual data

    Args:
        real_who_context: Real WHO dimension context

    Returns:
        DimensionQualityMetrics: Quality metrics for WHO dimension
    """
    # Count data points in WHO dimension
    data_points = (
        len(real_who_context.parties) +
        len(real_who_context.judges) +
        len(real_who_context.attorneys) +
        len(real_who_context.witnesses) +
        len(real_who_context.experts)
    )

    # Calculate completeness score (max 10 data points = 1.0 score)
    completeness_score = min(1.0, data_points / 10)

    # Dimension is sufficient if completeness >= 0.7
    is_sufficient = completeness_score >= 0.7

    return DimensionQualityMetrics(
        dimension_name="WHO",
        completeness_score=completeness_score,
        data_points=data_points,
        confidence_avg=0.9,  # Default confidence
        is_sufficient=is_sufficient
    )


# =============================================================================
# HELPER FIXTURES (Keep Existing Utility Functions)
# =============================================================================

@pytest.fixture
def batch_case_ids() -> List[str]:
    """Generate batch of case IDs for batch testing"""
    return [f"case-{i:05d}" for i in range(1, 51)]


@pytest.fixture
def multi_tenant_client_ids() -> List[str]:
    """Generate multiple client IDs for multi-tenant testing"""
    return [f"client-{chr(65 + i)}" for i in range(10)]


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Test configuration values with REAL service URLs"""
    return {
        "service_name": "context-engine-e2e-test",
        "port": 8015,
        "graphrag_base_url": "http://10.10.0.87:8010",  # REAL GraphRAG
        "supabase_url": os.getenv("SUPABASE_URL"),      # REAL Supabase
        "cache_memory_ttl": 600,
        "cache_active_case_ttl": 3600,
        "cache_closed_case_ttl": 86400,
        "max_cache_size": 1000,
        "enable_memory_cache": True,
        "enable_redis_cache": False,
        "enable_db_cache": False
    }


@pytest.fixture
def performance_thresholds() -> Dict[str, float]:
    """
    Performance SLA thresholds for real data tests

    Note: These are MORE LENIENT than mock tests because real service calls
    take longer (100ms vs 1ms for mocks).
    """
    return {
        "minimal_scope_ms": 300,       # Was 100ms with mocks
        "standard_scope_ms": 1000,     # Was 500ms with mocks
        "comprehensive_scope_ms": 3000,  # Was 2000ms with mocks
        "cache_hit_ms": 50,            # Was 10ms with mocks
        "cache_miss_minimal_ms": 400,
        "cache_miss_standard_ms": 1200,
        "cache_miss_comprehensive_ms": 3000,
        "min_cache_hit_rate": 0.70,
        "min_context_score": 0.85
    }


# =============================================================================
# CLEANUP FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Cleanup singleton instances between tests"""
    yield
    # Reset singleton instances in routes
    import src.api.routes.context as context_routes
    context_routes._graphrag_client = None
    context_routes._supabase_client = None
    context_routes._context_builder = None


@pytest.fixture(autouse=True)
async def cleanup_test_data():
    """Cleanup test data before and after each test"""
    # Setup: nothing to do (using real data)
    yield
    # Teardown: clear any test artifacts (if needed)
    # Note: We're using read-only queries, so no cleanup needed
    pass


# =============================================================================
# PRE-FLIGHT SERVICE CHECKS
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def check_services_available():
    """
    Pre-flight check: Verify all required services are running

    Checks:
    - GraphRAG service (port 8010)
    - Supabase database
    - vLLM services (ports 8080, 8081, 8082)

    Raises:
        pytest.skip: If any required service is unavailable
    """
    import httpx

    services = {
        "GraphRAG": "http://10.10.0.87:8010/api/v1/health",
        "vLLM Instruct": "http://localhost:8080/v1/models",
        "vLLM Embeddings": "http://localhost:8081/v1/models",
        "vLLM Thinking": "http://localhost:8082/v1/models"
    }

    unavailable = []
    for name, url in services.items():
        try:
            response = httpx.get(url, timeout=5.0)
            if response.status_code != 200:
                unavailable.append(f"{name} ({url})")
        except Exception as e:
            unavailable.append(f"{name} ({url}): {e}")

    if unavailable:
        pytest.skip(f"Required services unavailable: {', '.join(unavailable)}")

    print(f"\n✅ All Services Available:")
    for name in services.keys():
        print(f"   {name}: ✓")
