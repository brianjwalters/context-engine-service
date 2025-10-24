"""
Context Builder - Orchestrates WHO/WHAT/WHERE/WHEN/WHY Dimension Analysis

This module implements the ContextBuilder class which:
1. Orchestrates all five dimension analyzers
2. Executes dimension analysis in parallel for performance
3. Calculates overall context quality scores
4. Implements caching for frequently accessed contexts
5. Provides graceful degradation on dimension failures

The ContextBuilder is the main entry point for building case-specific context.
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.models.dimensions import (
    ContextResponse,
    WhoContext, WhatContext, WhereContext, WhenContext, WhyContext,
    DimensionQualityMetrics
)
from src.core.dimension_analyzer import (
    WhoAnalyzer,
    WhatAnalyzer,
    WhereAnalyzer,
    WhenAnalyzer,
    WhyAnalyzer
)
from src.core.cache_manager import CacheManager, create_cache_manager
from src.clients.graphrag_client import GraphRAGClient
from src.clients.supabase_client import create_supabase_client

logger = logging.getLogger(__name__)


class ContextBuilder:
    """
    Orchestrates building complete WHO/WHAT/WHERE/WHEN/WHY context for a case.

    The ContextBuilder coordinates all dimension analyzers and combines their
    results into a comprehensive ContextResponse. It supports:

    - Three context scopes: minimal, standard, comprehensive
    - Selective dimension building
    - Parallel execution of dimension analyzers
    - Quality scoring and completeness checking
    - Graceful degradation on analyzer failures
    - Multi-tier caching (in-memory, Redis, database)

    Example:
        builder = ContextBuilder(graphrag_client, supabase_client)
        context = await builder.build_context(
            client_id="client-123",
            case_id="case-456",
            scope="comprehensive"
        )
    """

    # Quality score threshold for completeness
    COMPLETENESS_THRESHOLD = 0.85

    # Scope definitions
    SCOPES = {
        'minimal': ['WHO', 'WHERE'],  # Basic parties and jurisdiction
        'standard': ['WHO', 'WHAT', 'WHERE', 'WHEN'],  # Add legal issues and timeline
        'comprehensive': ['WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY']  # Full context
    }

    def __init__(
        self,
        graphrag_client: GraphRAGClient,
        supabase_client: Any,
        cache_manager: Optional[CacheManager] = None
    ):
        """
        Initialize ContextBuilder with required service clients.

        Args:
            graphrag_client: Client for GraphRAG service queries
            supabase_client: Client for Supabase database queries
            cache_manager: Optional CacheManager instance (creates default if not provided)
        """
        self.graphrag_client = graphrag_client
        self.supabase_client = supabase_client

        # Initialize cache manager (in-memory only by default)
        self.cache_manager = cache_manager or create_cache_manager(
            supabase_client=supabase_client,
            enable_memory_cache=True,
            enable_redis_cache=False,  # TODO: Enable when Redis configured
            enable_db_cache=False  # TODO: Enable when context.cached_contexts table created
        )

        # Initialize dimension analyzers
        self.who_analyzer = WhoAnalyzer(graphrag_client, supabase_client)
        self.what_analyzer = WhatAnalyzer(graphrag_client, supabase_client)
        self.where_analyzer = WhereAnalyzer(graphrag_client, supabase_client)
        self.when_analyzer = WhenAnalyzer(graphrag_client, supabase_client)
        self.why_analyzer = WhyAnalyzer(graphrag_client, supabase_client)

        self.logger = logging.getLogger(__name__)

    async def build_context(
        self,
        client_id: str,
        case_id: str,
        scope: str = "comprehensive",
        include_dimensions: Optional[List[str]] = None,
        use_cache: bool = True
    ) -> ContextResponse:
        """
        Build complete multi-dimensional context for a specific case.

        This is the main entry point for context construction. It:
        1. Determines which dimensions to build based on scope
        2. Executes dimension analyzers in parallel
        3. Calculates overall context quality score
        4. Returns comprehensive ContextResponse

        Args:
            client_id: Client identifier for multi-tenant isolation
            case_id: Case identifier for case-scoped context (REQUIRED)
            scope: Context scope (minimal | standard | comprehensive)
            include_dimensions: Optional list of specific dimensions to build
                Override scope with explicit dimension list
            use_cache: Whether to use cached context if available

        Returns:
            ContextResponse with all requested dimensions populated

        Raises:
            ValueError: If invalid scope or dimension names provided

        Example:
            # Build comprehensive context
            context = await builder.build_context(
                client_id="client-abc",
                case_id="case-123",
                scope="comprehensive"
            )

            # Build specific dimensions only
            context = await builder.build_context(
                client_id="client-abc",
                case_id="case-123",
                include_dimensions=["WHO", "WHEN"]
            )
        """
        start_time = time.time()

        self.logger.info(
            f"Building {scope} context for case {case_id} (client: {client_id})"
        )

        # Check cache if enabled
        if use_cache:
            cached_context = await self._check_cache(client_id, case_id, scope)
            if cached_context:
                self.logger.info(f"Returning cached context for case {case_id}")
                cached_context.cached = True
                return cached_context

        # Determine which dimensions to build
        dimensions_to_build = self._determine_dimensions(scope, include_dimensions)

        self.logger.info(
            f"Building dimensions: {', '.join(dimensions_to_build)} for case {case_id}"
        )

        # Build dimensions in parallel
        dimension_results = await self._build_dimensions_parallel(
            client_id,
            case_id,
            dimensions_to_build
        )

        # Extract individual dimensions from results
        who_context = dimension_results.get('WHO')
        what_context = dimension_results.get('WHAT')
        where_context = dimension_results.get('WHERE')
        when_context = dimension_results.get('WHEN')
        why_context = dimension_results.get('WHY')

        # Calculate overall context quality score
        context_score = self._calculate_context_score(dimension_results)

        # Determine if context is complete (all dimensions meet threshold)
        is_complete = context_score >= self.COMPLETENESS_THRESHOLD

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Get case name (from any dimension that has it)
        case_name = self._get_case_name(dimension_results, case_id)

        # Build response
        context_response = ContextResponse(
            case_id=case_id,
            case_name=case_name,
            who=who_context,
            what=what_context,
            where=where_context,
            when=when_context,
            why=why_context,
            context_score=context_score,
            is_complete=is_complete,
            cached=False,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )

        # Cache the result if complete
        if is_complete and use_cache:
            await self._cache_context(client_id, case_id, scope, context_response)

        self.logger.info(
            f"Context building complete for case {case_id}: "
            f"score={context_score:.2f}, time={execution_time_ms}ms, "
            f"complete={is_complete}"
        )

        return context_response

    def _determine_dimensions(
        self,
        scope: str,
        include_dimensions: Optional[List[str]] = None
    ) -> List[str]:
        """
        Determine which dimensions to build based on scope or explicit list.

        Args:
            scope: Context scope (minimal | standard | comprehensive)
            include_dimensions: Optional explicit dimension list

        Returns:
            List of dimension names to build

        Raises:
            ValueError: If invalid scope or dimension names
        """
        # If explicit dimensions provided, use those
        if include_dimensions:
            # Validate dimension names
            valid_dimensions = {'WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY'}
            invalid = set(include_dimensions) - valid_dimensions
            if invalid:
                raise ValueError(
                    f"Invalid dimension names: {invalid}. "
                    f"Valid dimensions: {valid_dimensions}"
                )
            return include_dimensions

        # Otherwise use scope
        if scope not in self.SCOPES:
            raise ValueError(
                f"Invalid scope: {scope}. Valid scopes: {list(self.SCOPES.keys())}"
            )

        return self.SCOPES[scope]

    async def _build_dimensions_parallel(
        self,
        client_id: str,
        case_id: str,
        dimensions: List[str]
    ) -> Dict[str, Any]:
        """
        Build multiple dimensions in parallel for performance.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            dimensions: List of dimension names to build

        Returns:
            Dictionary mapping dimension names to their contexts
        """
        # Create tasks for each dimension
        tasks = {}

        if 'WHO' in dimensions:
            tasks['WHO'] = self.who_analyzer.analyze(client_id, case_id)

        if 'WHAT' in dimensions:
            tasks['WHAT'] = self.what_analyzer.analyze(client_id, case_id)

        if 'WHERE' in dimensions:
            tasks['WHERE'] = self.where_analyzer.analyze(client_id, case_id)

        if 'WHEN' in dimensions:
            tasks['WHEN'] = self.when_analyzer.analyze(client_id, case_id)

        if 'WHY' in dimensions:
            tasks['WHY'] = self.why_analyzer.analyze(client_id, case_id)

        # Execute all tasks in parallel
        results = {}
        completed_tasks = await asyncio.gather(
            *tasks.values(),
            return_exceptions=True
        )

        # Map results back to dimension names
        for dimension_name, result in zip(tasks.keys(), completed_tasks):
            if isinstance(result, Exception):
                self.logger.error(
                    f"Error building {dimension_name} dimension: {str(result)}",
                    exc_info=result
                )
                # Graceful degradation - set to None
                results[dimension_name] = None
            else:
                results[dimension_name] = result

        return results

    def _calculate_context_score(self, dimension_results: Dict[str, Any]) -> float:
        """
        Calculate overall context quality score.

        The score is based on:
        1. Number of dimensions successfully built
        2. Completeness of each dimension (data points)
        3. Confidence scores of extracted data

        Args:
            dimension_results: Dictionary of dimension contexts

        Returns:
            Overall quality score (0.0-1.0)
        """
        total_dimensions = len(dimension_results)
        if total_dimensions == 0:
            return 0.0

        # Count successfully built dimensions
        successful_dimensions = sum(
            1 for result in dimension_results.values()
            if result is not None
        )

        # Calculate dimension scores
        dimension_scores = []

        for dimension_name, context in dimension_results.items():
            if context is None:
                dimension_scores.append(0.0)
                continue

            # Calculate score based on data points in dimension
            score = self._score_dimension(dimension_name, context)
            dimension_scores.append(score)

        # Overall score is average of dimension scores
        avg_score = sum(dimension_scores) / len(dimension_scores)

        # Apply penalty for missing dimensions
        completeness_ratio = successful_dimensions / total_dimensions
        final_score = avg_score * completeness_ratio

        return min(1.0, max(0.0, final_score))

    def _score_dimension(self, dimension_name: str, context: Any) -> float:
        """
        Score individual dimension based on completeness.

        Args:
            dimension_name: Name of dimension (WHO, WHAT, etc.)
            context: Dimension context object

        Returns:
            Dimension score (0.0-1.0)
        """
        if context is None:
            return 0.0

        # WHO dimension scoring
        if dimension_name == 'WHO':
            data_points = (
                len(context.parties) +
                len(context.judges) +
                len(context.attorneys) +
                len(context.witnesses)
            )
            # Heuristic: 10+ data points = full score
            return min(1.0, data_points / 10.0)

        # WHAT dimension scoring
        elif dimension_name == 'WHAT':
            data_points = (
                len(context.causes_of_action) +
                len(context.legal_issues) +
                len(context.statutes) +
                len(context.case_citations)
            )
            return min(1.0, data_points / 10.0)

        # WHERE dimension scoring
        elif dimension_name == 'WHERE':
            # WHERE is complete if it has basic jurisdiction info
            has_jurisdiction = bool(context.primary_jurisdiction)
            has_court = bool(context.court)
            has_venue = bool(context.venue)
            return sum([has_jurisdiction, has_court, has_venue]) / 3.0

        # WHEN dimension scoring
        elif dimension_name == 'WHEN':
            data_points = (
                len(context.timeline) +
                len(context.upcoming_deadlines) +
                len(context.past_deadlines)
            )
            has_filing_date = bool(context.filing_date)
            time_score = min(1.0, data_points / 10.0)
            # Boost score if filing date is present
            return (time_score + (0.3 if has_filing_date else 0.0))

        # WHY dimension scoring
        elif dimension_name == 'WHY':
            data_points = (
                len(context.legal_theories) +
                len(context.supporting_precedents) +
                len(context.opposing_precedents)
            )
            return min(1.0, data_points / 10.0)

        return 0.5  # Default score

    def _get_case_name(
        self,
        dimension_results: Dict[str, Any],
        case_id: str
    ) -> str:
        """
        Extract case name from dimension results.

        Args:
            dimension_results: Dictionary of dimension contexts
            case_id: Fallback case ID

        Returns:
            Case name or formatted case ID
        """
        # Try to get case name from any dimension
        for context in dimension_results.values():
            if context and hasattr(context, 'case_name'):
                if context.case_name and context.case_name != f"Case {case_id}":
                    return context.case_name

        return f"Case {case_id}"

    async def _check_cache(
        self,
        client_id: str,
        case_id: str,
        scope: str
    ) -> Optional[ContextResponse]:
        """
        Check if cached context exists.

        Uses CacheManager to check:
        1. In-memory cache (10-minute TTL)
        2. Redis cache (1-hour TTL) - if enabled
        3. Database cache (persistent) - if enabled

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Context scope

        Returns:
            Cached ContextResponse if found, None otherwise
        """
        try:
            cached_data = await self.cache_manager.get(client_id, case_id, scope)
            if cached_data:
                # Reconstruct ContextResponse from cached dict
                return ContextResponse(**cached_data)
            return None
        except Exception as e:
            self.logger.warning(f"Cache retrieval failed: {str(e)}")
            return None

    async def _cache_context(
        self,
        client_id: str,
        case_id: str,
        scope: str,
        context: ContextResponse
    ) -> None:
        """
        Cache context for future retrieval.

        Uses CacheManager to store in:
        1. In-memory cache (fast access)
        2. Redis cache (shared across instances) - if enabled
        3. Database (persistent storage) - if enabled

        Args:
            client_id: Client identifier
            case_id: Case identifier
            scope: Context scope
            context: Context to cache
        """
        try:
            # Convert ContextResponse to dict for caching
            context_dict = context.model_dump()

            # Determine case status from context (if available)
            # Default to "active" if status not determinable
            case_status = "active"  # TODO: Get from case metadata in database

            await self.cache_manager.set(
                client_id=client_id,
                case_id=case_id,
                scope=scope,
                value=context_dict,
                case_status=case_status
            )
        except Exception as e:
            self.logger.warning(f"Cache storage failed: {str(e)}")

    async def get_dimension_quality(
        self,
        client_id: str,
        case_id: str,
        dimension_name: str
    ) -> DimensionQualityMetrics:
        """
        Get quality metrics for a specific dimension.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            dimension_name: Dimension name (WHO, WHAT, WHERE, WHEN, WHY)

        Returns:
            Quality metrics for dimension

        Raises:
            ValueError: If invalid dimension name
        """
        dimension_name = dimension_name.upper()
        valid_dimensions = {'WHO', 'WHAT', 'WHERE', 'WHEN', 'WHY'}

        if dimension_name not in valid_dimensions:
            raise ValueError(
                f"Invalid dimension: {dimension_name}. "
                f"Valid dimensions: {valid_dimensions}"
            )

        # Build the specific dimension
        analyzer_map = {
            'WHO': self.who_analyzer,
            'WHAT': self.what_analyzer,
            'WHERE': self.where_analyzer,
            'WHEN': self.when_analyzer,
            'WHY': self.why_analyzer
        }

        analyzer = analyzer_map[dimension_name]
        context = await analyzer.analyze(client_id, case_id)

        # Calculate quality metrics
        score = self._score_dimension(dimension_name, context)

        # Count data points
        data_points = self._count_data_points(dimension_name, context)

        return DimensionQualityMetrics(
            dimension_name=dimension_name,
            completeness_score=score,
            data_points=data_points,
            confidence_avg=0.9,  # Default high confidence
            is_sufficient=score >= self.COMPLETENESS_THRESHOLD
        )

    def _count_data_points(self, dimension_name: str, context: Any) -> int:
        """
        Count data points in a dimension context.

        Args:
            dimension_name: Dimension name
            context: Dimension context

        Returns:
            Number of data points
        """
        if context is None:
            return 0

        if dimension_name == 'WHO':
            return (
                len(context.parties) +
                len(context.judges) +
                len(context.attorneys) +
                len(context.witnesses)
            )
        elif dimension_name == 'WHAT':
            return (
                len(context.causes_of_action) +
                len(context.legal_issues) +
                len(context.statutes) +
                len(context.case_citations)
            )
        elif dimension_name == 'WHERE':
            return 3 if (context.primary_jurisdiction and context.court and context.venue) else 0
        elif dimension_name == 'WHEN':
            return (
                len(context.timeline) +
                len(context.upcoming_deadlines) +
                len(context.past_deadlines)
            )
        elif dimension_name == 'WHY':
            return (
                len(context.legal_theories) +
                len(context.supporting_precedents) +
                len(context.opposing_precedents)
            )

        return 0

    async def refresh_dimension(
        self,
        client_id: str,
        case_id: str,
        dimension_name: str
    ) -> Any:
        """
        Refresh a specific dimension (bypass cache).

        Useful for getting latest data after case updates.

        Args:
            client_id: Client identifier
            case_id: Case identifier
            dimension_name: Dimension to refresh

        Returns:
            Refreshed dimension context

        Raises:
            ValueError: If invalid dimension name
        """
        dimension_name = dimension_name.upper()
        analyzer_map = {
            'WHO': self.who_analyzer,
            'WHAT': self.what_analyzer,
            'WHERE': self.where_analyzer,
            'WHEN': self.when_analyzer,
            'WHY': self.why_analyzer
        }

        if dimension_name not in analyzer_map:
            raise ValueError(
                f"Invalid dimension: {dimension_name}. "
                f"Valid dimensions: {list(analyzer_map.keys())}"
            )

        analyzer = analyzer_map[dimension_name]
        return await analyzer.analyze(client_id, case_id)


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_context_builder(
    graphrag_client: GraphRAGClient,
    supabase_client: Any
) -> ContextBuilder:
    """
    Factory function to create ContextBuilder instance.

    Args:
        graphrag_client: GraphRAG service client
        supabase_client: Supabase database client

    Returns:
        Configured ContextBuilder instance

    Example:
        graphrag_client = GraphRAGClient(base_url="http://localhost:8010")
        supabase_client = create_supabase_client(service_name="context-engine")

        builder = create_context_builder(graphrag_client, supabase_client)
        context = await builder.build_context("client-123", "case-456")
    """
    return ContextBuilder(graphrag_client, supabase_client)
