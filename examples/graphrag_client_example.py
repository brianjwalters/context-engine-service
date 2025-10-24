"""
GraphRAG Client Usage Examples

Demonstrates comprehensive usage of the GraphRAGClient for:
- Case-specific queries (LOCAL_SEARCH)
- Legal research queries (GLOBAL_SEARCH)
- Entity/relationship retrieval
- Graph construction
- Health monitoring

Run: python examples/graphrag_client_example.py
"""

import asyncio
import logging
from typing import List

from src.clients.graphrag_client import (
    create_graphrag_client,
    GraphEntity,
    GraphRelationship,
    GraphCommunity,
    GraphQueryResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_health_check():
    """Example: Check GraphRAG service health"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 1: Health Check")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        health = await client.health_check()

        logger.info(f"Service Status: {health.get('status', 'unknown')}")
        logger.info(f"Ready: {health.get('ready', False)}")

        if 'checks' in health:
            logger.info("Dependency Checks:")
            for service, status in health['checks'].items():
                logger.info(f"  - {service}: {status}")


async def example_case_query():
    """Example: Query case-specific graph (LOCAL_SEARCH)"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 2: Case-Specific Query (LOCAL_SEARCH)")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Query specific case
        result = await client.query_case_graph(
            client_id="client-123",
            case_id="case-456",
            query="What statutes are cited in this case?",
            search_type="LOCAL",
            mode="LAZY_GRAPHRAG",
            max_results=50
        )

        logger.info(f"Query: {result.query}")
        logger.info(f"Search Type: {result.search_type}")
        logger.info(f"Mode: {result.mode}")
        logger.info(f"Execution Time: {result.execution_time_ms}ms")
        logger.info(f"AI Response: {result.response}")
        logger.info(f"Entities Found: {len(result.entities)}")

        # Display first 5 entities
        for i, entity in enumerate(result.entities[:5], 1):
            logger.info(
                f"  {i}. {entity.entity_text} ({entity.entity_type}) "
                f"- confidence: {entity.confidence_score:.2f}"
            )


async def example_get_case_entities():
    """Example: Get all entities for a case"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 3: Get Case Entities")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Get high-confidence case citations
        entities = await client.get_case_entities(
            client_id="client-123",
            case_id="case-456",
            entity_type="CASE_CITATION",
            min_confidence=0.9,
            limit=20
        )

        logger.info(f"Found {len(entities)} high-confidence case citations")

        for i, entity in enumerate(entities[:10], 1):
            logger.info(
                f"  {i}. {entity.entity_text} "
                f"(confidence: {entity.confidence_score:.2f})"
            )


async def example_legal_research():
    """Example: Cross-case legal research (GLOBAL_SEARCH)"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 4: Legal Research Query (GLOBAL_SEARCH)")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Search for Second Amendment cases across all client cases
        result = await client.query_legal_research(
            client_id="client-123",
            query="Find Second Amendment cases related to firearms regulations",
            jurisdiction="federal",
            search_type="GLOBAL",
            max_results=30
        )

        logger.info(f"Query: {result.query}")
        logger.info(f"Search Type: {result.search_type}")
        logger.info(f"Execution Time: {result.execution_time_ms}ms")
        logger.info(f"AI Response: {result.response}")
        logger.info(f"Entities Found: {len(result.entities)}")

        # Display entities by type
        entity_types = {}
        for entity in result.entities:
            entity_types[entity.entity_type] = entity_types.get(entity.entity_type, 0) + 1

        logger.info("Entity Type Breakdown:")
        for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  - {entity_type}: {count}")


async def example_find_similar_cases():
    """Example: Find cases similar to a reference case"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 5: Find Similar Cases")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Find cases similar to Rahimi v. US
        similar_cases = await client.find_similar_cases(
            client_id="client-123",
            reference_case_id="case-rahimi",
            similarity_threshold=0.8,
            max_results=10
        )

        logger.info(f"Found {len(similar_cases)} similar cases")

        for i, case in enumerate(similar_cases, 1):
            logger.info(
                f"  {i}. {case.entity_text} "
                f"(confidence: {case.confidence_score:.2f})"
            )


async def example_search_precedents():
    """Example: Search for legal precedents"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 6: Search Legal Precedents")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Search for Second Amendment precedents
        precedents = await client.search_precedents(
            client_id="client-123",
            legal_issue="Second Amendment right to bear arms",
            jurisdiction="federal",
            court_level="supreme",
            max_results=15
        )

        logger.info(f"Found {len(precedents)} precedents")

        for i, precedent in enumerate(precedents[:10], 1):
            logger.info(
                f"  {i}. {precedent.entity_text} ({precedent.entity_type})"
            )


async def example_get_case_communities():
    """Example: Get community clusters for a case"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 7: Get Case Communities")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Get communities
        communities = await client.get_case_communities(
            client_id="client-123",
            case_id="case-456",
            min_size=3
        )

        logger.info(f"Found {len(communities)} communities")

        for i, community in enumerate(communities, 1):
            logger.info(
                f"  {i}. {community.title} "
                f"(size: {community.size}, coherence: {community.coherence_score:.2f})"
            )
            logger.info(f"     Summary: {community.summary[:100]}...")


async def example_get_graph_stats():
    """Example: Get graph statistics"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 8: Graph Statistics")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        # Get overall statistics
        stats = await client.get_graph_stats(include_details=True)

        logger.info(f"Total Entities: {stats.total_entities:,}")
        logger.info(f"Total Relationships: {stats.total_relationships:,}")
        logger.info(f"Total Communities: {stats.total_communities:,}")
        logger.info(f"Total Documents: {stats.total_documents:,}")

        logger.info("\nEntity Type Breakdown (Top 10):")
        sorted_entities = sorted(
            stats.entity_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for entity_type, count in sorted_entities:
            logger.info(f"  - {entity_type}: {count:,}")

        logger.info("\nRelationship Type Breakdown (Top 10):")
        sorted_relationships = sorted(
            stats.relationship_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for rel_type, count in sorted_relationships:
            logger.info(f"  - {rel_type}: {count:,}")

        if stats.graph_metrics:
            logger.info("\nGraph Metrics:")
            for metric, value in stats.graph_metrics.items():
                logger.info(f"  - {metric}: {value}")


async def example_create_case_graph():
    """Example: Create knowledge graph from entities"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 9: Create Case Graph")
    logger.info("=" * 80)

    # Sample entities in LurisEntityV2 format
    sample_entities = [
        {
            "entity_id": "entity_case_001",
            "entity_text": "Rahimi v. United States",
            "entity_type": "CASE_CITATION",
            "confidence": 0.95,
            "start_position": 0,
            "end_position": 25,
            "context": "In Rahimi v. United States, the Court...",
            "metadata": {
                "year": 2024,
                "court": "Supreme Court",
                "jurisdiction": "federal"
            }
        },
        {
            "entity_id": "entity_statute_001",
            "entity_text": "18 U.S.C. § 922(g)(8)",
            "entity_type": "STATUTE_CITATION",
            "confidence": 0.98,
            "start_position": 150,
            "end_position": 171,
            "context": "Section 922(g)(8) prohibits...",
            "metadata": {
                "title": "18",
                "section": "922",
                "subsection": "g(8)"
            }
        }
    ]

    async with create_graphrag_client() as client:
        result = await client.create_case_graph(
            document_id="doc-example-001",
            case_id="case-456",
            client_id="client-123",
            markdown_content="Sample document content...",
            entities=sample_entities,
            citations=[],
            relationships=[],
            enhanced_chunks=[],
            enable_deduplication=True,
            enable_community_detection=True,
            enable_cross_document_linking=True,
            use_ai_summaries=False  # LAZY mode
        )

        logger.info(f"Graph Created Successfully!")
        logger.info(f"Graph ID: {result.graph_id}")
        logger.info(f"Success: {result.success}")
        logger.info(f"Processing Time: {result.processing_time_seconds:.2f}s")

        logger.info("\nProcessing Results:")
        for key, value in result.processing_results.items():
            logger.info(f"  - {key}: {value}")

        logger.info("\nGraph Metrics:")
        for key, value in result.graph_metrics.items():
            logger.info(f"  - {key}: {value}")

        logger.info("\nQuality Metrics:")
        for key, value in result.quality_metrics.items():
            logger.info(f"  - {key}: {value}")


async def example_get_visualization_data():
    """Example: Get graph visualization data"""
    logger.info("=" * 80)
    logger.info("EXAMPLE 10: Graph Visualization Data")
    logger.info("=" * 80)

    async with create_graphrag_client() as client:
        viz_data = await client.get_visualization_data(
            client_id="client-123",
            case_id="case-456",
            max_nodes=50,
            node_types=["entity", "citation"]
        )

        logger.info(f"Nodes: {len(viz_data.get('nodes', []))}")
        logger.info(f"Edges: {len(viz_data.get('edges', []))}")

        # Display first 5 nodes
        nodes = viz_data.get('nodes', [])[:5]
        logger.info("\nSample Nodes:")
        for i, node in enumerate(nodes, 1):
            logger.info(
                f"  {i}. {node.get('label')} ({node.get('node_type')}) "
                f"- importance: {node.get('importance_score', 0):.2f}"
            )

        # Display first 5 edges
        edges = viz_data.get('edges', [])[:5]
        logger.info("\nSample Edges:")
        for i, edge in enumerate(edges, 1):
            logger.info(
                f"  {i}. {edge.get('source_node_id')} → {edge.get('target_node_id')} "
                f"({edge.get('edge_type')})"
            )


async def main():
    """Run all examples"""
    logger.info("\n" + "=" * 80)
    logger.info("GraphRAG Client Usage Examples")
    logger.info("=" * 80 + "\n")

    examples = [
        ("Health Check", example_health_check),
        ("Case Query", example_case_query),
        ("Get Case Entities", example_get_case_entities),
        ("Legal Research", example_legal_research),
        ("Find Similar Cases", example_find_similar_cases),
        ("Search Precedents", example_search_precedents),
        ("Get Communities", example_get_case_communities),
        ("Graph Statistics", example_get_graph_stats),
        ("Create Graph", example_create_case_graph),
        ("Visualization Data", example_get_visualization_data)
    ]

    for name, example_func in examples:
        try:
            await example_func()
            logger.info(f"\n✅ {name} completed successfully\n")
        except Exception as e:
            logger.error(f"\n❌ {name} failed: {e}\n")

    logger.info("\n" + "=" * 80)
    logger.info("All Examples Completed!")
    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
