#!/usr/bin/env python3
"""
Data Discovery Script for Context Engine E2E Tests

Queries the graph database to discover available real data and generates
a test data manifest with recommended test queries.
"""

import sys
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any
from collections import Counter
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

sys.path.insert(0, '/srv/luris/be/context-engine-service')
from src.clients.supabase_client import create_supabase_client


class DataDiscovery:
    """Discover available test data in the graph database"""

    def __init__(self):
        self.console = Console()
        self.client = None
        self.manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database_summary": {},
            "entity_types_discovered": {},
            "relationship_types_discovered": {},
            "sample_entities": [],
            "recommended_test_queries": [],
            "sample_document_ids": [],
            "test_data_coverage": {
                "who_dimension": [],
                "what_dimension": [],
                "where_dimension": [],
                "when_dimension": [],
                "why_dimension": []
            }
        }

    async def connect_database(self):
        """Initialize database connection"""
        self.client = create_supabase_client(service_name="data-discovery")
        self.console.print("[green]✅ Connected to database[/green]")

    async def discover_graph_nodes(self) -> Dict[str, Any]:
        """Discover graph node types and counts"""
        self.console.print("\n[cyan]Analyzing graph nodes...[/cyan]")

        # Get total count
        total_result = await self.client.schema('graph').table('nodes') \
            .select('count', count='exact').execute()
        total_count = total_result.count

        # Get sample nodes with metadata (batch by batch to avoid memory issues)
        all_nodes = []
        batch_size = 1000
        offset = 0

        while len(all_nodes) < min(10000, total_count):
            batch = await self.client.schema('graph').table('nodes') \
                .select('node_id, title, description, metadata') \
                .limit(batch_size) \
                .offset(offset) \
                .execute()

            if not batch.data:
                break

            all_nodes.extend(batch.data)
            offset += batch_size

            if len(batch.data) < batch_size:
                break

        # Count by entity_type from metadata
        entity_types = Counter()
        sample_nodes = {}
        node_titles = Counter()

        for node in all_nodes:
            metadata = node.get('metadata', {})
            entity_type = metadata.get('entity_type', 'UNKNOWN')
            entity_types[entity_type] += 1

            # Track most common titles
            title = node.get('title', '')
            if title:
                node_titles[title] += 1

            # Store sample nodes for each type (first occurrence)
            if entity_type not in sample_nodes:
                sample_nodes[entity_type] = {
                    "text": node.get('title') or node.get('description', '')[:100],
                    "type": entity_type,
                    "node_id": node.get('node_id')
                }

        # Get top 20 most common node titles
        common_nodes = [
            {"title": title, "count": count}
            for title, count in node_titles.most_common(20)
        ]

        return {
            "total_count": total_count,
            "types": dict(entity_types),
            "samples": list(sample_nodes.values()),
            "common_nodes": common_nodes
        }

    async def discover_graph_edges(self) -> Dict[str, Any]:
        """Discover edge relationship types"""
        self.console.print("[cyan]Analyzing graph edges...[/cyan]")

        # Get total count
        total_result = await self.client.schema('graph').table('edges') \
            .select('count', count='exact').execute()
        total_count = total_result.count

        # Get sample edges
        all_edges = []
        batch_size = 1000
        offset = 0

        while len(all_edges) < min(5000, total_count):
            batch = await self.client.schema('graph').table('edges') \
                .select('relationship_type, evidence, metadata') \
                .limit(batch_size) \
                .offset(offset) \
                .execute()

            if not batch.data:
                break

            all_edges.extend(batch.data)
            offset += batch_size

            if len(batch.data) < batch_size:
                break

        relationship_types = Counter()
        sample_relationships = {}

        for edge in all_edges:
            rel_type = edge.get('relationship_type', 'UNKNOWN')
            relationship_types[rel_type] += 1

            # Store sample relationship
            if rel_type not in sample_relationships:
                evidence = edge.get('evidence', [])
                sample_relationships[rel_type] = {
                    "type": rel_type,
                    "sample_evidence": evidence[:2] if evidence else []
                }

        return {
            "total_count": total_count,
            "types": dict(relationship_types),
            "samples": list(sample_relationships.values())
        }

    async def discover_law_entities(self) -> Dict[str, Any]:
        """Discover law schema entities"""
        self.console.print("[cyan]Analyzing law entities...[/cyan]")

        # Get total count
        total_result = await self.client.schema('law').table('entities') \
            .select('count', count='exact').execute()
        total_count = total_result.count

        # Get sample entities
        all_entities = []
        batch_size = 1000
        offset = 0

        while len(all_entities) < min(5000, total_count):
            batch = await self.client.schema('law').table('entities') \
                .select('id, entity_text, entity_type, confidence_score, attributes') \
                .limit(batch_size) \
                .offset(offset) \
                .execute()

            if not batch.data:
                break

            all_entities.extend(batch.data)
            offset += batch_size

            if len(batch.data) < batch_size:
                break

        entity_types = Counter()
        sample_entities = {}
        entity_texts = Counter()

        for entity in all_entities:
            entity_type = entity.get('entity_type', 'UNKNOWN')
            entity_types[entity_type] += 1

            # Track common entity texts
            text = entity.get('entity_text', '')
            if text:
                entity_texts[text] += 1

            if entity_type not in sample_entities:
                sample_entities[entity_type] = {
                    "text": entity.get('entity_text', 'N/A')[:100],
                    "type": entity_type,
                    "confidence": entity.get('confidence_score', 0)
                }

        # Get top 20 most common entities
        common_entities = [
            {"text": text, "count": count}
            for text, count in entity_texts.most_common(20)
        ]

        return {
            "total_count": total_count,
            "types": dict(entity_types),
            "samples": list(sample_entities.values()),
            "common_entities": common_entities
        }

    async def discover_law_documents(self) -> Dict[str, Any]:
        """Discover law documents"""
        self.console.print("[cyan]Analyzing law documents...[/cyan]")

        # Get total count
        total_result = await self.client.schema('law').table('documents') \
            .select('count', count='exact').execute()
        total_count = total_result.count

        # Get sample documents with details
        docs = await self.client.schema('law').table('documents') \
            .select('id, title, document_type') \
            .limit(20) \
            .execute()

        doc_types = Counter()
        sample_docs = []

        for doc in docs.data:
            doc_type = doc.get('document_type', 'UNKNOWN')
            doc_types[doc_type] += 1

            if len(sample_docs) < 10:
                sample_docs.append({
                    "id": doc.get('id'),
                    "title": doc.get('title', 'N/A')[:100],
                    "type": doc_type
                })

        return {
            "total_count": total_count,
            "types": dict(doc_types),
            "samples": sample_docs
        }

    def map_to_dimensions(self):
        """Map discovered entity types to WHO/WHAT/WHERE/WHEN/WHY dimensions"""
        entity_types = set(self.manifest["entity_types_discovered"].keys())

        # WHO dimension (people, organizations, courts)
        who_keywords = ['court', 'judge', 'justice', 'attorney', 'party', 'plaintiff',
                        'defendant', 'person', 'organization', 'agency']
        self.manifest["test_data_coverage"]["who_dimension"] = [
            et for et in entity_types
            if any(kw in et.lower() for kw in who_keywords)
        ]

        # WHAT dimension (legal issues, statutes, cases)
        what_keywords = ['statute', 'usc', 'cfr', 'case', 'law', 'rule', 'regulation',
                         'issue', 'claim', 'cause', 'motion']
        self.manifest["test_data_coverage"]["what_dimension"] = [
            et for et in entity_types
            if any(kw in et.lower() for kw in what_keywords)
        ]

        # WHERE dimension (jurisdiction, venue, location)
        where_keywords = ['jurisdiction', 'venue', 'location', 'district', 'circuit',
                          'state', 'federal', 'court']
        self.manifest["test_data_coverage"]["where_dimension"] = [
            et for et in entity_types
            if any(kw in et.lower() for kw in where_keywords)
        ]

        # WHEN dimension (dates, deadlines, terms)
        when_keywords = ['date', 'time', 'deadline', 'filing', 'hearing', 'term']
        self.manifest["test_data_coverage"]["when_dimension"] = [
            et for et in entity_types
            if any(kw in et.lower() for kw in when_keywords)
        ]

        # WHY dimension (reasoning, precedent, citation)
        why_keywords = ['reason', 'precedent', 'citation', 'opinion', 'holding',
                        'doctrine', 'principle']
        self.manifest["test_data_coverage"]["why_dimension"] = [
            et for et in entity_types
            if any(kw in et.lower() for kw in why_keywords)
        ]

    def generate_test_queries(self):
        """Generate recommended test queries based on discovered data"""
        queries = []

        entity_types = self.manifest["entity_types_discovered"]
        relationship_types = self.manifest["relationship_types_discovered"]
        dimensions = self.manifest["test_data_coverage"]

        # WHO dimension queries
        if dimensions["who_dimension"]:
            who_type = dimensions["who_dimension"][0]
            count = entity_types.get(who_type, 0)
            queries.append({
                "query": f"What {who_type.lower().replace('_', ' ')}s are mentioned in the documents?",
                "expected_entity_type": who_type,
                "dimension": "WHO",
                "estimated_results": count,
                "reasoning": f"{who_type} entities represent WHO dimension - key actors in legal documents"
            })

        # WHAT dimension queries
        if dimensions["what_dimension"]:
            what_type = dimensions["what_dimension"][0]
            count = entity_types.get(what_type, 0)
            queries.append({
                "query": f"Find all {what_type.lower().replace('_', ' ')}s in the legal corpus",
                "expected_entity_type": what_type,
                "dimension": "WHAT",
                "estimated_results": count,
                "reasoning": f"{what_type} entities represent WHAT legal issues/authorities are involved"
            })

        # WHERE dimension queries
        if dimensions["where_dimension"]:
            where_type = dimensions["where_dimension"][0]
            count = entity_types.get(where_type, 0)
            queries.append({
                "query": f"What {where_type.lower().replace('_', ' ')}s appear in the documents?",
                "expected_entity_type": where_type,
                "dimension": "WHERE",
                "estimated_results": count,
                "reasoning": f"{where_type} entities represent WHERE geographically/jurisdictionally"
            })

        # Relationship-based queries (WHY dimension)
        if relationship_types:
            rel_type = list(relationship_types.keys())[0]
            count = relationship_types[rel_type]
            queries.append({
                "query": f"What entities have '{rel_type}' relationships?",
                "expected_relationship": rel_type,
                "dimension": "WHY",
                "estimated_results": count,
                "reasoning": f"'{rel_type}' relationships explain WHY entities are connected"
            })

        # Multi-entity query
        if len(entity_types) >= 2:
            types = list(entity_types.keys())[:2]
            queries.append({
                "query": f"Find documents containing both {types[0]} and {types[1]} entities",
                "expected_entity_types": types,
                "dimension": "COMPREHENSIVE",
                "estimated_results": min(entity_types[types[0]], entity_types[types[1]]),
                "reasoning": "Multi-entity query tests cross-dimensional context retrieval"
            })

        # Common entity query
        if self.manifest.get("common_entities"):
            common = self.manifest["common_entities"][0]
            queries.append({
                "query": f"What is the context around '{common['text']}'?",
                "expected_entity_text": common['text'],
                "dimension": "COMPREHENSIVE",
                "estimated_results": common['count'],
                "reasoning": f"Most common entity (appears {common['count']} times), good for testing retrieval"
            })

        return queries

    async def run_discovery(self):
        """Run complete data discovery process"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:

            # Connect to database
            task = progress.add_task("[cyan]Connecting to database...", total=None)
            await self.connect_database()
            progress.update(task, completed=True)

            # Discover graph nodes
            task = progress.add_task("[cyan]Discovering graph nodes...", total=None)
            nodes_data = await self.discover_graph_nodes()
            self.manifest["database_summary"]["graph_nodes"] = nodes_data["total_count"]
            self.manifest["entity_types_discovered"] = nodes_data["types"]
            self.manifest["sample_entities"].extend(nodes_data["samples"])
            self.manifest["common_nodes"] = nodes_data["common_nodes"]
            progress.update(task, completed=True)

            # Discover graph edges
            task = progress.add_task("[cyan]Discovering graph edges...", total=None)
            edges_data = await self.discover_graph_edges()
            self.manifest["database_summary"]["graph_edges"] = edges_data["total_count"]
            self.manifest["relationship_types_discovered"] = edges_data["types"]
            self.manifest["sample_relationships"] = edges_data["samples"]
            progress.update(task, completed=True)

            # Discover law entities
            task = progress.add_task("[cyan]Discovering law entities...", total=None)
            entities_data = await self.discover_law_entities()
            self.manifest["database_summary"]["law_entities"] = entities_data["total_count"]
            # Merge entity types
            for et, count in entities_data["types"].items():
                self.manifest["entity_types_discovered"][et] = \
                    self.manifest["entity_types_discovered"].get(et, 0) + count
            self.manifest["common_entities"] = entities_data["common_entities"]
            progress.update(task, completed=True)

            # Discover documents
            task = progress.add_task("[cyan]Discovering documents...", total=None)
            docs_data = await self.discover_law_documents()
            self.manifest["database_summary"]["law_documents"] = docs_data["total_count"]
            self.manifest["sample_document_ids"] = [d["id"] for d in docs_data["samples"]]
            self.manifest["sample_documents"] = docs_data["samples"]
            self.manifest["document_types"] = docs_data["types"]
            progress.update(task, completed=True)

            # Map to dimensions
            task = progress.add_task("[cyan]Mapping to context dimensions...", total=None)
            self.map_to_dimensions()
            progress.update(task, completed=True)

            # Generate test queries
            task = progress.add_task("[cyan]Generating test queries...", total=None)
            self.manifest["recommended_test_queries"] = self.generate_test_queries()
            progress.update(task, completed=True)

        # Save manifest
        output_path = '/srv/luris/be/context-engine-service/tests/e2e/data_manifest.json'
        with open(output_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

        self.console.print(f"\n[green]✅ Data manifest saved to: {output_path}[/green]\n")

        # Display summary
        self.display_summary()

    def display_summary(self):
        """Display discovery summary"""

        # Database summary
        self.console.print("\n[bold cyan]Database Summary:[/bold cyan]\n")
        summary = self.manifest["database_summary"]
        for key, value in summary.items():
            self.console.print(f"  {key.replace('_', ' ').title()}: [green]{value:,}[/green]")

        # Entity types table
        self.console.print("\n")
        table = Table(title="Top 15 Entity Types Discovered")
        table.add_column("Entity Type", style="cyan")
        table.add_column("Count", justify="right", style="green")
        table.add_column("% of Total", justify="right", style="yellow")

        sorted_types = sorted(
            self.manifest["entity_types_discovered"].items(),
            key=lambda x: x[1],
            reverse=True
        )

        total_entities = sum(count for _, count in sorted_types)

        for entity_type, count in sorted_types[:15]:
            percentage = (count / total_entities * 100) if total_entities > 0 else 0
            table.add_row(entity_type, f"{count:,}", f"{percentage:.1f}%")

        self.console.print(table)

        # Relationship types table
        if self.manifest["relationship_types_discovered"]:
            self.console.print("\n")
            table2 = Table(title="Discovered Relationship Types")
            table2.add_column("Relationship", style="cyan")
            table2.add_column("Count", justify="right", style="green")

            sorted_rels = sorted(
                self.manifest["relationship_types_discovered"].items(),
                key=lambda x: x[1],
                reverse=True
            )

            for rel_type, count in sorted_rels:
                table2.add_row(rel_type, f"{count:,}")

            self.console.print(table2)

        # Dimension coverage
        self.console.print("\n[bold cyan]Context Dimension Coverage:[/bold cyan]\n")
        dimensions = self.manifest["test_data_coverage"]
        for dim_name, entity_types in dimensions.items():
            dim_display = dim_name.replace('_', ' ').title()
            count = len(entity_types)
            self.console.print(f"  {dim_display}: [green]{count}[/green] entity types")
            if entity_types:
                self.console.print(f"    Examples: {', '.join(entity_types[:3])}")

        # Common entities
        if self.manifest.get("common_entities"):
            self.console.print("\n")
            table3 = Table(title="Most Common Entities (Top 10)")
            table3.add_column("Entity Text", style="cyan")
            table3.add_column("Occurrences", justify="right", style="green")

            for entity in self.manifest["common_entities"][:10]:
                text = entity["text"][:60] + "..." if len(entity["text"]) > 60 else entity["text"]
                table3.add_row(text, f"{entity['count']:,}")

            self.console.print(table3)

        # Test queries
        self.console.print("\n[bold cyan]Recommended Test Queries:[/bold cyan]\n")
        for i, query in enumerate(self.manifest["recommended_test_queries"], 1):
            self.console.print(f"{i}. [yellow]{query['query']}[/yellow]")
            self.console.print(f"   Dimension: [magenta]{query.get('dimension', 'N/A')}[/magenta]")
            self.console.print(f"   Expected results: ~[green]{query.get('estimated_results', 0):,}[/green]")
            self.console.print(f"   Reasoning: {query.get('reasoning', 'N/A')}\n")


async def main():
    """Main entry point"""
    console = Console()

    console.print("\n[bold blue]Context Engine Data Discovery Tool[/bold blue]")
    console.print("[dim]Analyzing graph database to generate test data manifest...[/dim]\n")

    try:
        discovery = DataDiscovery()
        await discovery.run_discovery()

        console.print("\n[bold green]✅ Discovery complete![/bold green]")
        console.print("[dim]Use the generated data_manifest.json for E2E test development[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]❌ Discovery failed: {e}[/bold red]\n")
        raise


if __name__ == "__main__":
    asyncio.run(main())
