#!/usr/bin/env python3
"""
Example E2E Test Using Data Manifest

This demonstrates how to use the data_manifest.json file
to create realistic E2E tests based on actual database content.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def manifest():
    """Load the data manifest"""
    manifest_path = Path(__file__).parent / 'data_manifest.json'

    if not manifest_path.exists():
        pytest.skip("data_manifest.json not found. Run discover_data.py first.")

    with open(manifest_path, 'r') as f:
        return json.load(f)


class TestManifestUsage:
    """Example tests using the manifest"""

    def test_manifest_structure(self, manifest):
        """Verify manifest has expected structure"""
        assert 'database_summary' in manifest
        assert 'entity_types_discovered' in manifest
        assert 'relationship_types_discovered' in manifest
        assert 'recommended_test_queries' in manifest
        assert 'test_data_coverage' in manifest

    def test_database_summary(self, manifest):
        """Verify database has sufficient data for testing"""
        summary = manifest['database_summary']

        # Verify we have meaningful amounts of data
        assert summary['graph_nodes'] > 1000, "Need at least 1000 graph nodes for testing"
        assert summary['graph_edges'] > 1000, "Need at least 1000 graph edges for testing"
        assert summary['law_entities'] > 1000, "Need at least 1000 law entities for testing"
        assert summary['law_documents'] > 100, "Need at least 100 law documents for testing"

    def test_dimension_coverage(self, manifest):
        """Verify all dimensions have entity types"""
        coverage = manifest['test_data_coverage']

        # All dimensions should have at least one entity type
        assert len(coverage['who_dimension']) > 0, "WHO dimension needs entities"
        assert len(coverage['what_dimension']) > 0, "WHAT dimension needs entities"
        assert len(coverage['where_dimension']) > 0, "WHERE dimension needs entities"
        assert len(coverage['when_dimension']) > 0, "WHEN dimension needs entities"
        assert len(coverage['why_dimension']) > 0, "WHY dimension needs entities"

    def test_recommended_queries_structure(self, manifest):
        """Verify recommended queries have required fields"""
        queries = manifest['recommended_test_queries']

        assert len(queries) > 0, "Should have at least one recommended query"

        for query in queries:
            assert 'query' in query, "Query must have 'query' field"
            assert 'dimension' in query, "Query must specify dimension"
            assert 'estimated_results' in query, "Query must have estimated results"
            assert 'reasoning' in query, "Query must explain reasoning"

    def test_sample_entities_available(self, manifest):
        """Verify we have sample entities for each discovered type"""
        entity_types = set(manifest['entity_types_discovered'].keys())
        sample_types = set(e['type'] for e in manifest['sample_entities'])

        # Should have at least some sample entities
        assert len(sample_types) > 0, "Should have sample entities"

        # Verify sample types are from discovered types
        for sample_type in sample_types:
            assert sample_type in entity_types, \
                f"Sample entity type '{sample_type}' not in discovered types"

    def test_common_entities(self, manifest):
        """Verify common entities are suitable for testing"""
        common = manifest.get('common_entities', [])

        if common:
            # Most common entity should appear multiple times
            most_common = common[0]
            assert most_common['count'] > 10, \
                "Most common entity should appear at least 10 times for testing"

            # Verify structure
            assert 'text' in most_common
            assert 'count' in most_common


class TestManifestGuidedQueries:
    """Example tests guided by manifest recommendations"""

    def test_who_dimension_query(self, manifest):
        """Test WHO dimension using recommended query"""
        # Find WHO dimension query
        who_queries = [
            q for q in manifest['recommended_test_queries']
            if q['dimension'] == 'WHO'
        ]

        if who_queries:
            query_spec = who_queries[0]

            # This is where you would call Context Engine
            # For now, just verify the query spec is usable
            assert query_spec['query'] is not None
            assert query_spec['estimated_results'] > 0

            # Example (commented out - needs Context Engine running):
            # result = await context_engine.retrieve_context(
            #     query=query_spec['query'],
            #     scope="comprehensive"
            # )
            # assert 'who' in result

    def test_what_dimension_query(self, manifest):
        """Test WHAT dimension using recommended query"""
        what_queries = [
            q for q in manifest['recommended_test_queries']
            if q['dimension'] == 'WHAT'
        ]

        if what_queries:
            query_spec = what_queries[0]

            assert query_spec['query'] is not None
            assert query_spec['estimated_results'] > 0

    def test_multi_entity_query(self, manifest):
        """Test multi-entity query from recommendations"""
        multi_queries = [
            q for q in manifest['recommended_test_queries']
            if q['dimension'] == 'COMPREHENSIVE'
        ]

        if multi_queries:
            query_spec = multi_queries[0]

            assert query_spec['query'] is not None

            # If query has multiple entity types, verify they exist
            if 'expected_entity_types' in query_spec:
                for entity_type in query_spec['expected_entity_types']:
                    assert entity_type in manifest['entity_types_discovered'], \
                        f"Entity type '{entity_type}' should exist in database"


class TestManifestEntityRetrieval:
    """Example tests using specific entities from manifest"""

    def test_retrieve_sample_court(self, manifest):
        """Test retrieval using sample court entity"""
        # Find a court entity
        court_entities = [
            e for e in manifest['sample_entities']
            if e['type'] == 'court'
        ]

        if court_entities:
            court = court_entities[0]

            # Verify we have usable data
            assert court['text'] is not None
            assert court['node_id'] is not None

            # Example (commented out - needs Context Engine):
            # result = await context_engine.retrieve_context(
            #     query=f"Find information about {court['text']}",
            #     scope="standard"
            # )
            # assert result is not None

    def test_retrieve_common_case(self, manifest):
        """Test retrieval using most common case citation"""
        common = manifest.get('common_entities', [])

        if common:
            # Find most common case citation
            case_citations = [
                e for e in common
                if 'v.' in e['text']  # Simple heuristic for case citations
            ]

            if case_citations:
                case = case_citations[0]

                # Verify it appears enough times to be meaningful
                assert case['count'] > 10

                # Example test (commented out):
                # result = await context_engine.retrieve_context(
                #     query=f"What is the context around '{case['text']}'?",
                #     scope="comprehensive"
                # )
                # assert 'why' in result  # Should include citations/precedent


@pytest.mark.integration
class TestManifestIntegration:
    """Integration tests using manifest data (requires running services)"""

    @pytest.mark.skip(reason="Requires Context Engine service running")
    async def test_all_recommended_queries(self, manifest):
        """Run all recommended queries from manifest"""
        queries = manifest['recommended_test_queries']

        for query_spec in queries:
            # Example integration test
            # result = await context_engine.retrieve_context(
            #     query=query_spec['query'],
            #     scope="comprehensive"
            # )
            #
            # dimension = query_spec['dimension'].lower()
            # if dimension in ['who', 'what', 'where', 'when', 'why']:
            #     assert dimension in result
            #     assert len(result[dimension]) > 0
            pass


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
