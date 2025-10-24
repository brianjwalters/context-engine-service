"""
Context Engine Service - FastAPI Application
Port: 8015

Provides case-centric context retrieval using WHO/WHAT/WHERE/WHEN/WHY framework.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time

# Create FastAPI app
app = FastAPI(
    title="Context Engine Service",
    description="Case-centric context retrieval using WHO/WHAT/WHERE/WHEN/WHY framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
REQUESTS_TOTAL = Counter(
    "context_engine_requests_total",
    "Total requests to Context Engine",
    ["endpoint", "method"]
)

REQUEST_LATENCY = Histogram(
    "context_engine_request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"]
)

@app.middleware("http")
async def add_metrics(request, call_next):
    """Add Prometheus metrics to all requests"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Record metrics
    REQUESTS_TOTAL.labels(endpoint=request.url.path, method=request.method).inc()
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(duration)

    return response

@app.get("/")
async def root():
    """Root endpoint - service information"""
    return {
        "service": "context-engine-service",
        "version": "1.0.0",
        "port": 8015,
        "status": "running",
        "description": "Case-centric context retrieval using WHO/WHAT/WHERE/WHEN/WHY framework",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
            "metrics": "/metrics"
        }
    }

@app.get("/api/v1/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "context-engine",
        "port": 8015,
        "version": "1.0.0"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# Import and include routers
from src.api.routes import context, cache
app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
app.include_router(cache.router, prefix="/api/v1/cache", tags=["cache"])
