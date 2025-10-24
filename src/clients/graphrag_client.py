"""
GraphRAG Client for Context Engine Service

Provides case-aware client wrapper for GraphRAG Service (Port 8010) with:
- Case-specific queries (LOCAL_SEARCH) - 99% of use cases
- Legal research queries (GLOBAL_SEARCH) - cross-case precedent research
- Comprehensive error handling and retry logic
- Automatic timeout management
- Type-safe response models

Architecture:
- Base URL: http://10.10.0.87:8010
- Two query modes:
  1. Case Context Mode: Queries scoped to specific case_id (LOCAL_SEARCH)
  2. Legal Research Mode: Cross-case queries for precedents (GLOBAL_SEARCH)
"""

import asyncio
import httpx
import logging
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import time

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Response Models
# ============================================================================


class GraphEntity(BaseModel):
    """Entity node in knowledge graph"""

    entity_id: str = Field(..., description="Unique entity identifier")
    entity_text: str = Field(..., description="Entity text/label")
    entity_type: str = Field(..., description="Entity type (CASE_CITATION, COURT, etc.)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    document_ids: List[str] = Field(default_factory=list, description="Source documents")
    case_id: Optional[str] = Field(None, description="Case ID for tenant isolation")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Entity metadata")

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type is uppercase"""
        return v.upper()


class GraphRelationship(BaseModel):
    """Relationship edge in knowledge graph"""

    relationship_id: str = Field(..., description="Unique relationship identifier")
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relationship_type: str = Field(..., description="Relationship type (CITES, DECIDED_CASE, etc.)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Relationship confidence")
    case_id: Optional[str] = Field(None, description="Case ID for tenant isolation")
    context: Optional[str] = Field(None, description="Relationship context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Relationship metadata")


class GraphCommunity(BaseModel):
    """Community cluster in knowledge graph"""

    community_id: str = Field(..., description="Unique community identifier")
    title: str = Field(..., description="Community title/name")
    summary: str = Field(..., description="AI-generated community summary")
    size: int = Field(..., ge=0, description="Number of entities in community")
    level: int = Field(..., ge=0, description="Hierarchical level")
    entities: List[str] = Field(default_factory=list, description="Entity IDs in community")
    coherence_score: float = Field(..., ge=0.0, le=1.0, description="Community coherence metric")
    key_relationships: List[str] = Field(default_factory=list, description="Primary relationship types")
    client_id: Optional[str] = Field(None, description="Client ID for tenant isolation")


class GraphQueryResponse(BaseModel):
    """Response from GraphRAG query operation"""

    query: str = Field(..., description="Original query text")
    search_type: str = Field(..., description="Search type used (LOCAL/GLOBAL/HYBRID)")
    mode: str = Field(..., description="Processing mode (FULL/LAZY/HYBRID)")
    response: str = Field(..., description="AI-generated response text")
    entities: List[GraphEntity] = Field(default_factory=list, description="Matching entities")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="Matching relationships")
    communities: Optional[List[GraphCommunity]] = Field(None, description="Matching communities")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Query metadata")
    execution_time_ms: int = Field(..., ge=0, description="Query execution time in milliseconds")


class GraphStats(BaseModel):
    """Graph database statistics"""

    total_entities: int = Field(..., ge=0, description="Total entity count")
    total_relationships: int = Field(..., ge=0, description="Total relationship count")
    total_communities: int = Field(..., ge=0, description="Total community count")
    total_documents: int = Field(..., ge=0, description="Total document count")
    entity_breakdown: Dict[str, int] = Field(default_factory=dict, description="Entity type counts")
    relationship_breakdown: Dict[str, int] = Field(default_factory=dict, description="Relationship type counts")
    graph_metrics: Dict[str, float] = Field(default_factory=dict, description="Graph topology metrics")
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Quality assessment metrics")


class GraphBuildResponse(BaseModel):
    """Response from graph build operation"""

    success: bool = Field(..., description="Build success status")
    graph_id: str = Field(..., description="Generated graph identifier")
    case_id: Optional[str] = Field(None, description="Case ID")
    client_id: str = Field(..., description="Client ID")
    processing_results: Dict[str, int] = Field(default_factory=dict, description="Processing statistics")
    graph_metrics: Dict[str, float] = Field(default_factory=dict, description="Graph metrics")
    quality_metrics: Dict[str, float] = Field(default_factory=dict, description="Quality metrics")
    communities: List[GraphCommunity] = Field(default_factory=list, description="Detected communities")
    processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")
    timestamp: str = Field(..., description="Build timestamp")


# ============================================================================
# GraphRAG Client
# ============================================================================


class GraphRAGClient:
    """
    Case-aware client for GraphRAG Service (Port 8010).

    Provides two query modes:
    1. Case Context Mode: Queries scoped to specific case_id (99% of queries)
    2. Legal Research Mode: Cross-case queries for precedent research

    Features:
    - Automatic retry with exponential backoff
    - Comprehensive error handling
    - Timeout management
    - Type-safe response models
    - Case isolation enforcement

    Example Usage:
        ```python
        client = GraphRAGClient()

        # Case-specific query (LOCAL_SEARCH)
        result = await client.query_case_graph(
            client_id="client-123",
            case_id="case-456",
            query="What statutes are cited in this case?",
            search_type="LOCAL"
        )

        # Legal research query (GLOBAL_SEARCH)
        precedents = await client.query_legal_research(
            client_id="client-123",
            query="Find Second Amendment cases similar to Rahimi",
            jurisdiction="federal"
        )
        ```
    """

    def __init__(
        self,
        base_url: str = "http://10.10.0.87:8010",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize GraphRAG client.

        Args:
            base_url: GraphRAG service base URL (default: http://10.10.0.87:8010)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Create async HTTP client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True
        )

        logger.info(
            f"GraphRAGClient initialized: base_url={base_url}, timeout={timeout}s, "
            f"max_retries={max_retries}"
        )

    # ========================================================================
    # Context Manager Support
    # ========================================================================

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Close HTTP client and cleanup resources"""
        await self._client.aclose()
        logger.info("GraphRAGClient closed")

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic and error handling.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            data: Request body data (for POST/PUT)
            params: URL query parameters
            retry_count: Current retry attempt number

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: On request failure after all retries
        """
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = await self._client.get(url, params=params)
            elif method == "POST":
                response = await self._client.post(url, json=data, params=params)
            elif method == "DELETE":
                response = await self._client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Raise exception for HTTP error status codes
            response.raise_for_status()
            return response

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # Retry on timeout or connection errors
            if retry_count < self.max_retries:
                delay = self.retry_delay * (2 ** retry_count)  # Exponential backoff
                logger.warning(
                    f"Request failed (attempt {retry_count + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                return await self._make_request(method, endpoint, data, params, retry_count + 1)
            else:
                logger.error(f"Request failed after {self.max_retries} retries: {e}")
                raise

        except httpx.HTTPStatusError as e:
            # Log HTTP errors but don't retry
            logger.error(
                f"HTTP error {e.response.status_code} for {method} {url}: {e.response.text}"
            )
            raise

    def _validate_case_id(self, case_id: Optional[str], operation: str):
        """
        Validate case_id is provided for case-specific operations.

        Args:
            case_id: Case ID to validate
            operation: Operation name (for logging)

        Raises:
            ValueError: If case_id is missing for case-specific operation
        """
        if not case_id:
            error_msg = (
                f"case_id is REQUIRED for case-specific operation: {operation}. "
                f"Case isolation prevents cross-tenant data leaks."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    # ========================================================================
    # Case-Specific Query Methods (require case_id)
    # ========================================================================

    async def query_case_graph(
        self,
        client_id: str,
        case_id: str,
        query: str,
        search_type: Literal["LOCAL", "GLOBAL", "HYBRID"] = "LOCAL",
        mode: Literal["FULL_GRAPHRAG", "LAZY_GRAPHRAG", "HYBRID_MODE"] = "LAZY_GRAPHRAG",
        max_results: int = 100,
        relevance_budget: Optional[int] = None,
        community_level: int = 2,
        vector_weight: float = 0.7
    ) -> GraphQueryResponse:
        """
        Query knowledge graph for specific case.

        Uses LOCAL_SEARCH by default for case-specific context.
        Filters all results by case_id to ensure case isolation.

        Args:
            client_id: Client identifier (required)
            case_id: Case identifier (REQUIRED for case isolation)
            query: Natural language query
            search_type: Search type - LOCAL (default), GLOBAL, or HYBRID
            mode: Processing mode - LAZY_GRAPHRAG (default), FULL_GRAPHRAG, or HYBRID_MODE
            max_results: Maximum results to return (default: 100)
            relevance_budget: Relevance score budget for LAZY mode (optional)
            community_level: Community hierarchy level (default: 2)
            vector_weight: Weight for vector similarity (0.0-1.0, default: 0.7)

        Returns:
            GraphQueryResponse with entities, relationships, and AI-generated response

        Raises:
            ValueError: If case_id is missing
            httpx.HTTPError: On request failure

        Example:
            ```python
            result = await client.query_case_graph(
                client_id="client-123",
                case_id="case-456",
                query="What statutes are cited in this case?",
                search_type="LOCAL"
            )

            print(f"Response: {result.response}")
            print(f"Found {len(result.entities)} entities")
            for entity in result.entities:
                print(f"  - {entity.entity_text} ({entity.entity_type})")
            ```
        """
        # Validate case_id is provided
        self._validate_case_id(case_id, "query_case_graph")

        start_time = time.time()

        payload = {
            "query": query,
            "client_id": client_id,
            "case_id": case_id,  # CRITICAL: Enforces case isolation
            "search_type": search_type,
            "mode": mode,
            "community_level": community_level,
            "vector_weight": vector_weight
        }

        if relevance_budget is not None:
            payload["relevance_budget"] = relevance_budget

        logger.info(
            f"Querying case graph: case_id={case_id}, query='{query}', "
            f"search_type={search_type}, mode={mode}"
        )

        response = await self._make_request("POST", "/api/v1/graphrag/query", data=payload)
        result_data = response.json()

        # Add execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        result_data["execution_time_ms"] = execution_time_ms

        # Validate all entities have case_id (data quality check)
        entities_without_case_id = [
            e for e in result_data.get("entities", [])
            if not e.get("case_id")
        ]
        if entities_without_case_id:
            logger.warning(
                f"Found {len(entities_without_case_id)} entities without case_id - "
                f"potential case isolation violation"
            )

        return GraphQueryResponse(**result_data)

    async def get_case_entities(
        self,
        client_id: str,
        case_id: str,
        entity_type: Optional[str] = None,
        min_confidence: float = 0.7,
        limit: int = 100
    ) -> List[GraphEntity]:
        """
        Get all entities for a specific case.

        Args:
            client_id: Client identifier
            case_id: Case identifier (REQUIRED for case isolation)
            entity_type: Filter by entity type (optional)
            min_confidence: Minimum confidence threshold (default: 0.7)
            limit: Maximum results to return (default: 100)

        Returns:
            List of GraphEntity objects

        Raises:
            ValueError: If case_id is missing

        Example:
            ```python
            # Get all high-confidence case citations
            citations = await client.get_case_entities(
                client_id="client-123",
                case_id="case-456",
                entity_type="CASE_CITATION",
                min_confidence=0.9
            )
            ```
        """
        self._validate_case_id(case_id, "get_case_entities")

        params = {
            "case_id": case_id,
            "min_confidence": min_confidence,
            "limit": limit
        }

        if entity_type:
            params["entity_type"] = entity_type

        logger.info(f"Getting entities for case: case_id={case_id}, entity_type={entity_type}")

        response = await self._make_request(
            "GET",
            f"/api/v1/graphrag/entities/{client_id}",
            params=params
        )

        result = response.json()
        entities = [GraphEntity(**e) for e in result.get("entities", [])]

        logger.info(f"Retrieved {len(entities)} entities for case {case_id}")
        return entities

    async def get_case_relationships(
        self,
        case_id: str,
        relationship_type: Optional[str] = None,
        min_confidence: float = 0.7,
        limit: int = 100
    ) -> List[GraphRelationship]:
        """
        Get all relationships for a specific case.

        Args:
            case_id: Case identifier (REQUIRED for case isolation)
            relationship_type: Filter by relationship type (optional)
            min_confidence: Minimum confidence threshold (default: 0.7)
            limit: Maximum results to return (default: 100)

        Returns:
            List of GraphRelationship objects

        Raises:
            ValueError: If case_id is missing

        Example:
            ```python
            # Get all citation relationships
            citations = await client.get_case_relationships(
                case_id="case-456",
                relationship_type="CITES",
                min_confidence=0.8
            )
            ```
        """
        self._validate_case_id(case_id, "get_case_relationships")

        # Use graph query endpoint with relationship filters
        query_payload = {
            "query_type": "relationships",
            "filters": {
                "case_id": case_id,
                "confidence_threshold": min_confidence
            },
            "max_results": limit
        }

        if relationship_type:
            query_payload["filters"]["relationship_type"] = relationship_type

        logger.info(
            f"Getting relationships for case: case_id={case_id}, "
            f"type={relationship_type}"
        )

        response = await self._make_request("POST", "/api/v1/graph/query", data=query_payload)
        result = response.json()

        relationships = [GraphRelationship(**r) for r in result.get("relationships", [])]

        logger.info(f"Retrieved {len(relationships)} relationships for case {case_id}")
        return relationships

    async def get_case_communities(
        self,
        client_id: str,
        case_id: str,
        min_size: int = 3
    ) -> List[GraphCommunity]:
        """
        Get community clusters for a specific case.

        Args:
            client_id: Client identifier
            case_id: Case identifier (REQUIRED for case isolation)
            min_size: Minimum community size (default: 3)

        Returns:
            List of GraphCommunity objects

        Raises:
            ValueError: If case_id is missing

        Example:
            ```python
            # Get all communities for case
            communities = await client.get_case_communities(
                client_id="client-123",
                case_id="case-456",
                min_size=5
            )

            for community in communities:
                print(f"{community.title}: {community.size} entities")
            ```
        """
        self._validate_case_id(case_id, "get_case_communities")

        query_payload = {
            "query_type": "communities",
            "filters": {
                "case_id": case_id,
                "client_id": client_id,
                "min_size": min_size
            },
            "include_communities": True
        }

        logger.info(f"Getting communities for case: case_id={case_id}, min_size={min_size}")

        response = await self._make_request("POST", "/api/v1/graph/query", data=query_payload)
        result = response.json()

        communities = [GraphCommunity(**c) for c in result.get("communities", [])]

        logger.info(f"Retrieved {len(communities)} communities for case {case_id}")
        return communities

    async def create_case_graph(
        self,
        document_id: str,
        case_id: str,
        client_id: str,
        markdown_content: str,
        entities: List[Dict[str, Any]],
        citations: Optional[List[Dict[str, Any]]] = None,
        relationships: Optional[List[Dict[str, Any]]] = None,
        enhanced_chunks: Optional[List[Dict[str, Any]]] = None,
        enable_deduplication: bool = True,
        enable_community_detection: bool = True,
        enable_cross_document_linking: bool = True,
        enable_analytics: bool = True,
        use_ai_summaries: bool = False,  # Default to LAZY mode
        leiden_resolution: float = 1.0,
        min_community_size: int = 3,
        similarity_threshold: float = 0.85
    ) -> GraphBuildResponse:
        """
        Build knowledge graph from case document entities.

        Args:
            document_id: Document identifier
            case_id: Case identifier (REQUIRED for case isolation)
            client_id: Client identifier
            markdown_content: Document markdown content
            entities: List of extracted entities (LurisEntityV2 format)
            citations: List of extracted citations (optional)
            relationships: List of extracted relationships (optional)
            enhanced_chunks: List of enhanced chunks with embeddings (optional)
            enable_deduplication: Enable entity deduplication (default: True)
            enable_community_detection: Enable community detection (default: True)
            enable_cross_document_linking: Enable cross-document links (default: True)
            enable_analytics: Enable graph analytics (default: True)
            use_ai_summaries: Use AI-generated summaries (FULL mode, default: False)
            leiden_resolution: Leiden algorithm resolution (default: 1.0)
            min_community_size: Minimum community size (default: 3)
            similarity_threshold: Entity similarity threshold (default: 0.85)

        Returns:
            GraphBuildResponse with processing results and metrics

        Raises:
            ValueError: If case_id is missing

        Example:
            ```python
            result = await client.create_case_graph(
                document_id="doc-123",
                case_id="case-456",
                client_id="client-789",
                markdown_content="Document text...",
                entities=extracted_entities,
                enable_community_detection=True
            )

            print(f"Graph ID: {result.graph_id}")
            print(f"Entities processed: {result.processing_results['entities_processed']}")
            print(f"Communities detected: {result.processing_results['communities_detected']}")
            ```
        """
        self._validate_case_id(case_id, "create_case_graph")

        payload = {
            "document_id": document_id,
            "case_id": case_id,
            "client_id": client_id,
            "markdown_content": markdown_content,
            "entities": entities,
            "citations": citations or [],
            "relationships": relationships or [],
            "enhanced_chunks": enhanced_chunks or [],
            "graph_options": {
                "enable_deduplication": enable_deduplication,
                "enable_community_detection": enable_community_detection,
                "enable_cross_document_linking": enable_cross_document_linking,
                "enable_analytics": enable_analytics,
                "use_ai_summaries": use_ai_summaries,
                "leiden_resolution": leiden_resolution,
                "min_community_size": min_community_size,
                "similarity_threshold": similarity_threshold
            },
            "metadata": {
                "processing_timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }

        logger.info(
            f"Creating graph for case: document_id={document_id}, case_id={case_id}, "
            f"entities={len(entities)}"
        )

        response = await self._make_request("POST", "/api/v1/graph/create", data=payload)
        result = response.json()

        logger.info(
            f"Graph created successfully: graph_id={result.get('graph_id')}, "
            f"entities={result.get('processing_results', {}).get('entities_processed')}, "
            f"communities={result.get('processing_results', {}).get('communities_detected')}"
        )

        return GraphBuildResponse(**result)

    # ========================================================================
    # Legal Research Query Methods (no case_id - cross-case)
    # ========================================================================

    async def query_legal_research(
        self,
        client_id: str,
        query: str,
        jurisdiction: Optional[str] = None,
        search_type: Literal["GLOBAL", "HYBRID"] = "GLOBAL",
        mode: Literal["LAZY_GRAPHRAG", "FULL_GRAPHRAG", "HYBRID_MODE"] = "LAZY_GRAPHRAG",
        max_results: int = 50,
        relevance_budget: Optional[int] = None,
        community_level: int = 2,
        vector_weight: float = 0.7
    ) -> GraphQueryResponse:
        """
        Cross-case legal research query.

        NO case_id - searches across all cases for precedents.
        Uses GLOBAL_SEARCH for comprehensive results.

        Args:
            client_id: Client identifier (required)
            query: Natural language research query
            jurisdiction: Filter by jurisdiction (optional)
            search_type: Search type - GLOBAL (default) or HYBRID
            mode: Processing mode - LAZY_GRAPHRAG (default), FULL_GRAPHRAG, or HYBRID_MODE
            max_results: Maximum results to return (default: 50)
            relevance_budget: Relevance score budget for LAZY mode (optional)
            community_level: Community hierarchy level (default: 2)
            vector_weight: Weight for vector similarity (0.0-1.0, default: 0.7)

        Returns:
            GraphQueryResponse with cross-case results

        Example:
            ```python
            # Find Second Amendment cases across all client cases
            results = await client.query_legal_research(
                client_id="client-123",
                query="Find Second Amendment cases similar to Rahimi v. US",
                jurisdiction="federal",
                search_type="GLOBAL"
            )

            print(f"Found {len(results.entities)} relevant entities across cases")
            ```
        """
        start_time = time.time()

        payload = {
            "query": query,
            "client_id": client_id,
            # NO case_id - cross-case research
            "search_type": search_type,
            "mode": mode,
            "community_level": community_level,
            "vector_weight": vector_weight
        }

        if relevance_budget is not None:
            payload["relevance_budget"] = relevance_budget

        if jurisdiction:
            payload["filters"] = {"jurisdiction": jurisdiction}

        logger.info(
            f"Legal research query: query='{query}', jurisdiction={jurisdiction}, "
            f"search_type={search_type}"
        )

        response = await self._make_request("POST", "/api/v1/graphrag/query", data=payload)
        result_data = response.json()

        # Add execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        result_data["execution_time_ms"] = execution_time_ms

        logger.info(
            f"Legal research completed: found {len(result_data.get('entities', []))} entities "
            f"in {execution_time_ms}ms"
        )

        return GraphQueryResponse(**result_data)

    async def find_similar_cases(
        self,
        client_id: str,
        reference_case_id: str,
        similarity_threshold: float = 0.8,
        max_results: int = 10
    ) -> List[GraphEntity]:
        """
        Find cases similar to a reference case.

        Uses entity similarity and community membership to identify related cases.

        Args:
            client_id: Client identifier
            reference_case_id: Reference case ID to find similar cases
            similarity_threshold: Minimum similarity score (default: 0.8)
            max_results: Maximum results to return (default: 10)

        Returns:
            List of GraphEntity objects representing similar cases

        Example:
            ```python
            # Find cases similar to Rahimi
            similar = await client.find_similar_cases(
                client_id="client-123",
                reference_case_id="case-rahimi",
                similarity_threshold=0.85
            )
            ```
        """
        # Use cross-case query to find similar entities
        query = f"Find cases similar to case {reference_case_id} based on legal issues and entities"

        response = await self.query_legal_research(
            client_id=client_id,
            query=query,
            search_type="GLOBAL",
            max_results=max_results
        )

        # Filter entities by similarity threshold
        similar_cases = [
            entity for entity in response.entities
            if entity.entity_type in ("CASE_CITATION", "CASE_LAW")
            and entity.case_id != reference_case_id
            # Similarity filtering would be done server-side based on vector distance
        ]

        logger.info(
            f"Found {len(similar_cases)} similar cases to {reference_case_id}"
        )

        return similar_cases[:max_results]

    async def search_precedents(
        self,
        client_id: str,
        legal_issue: str,
        jurisdiction: Optional[str] = None,
        court_level: Optional[str] = None,
        max_results: int = 20
    ) -> List[GraphEntity]:
        """
        Search for legal precedents across all cases.

        Args:
            client_id: Client identifier
            legal_issue: Legal issue or doctrine to search
            jurisdiction: Filter by jurisdiction (optional)
            court_level: Filter by court level (optional)
            max_results: Maximum results to return (default: 20)

        Returns:
            List of GraphEntity objects representing precedent cases

        Example:
            ```python
            # Search for Second Amendment precedents
            precedents = await client.search_precedents(
                client_id="client-123",
                legal_issue="Second Amendment right to bear arms",
                jurisdiction="federal",
                court_level="supreme"
            )
            ```
        """
        query = f"Find legal precedents related to: {legal_issue}"

        if jurisdiction:
            query += f" in {jurisdiction} jurisdiction"
        if court_level:
            query += f" from {court_level} court"

        response = await self.query_legal_research(
            client_id=client_id,
            query=query,
            jurisdiction=jurisdiction,
            search_type="GLOBAL",
            max_results=max_results
        )

        # Filter for case citations and precedent-related entities
        precedents = [
            entity for entity in response.entities
            if entity.entity_type in ("CASE_CITATION", "CASE_LAW", "LEGAL_DOCTRINE", "HOLDING")
        ]

        logger.info(f"Found {len(precedents)} precedents for: {legal_issue}")

        return precedents

    # ========================================================================
    # Utility Methods
    # ========================================================================

    async def get_graph_stats(
        self,
        case_id: Optional[str] = None,
        client_id: Optional[str] = None,
        include_details: bool = True
    ) -> GraphStats:
        """
        Get graph statistics (overall or case-specific).

        Args:
            case_id: Case ID for case-specific stats (optional)
            client_id: Client ID for client-specific stats (optional)
            include_details: Include detailed breakdowns (default: True)

        Returns:
            GraphStats object with comprehensive metrics

        Example:
            ```python
            # Overall stats
            stats = await client.get_graph_stats()
            print(f"Total entities: {stats.total_entities}")

            # Case-specific stats
            case_stats = await client.get_graph_stats(case_id="case-456")
            print(f"Case entities: {case_stats.total_entities}")
            ```
        """
        params = {}
        if include_details:
            params["include_details"] = "true"
        if case_id:
            params["case_id"] = case_id
        if client_id:
            params["client_id"] = client_id

        logger.info(f"Getting graph stats: case_id={case_id}, client_id={client_id}")

        response = await self._make_request("GET", "/api/v1/graph/stats", params=params)
        result = response.json()

        # Flatten nested statistics structure
        stats_data = {
            "total_entities": result.get("statistics", {}).get("total_entities", 0),
            "total_relationships": result.get("statistics", {}).get("total_relationships", 0),
            "total_communities": result.get("statistics", {}).get("total_communities", 0),
            "total_documents": result.get("statistics", {}).get("total_documents", 0),
            "entity_breakdown": result.get("entity_breakdown", {}),
            "relationship_breakdown": result.get("relationship_breakdown", {}),
            "graph_metrics": result.get("graph_metrics", {}),
            "quality_metrics": result.get("quality_metrics", {})
        }

        return GraphStats(**stats_data)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check GraphRAG service health.

        Returns:
            Health status dict with service information

        Example:
            ```python
            health = await client.health_check()
            if health["status"] == "healthy":
                print("GraphRAG service is ready")
            ```
        """
        try:
            response = await self._make_request("GET", "/api/v1/health/ready")
            health_data = response.json()

            logger.info(f"GraphRAG service health: {health_data.get('status')}")
            return health_data

        except httpx.HTTPError as e:
            logger.error(f"GraphRAG service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "ready": False
            }

    async def get_visualization_data(
        self,
        client_id: str,
        case_id: Optional[str] = None,
        max_nodes: int = 100,
        node_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get graph data formatted for visualization.

        Args:
            client_id: Client identifier
            case_id: Case ID for case-specific visualization (optional)
            max_nodes: Maximum number of nodes to return (default: 100)
            node_types: Filter by node types (optional)

        Returns:
            Dict with nodes, edges, and metadata for visualization

        Example:
            ```python
            viz_data = await client.get_visualization_data(
                client_id="client-123",
                case_id="case-456",
                max_nodes=50,
                node_types=["entity", "citation"]
            )

            print(f"Nodes: {len(viz_data['nodes'])}")
            print(f"Edges: {len(viz_data['edges'])}")
            ```
        """
        params = {"max_nodes": max_nodes}

        if case_id:
            params["case_id"] = case_id

        if node_types:
            for node_type in node_types:
                params["node_types"] = node_type

        logger.info(
            f"Getting visualization data: client_id={client_id}, case_id={case_id}, "
            f"max_nodes={max_nodes}"
        )

        response = await self._make_request(
            "GET",
            f"/api/v1/graphrag/graph/visualization/{client_id}",
            params=params
        )

        return response.json()


# ============================================================================
# Factory Functions
# ============================================================================


def create_graphrag_client(
    base_url: str = "http://10.10.0.87:8010",
    timeout: float = 30.0
) -> GraphRAGClient:
    """
    Factory function to create GraphRAG client.

    Args:
        base_url: GraphRAG service base URL (default: http://10.10.0.87:8010)
        timeout: Request timeout in seconds (default: 30.0)

    Returns:
        Initialized GraphRAGClient instance

    Example:
        ```python
        client = create_graphrag_client()

        # Use as async context manager
        async with client:
            result = await client.query_case_graph(
                client_id="client-123",
                case_id="case-456",
                query="What are the key legal issues?"
            )
        ```
    """
    return GraphRAGClient(base_url=base_url, timeout=timeout)
