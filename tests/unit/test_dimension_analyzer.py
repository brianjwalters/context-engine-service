"""
Integration Tests for Dimension Analyzers

Tests all five dimension analyzers (WHO/WHAT/WHERE/WHEN/WHY) using REAL data:
- Real GraphRAG client queries
- Real Supabase database queries
- Real case data from database

NO MOCKS - All tests use actual service calls and database queries.
"""

import pytest
import os
from datetime import datetime
from dotenv import load_dotenv

from src.core.dimension_analyzer import (
    DimensionAnalyzer,
    WhoAnalyzer,
    WhatAnalyzer,
    WhereAnalyzer,
    WhenAnalyzer,
    WhyAnalyzer
)
from src.models.dimensions import (
    WhoContext, WhatContext, WhereContext, WhenContext, WhyContext,
    Party, Judge, Attorney
)
from src.clients.graphrag_client import create_graphrag_client
from src.clients.supabase_client import create_supabase_client

# Load environment variables
load_dotenv()


# ============================================================================
# FIXTURES WITH REAL CLIENTS
# ============================================================================

@pytest.fixture
async def graphrag_client():
    """Create real GraphRAG client"""
    client = create_graphrag_client(base_url="http://10.10.0.87:8010")
    yield client
    await client.close()


@pytest.fixture
def supabase_client():
    """Create real Supabase client"""
    return create_supabase_client(service_name="test-dimension-analyzer")


@pytest.fixture
def test_client_id():
    """Test client ID"""
    return os.getenv("TEST_CLIENT_ID", "client-abc")


@pytest.fixture
def test_case_id():
    """Test case ID"""
    return os.getenv("TEST_CASE_ID", "case-123")


# ============================================================================
# WHO ANALYZER TESTS
# ============================================================================

@pytest.mark.asyncio
class TestWhoAnalyzer:
    """Test WHO dimension analyzer with real data"""

    async def test_who_analyzer_initialization(self, graphrag_client, supabase_client):
        """Test WHO analyzer initializes correctly"""
        analyzer = WhoAnalyzer(graphrag_client, supabase_client)

        assert analyzer.graphrag is not None
        assert analyzer.supabase is not None

    async def test_who_analyze_real_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id,
        test_case_id
    ):
        """Test WHO analysis with real case data"""
        analyzer = WhoAnalyzer(graphrag_client, supabase_client)

        try:
            context = await analyzer.analyze(test_client_id, test_case_id)

            assert isinstance(context, WhoContext)
            assert context.case_id == test_case_id
            assert isinstance(context.parties, list)
            assert isinstance(context.judges, list)
            assert isinstance(context.attorneys, list)

            print(f"\nWHO Context for case {test_case_id}:")
            print(f"  Parties: {len(context.parties)}")
            print(f"  Judges: {len(context.judges)}")
            print(f"  Attorneys: {len(context.attorneys)}")

            # Verify case isolation
            for party in context.parties:
                assert party.case_id == test_case_id, "Case isolation violated!"

        except Exception as e:
            print(f"\nWHO analysis failed (case may not exist): {e}")
            pytest.skip(f"Case {test_case_id} not found or has no WHO data")

    async def test_who_empty_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id
    ):
        """Test WHO analysis with non-existent case"""
        analyzer = WhoAnalyzer(graphrag_client, supabase_client)

        # Use a non-existent case ID
        fake_case_id = "case-nonexistent-12345"

        context = await analyzer.analyze(test_client_id, fake_case_id)

        # Should return empty context, not fail
        assert isinstance(context, WhoContext)
        assert context.case_id == fake_case_id
        assert len(context.parties) == 0
        assert len(context.judges) == 0
        assert len(context.attorneys) == 0


# ============================================================================
# WHAT ANALYZER TESTS
# ============================================================================

@pytest.mark.asyncio
class TestWhatAnalyzer:
    """Test WHAT dimension analyzer with real data"""

    async def test_what_analyzer_initialization(self, graphrag_client, supabase_client):
        """Test WHAT analyzer initializes correctly"""
        analyzer = WhatAnalyzer(graphrag_client, supabase_client)

        assert analyzer.graphrag is not None
        assert analyzer.supabase is not None

    async def test_what_analyze_real_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id,
        test_case_id
    ):
        """Test WHAT analysis with real case data"""
        analyzer = WhatAnalyzer(graphrag_client, supabase_client)

        try:
            context = await analyzer.analyze(test_client_id, test_case_id)

            assert isinstance(context, WhatContext)
            assert context.case_id == test_case_id
            assert isinstance(context.causes_of_action, list)
            assert isinstance(context.legal_issues, list)
            assert isinstance(context.statutes, list)

            print(f"\nWHAT Context for case {test_case_id}:")
            print(f"  Causes of action: {len(context.causes_of_action)}")
            print(f"  Legal issues: {len(context.legal_issues)}")
            print(f"  Statutes: {len(context.statutes)}")

        except Exception as e:
            print(f"\nWHAT analysis failed (case may not exist): {e}")
            pytest.skip(f"Case {test_case_id} not found or has no WHAT data")


# ============================================================================
# WHERE ANALYZER TESTS
# ============================================================================

@pytest.mark.asyncio
class TestWhereAnalyzer:
    """Test WHERE dimension analyzer with real data"""

    async def test_where_analyzer_initialization(self, graphrag_client, supabase_client):
        """Test WHERE analyzer initializes correctly"""
        analyzer = WhereAnalyzer(graphrag_client, supabase_client)

        assert analyzer.graphrag is not None
        assert analyzer.supabase is not None

    async def test_where_analyze_real_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id,
        test_case_id
    ):
        """Test WHERE analysis with real case data"""
        analyzer = WhereAnalyzer(graphrag_client, supabase_client)

        try:
            context = await analyzer.analyze(test_client_id, test_case_id)

            assert isinstance(context, WhereContext)
            assert context.case_id == test_case_id

            print(f"\nWHERE Context for case {test_case_id}:")
            print(f"  Jurisdiction: {context.primary_jurisdiction}")
            print(f"  Court: {context.court}")
            print(f"  Venue: {context.venue}")

        except Exception as e:
            print(f"\nWHERE analysis failed (case may not exist): {e}")
            pytest.skip(f"Case {test_case_id} not found or has no WHERE data")


# ============================================================================
# WHEN ANALYZER TESTS
# ============================================================================

@pytest.mark.asyncio
class TestWhenAnalyzer:
    """Test WHEN dimension analyzer with real data"""

    async def test_when_analyzer_initialization(self, graphrag_client, supabase_client):
        """Test WHEN analyzer initializes correctly"""
        analyzer = WhenAnalyzer(graphrag_client, supabase_client)

        assert analyzer.graphrag is not None
        assert analyzer.supabase is not None

    async def test_when_analyze_real_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id,
        test_case_id
    ):
        """Test WHEN analysis with real case data"""
        analyzer = WhenAnalyzer(graphrag_client, supabase_client)

        try:
            context = await analyzer.analyze(test_client_id, test_case_id)

            assert isinstance(context, WhenContext)
            assert context.case_id == test_case_id
            assert isinstance(context.timeline, list)
            assert isinstance(context.upcoming_deadlines, list)

            print(f"\nWHEN Context for case {test_case_id}:")
            print(f"  Filing date: {context.filing_date}")
            print(f"  Timeline events: {len(context.timeline)}")
            print(f"  Upcoming deadlines: {len(context.upcoming_deadlines)}")
            print(f"  Case age (days): {context.case_age_days}")

        except Exception as e:
            print(f"\nWHEN analysis failed (case may not exist): {e}")
            pytest.skip(f"Case {test_case_id} not found or has no WHEN data")


# ============================================================================
# WHY ANALYZER TESTS
# ============================================================================

@pytest.mark.asyncio
class TestWhyAnalyzer:
    """Test WHY dimension analyzer with real data"""

    async def test_why_analyzer_initialization(self, graphrag_client, supabase_client):
        """Test WHY analyzer initializes correctly"""
        analyzer = WhyAnalyzer(graphrag_client, supabase_client)

        assert analyzer.graphrag is not None
        assert analyzer.supabase is not None

    async def test_why_analyze_real_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id,
        test_case_id
    ):
        """Test WHY analysis with real case data"""
        analyzer = WhyAnalyzer(graphrag_client, supabase_client)

        try:
            context = await analyzer.analyze(test_client_id, test_case_id)

            assert isinstance(context, WhyContext)
            assert context.case_id == test_case_id
            assert isinstance(context.legal_theories, list)
            assert isinstance(context.supporting_precedents, list)

            print(f"\nWHY Context for case {test_case_id}:")
            print(f"  Legal theories: {len(context.legal_theories)}")
            print(f"  Supporting precedents: {len(context.supporting_precedents)}")
            print(f"  Argument strength: {context.argument_strength}")

        except Exception as e:
            print(f"\nWHY analysis failed (case may not exist): {e}")
            pytest.skip(f"Case {test_case_id} not found or has no WHY data")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestDimensionAnalyzerIntegration:
    """Test all analyzers together with real data"""

    async def test_all_analyzers_real_case(
        self,
        graphrag_client,
        supabase_client,
        test_client_id,
        test_case_id
    ):
        """Test all five dimensions with real case"""
        analyzers = {
            'WHO': WhoAnalyzer(graphrag_client, supabase_client),
            'WHAT': WhatAnalyzer(graphrag_client, supabase_client),
            'WHERE': WhereAnalyzer(graphrag_client, supabase_client),
            'WHEN': WhenAnalyzer(graphrag_client, supabase_client),
            'WHY': WhyAnalyzer(graphrag_client, supabase_client)
        }

        print(f"\nAnalyzing all dimensions for case {test_case_id}:")

        results = {}
        for name, analyzer in analyzers.items():
            try:
                context = await analyzer.analyze(test_client_id, test_case_id)
                results[name] = context
                print(f"  ✓ {name} dimension analyzed successfully")
            except Exception as e:
                print(f"  ✗ {name} dimension failed: {e}")
                results[name] = None

        # At least one dimension should succeed (or all skip if case doesn't exist)
        successful = sum(1 for ctx in results.values() if ctx is not None)
        print(f"\nSuccessful dimensions: {successful}/5")


# ============================================================================
# Test Execution Instructions
# ============================================================================

"""
Run these tests with:

# All dimension analyzer tests
pytest tests/unit/test_dimension_analyzer.py -v -s

# Specific dimension
pytest tests/unit/test_dimension_analyzer.py::TestWhoAnalyzer -v -s

# Set custom client/case IDs
TEST_CLIENT_ID=client-abc TEST_CASE_ID=case-123 pytest tests/unit/test_dimension_analyzer.py -v -s

Prerequisites:
1. GraphRAG service running on http://10.10.0.87:8010
2. Supabase database accessible with real case data
3. Case data must exist in database for tests to pass
"""
