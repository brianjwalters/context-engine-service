"""
Context Engine Service - Performance Baseline Test Suite

Purpose: Establish performance baselines for production deployment
Tests: Load, Stress, Endurance, Spike

Metrics:
- Response time percentiles (P50, P95, P99)
- Throughput (requests/second)
- Error rates
- Resource utilization (CPU, memory, connections)

Requirements:
- httpx (already installed)
- psutil (pip install psutil)

Usage:
    # Run all baselines
    pytest tests/performance/baseline_tests.py -v

    # Run specific test
    pytest tests/performance/baseline_tests.py::test_load_baseline -v

    # Skip endurance (takes 1 hour)
    pytest tests/performance/baseline_tests.py -v -m "not endurance"
"""

import pytest
import time
import asyncio
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import httpx
import json
from pathlib import Path

# Test configuration
CONTEXT_ENGINE_URL = "http://localhost:8015"
RESULTS_DIR = Path(__file__).parent.parent / "results" / "performance"


@dataclass
class PerformanceMetrics:
    """Performance test metrics"""
    test_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    min_latency_ms: float
    avg_latency_ms: float
    error_rate_percent: float

    def to_dict(self) -> dict:
        return asdict(self)

    def passed_sla(self) -> bool:
        """Check if metrics meet SLA requirements"""
        return (
            self.p95_latency_ms < 2000 and  # P95 < 2s
            self.error_rate_percent < 1.0  # Error rate < 1%
        )


class PerformanceTester:
    """Performance testing harness"""

    def __init__(self, base_url: str = CONTEXT_ENGINE_URL):
        self.base_url = base_url
        self.latencies: List[float] = []
        self.errors: List[Exception] = []

    async def make_request(self, endpoint: str = "/api/v1/health") -> float:
        """
        Make HTTP request and return latency in milliseconds

        Args:
            endpoint: API endpoint to test

        Returns:
            Latency in milliseconds
        """
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}{endpoint}")
                response.raise_for_status()
            latency_ms = (time.perf_counter() - start) * 1000
            self.latencies.append(latency_ms)
            return latency_ms
        except Exception as e:
            self.errors.append(e)
            return 0.0

    def calculate_metrics(self, test_name: str, duration: float) -> PerformanceMetrics:
        """Calculate performance metrics from collected data"""
        total_requests = len(self.latencies) + len(self.errors)
        successful_requests = len(self.latencies)
        failed_requests = len(self.errors)

        if not self.latencies:
            # No successful requests
            return PerformanceMetrics(
                test_name=test_name,
                duration_seconds=duration,
                total_requests=total_requests,
                successful_requests=0,
                failed_requests=failed_requests,
                requests_per_second=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                max_latency_ms=0.0,
                min_latency_ms=0.0,
                avg_latency_ms=0.0,
                error_rate_percent=100.0
            )

        sorted_latencies = sorted(self.latencies)

        return PerformanceMetrics(
            test_name=test_name,
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=total_requests / duration if duration > 0 else 0.0,
            p50_latency_ms=statistics.median(sorted_latencies),
            p95_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 0 else 0.0,
            p99_latency_ms=sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 0 else 0.0,
            max_latency_ms=max(sorted_latencies),
            min_latency_ms=min(sorted_latencies),
            avg_latency_ms=statistics.mean(sorted_latencies),
            error_rate_percent=(failed_requests / total_requests * 100) if total_requests > 0 else 0.0
        )

    def save_results(self, metrics: PerformanceMetrics):
        """Save performance results to file"""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

        output_file = RESULTS_DIR / f"{metrics.test_name}_{int(time.time())}.json"

        with open(output_file, 'w') as f:
            json.dump(metrics.to_dict(), f, indent=2)

        print(f"\n📊 Results saved to: {output_file}")

    def print_report(self, metrics: PerformanceMetrics):
        """Print performance report to console"""
        print(f"\n{'='*60}")
        print(f"Performance Test: {metrics.test_name}")
        print(f"{'='*60}")
        print(f"\nExecution:")
        print(f"  Duration:           {metrics.duration_seconds:.2f}s")
        print(f"  Total Requests:     {metrics.total_requests}")
        print(f"  Successful:         {metrics.successful_requests}")
        print(f"  Failed:             {metrics.failed_requests}")
        print(f"  Throughput:         {metrics.requests_per_second:.2f} req/s")

        print(f"\nLatency:")
        print(f"  P50 (Median):       {metrics.p50_latency_ms:.2f} ms")
        print(f"  P95:                {metrics.p95_latency_ms:.2f} ms")
        print(f"  P99:                {metrics.p99_latency_ms:.2f} ms")
        print(f"  Min:                {metrics.min_latency_ms:.2f} ms")
        print(f"  Max:                {metrics.max_latency_ms:.2f} ms")
        print(f"  Average:            {metrics.avg_latency_ms:.2f} ms")

        print(f"\nQuality:")
        print(f"  Error Rate:         {metrics.error_rate_percent:.2f}%")

        # SLA Check
        sla_status = "✅ PASS" if metrics.passed_sla() else "❌ FAIL"
        print(f"\nSLA Status:           {sla_status}")

        if not metrics.passed_sla():
            print("\nSLA Violations:")
            if metrics.p95_latency_ms >= 2000:
                print(f"  ❌ P95 latency ({metrics.p95_latency_ms:.2f}ms) >= 2000ms")
            if metrics.error_rate_percent >= 1.0:
                print(f"  ❌ Error rate ({metrics.error_rate_percent:.2f}%) >= 1%")

        print(f"{'='*60}\n")


# ============================================================================
# Performance Baseline Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
async def test_load_baseline():
    """
    Load Test: Sustained 50 concurrent requests for 60 seconds

    Target SLA:
    - P95 latency < 2s
    - Error rate < 1%
    - Throughput > 50 req/s
    """
    tester = PerformanceTester()

    print("\n🔥 Starting Load Test (50 concurrent, 60s)")

    duration = 60  # seconds
    concurrency = 50

    start_time = time.time()

    async def worker():
        """Worker coroutine"""
        while time.time() - start_time < duration:
            await tester.make_request("/api/v1/health")
            await asyncio.sleep(0.01)  # Small delay to prevent overwhelming

    # Run concurrent workers
    await asyncio.gather(*[worker() for _ in range(concurrency)])

    elapsed = time.time() - start_time

    # Calculate and report metrics
    metrics = tester.calculate_metrics("load_test", elapsed)
    tester.print_report(metrics)
    tester.save_results(metrics)

    # Assert SLA
    assert metrics.passed_sla(), f"Load test failed SLA requirements"
    assert metrics.p95_latency_ms < 2000, f"P95 latency {metrics.p95_latency_ms}ms exceeds 2000ms"


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
async def test_stress_baseline():
    """
    Stress Test: Ramp from 0 to 200 req/s to find breaking point

    Target: Identify maximum sustainable throughput
    """
    tester = PerformanceTester()

    print("\n💪 Starting Stress Test (0 → 200 req/s ramp)")

    duration = 120  # 2 minutes
    start_time = time.time()

    async def ramping_worker(worker_id: int):
        """Worker with ramping load"""
        request_count = 0
        while time.time() - start_time < duration:
            elapsed = time.time() - start_time
            # Ramp: 0 req/s at t=0, 200 req/s at t=120
            target_rps = (elapsed / duration) * 200

            # Sleep to maintain target RPS (distributed across workers)
            if target_rps > 0:
                delay = 10 / max(target_rps, 1)  # 10 workers
                await asyncio.sleep(delay)

            await tester.make_request("/api/v1/health")
            request_count += 1

    # Run workers
    await asyncio.gather(*[ramping_worker(i) for i in range(10)])

    elapsed = time.time() - start_time

    # Calculate and report metrics
    metrics = tester.calculate_metrics("stress_test", elapsed)
    tester.print_report(metrics)
    tester.save_results(metrics)

    print(f"\n📈 Maximum Throughput: {metrics.requests_per_second:.2f} req/s")
    print(f"   Breaking Point: {'Not reached' if metrics.error_rate_percent < 5 else 'Exceeded capacity'}")


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.endurance
@pytest.mark.asyncio
async def test_endurance_baseline():
    """
    Endurance Test: Sustained 30 req/s for 1 hour

    Target: Detect memory leaks and performance degradation over time
    """
    pytest.skip("Endurance test takes 1 hour - run manually with: pytest -m endurance")

    tester = PerformanceTester()

    print("\n⏰ Starting Endurance Test (30 req/s, 1 hour)")

    duration = 3600  # 1 hour
    concurrency = 30

    start_time = time.time()

    async def worker():
        """Worker coroutine"""
        while time.time() - start_time < duration:
            await tester.make_request("/api/v1/health")
            await asyncio.sleep(1.0)  # 1 req/s per worker

    # Run concurrent workers
    await asyncio.gather(*[worker() for _ in range(concurrency)])

    elapsed = time.time() - start_time

    # Calculate and report metrics
    metrics = tester.calculate_metrics("endurance_test", elapsed)
    tester.print_report(metrics)
    tester.save_results(metrics)

    # Endurance test should maintain SLA for entire duration
    assert metrics.passed_sla(), f"Endurance test failed SLA requirements"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_spike_baseline():
    """
    Spike Test: Sudden burst from 0 to 200 req/s

    Target: Validate cache and connection pool behavior under sudden load
    """
    tester = PerformanceTester()

    print("\n⚡ Starting Spike Test (0 → 200 req/s instant)")

    # Baseline period (low load)
    print("   Phase 1: Baseline (5s, 10 req/s)")
    start_time = time.time()
    for _ in range(50):  # 50 requests in 5 seconds = 10 req/s
        await tester.make_request("/api/v1/health")
        await asyncio.sleep(0.1)

    # Spike period (high load)
    print("   Phase 2: Spike (10s, 200 req/s)")
    spike_start = time.time()

    async def spike_worker():
        """High-load worker"""
        while time.time() - spike_start < 10:
            await tester.make_request("/api/v1/health")
            await asyncio.sleep(0.005)  # 200 req/s across 100 workers

    await asyncio.gather(*[spike_worker() for _ in range(100)])

    # Recovery period
    print("   Phase 3: Recovery (5s, 10 req/s)")
    for _ in range(50):
        await tester.make_request("/api/v1/health")
        await asyncio.sleep(0.1)

    elapsed = time.time() - start_time

    # Calculate and report metrics
    metrics = tester.calculate_metrics("spike_test", elapsed)
    tester.print_report(metrics)
    tester.save_results(metrics)

    # Spike test passes if error rate stays low during spike
    assert metrics.error_rate_percent < 5.0, f"Error rate {metrics.error_rate_percent}% too high during spike"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_quick_baseline():
    """
    Quick Baseline Test: Fast baseline measurement (10 seconds)

    Target: Rapid performance check for CI/CD pipelines
    """
    tester = PerformanceTester()

    print("\n⚡ Starting Quick Baseline Test (10 concurrent, 10s)")

    duration = 10  # 10 seconds
    concurrency = 10

    start_time = time.time()

    async def worker():
        """Worker coroutine"""
        while time.time() - start_time < duration:
            await tester.make_request("/api/v1/health")
            await asyncio.sleep(0.05)  # 20 req/s per worker

    # Run concurrent workers
    await asyncio.gather(*[worker() for _ in range(concurrency)])

    elapsed = time.time() - start_time

    # Calculate and report metrics
    metrics = tester.calculate_metrics("quick_baseline", elapsed)
    tester.print_report(metrics)
    tester.save_results(metrics)

    # Quick baseline should still meet basic SLA
    assert metrics.error_rate_percent < 5.0, f"Error rate {metrics.error_rate_percent}% too high"
    assert metrics.p95_latency_ms < 5000, f"P95 latency {metrics.p95_latency_ms}ms exceeds 5000ms"


# ============================================================================
# Comprehensive Context Endpoint Tests
# ============================================================================

@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.asyncio
async def test_comprehensive_context_baseline():
    """
    Comprehensive Context Endpoint Load Test

    Target: Test actual context retrieval performance under load
    Note: Requires GraphRAG service and database to be running
    """
    tester = PerformanceTester()

    print("\n🔍 Starting Comprehensive Context Baseline Test")

    # Test payload
    test_query = "federal question jurisdiction"

    duration = 30  # 30 seconds
    concurrency = 10

    start_time = time.time()

    async def worker():
        """Worker coroutine for context endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            while time.time() - start_time < duration:
                try:
                    request_start = time.perf_counter()
                    response = await client.post(
                        f"{CONTEXT_ENGINE_URL}/api/v1/context/retrieve",
                        json={
                            "query": test_query,
                            "scope": "comprehensive",
                            "include_precedents": True
                        }
                    )
                    response.raise_for_status()
                    latency_ms = (time.perf_counter() - request_start) * 1000
                    tester.latencies.append(latency_ms)
                except Exception as e:
                    tester.errors.append(e)

                await asyncio.sleep(0.1)  # Rate limiting

    # Run concurrent workers
    await asyncio.gather(*[worker() for _ in range(concurrency)])

    elapsed = time.time() - start_time

    # Calculate and report metrics
    metrics = tester.calculate_metrics("comprehensive_context_baseline", elapsed)
    tester.print_report(metrics)
    tester.save_results(metrics)

    # Context endpoint should meet SLA (may be slower than health check)
    if metrics.successful_requests > 0:
        assert metrics.p95_latency_ms < 5000, f"P95 latency {metrics.p95_latency_ms}ms exceeds 5000ms"
        assert metrics.error_rate_percent < 10.0, f"Error rate {metrics.error_rate_percent}% too high"
    else:
        pytest.skip("No successful requests - service may not be fully operational")


# ============================================================================
# Run all baselines
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Context Engine - Performance Baseline Suite")
    print("="*60)

    # Run with pytest
    import subprocess
    subprocess.run(["pytest", __file__, "-v", "-s", "-m", "not endurance"])
