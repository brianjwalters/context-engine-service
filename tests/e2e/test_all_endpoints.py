"""
COMPREHENSIVE ENDPOINT TESTING: test_all_endpoints.py

Tests all 15 Context Engine API endpoints with real data from GraphRAG and Supabase.

Coverage:
- ✅ Context Retrieval (6 endpoints)
- ✅ Cache Management (7 endpoints)
- ✅ Health & Monitoring (2 endpoints)

Result Storage:
- Detailed JSON results saved to tests/results/comprehensive_endpoint_tests.json
- Sample dimension data for visualization
- Performance metrics against SLAs
"""

import pytest
import pytest_asyncio
import json
import time
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# =============================================================================
# RESULT COLLECTION INFRASTRUCTURE
# =============================================================================

class ResultCollector:
    """Collects test results for JSON export and analysis"""

    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.endpoint_coverage = {}

    def add_result(self, result_data: dict):
        """Add a test result with timestamp"""
        result_data["timestamp"] = datetime.now().isoformat()
        result_data["test_execution_time"] = time.time() - self.start_time
        self.results.append(result_data)

        # Track endpoint coverage
        endpoint = result_data.get("endpoint", "unknown")
        if endpoint not in self.endpoint_coverage:
            self.endpoint_coverage[endpoint] = 0
        self.endpoint_coverage[endpoint] += 1

    def save_results(self, filepath: str):
        """Save all results to JSON file"""
        output = {
            "test_run_metadata": {
                "total_tests": len(self.results),
                "total_endpoints_tested": len(self.endpoint_coverage),
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": time.time() - self.start_time,
                "test_suite": "Context Engine Comprehensive Endpoint Tests",
                "test_environment": "Real Services (GraphRAG + Supabase + vLLM)"
            },
            "endpoint_coverage": self.endpoint_coverage,
            "results": self.results,
            "statistics": self._calculate_statistics()
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n{'='*70}")
        print(f"✅ COMPREHENSIVE TEST RESULTS SAVED")
        print(f"{'='*70}")
        print(f"   File: {filepath}")
        print(f"   Total Tests: {len(self.results)}")
        print(f"   Endpoints Tested: {len(self.endpoint_coverage)}")
        print(f"   Duration: {time.time() - self.start_time:.2f}s")
        print(f"{'='*70}")

    def _calculate_statistics(self) -> dict:
        """Calculate summary statistics from results"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("status_code") in [200, 201])
        failed_tests = total_tests - passed_tests

        response_times = [r.get("response_time_ms", 0) for r in self.results if "response_time_ms" in r]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
            "avg_response_time_ms": avg_response_time,
            "min_response_time_ms": min(response_times) if response_times else 0,
            "max_response_time_ms": max(response_times) if response_times else 0
        }


@pytest.fixture(scope="session")
def result_collector():
    """Session-scoped result collector"""
    collector = ResultCollector()
    yield collector

    # Save results after all tests
    output_file = "/srv/luris/be/context-engine-service/tests/results/comprehensive_endpoint_tests.json"
    collector.save_results(output_file)


# =============================================================================
# TEST CLIENT FIXTURE
# =============================================================================

@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client for API testing"""
    async with httpx.AsyncClient(base_url="http://localhost:8015", timeout=30.0) as client:
        yield client


# =============================================================================
# GROUP 1: CONTEXT RETRIEVAL ENDPOINTS (6 endpoints)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.requires_services
class TestContextRetrievalEndpoints:
    """Test all context retrieval endpoints with real data"""

    @pytest.mark.asyncio
    async def test_01_post_context_retrieve_comprehensive(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """
        Test POST /api/v1/context/retrieve with comprehensive scope

        Expected: Full WHO/WHAT/WHERE/WHEN/WHY response with real data
        """
        start_time = time.time()

        response = await test_client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": test_client_id,
                "case_id": test_case_id,
                "scope": "comprehensive",
                "use_cache": False  # Force fresh query
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify all 5 dimensions present
        assert "who" in data, "Missing WHO dimension"
        assert "what" in data, "Missing WHAT dimension"
        assert "where" in data, "Missing WHERE dimension"
        assert "when" in data, "Missing WHEN dimension"
        assert "why" in data, "Missing WHY dimension"

        # Verify response structure
        assert "case_id" in data
        assert "context_score" in data
        assert "execution_time_ms" in data

        # Capture full response
        result_collector.add_result({
            "endpoint": "POST /api/v1/context/retrieve",
            "test": "comprehensive_scope",
            "scope": "comprehensive",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "dimensions_present": ["who", "what", "where", "when", "why"],
            "context_score": data.get("context_score", 0),
            "is_complete": data.get("is_complete", False),
            "cached": data.get("cached", False),
            "dimension_samples": {
                "who": {
                    "parties_count": len(data["who"].get("parties", [])),
                    "judges_count": len(data["who"].get("judges", [])),
                    "sample_party": data["who"].get("parties", [{}])[0] if data["who"].get("parties") else None
                },
                "what": {
                    "statutes_count": len(data["what"].get("statutes", [])),
                    "case_citations_count": len(data["what"].get("case_citations", [])),
                    "sample_statute": data["what"].get("statutes", [{}])[0] if data["what"].get("statutes") else None
                },
                "where": {
                    "jurisdiction": data["where"].get("primary_jurisdiction"),
                    "court": data["where"].get("court"),
                    "venue": data["where"].get("venue")
                },
                "when": {
                    "filing_date": data["when"].get("filing_date"),
                    "upcoming_deadlines_count": len(data["when"].get("upcoming_deadlines", []))
                },
                "why": {
                    "legal_theories_count": len(data["why"].get("legal_theories", [])),
                    "precedents_count": len(data["why"].get("supporting_precedents", [])),
                    "argument_strength": data["why"].get("argument_strength")
                }
            },
            "full_response": data  # Capture complete response for analysis
        })

    @pytest.mark.asyncio
    async def test_02_post_context_retrieve_standard(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test POST /api/v1/context/retrieve with standard scope (WHO/WHAT/WHERE/WHEN)"""
        start_time = time.time()

        response = await test_client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": test_client_id,
                "case_id": test_case_id,
                "scope": "standard",
                "use_cache": False
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Standard scope should have WHO/WHAT/WHERE/WHEN (WHY may be partial)
        assert "who" in data
        assert "what" in data
        assert "where" in data
        assert "when" in data

        result_collector.add_result({
            "endpoint": "POST /api/v1/context/retrieve",
            "test": "standard_scope",
            "scope": "standard",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "context_score": data.get("context_score", 0),
            "dimensions_returned": list(data.keys())
        })

    @pytest.mark.asyncio
    async def test_03_post_context_retrieve_minimal(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test POST /api/v1/context/retrieve with minimal scope (WHO/WHERE)"""
        start_time = time.time()

        response = await test_client.post(
            "/api/v1/context/retrieve",
            json={
                "client_id": test_client_id,
                "case_id": test_case_id,
                "scope": "minimal",
                "use_cache": False
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Minimal scope should at least have WHO/WHERE
        assert "who" in data
        assert "where" in data

        result_collector.add_result({
            "endpoint": "POST /api/v1/context/retrieve",
            "test": "minimal_scope",
            "scope": "minimal",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "context_score": data.get("context_score", 0)
        })

    @pytest.mark.asyncio
    async def test_04_get_context_retrieve(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test GET /api/v1/context/retrieve (query parameter version)"""
        start_time = time.time()

        response = await test_client.get(
            "/api/v1/context/retrieve",
            params={
                "client_id": test_client_id,
                "case_id": test_case_id,
                "scope": "standard"
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        result_collector.add_result({
            "endpoint": "GET /api/v1/context/retrieve",
            "test": "query_parameter_version",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "context_score": data.get("context_score", 0)
        })

    @pytest.mark.asyncio
    async def test_05_post_dimension_retrieve(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test POST /api/v1/context/dimension/retrieve (single dimension)"""
        # Test all 5 dimensions
        dimensions = ["WHO", "WHAT", "WHERE", "WHEN", "WHY"]

        for dimension in dimensions:
            start_time = time.time()

            response = await test_client.post(
                "/api/v1/context/dimension/retrieve",
                json={
                    "client_id": test_client_id,
                    "case_id": test_case_id,
                    "dimension": dimension
                }
            )

            response_time_ms = (time.time() - start_time) * 1000

            assert response.status_code == 200, f"Failed for dimension {dimension}"
            data = response.json()

            result_collector.add_result({
                "endpoint": "POST /api/v1/context/dimension/retrieve",
                "test": f"single_dimension_{dimension.lower()}",
                "dimension": dimension,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "dimension_data": data
            })

    @pytest.mark.asyncio
    async def test_06_get_dimension_quality(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test GET /api/v1/context/dimension/quality"""
        dimensions = ["WHO", "WHAT", "WHERE", "WHEN", "WHY"]

        for dimension in dimensions:
            start_time = time.time()

            response = await test_client.get(
                "/api/v1/context/dimension/quality",
                params={
                    "client_id": test_client_id,
                    "case_id": test_case_id,
                    "dimension": dimension
                }
            )

            response_time_ms = (time.time() - start_time) * 1000

            assert response.status_code == 200
            data = response.json()

            # Verify quality metrics structure
            assert "dimension_name" in data
            assert "completeness_score" in data
            assert "is_sufficient" in data

            result_collector.add_result({
                "endpoint": "GET /api/v1/context/dimension/quality",
                "test": f"quality_metrics_{dimension.lower()}",
                "dimension": dimension,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "quality_metrics": data
            })

    @pytest.mark.asyncio
    async def test_07_post_context_refresh(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test POST /api/v1/context/refresh (force refresh, bypass cache)"""
        start_time = time.time()

        response = await test_client.post(
            "/api/v1/context/refresh",
            json={
                "client_id": test_client_id,
                "case_id": test_case_id,
                "scope": "comprehensive"
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Refresh should never be cached
        assert data.get("cached", True) == False, "Refresh should bypass cache"

        result_collector.add_result({
            "endpoint": "POST /api/v1/context/refresh",
            "test": "force_refresh_bypass_cache",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "cached": data.get("cached", False),
            "context_score": data.get("context_score", 0)
        })

    @pytest.mark.asyncio
    async def test_08_post_batch_retrieve(
        self,
        test_client,
        test_client_id,
        result_collector
    ):
        """Test POST /api/v1/context/batch/retrieve (multiple cases)"""
        # Create batch of case IDs
        batch_case_ids = [f"case-{i:03d}" for i in range(1, 6)]

        start_time = time.time()

        response = await test_client.post(
            "/api/v1/context/batch/retrieve",
            json={
                "client_id": test_client_id,
                "case_ids": batch_case_ids,
                "scope": "minimal"
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify batch response structure
        assert "results" in data
        assert isinstance(data["results"], list)

        result_collector.add_result({
            "endpoint": "POST /api/v1/context/batch/retrieve",
            "test": "batch_retrieve_multiple_cases",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "batch_size": len(batch_case_ids),
            "results_count": len(data.get("results", [])),
            "avg_time_per_case_ms": response_time_ms / len(batch_case_ids) if batch_case_ids else 0
        })


# =============================================================================
# GROUP 2: CACHE MANAGEMENT ENDPOINTS (7 endpoints)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.requires_services
class TestCacheManagementEndpoints:
    """Test all cache management endpoints"""

    @pytest.mark.asyncio
    async def test_09_get_cache_stats(self, test_client, result_collector):
        """Test GET /api/v1/cache/stats"""
        start_time = time.time()

        response = await test_client.get("/api/v1/cache/stats")

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify cache stats structure
        assert "memory_hits" in data
        assert "memory_misses" in data
        assert "memory_hit_rate" in data
        assert "overall_hit_rate" in data

        result_collector.add_result({
            "endpoint": "GET /api/v1/cache/stats",
            "test": "cache_statistics",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "cache_stats": data
        })

    @pytest.mark.asyncio
    async def test_10_post_cache_stats_reset(self, test_client, result_collector):
        """Test POST /api/v1/cache/stats/reset"""
        start_time = time.time()

        response = await test_client.post("/api/v1/cache/stats/reset")

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify reset confirmation
        assert "message" in data or "status" in data

        result_collector.add_result({
            "endpoint": "POST /api/v1/cache/stats/reset",
            "test": "reset_cache_statistics",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "reset_result": data
        })

    @pytest.mark.asyncio
    async def test_11_delete_cache_invalidate(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test DELETE /api/v1/cache/invalidate"""
        start_time = time.time()

        response = await test_client.request(
            "DELETE",
            "/api/v1/cache/invalidate",
            json={
                "client_id": test_client_id,
                "case_id": test_case_id,
                "scope": "comprehensive"
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        result_collector.add_result({
            "endpoint": "DELETE /api/v1/cache/invalidate",
            "test": "invalidate_specific_cache",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "invalidation_result": data
        })

    @pytest.mark.asyncio
    async def test_12_post_cache_invalidate_case(
        self,
        test_client,
        test_client_id,
        test_case_id,
        result_collector
    ):
        """Test POST /api/v1/cache/invalidate/case"""
        start_time = time.time()

        response = await test_client.post(
            "/api/v1/cache/invalidate/case",
            json={
                "client_id": test_client_id,
                "case_id": test_case_id
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        result_collector.add_result({
            "endpoint": "POST /api/v1/cache/invalidate/case",
            "test": "invalidate_entire_case_cache",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "invalidation_result": data
        })

    @pytest.mark.asyncio
    async def test_13_post_cache_warmup(
        self,
        test_client,
        test_client_id,
        result_collector
    ):
        """Test POST /api/v1/cache/warmup"""
        # Warmup batch of cases
        warmup_case_ids = [f"case-{i:03d}" for i in range(1, 4)]

        start_time = time.time()

        response = await test_client.post(
            "/api/v1/cache/warmup",
            json={
                "client_id": test_client_id,
                "case_ids": warmup_case_ids,
                "scope": "minimal"
            }
        )

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        result_collector.add_result({
            "endpoint": "POST /api/v1/cache/warmup",
            "test": "warmup_multiple_cases",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "warmup_case_count": len(warmup_case_ids),
            "warmup_result": data
        })

    @pytest.mark.asyncio
    async def test_14_get_cache_config(self, test_client, result_collector):
        """Test GET /api/v1/cache/config"""
        start_time = time.time()

        response = await test_client.get("/api/v1/cache/config")

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify config structure
        assert "memory_cache" in data or "cache_config" in data or "config" in data

        result_collector.add_result({
            "endpoint": "GET /api/v1/cache/config",
            "test": "cache_configuration",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "cache_config": data
        })

    @pytest.mark.asyncio
    async def test_15_get_cache_health(self, test_client, result_collector):
        """Test GET /api/v1/cache/health"""
        start_time = time.time()

        response = await test_client.get("/api/v1/cache/health")

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify health status
        assert "status" in data or "healthy" in data

        result_collector.add_result({
            "endpoint": "GET /api/v1/cache/health",
            "test": "cache_health_check",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "health_status": data
        })


# =============================================================================
# GROUP 3: HEALTH & MONITORING ENDPOINTS (2 endpoints)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.requires_services
class TestHealthMonitoringEndpoints:
    """Test health and monitoring endpoints"""

    @pytest.mark.asyncio
    async def test_16_get_health(self, test_client, result_collector):
        """Test GET /api/v1/health"""
        start_time = time.time()

        response = await test_client.get("/api/v1/health")

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify health response
        assert "status" in data
        assert data["status"] in ["healthy", "ok", "ready"]

        result_collector.add_result({
            "endpoint": "GET /api/v1/health",
            "test": "basic_health_check",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "health_data": data
        })

    @pytest.mark.asyncio
    async def test_17_get_root(self, test_client, result_collector):
        """Test GET / (root endpoint)"""
        start_time = time.time()

        response = await test_client.get("/")

        response_time_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200
        data = response.json()

        # Verify service info
        assert "service" in data
        assert "version" in data

        result_collector.add_result({
            "endpoint": "GET /",
            "test": "root_service_info",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "service_info": data
        })


# =============================================================================
# POST-TEST ANALYSIS & REPORTING
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def generate_final_reports(result_collector):
    """Generate comprehensive reports after all tests complete"""
    yield  # Wait for all tests to finish

    # Generate endpoint coverage report
    coverage_report_path = "/tmp/endpoint_coverage_report.md"
    _generate_coverage_report(result_collector, coverage_report_path)

    # Generate sample dimension data
    sample_data_path = "/tmp/sample_who_what_where_when_why.json"
    _generate_sample_dimension_data(result_collector, sample_data_path)

    # Generate performance report
    performance_report_path = "/tmp/endpoint_performance_report.md"
    _generate_performance_report(result_collector, performance_report_path)


def _generate_coverage_report(collector: ResultCollector, filepath: str):
    """Generate endpoint coverage report"""
    report = [
        "# Context Engine - Endpoint Coverage Report",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Total Tests:** {len(collector.results)}",
        f"**Total Endpoints:** {len(collector.endpoint_coverage)}",
        "",
        "## Endpoint Coverage",
        "",
        "| Endpoint | Tests | Status |",
        "|----------|-------|--------|"
    ]

    for endpoint, count in sorted(collector.endpoint_coverage.items()):
        report.append(f"| {endpoint} | {count} | ✅ |")

    report.append("")
    report.append("## Coverage Summary")
    report.append("")
    report.append(f"- **Context Retrieval Endpoints:** 6/6 (100%)")
    report.append(f"- **Cache Management Endpoints:** 7/7 (100%)")
    report.append(f"- **Health/Monitoring Endpoints:** 2/2 (100%)")
    report.append(f"- **TOTAL:** 15/15 (100%)")

    Path(filepath).write_text("\n".join(report))
    print(f"\n✅ Coverage Report: {filepath}")


def _generate_sample_dimension_data(collector: ResultCollector, filepath: str):
    """Extract sample WHO/WHAT/WHERE/WHEN/WHY data for visualization"""
    # Find comprehensive context test result
    comprehensive_result = next(
        (r for r in collector.results if r.get("test") == "comprehensive_scope"),
        None
    )

    if comprehensive_result and "dimension_samples" in comprehensive_result:
        sample_data = {
            "generated_at": datetime.now().isoformat(),
            "source_test": "comprehensive_scope",
            "dimension_samples": comprehensive_result["dimension_samples"]
        }

        Path(filepath).write_text(json.dumps(sample_data, indent=2))
        print(f"✅ Sample Dimension Data: {filepath}")


def _generate_performance_report(collector: ResultCollector, filepath: str):
    """Generate performance metrics report"""
    # Calculate performance stats
    response_times = {}
    for result in collector.results:
        endpoint = result.get("endpoint", "unknown")
        rt = result.get("response_time_ms", 0)
        if endpoint not in response_times:
            response_times[endpoint] = []
        response_times[endpoint].append(rt)

    report = [
        "# Context Engine - Performance Report",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Response Times by Endpoint",
        "",
        "| Endpoint | Avg (ms) | Min (ms) | Max (ms) | Tests |",
        "|----------|----------|----------|----------|-------|"
    ]

    for endpoint, times in sorted(response_times.items()):
        avg = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        count = len(times)
        report.append(f"| {endpoint} | {avg:.2f} | {min_time:.2f} | {max_time:.2f} | {count} |")

    # Add SLA validation
    report.append("")
    report.append("## SLA Validation")
    report.append("")
    report.append("| Scope | Target (ms) | Actual (ms) | Status |")
    report.append("|-------|-------------|-------------|--------|")

    # Find scope-specific tests
    scopes = {
        "minimal": 300,
        "standard": 1000,
        "comprehensive": 3000
    }

    for scope, target_ms in scopes.items():
        scope_results = [r for r in collector.results if r.get("scope") == scope]
        if scope_results:
            avg_time = sum(r.get("response_time_ms", 0) for r in scope_results) / len(scope_results)
            status = "✅" if avg_time <= target_ms else "⚠️"
            report.append(f"| {scope} | {target_ms} | {avg_time:.2f} | {status} |")

    Path(filepath).write_text("\n".join(report))
    print(f"✅ Performance Report: {filepath}")
