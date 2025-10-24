"""
Dimension Analyzers for WHO/WHAT/WHERE/WHEN/WHY Context Construction

This module implements analyzers for each dimension of legal context.
Each analyzer is responsible for:
1. Querying GraphRAG service for graph-based insights
2. Querying Supabase for structured data
3. Transforming raw data into dimension-specific models
4. Calculating quality metrics

All analyzers are case-scoped and filter by case_id.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from src.models.dimensions import (
    WhoContext, WhatContext, WhereContext, WhenContext, WhyContext,
    Party, Judge, Attorney, Witness,
    Citation, CauseOfAction,
    LocalRule,
    TimelineEvent, Deadline,
    PrecedentAnalysis, LegalTheory,
    DimensionQualityMetrics
)
from src.clients.graphrag_client import GraphRAGClient
from src.clients.supabase_client import create_supabase_client

logger = logging.getLogger(__name__)


# ============================================================================
# BASE DIMENSION ANALYZER
# ============================================================================

class DimensionAnalyzer:
    """
    Base class for all dimension analyzers.

    Provides common functionality:
    - GraphRAG and Supabase client access
    - Quality scoring
    - Error handling with graceful degradation
    - Logging
    """

    def __init__(
        self,
        graphrag_client: GraphRAGClient,
        supabase_client: Any
    ):
        """
        Initialize dimension analyzer.

        Args:
            graphrag_client: Client for GraphRAG service queries
            supabase_client: Client for Supabase database queries
        """
        self.graphrag = graphrag_client
        self.supabase = supabase_client
        self.logger = logging.getLogger(self.__class__.__name__)

    async def analyze(self, client_id: str, case_id: str, **kwargs) -> Any:
        """
        Analyze dimension for specific case.

        Must be implemented by subclasses.

        Args:
            client_id: Client identifier for multi-tenant isolation
            case_id: Case identifier for case-scoped context

        Returns:
            Dimension-specific context model
        """
        raise NotImplementedError("Subclasses must implement analyze()")

    def calculate_quality_score(
        self,
        data_points: int,
        confidence_scores: List[float]
    ) -> DimensionQualityMetrics:
        """
        Calculate quality metrics for dimension.

        Args:
            data_points: Number of data points extracted
            confidence_scores: List of confidence scores for extracted data

        Returns:
            Quality metrics for dimension
        """
        # Calculate completeness based on data points
        # Heuristic: 10+ data points = full completeness
        completeness = min(1.0, data_points / 10.0)

        # Calculate average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        return DimensionQualityMetrics(
            dimension_name=self.__class__.__name__.replace('Analyzer', '').upper(),
            completeness_score=completeness,
            data_points=data_points,
            confidence_avg=avg_confidence,
            is_sufficient=completeness >= 0.85
        )


# ============================================================================
# WHO ANALYZER - Parties, Judges, Attorneys
# ============================================================================

class WhoAnalyzer(DimensionAnalyzer):
    """
    Analyzes WHO dimension for a case.

    Extracts:
    - Parties (plaintiffs, defendants, third parties)
    - Judges assigned to case
    - Attorneys representing parties
    - Witnesses
    - Relationships between entities
    """

    async def analyze(self, client_id: str, case_id: str, **kwargs) -> WhoContext:
        """
        Build WHO context for specific case.

        Args:
            client_id: Client identifier
            case_id: Case identifier

        Returns:
            WhoContext with all parties, judges, attorneys, witnesses
        """
        self.logger.info(f"Analyzing WHO dimension for case {case_id}")

        try:
            # 1. Query GraphRAG for case entities and relationships
            graph_result = await self._query_graphrag(client_id, case_id)

            # 2. Query Supabase for structured case data
            supabase_data = await self._query_supabase(client_id, case_id)

            # 3. Extract and transform entities
            parties = await self._extract_parties(graph_result, supabase_data, case_id)
            judges = await self._extract_judges(graph_result, supabase_data, case_id)
            attorneys = await self._extract_attorneys(graph_result, supabase_data, case_id)
            witnesses = await self._extract_witnesses(graph_result, supabase_data, case_id)

            # 4. Build relationships
            party_relationships = await self._build_party_relationships(
                client_id, case_id, parties
            )
            representation_map = self._build_representation_map(attorneys)

            # 5. Get case name
            case_name = await self._get_case_name(client_id, case_id)

            who_context = WhoContext(
                case_id=case_id,
                case_name=case_name,
                parties=parties,
                judges=judges,
                attorneys=attorneys,
                witnesses=witnesses,
                party_relationships=party_relationships,
                representation_map=representation_map
            )

            self.logger.info(
                f"WHO analysis complete: {len(parties)} parties, "
                f"{len(judges)} judges, {len(attorneys)} attorneys"
            )

            return who_context

        except Exception as e:
            self.logger.error(f"Error analyzing WHO dimension: {str(e)}", exc_info=True)
            # Return empty context on error (graceful degradation)
            return WhoContext(
                case_id=case_id,
                case_name=f"Case {case_id}",
                parties=[],
                judges=[],
                attorneys=[],
                witnesses=[]
            )

    async def _query_graphrag(self, client_id: str, case_id: str) -> Dict[str, Any]:
        """Query GraphRAG for case entities"""
        try:
            query = f"""
            Find all parties, judges, attorneys, and witnesses in case {case_id}.
            Include their roles, relationships, and metadata.
            """
            result = await self.graphrag.query(
                client_id=client_id,
                query=query,
                search_type="LOCAL",
                case_id=case_id
            )
            return result
        except Exception as e:
            self.logger.warning(f"GraphRAG query failed: {str(e)}")
            return {}

    async def _query_supabase(self, client_id: str, case_id: str) -> List[Dict[str, Any]]:
        """Query Supabase for case entities"""
        try:
            result = await self.supabase.schema('graph').table('nodes') \
                .select('*') \
                .eq('client_id', client_id) \
                .eq('case_id', case_id) \
                .in_('entity_type', ['PARTY', 'JUDGE', 'ATTORNEY', 'WITNESS']) \
                .execute()
            return result.data if result.data else []
        except Exception as e:
            self.logger.warning(f"Supabase query failed: {str(e)}")
            return []

    async def _extract_parties(
        self,
        graph_result: Dict[str, Any],
        supabase_data: List[Dict[str, Any]],
        case_id: str
    ) -> List[Party]:
        """Extract parties from data sources"""
        parties = []

        # Extract from Supabase data
        for node in supabase_data:
            if node.get('entity_type') == 'PARTY':
                properties = node.get('properties', {})
                party = Party(
                    id=node.get('node_id', ''),
                    name=properties.get('name', 'Unknown Party'),
                    role=properties.get('role', 'unknown'),
                    entity_type=properties.get('entity_type', 'person'),
                    case_id=case_id,
                    metadata=properties
                )
                parties.append(party)

        return parties

    async def _extract_judges(
        self,
        graph_result: Dict[str, Any],
        supabase_data: List[Dict[str, Any]],
        case_id: str
    ) -> List[Judge]:
        """Extract judges from data sources"""
        judges = []

        for node in supabase_data:
            if node.get('entity_type') == 'JUDGE':
                properties = node.get('properties', {})
                judge = Judge(
                    id=node.get('node_id', ''),
                    name=properties.get('name', 'Unknown Judge'),
                    court=properties.get('court', 'Unknown Court'),
                    case_id=case_id,
                    assignment_date=properties.get('assignment_date')
                )
                judges.append(judge)

        return judges

    async def _extract_attorneys(
        self,
        graph_result: Dict[str, Any],
        supabase_data: List[Dict[str, Any]],
        case_id: str
    ) -> List[Attorney]:
        """Extract attorneys from data sources"""
        attorneys = []

        for node in supabase_data:
            if node.get('entity_type') == 'ATTORNEY':
                properties = node.get('properties', {})
                attorney = Attorney(
                    id=node.get('node_id', ''),
                    name=properties.get('name', 'Unknown Attorney'),
                    firm=properties.get('firm'),
                    bar_number=properties.get('bar_number'),
                    representing=properties.get('representing', []),
                    case_id=case_id
                )
                attorneys.append(attorney)

        return attorneys

    async def _extract_witnesses(
        self,
        graph_result: Dict[str, Any],
        supabase_data: List[Dict[str, Any]],
        case_id: str
    ) -> List[Witness]:
        """Extract witnesses from data sources"""
        witnesses = []

        for node in supabase_data:
            if node.get('entity_type') == 'WITNESS':
                properties = node.get('properties', {})
                witness = Witness(
                    id=node.get('node_id', ''),
                    name=properties.get('name', 'Unknown Witness'),
                    witness_type=properties.get('witness_type', 'fact'),
                    representing_party=properties.get('representing_party'),
                    case_id=case_id,
                    expertise=properties.get('expertise')
                )
                witnesses.append(witness)

        return witnesses

    async def _build_party_relationships(
        self,
        client_id: str,
        case_id: str,
        parties: List[Party]
    ) -> Dict[str, List[str]]:
        """Build party relationship map"""
        relationships = {}

        try:
            # Query graph for relationships between parties
            result = await self.supabase.schema('graph').table('edges') \
                .select('*') \
                .eq('client_id', client_id) \
                .eq('case_id', case_id) \
                .execute()

            for edge in result.data if result.data else []:
                source = edge.get('source_node_id')
                target = edge.get('target_node_id')
                if source not in relationships:
                    relationships[source] = []
                relationships[source].append(target)

        except Exception as e:
            self.logger.warning(f"Failed to build party relationships: {str(e)}")

        return relationships

    def _build_representation_map(self, attorneys: List[Attorney]) -> Dict[str, str]:
        """Build party → attorney representation map"""
        rep_map = {}
        for attorney in attorneys:
            for party_id in attorney.representing:
                rep_map[party_id] = attorney.id
        return rep_map

    async def _get_case_name(self, client_id: str, case_id: str) -> str:
        """Get case name from database"""
        try:
            result = await self.supabase.schema('client').table('client_cases') \
                .select('case_name') \
                .eq('client_id', client_id) \
                .eq('id', case_id) \
                .maybe_single() \
                .execute()

            if result.data:
                return result.data.get('case_name', f'Case {case_id}')
        except Exception as e:
            self.logger.warning(f"Failed to get case name: {str(e)}")

        return f"Case {case_id}"


# ============================================================================
# WHAT ANALYZER - Legal Issues, Claims, Citations
# ============================================================================

class WhatAnalyzer(DimensionAnalyzer):
    """
    Analyzes WHAT dimension for a case.

    Extracts:
    - Causes of action
    - Legal issues
    - Legal doctrines
    - Statute citations
    - Case law citations
    """

    async def analyze(self, client_id: str, case_id: str, **kwargs) -> WhatContext:
        """Build WHAT context for specific case"""
        self.logger.info(f"Analyzing WHAT dimension for case {case_id}")

        try:
            # Query for legal entities
            entities = await self._query_legal_entities(client_id, case_id)

            # Extract components
            causes_of_action = await self._extract_causes_of_action(entities, case_id)
            legal_issues = self._extract_legal_issues(entities)
            doctrines = self._extract_doctrines(entities)
            statutes = self._extract_statutes(entities, case_id)
            case_citations = self._extract_case_citations(entities, case_id)

            # Determine primary legal theory
            primary_theory = self._determine_primary_theory(causes_of_action, legal_issues)

            # Calculate issue complexity
            complexity = self._calculate_complexity(
                len(causes_of_action),
                len(legal_issues),
                len(statutes)
            )

            # Get case name
            case_name = await self._get_case_name(client_id, case_id)

            what_context = WhatContext(
                case_id=case_id,
                case_name=case_name,
                causes_of_action=causes_of_action,
                legal_issues=legal_issues,
                doctrines=doctrines,
                statutes=statutes,
                case_citations=case_citations,
                primary_legal_theory=primary_theory,
                issue_complexity=complexity,
                jurisdiction_type="federal"
            )

            self.logger.info(
                f"WHAT analysis complete: {len(causes_of_action)} causes, "
                f"{len(statutes)} statutes, {len(case_citations)} cases"
            )

            return what_context

        except Exception as e:
            self.logger.error(f"Error analyzing WHAT dimension: {str(e)}", exc_info=True)
            return WhatContext(
                case_id=case_id,
                case_name=f"Case {case_id}"
            )

    async def _query_legal_entities(self, client_id: str, case_id: str) -> List[Dict[str, Any]]:
        """Query for legal entities (statutes, cases, doctrines)"""
        try:
            result = await self.supabase.schema('graph').table('nodes') \
                .select('*') \
                .eq('client_id', client_id) \
                .eq('case_id', case_id) \
                .in_('entity_type', [
                    'STATUTE_CITATION', 'CASE_CITATION', 'LEGAL_PRINCIPLE',
                    'CAUSE_OF_ACTION', 'DOCTRINE'
                ]) \
                .execute()
            return result.data if result.data else []
        except Exception as e:
            self.logger.warning(f"Failed to query legal entities: {str(e)}")
            return []

    async def _extract_causes_of_action(
        self,
        entities: List[Dict[str, Any]],
        case_id: str
    ) -> List[CauseOfAction]:
        """Extract causes of action"""
        causes = []
        for entity in entities:
            if entity.get('entity_type') == 'CAUSE_OF_ACTION':
                props = entity.get('properties', {})
                cause = CauseOfAction(
                    id=entity.get('node_id', ''),
                    name=props.get('name', 'Unknown Cause'),
                    description=props.get('description', ''),
                    elements=props.get('elements', []),
                    case_id=case_id
                )
                causes.append(cause)
        return causes

    def _extract_legal_issues(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Extract legal issues"""
        issues = []
        for entity in entities:
            if entity.get('entity_type') == 'LEGAL_PRINCIPLE':
                props = entity.get('properties', {})
                issue = props.get('name') or props.get('text')
                if issue:
                    issues.append(issue)
        return list(set(issues))  # Deduplicate

    def _extract_doctrines(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Extract legal doctrines"""
        doctrines = []
        for entity in entities:
            if entity.get('entity_type') == 'DOCTRINE':
                props = entity.get('properties', {})
                doctrine = props.get('name') or props.get('text')
                if doctrine:
                    doctrines.append(doctrine)
        return list(set(doctrines))

    def _extract_statutes(
        self,
        entities: List[Dict[str, Any]],
        case_id: str
    ) -> List[Citation]:
        """Extract statute citations"""
        statutes = []
        for entity in entities:
            if entity.get('entity_type') == 'STATUTE_CITATION':
                props = entity.get('properties', {})
                citation = Citation(
                    text=props.get('text', ''),
                    type='statute',
                    jurisdiction=props.get('jurisdiction', 'federal'),
                    confidence=props.get('confidence', 0.9),
                    case_id=case_id
                )
                statutes.append(citation)
        return statutes

    def _extract_case_citations(
        self,
        entities: List[Dict[str, Any]],
        case_id: str
    ) -> List[Citation]:
        """Extract case law citations"""
        citations = []
        for entity in entities:
            if entity.get('entity_type') == 'CASE_CITATION':
                props = entity.get('properties', {})
                citation = Citation(
                    text=props.get('text', ''),
                    type='case_law',
                    jurisdiction=props.get('jurisdiction', 'federal'),
                    confidence=props.get('confidence', 0.9),
                    case_id=case_id
                )
                citations.append(citation)
        return citations

    def _determine_primary_theory(
        self,
        causes: List[CauseOfAction],
        issues: List[str]
    ) -> Optional[str]:
        """Determine primary legal theory"""
        if causes:
            return causes[0].name
        elif issues:
            return issues[0]
        return None

    def _calculate_complexity(
        self,
        cause_count: int,
        issue_count: int,
        statute_count: int
    ) -> float:
        """Calculate issue complexity score (0.0-1.0)"""
        # Simple heuristic: more causes/issues/statutes = higher complexity
        total = cause_count + issue_count + statute_count
        # Cap at 20 for max complexity
        return min(1.0, total / 20.0)

    async def _get_case_name(self, client_id: str, case_id: str) -> str:
        """Get case name"""
        try:
            result = await self.supabase.schema('client').table('client_cases') \
                .select('case_name') \
                .eq('client_id', client_id) \
                .eq('id', case_id) \
                .maybe_single() \
                .execute()
            if result.data:
                return result.data.get('case_name', f'Case {case_id}')
        except:
            pass
        return f"Case {case_id}"


# ============================================================================
# WHERE ANALYZER - Jurisdiction, Venue, Court
# ============================================================================

class WhereAnalyzer(DimensionAnalyzer):
    """
    Analyzes WHERE dimension for a case.

    Extracts:
    - Primary jurisdiction
    - Court information
    - Venue
    - Local rules
    - Filing requirements
    """

    async def analyze(self, client_id: str, case_id: str, **kwargs) -> WhereContext:
        """Build WHERE context for specific case"""
        self.logger.info(f"Analyzing WHERE dimension for case {case_id}")

        try:
            # Query case metadata
            case_data = await self._query_case_metadata(client_id, case_id)

            # Extract components
            jurisdiction = case_data.get('jurisdiction', 'Unknown')
            court = case_data.get('court', 'Unknown Court')
            venue = case_data.get('venue', 'Unknown Venue')
            judge_chambers = case_data.get('judge_chambers')

            # Get local rules (placeholder for now)
            local_rules = await self._get_local_rules(jurisdiction, court)

            # Get case name
            case_name = case_data.get('case_name', f'Case {case_id}')

            where_context = WhereContext(
                case_id=case_id,
                case_name=case_name,
                primary_jurisdiction=jurisdiction,
                court=court,
                venue=venue,
                judge_chambers=judge_chambers,
                local_rules=local_rules,
                filing_requirements=[],
                related_proceedings=[]
            )

            self.logger.info(f"WHERE analysis complete: {jurisdiction}, {court}")

            return where_context

        except Exception as e:
            self.logger.error(f"Error analyzing WHERE dimension: {str(e)}", exc_info=True)
            return WhereContext(
                case_id=case_id,
                case_name=f"Case {case_id}",
                primary_jurisdiction="Unknown",
                court="Unknown Court",
                venue="Unknown Venue"
            )

    async def _query_case_metadata(self, client_id: str, case_id: str) -> Dict[str, Any]:
        """Query case metadata from database"""
        try:
            result = await self.supabase.schema('client').table('client_cases') \
                .select('*') \
                .eq('client_id', client_id) \
                .eq('id', case_id) \
                .maybe_single() \
                .execute()
            return result.data if result.data else {}
        except Exception as e:
            self.logger.warning(f"Failed to query case metadata: {str(e)}")
            return {}

    async def _get_local_rules(self, jurisdiction: str, court: str) -> List[LocalRule]:
        """Get local court rules (placeholder)"""
        # In production, this would query a rules database
        return []


# ============================================================================
# WHEN ANALYZER - Timeline, Deadlines
# ============================================================================

class WhenAnalyzer(DimensionAnalyzer):
    """
    Analyzes WHEN dimension for a case.

    Extracts:
    - Filing date
    - Timeline of events
    - Upcoming deadlines
    - Past deadlines
    - Urgency metrics
    """

    async def analyze(self, client_id: str, case_id: str, **kwargs) -> WhenContext:
        """Build WHEN context for specific case"""
        self.logger.info(f"Analyzing WHEN dimension for case {case_id}")

        try:
            # Query case dates and timeline
            case_data = await self._query_case_dates(client_id, case_id)
            timeline = await self._build_timeline(client_id, case_id)
            deadlines = await self._get_deadlines(client_id, case_id)

            # Separate upcoming and past deadlines
            now = datetime.now()
            upcoming = [d for d in deadlines if d.deadline_date > now]
            past = [d for d in deadlines if d.deadline_date <= now]

            # Calculate metrics
            filing_date = case_data.get('filing_date', datetime.now())
            case_age = (now - filing_date).days
            next_deadline = min([d.deadline_date for d in upcoming]) if upcoming else None
            days_until_next = (next_deadline - now).days if next_deadline else None

            # Calculate urgency
            urgency = self._calculate_urgency(upcoming, case_age)

            # Get case name
            case_name = case_data.get('case_name', f'Case {case_id}')

            when_context = WhenContext(
                case_id=case_id,
                case_name=case_name,
                filing_date=filing_date,
                incident_date=case_data.get('incident_date'),
                timeline=timeline,
                upcoming_deadlines=upcoming,
                past_deadlines=past,
                discovery_cutoff=case_data.get('discovery_cutoff'),
                motion_deadline=case_data.get('motion_deadline'),
                trial_date=case_data.get('trial_date'),
                statute_of_limitations=case_data.get('statute_of_limitations'),
                days_until_next_deadline=days_until_next,
                urgency_score=urgency,
                case_age_days=case_age
            )

            self.logger.info(
                f"WHEN analysis complete: {len(timeline)} events, "
                f"{len(upcoming)} upcoming deadlines"
            )

            return when_context

        except Exception as e:
            self.logger.error(f"Error analyzing WHEN dimension: {str(e)}", exc_info=True)
            return WhenContext(
                case_id=case_id,
                case_name=f"Case {case_id}",
                filing_date=datetime.now(),
                case_age_days=0
            )

    async def _query_case_dates(self, client_id: str, case_id: str) -> Dict[str, Any]:
        """Query case dates"""
        try:
            result = await self.supabase.schema('client').table('client_cases') \
                .select('*') \
                .eq('client_id', client_id) \
                .eq('id', case_id) \
                .maybe_single() \
                .execute()
            return result.data if result.data else {}
        except:
            return {}

    async def _build_timeline(self, client_id: str, case_id: str) -> List[TimelineEvent]:
        """Build case timeline"""
        # Placeholder - in production would query events table
        return []

    async def _get_deadlines(self, client_id: str, case_id: str) -> List[Deadline]:
        """Get all deadlines for case"""
        # Placeholder - in production would query deadlines table
        return []

    def _calculate_urgency(self, upcoming_deadlines: List[Deadline], case_age: int) -> float:
        """Calculate urgency score (0.0-1.0)"""
        if not upcoming_deadlines:
            return 0.3  # Low urgency if no deadlines

        # Check for imminent deadlines (within 7 days)
        now = datetime.now()
        imminent = [d for d in upcoming_deadlines if (d.deadline_date - now).days <= 7]

        if imminent:
            return 1.0  # Maximum urgency

        # Check for upcoming deadlines (within 30 days)
        upcoming_30 = [d for d in upcoming_deadlines if (d.deadline_date - now).days <= 30]

        if upcoming_30:
            return 0.7  # High urgency

        return 0.5  # Medium urgency


# ============================================================================
# WHY ANALYZER - Legal Reasoning, Precedents
# ============================================================================

class WhyAnalyzer(DimensionAnalyzer):
    """
    Analyzes WHY dimension for a case.

    Extracts:
    - Legal theories
    - Supporting precedents
    - Opposing precedents
    - Argument strength
    - Risk factors
    """

    async def analyze(self, client_id: str, case_id: str, **kwargs) -> WhyContext:
        """Build WHY context for specific case"""
        self.logger.info(f"Analyzing WHY dimension for case {case_id}")

        try:
            # Query GraphRAG for precedents
            precedents = await self._query_precedents(client_id, case_id)

            # Extract components
            legal_theories = await self._extract_legal_theories(client_id, case_id)
            supporting = self._categorize_precedents(precedents, "supporting")
            opposing = self._categorize_precedents(precedents, "opposing")

            # Calculate argument strength
            strength = self._calculate_argument_strength(supporting, opposing)

            # Get case name
            case_name = await self._get_case_name(client_id, case_id)

            why_context = WhyContext(
                case_id=case_id,
                case_name=case_name,
                legal_theories=legal_theories,
                argument_outline=[],
                supporting_precedents=supporting,
                opposing_precedents=opposing,
                distinguishing_factors=[],
                argument_strength=strength,
                risk_factors=[],
                mitigation_strategies=[],
                similar_case_outcomes={},
                judge_ruling_patterns={}
            )

            self.logger.info(
                f"WHY analysis complete: {len(supporting)} supporting, "
                f"{len(opposing)} opposing precedents"
            )

            return why_context

        except Exception as e:
            self.logger.error(f"Error analyzing WHY dimension: {str(e)}", exc_info=True)
            return WhyContext(
                case_id=case_id,
                case_name=f"Case {case_id}"
            )

    async def _query_precedents(self, client_id: str, case_id: str) -> List[Dict[str, Any]]:
        """Query for precedent cases via GraphRAG"""
        try:
            query = f"Find relevant precedent cases for case {case_id}"
            result = await self.graphrag.query(
                client_id=client_id,
                query=query,
                search_type="GLOBAL",
                case_id=case_id
            )
            return result.get('precedents', [])
        except:
            return []

    async def _extract_legal_theories(self, client_id: str, case_id: str) -> List[LegalTheory]:
        """Extract legal theories for case"""
        # Placeholder
        return []

    def _categorize_precedents(
        self,
        precedents: List[Dict[str, Any]],
        category: str
    ) -> List[PrecedentAnalysis]:
        """Categorize precedents as supporting or opposing"""
        categorized = []
        for prec in precedents:
            if prec.get('category') == category:
                analysis = PrecedentAnalysis(
                    case_name=prec.get('name', 'Unknown Case'),
                    citation=prec.get('citation', ''),
                    relevance_score=prec.get('relevance', 0.5),
                    holding=prec.get('holding', ''),
                    distinguishing_factors=prec.get('distinguishing_factors', []),
                    favorability=category
                )
                categorized.append(analysis)
        return categorized

    def _calculate_argument_strength(
        self,
        supporting: List[PrecedentAnalysis],
        opposing: List[PrecedentAnalysis]
    ) -> float:
        """Calculate argument strength based on precedents"""
        if not supporting and not opposing:
            return 0.5

        support_score = sum(p.relevance_score for p in supporting)
        oppose_score = sum(p.relevance_score for p in opposing)

        total = support_score + oppose_score
        if total == 0:
            return 0.5

        return support_score / total

    async def _get_case_name(self, client_id: str, case_id: str) -> str:
        """Get case name"""
        try:
            result = await self.supabase.schema('client').table('client_cases') \
                .select('case_name') \
                .eq('client_id', client_id) \
                .eq('id', case_id) \
                .maybe_single() \
                .execute()
            if result.data:
                return result.data.get('case_name', f'Case {case_id}')
        except:
            pass
        return f"Case {case_id}"
