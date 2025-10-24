"""
Context API Routes - Core Context Retrieval Endpoints

Provides endpoints for building and retrieving multi-dimensional case context.
All endpoints require case_id for case-centric context construction.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from src.core.context_builder import ContextBuilder, create_context_builder
from src.clients.graphrag_client import create_graphrag_client
from src.clients.supabase_client import create_supabase_client
from src.models.dimensions import ContextResponse, DimensionQualityMetrics

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize service clients (singleton pattern)
_graphrag_client = None
_supabase_client = None
_context_builder = None

def get_context_builder() -> ContextBuilder:
    """Get or create ContextBuilder instance"""
    global _graphrag_client, _supabase_client, _context_builder

    if _context_builder is None:
        logger.info("Initializing Context Builder...")

        # Create service clients
        _graphrag_client = create_graphrag_client(base_url="http://10.10.0.87:8010")
        _supabase_client = create_supabase_client(service_name="context-engine")

        # Create context builder
        _context_builder = create_context_builder(
            graphrag_client=_graphrag_client,
            supabase_client=_supabase_client
        )

        logger.info("Context Builder initialized successfully")

    return _context_builder


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ContextRetrievalRequest(BaseModel):
    """Request model for context retrieval"""
    client_id: str = Field(..., description="Client identifier for multi-tenant isolation")
    case_id: str = Field(..., description="Case identifier (REQUIRED for case-centric context)")
    scope: str = Field(
        default="comprehensive",
        description="Context scope: minimal (WHO/WHERE), standard (WHO/WHAT/WHERE/WHEN), comprehensive (all 5 dimensions)"
    )
    include_dimensions: Optional[List[str]] = Field(
        default=None,
        description="Optional explicit dimension list (overrides scope): WHO, WHAT, WHERE, WHEN, WHY"
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to use cached context if available"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client-abc-123",
                "case_id": "case-xyz-456",
                "scope": "comprehensive",
                "use_cache": True
            }
        }


class DimensionRequest(BaseModel):
    """Request model for single dimension retrieval"""
    client_id: str = Field(..., description="Client identifier")
    case_id: str = Field(..., description="Case identifier")
    dimension: str = Field(
        ...,
        description="Dimension name: WHO, WHAT, WHERE, WHEN, or WHY"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client-abc-123",
                "case_id": "case-xyz-456",
                "dimension": "WHO"
            }
        }


# ============================================================================
# CORE CONTEXT ENDPOINTS
# ============================================================================

@router.post("/retrieve", response_model=ContextResponse)
async def retrieve_context(request: ContextRetrievalRequest = Body(...)):
    """
    Retrieve multi-dimensional context for a specific case.

    This is the primary endpoint for context retrieval. It builds comprehensive
    case context using the WHO/WHAT/WHERE/WHEN/WHY framework.

    **Context Scopes:**
    - `minimal`: WHO + WHERE (parties, jurisdiction) - fastest, <100ms
    - `standard`: WHO + WHAT + WHERE + WHEN (adds legal issues, timeline) - 100-500ms
    - `comprehensive`: All 5 dimensions including WHY (precedents, reasoning) - 500-2000ms

    **Caching:**
    - Active cases: 1 hour TTL
    - Closed cases: 24 hour TTL
    - In-memory cache: 10 minute TTL

    **Example Request:**
    ```json
    {
        "client_id": "client-abc-123",
        "case_id": "case-xyz-456",
        "scope": "comprehensive",
        "use_cache": true
    }
    ```

    **Example Response:**
    ```json
    {
        "case_id": "case-xyz-456",
        "case_name": "Smith v. Jones",
        "who": {
            "parties": [...],
            "judges": [...],
            "attorneys": [...]
        },
        "what": {
            "causes_of_action": [...],
            "statutes": [...],
            "case_citations": [...]
        },
        "where": {
            "primary_jurisdiction": "federal",
            "court": "U.S. District Court",
            "venue": "Northern District of California"
        },
        "when": {
            "filing_date": "2024-01-15",
            "upcoming_deadlines": [...],
            "case_age_days": 120
        },
        "why": {
            "legal_theories": [...],
            "supporting_precedents": [...],
            "argument_strength": 0.75
        },
        "context_score": 0.92,
        "is_complete": true,
        "cached": false,
        "execution_time_ms": 850
    }
    ```
    """
    try:
        logger.info(
            f"Context retrieval request: case={request.case_id}, "
            f"scope={request.scope}, cache={request.use_cache}"
        )

        # Get context builder
        builder = get_context_builder()

        # Build context
        context = await builder.build_context(
            client_id=request.client_id,
            case_id=request.case_id,
            scope=request.scope,
            include_dimensions=request.include_dimensions,
            use_cache=request.use_cache
        )

        logger.info(
            f"Context built successfully: case={request.case_id}, "
            f"score={context.context_score:.2f}, "
            f"time={context.execution_time_ms}ms, "
            f"cached={context.cached}"
        )

        return context

    except ValueError as e:
        logger.error(f"Invalid request parameters: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Context retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Context retrieval failed: {str(e)}")


@router.get("/retrieve", response_model=ContextResponse)
async def retrieve_context_get(
    client_id: str = Query(..., description="Client identifier"),
    case_id: str = Query(..., description="Case identifier"),
    scope: str = Query(
        default="comprehensive",
        description="Context scope: minimal, standard, comprehensive"
    ),
    use_cache: bool = Query(
        default=True,
        description="Whether to use cached context"
    )
):
    """
    Retrieve context using GET method (convenience endpoint).

    Same functionality as POST /retrieve but using query parameters.
    Useful for simple requests without request body.

    **Example:**
    ```
    GET /api/v1/context/retrieve?client_id=client-123&case_id=case-456&scope=standard
    ```
    """
    # Convert to request model and delegate to POST handler
    request = ContextRetrievalRequest(
        client_id=client_id,
        case_id=case_id,
        scope=scope,
        use_cache=use_cache
    )
    return await retrieve_context(request)


# ============================================================================
# DIMENSION-SPECIFIC ENDPOINTS
# ============================================================================

@router.post("/dimension/retrieve")
async def retrieve_dimension(request: DimensionRequest = Body(...)):
    """
    Retrieve a specific dimension for a case.

    Use this endpoint when you only need one dimension (e.g., just WHO or WHAT).
    Faster than retrieving full context if you don't need all dimensions.

    **Supported Dimensions:**
    - `WHO`: Parties, judges, attorneys, witnesses
    - `WHAT`: Legal issues, causes of action, citations
    - `WHERE`: Jurisdiction, court, venue
    - `WHEN`: Timeline, deadlines, dates
    - `WHY`: Legal theories, precedents, argument analysis

    **Example Request:**
    ```json
    {
        "client_id": "client-abc-123",
        "case_id": "case-xyz-456",
        "dimension": "WHO"
    }
    ```
    """
    try:
        logger.info(
            f"Dimension retrieval: case={request.case_id}, dimension={request.dimension}"
        )

        # Validate dimension name
        valid_dimensions = {"WHO", "WHAT", "WHERE", "WHEN", "WHY"}
        dimension_upper = request.dimension.upper()

        if dimension_upper not in valid_dimensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dimension: {request.dimension}. "
                       f"Valid dimensions: {valid_dimensions}"
            )

        # Get context builder
        builder = get_context_builder()

        # Refresh specific dimension (bypass cache)
        dimension_context = await builder.refresh_dimension(
            client_id=request.client_id,
            case_id=request.case_id,
            dimension_name=dimension_upper
        )

        logger.info(f"Dimension retrieved: {dimension_upper} for case {request.case_id}")

        return {
            "case_id": request.case_id,
            "dimension": dimension_upper,
            "data": dimension_context
        }

    except ValueError as e:
        logger.error(f"Invalid dimension request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Dimension retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dimension retrieval failed: {str(e)}")


@router.get("/dimension/quality")
async def get_dimension_quality(
    client_id: str = Query(..., description="Client identifier"),
    case_id: str = Query(..., description="Case identifier"),
    dimension: str = Query(..., description="Dimension name (WHO/WHAT/WHERE/WHEN/WHY)")
):
    """
    Get quality metrics for a specific dimension.

    Returns completeness score, data point count, and sufficiency indicator.

    **Example:**
    ```
    GET /api/v1/context/dimension/quality?client_id=client-123&case_id=case-456&dimension=WHO
    ```

    **Example Response:**
    ```json
    {
        "dimension_name": "WHO",
        "completeness_score": 0.87,
        "data_points": 12,
        "confidence_avg": 0.91,
        "is_sufficient": true
    }
    ```
    """
    try:
        logger.info(f"Quality check: case={case_id}, dimension={dimension}")

        # Get context builder
        builder = get_context_builder()

        # Get quality metrics
        quality = await builder.get_dimension_quality(
            client_id=client_id,
            case_id=case_id,
            dimension_name=dimension
        )

        return quality

    except ValueError as e:
        logger.error(f"Invalid quality request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Quality check failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quality check failed: {str(e)}")


# ============================================================================
# CONTEXT REFRESH
# ============================================================================

@router.post("/refresh")
async def refresh_context(
    client_id: str = Query(..., description="Client identifier"),
    case_id: str = Query(..., description="Case identifier"),
    scope: str = Query(
        default="comprehensive",
        description="Context scope to refresh"
    )
):
    """
    Force refresh of case context (bypass cache).

    Use this after case data has been updated to regenerate context
    with latest information.

    **Example:**
    ```
    POST /api/v1/context/refresh?client_id=client-123&case_id=case-456&scope=comprehensive
    ```
    """
    try:
        logger.info(f"Context refresh: case={case_id}, scope={scope}")

        # Build request with cache disabled
        request = ContextRetrievalRequest(
            client_id=client_id,
            case_id=case_id,
            scope=scope,
            use_cache=False  # Force rebuild
        )

        # Build context (will invalidate and rebuild cache)
        context = await retrieve_context(request)

        logger.info(f"Context refreshed: case={case_id}, new_score={context.context_score:.2f}")

        return {
            "message": "Context refreshed successfully",
            "case_id": case_id,
            "scope": scope,
            "new_context_score": context.context_score,
            "execution_time_ms": context.execution_time_ms
        }

    except Exception as e:
        logger.error(f"Context refresh failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Context refresh failed: {str(e)}")


# ============================================================================
# BATCH OPERATIONS
# ============================================================================

class BatchContextRequest(BaseModel):
    """Request model for batch context retrieval"""
    client_id: str = Field(..., description="Client identifier")
    case_ids: List[str] = Field(..., description="List of case IDs to retrieve context for")
    scope: str = Field(default="standard", description="Context scope for all cases")
    use_cache: bool = Field(default=True, description="Whether to use cached contexts")

    class Config:
        json_schema_extra = {
            "example": {
                "client_id": "client-abc-123",
                "case_ids": ["case-1", "case-2", "case-3"],
                "scope": "standard",
                "use_cache": True
            }
        }


@router.post("/batch/retrieve")
async def batch_retrieve_context(request: BatchContextRequest = Body(...)):
    """
    Retrieve context for multiple cases in a single request.

    **Note:** For large batch sizes (>10 cases), this may take significant time.
    Consider using async task queue for very large batches.

    **Example Request:**
    ```json
    {
        "client_id": "client-abc-123",
        "case_ids": ["case-1", "case-2", "case-3"],
        "scope": "standard",
        "use_cache": true
    }
    ```

    **Example Response:**
    ```json
    {
        "total_cases": 3,
        "successful": 3,
        "failed": 0,
        "contexts": {
            "case-1": {...},
            "case-2": {...},
            "case-3": {...}
        },
        "errors": {}
    }
    ```
    """
    try:
        logger.info(
            f"Batch context retrieval: {len(request.case_ids)} cases, scope={request.scope}"
        )

        builder = get_context_builder()

        results = {
            "total_cases": len(request.case_ids),
            "successful": 0,
            "failed": 0,
            "contexts": {},
            "errors": {}
        }

        # Process each case
        for case_id in request.case_ids:
            try:
                context = await builder.build_context(
                    client_id=request.client_id,
                    case_id=case_id,
                    scope=request.scope,
                    use_cache=request.use_cache
                )
                results["contexts"][case_id] = context
                results["successful"] += 1

            except Exception as e:
                logger.error(f"Failed to build context for case {case_id}: {str(e)}")
                results["errors"][case_id] = str(e)
                results["failed"] += 1

        logger.info(
            f"Batch retrieval complete: {results['successful']}/{results['total_cases']} successful"
        )

        return results

    except Exception as e:
        logger.error(f"Batch retrieval failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch retrieval failed: {str(e)}")
