"""
Pytest configuration and shared fixtures for Context Engine Service tests.

This file is automatically loaded by pytest and provides:
- Global test configuration
- Shared fixtures available to all tests
- Test markers and plugins
- Custom test collection rules
"""

import pytest
import sys
import logging
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all fixtures from fixtures module
from tests.fixtures.context_fixtures import *  # noqa: F401, F403


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "unit: Unit tests (no external dependencies)"
    )
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (requires services)"
    )
    config.addinivalue_line(
        "markers",
        "e2e: End-to-end tests (requires all services + database)"
    )
    config.addinivalue_line(
        "markers",
        "slow: Slow running tests (>5 seconds)"
    )
    config.addinivalue_line(
        "markers",
        "requires_services: Test requires external services to be running"
    )
    config.addinivalue_line(
        "markers",
        "requires_graphrag: Test requires GraphRAG service (port 8010)"
    )
    config.addinivalue_line(
        "markers",
        "requires_database: Test requires Supabase database"
    )

    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Auto-mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.requires_services)

        # Auto-mark unit tests
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Auto-mark e2e tests
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.requires_services)
            item.add_marker(pytest.mark.requires_graphrag)
            item.add_marker(pytest.mark.requires_database)

        # Auto-mark slow tests (integration and e2e tests are typically slow)
        if "integration" in str(item.fspath) or "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.slow)


# =============================================================================
# Session-Level Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def test_environment():
    """Provide test environment information"""
    return {
        "environment": "test",
        "debug": True,
        "log_level": "DEBUG"
    }


@pytest.fixture(scope="session")
def project_root_path():
    """Return project root directory path"""
    return project_root


# =============================================================================
# Module-Level Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def logger():
    """Provide logger for tests"""
    return logging.getLogger("test")


# =============================================================================
# Function-Level Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test"""
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Reset to INFO level
    logging.root.setLevel(logging.INFO)


@pytest.fixture
def mock_environment(monkeypatch):
    """Mock environment variables for testing"""
    test_env = {
        "PORT": "8015",
        "SERVICE_NAME": "context-engine-test",
        "GRAPHRAG_BASE_URL": "http://10.10.0.87:8010",
        "SUPABASE_URL": "http://localhost:54321",
        "SUPABASE_KEY": "test-key",
        "ENABLE_MEMORY_CACHE": "true",
        "ENABLE_REDIS_CACHE": "false",
        "ENABLE_DB_CACHE": "false"
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


# =============================================================================
# Performance Measurement
# =============================================================================

@pytest.fixture
def performance_tracker():
    """Track test performance metrics"""
    import time

    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration_ms = None

        def start(self):
            """Start timing"""
            self.start_time = time.time()

        def stop(self):
            """Stop timing and calculate duration"""
            self.end_time = time.time()
            self.duration_ms = (self.end_time - self.start_time) * 1000
            return self.duration_ms

        def assert_within_threshold(self, threshold_ms: float, operation: str = "Operation"):
            """Assert that duration is within threshold"""
            assert self.duration_ms is not None, "Must call stop() before asserting"
            assert self.duration_ms <= threshold_ms, (
                f"{operation} took {self.duration_ms:.2f}ms, "
                f"exceeds threshold of {threshold_ms}ms"
            )

    return PerformanceTracker()


# =============================================================================
# Test Data Cleanup
# =============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data before and after each test"""
    # Setup: cleanup before test
    yield
    # Teardown: cleanup after test
    # Add any cleanup logic here (e.g., clear test database, reset caches)
    pass


# =============================================================================
# Error Injection for Testing
# =============================================================================

@pytest.fixture
def error_injector():
    """Inject errors for testing error handling"""
    from unittest.mock import AsyncMock

    class ErrorInjector:
        @staticmethod
        def create_failing_async_mock(error_type=Exception, error_message="Injected error"):
            """Create async mock that raises error"""
            return AsyncMock(side_effect=error_type(error_message))

        @staticmethod
        def create_timeout_mock(delay: float = 5.0):
            """Create async mock that times out"""
            import asyncio

            async def timeout_func(*args, **kwargs):
                await asyncio.sleep(delay)
                raise asyncio.TimeoutError("Operation timed out")

            return AsyncMock(side_effect=timeout_func)

        @staticmethod
        def create_intermittent_failure_mock(success_rate: float = 0.5):
            """Create mock that fails intermittently"""
            import random

            call_count = 0

            async def intermittent_func(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if random.random() > success_rate:
                    raise Exception(f"Intermittent failure on call {call_count}")
                return {"success": True, "call_count": call_count}

            return AsyncMock(side_effect=intermittent_func)

    return ErrorInjector()


# =============================================================================
# Snapshot Testing Support
# =============================================================================

@pytest.fixture
def snapshot_dir(tmp_path):
    """Directory for test snapshots"""
    snapshot_path = tmp_path / "snapshots"
    snapshot_path.mkdir(exist_ok=True)
    return snapshot_path


@pytest.fixture
def assert_snapshot():
    """Helper for snapshot testing"""
    import json

    def _assert_snapshot(data: dict, snapshot_file: Path, update: bool = False):
        """
        Compare data against snapshot file.

        Args:
            data: Data to compare
            snapshot_file: Path to snapshot file
            update: If True, update snapshot instead of comparing
        """
        if update or not snapshot_file.exists():
            # Update or create snapshot
            snapshot_file.write_text(json.dumps(data, indent=2, sort_keys=True))
            return True

        # Load and compare snapshot
        snapshot_data = json.loads(snapshot_file.read_text())
        assert data == snapshot_data, (
            f"Data doesn't match snapshot in {snapshot_file}\n"
            f"Expected:\n{json.dumps(snapshot_data, indent=2)}\n"
            f"Got:\n{json.dumps(data, indent=2)}"
        )
        return True

    return _assert_snapshot


# =============================================================================
# Test Utilities
# =============================================================================

@pytest.fixture
def test_utilities():
    """Collection of test utility functions"""

    class TestUtilities:
        @staticmethod
        def create_test_request_payload(
            client_id: str = "test-client",
            case_id: str = "test-case",
            scope: str = "comprehensive",
            use_cache: bool = True
        ) -> dict:
            """Create standard test request payload"""
            return {
                "client_id": client_id,
                "case_id": case_id,
                "scope": scope,
                "use_cache": use_cache
            }

        @staticmethod
        def assert_valid_context_response(data: dict):
            """Assert that response is a valid ContextResponse"""
            required_fields = [
                "case_id", "case_name", "who", "what", "where", "when", "why",
                "context_score", "is_complete", "cached", "execution_time_ms"
            ]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Validate types
            assert isinstance(data["who"], dict), "who must be dict"
            assert isinstance(data["what"], dict), "what must be dict"
            assert isinstance(data["where"], dict), "where must be dict"
            assert isinstance(data["when"], dict), "when must be dict"
            assert isinstance(data["why"], dict), "why must be dict"
            assert isinstance(data["context_score"], (int, float)), "context_score must be number"
            assert 0.0 <= data["context_score"] <= 1.0, "context_score must be 0.0-1.0"
            assert isinstance(data["is_complete"], bool), "is_complete must be bool"
            assert isinstance(data["cached"], bool), "cached must be bool"
            assert isinstance(data["execution_time_ms"], (int, float)), "execution_time_ms must be number"

        @staticmethod
        def assert_valid_cache_stats(data: dict):
            """Assert that response contains valid cache statistics"""
            required_fields = [
                "memory_hits", "memory_misses", "memory_hit_rate", "overall_hit_rate"
            ]
            for field in required_fields:
                assert field in data, f"Missing required cache stat field: {field}"

            # Validate hit rates are 0.0-1.0
            for rate_field in ["memory_hit_rate", "overall_hit_rate"]:
                if rate_field in data:
                    rate = data[rate_field]
                    assert 0.0 <= rate <= 1.0, f"{rate_field} must be 0.0-1.0, got {rate}"

    return TestUtilities()


# =============================================================================
# Pytest Hooks for Custom Behavior
# =============================================================================

def pytest_runtest_setup(item):
    """Called before running each test"""
    # Add any pre-test setup here
    pass


def pytest_runtest_teardown(item):
    """Called after running each test"""
    # Add any post-test cleanup here
    pass


def pytest_sessionstart(session):
    """Called before test session starts"""
    logging.info("=" * 70)
    logging.info("Context Engine Service - Test Session Starting")
    logging.info("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """Called after test session finishes"""
    logging.info("=" * 70)
    logging.info(f"Context Engine Service - Test Session Finished (exit status: {exitstatus})")
    logging.info("=" * 70)
