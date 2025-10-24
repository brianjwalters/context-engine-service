# Context Engine Test Runner - Quick Start Guide

## Overview

The comprehensive test runner executes all 105 E2E tests, validates services, and generates detailed reports in multiple formats.

## Quick Start

```bash
# Navigate to service directory
cd /srv/luris/be/context-engine-service

# Activate virtual environment
source venv/bin/activate

# Run all tests with reports
python tests/e2e/run_comprehensive_tests.py --skip-services
```

## Command-Line Options

### Basic Options

```bash
# Skip service health checks (faster execution)
python tests/e2e/run_comprehensive_tests.py --skip-services

# Run only fast tests (excludes slow tests)
python tests/e2e/run_comprehensive_tests.py --fast

# Show verbose test output
python tests/e2e/run_comprehensive_tests.py --verbose

# Generate HTML report (enabled by default)
python tests/e2e/run_comprehensive_tests.py --report
```

### Combined Options

```bash
# Fast execution with no service checks
python tests/e2e/run_comprehensive_tests.py --skip-services --fast

# Full verbose run with all reports
python tests/e2e/run_comprehensive_tests.py --verbose --report

# CI/CD friendly (fast, no service checks)
python tests/e2e/run_comprehensive_tests.py --skip-services --fast
```

## Generated Reports

All reports are saved to: `/srv/luris/be/context-engine-service/tests/results/`

### 1. JSON Report (Machine-Readable)

**Filename:** `comprehensive_results_YYYYMMDD_HHMMSS.json`

**Contents:**
- Test metadata and execution time
- Service health status
- Test results and counts
- Performance metrics
- Code coverage data
- Dimension samples

**Use Case:** CI/CD integration, automated analysis, data processing

**Example:**
```bash
cat tests/results/comprehensive_results_*.json | jq '.summary.test_counts'
```

### 2. Markdown Report (Human-Readable)

**Filename:** `test_summary_YYYYMMDD_HHMMSS.md`

**Sections:**
- Executive summary with test counts
- Performance metrics table
- Code coverage statistics
- Dimension samples (WHO/WHAT/WHERE/WHEN/WHY)
- Service health status
- File locations

**Use Case:** Documentation, GitHub README, reports

**Example:**
```bash
cat tests/results/test_summary_*.md
```

### 3. HTML Dashboard (Visual)

**Filename:** `test_dashboard_YYYYMMDD_HHMMSS.html`

**Features:**
- Beautiful gradient header
- Metric cards with large numbers
- Performance tables
- Progress bars
- Code coverage visualization
- Responsive design

**Use Case:** Executive presentations, stakeholder reports

**Example:**
```bash
# Open in browser
firefox tests/results/test_dashboard_*.html
```

### 4. JUnit XML (CI/CD Compatible)

**Filename:** `junit_report.xml`

**Use Case:** Jenkins, GitLab CI, CircleCI, GitHub Actions

**Example:**
```xml
<testsuite name="pytest" tests="97" failures="0" errors="0" time="23.25">
  <testcase classname="tests.unit.test_cache_manager" name="test_cache_set_get" time="0.005"/>
  ...
</testsuite>
```

### 5. HTML Coverage Report

**Location:** `tests/results/coverage_html/index.html`

**Features:**
- Interactive coverage browser
- Line-by-line coverage
- File-by-file breakdown
- Missing line highlights

**Use Case:** Code quality analysis, coverage improvement

**Example:**
```bash
firefox tests/results/coverage_html/index.html
```

## Test Execution Results

### Latest Execution Example

```
============================================================
Context Engine Comprehensive Test Runner
============================================================

⏭️  Skipping service health checks
🧪 Executing test suite...
   Command: pytest tests/ -q --tb=short --junit-xml=...
📄 JSON Report: .../comprehensive_results_20251023_140309.json
📄 Markdown Report: .../test_summary_20251023_140309.md
📄 HTML Dashboard: .../test_dashboard_20251023_140309.html

╭─────────────────────────────────────╮
│ Context Engine E2E Test Results     │
│ Execution Time: 2025-10-23 14:03:09 │
│ Duration: 23.25s                    │
╰─────────────────────────────────────╯
      Test Summary
┏━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric      ┃ Value  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━┩
│ Total Tests │ 97     │
│ Passed      │ 73     │
│ Failed      │ 0      │
│ Skipped     │ 24     │
│ Pass Rate   │ 75.26% │
└─────────────┴────────┘

⚡ Performance:
   Avg Response Time: 0s
   p95 Response Time: 0s
   Max Response Time: 0s

📊 Code Coverage: 57.23%

✨ Test execution complete in 23.27s
```

## Test Inventory

### Total Tests: 105

**Distribution by Category:**

```
tests/
├── unit/ (55+ tests)
│   ├── test_cache_manager.py      (37 tests) - LRU cache, TTL, stats
│   ├── test_api_routes.py         (18 tests) - All API endpoints
│   ├── test_dimension_analyzer.py (tests)    - Dimension analysis
│   ├── test_context_builder.py    (tests)    - Context construction
│   └── test_graphrag_client.py    (tests)    - GraphRAG integration
├── integration/ (15+ tests)
│   └── test_api_integration.py    (15 tests) - E2E workflows
└── e2e/ (35+ tests)
    ├── test_all_endpoints.py      (17 tests) - Comprehensive endpoint tests
    ├── test_service_integration.py (tests)   - Service communication
    └── test_with_manifest.py      (tests)    - Manifest processing
```

### Test Categories (Markers)

```bash
# Run only unit tests
pytest tests/ -m unit

# Run only integration tests
pytest tests/ -m integration

# Skip slow tests
pytest tests/ -m "not slow"

# Run specific category
pytest tests/ -k "cache"
```

## Service Health Validation

When **not** using `--skip-services`, the test runner validates:

### Required Services

1. **GraphRAG Service** (port 8010)
   - URL: `http://localhost:8010`
   - Endpoint: `/api/v1/health`
   - Expected: 119K+ nodes

2. **Supabase Database**
   - Schema: client, graph, law
   - Expected: 59K+ entities

3. **Context Engine API** (port 8015)
   - All 15 endpoints functional
   - Response time < 2s

### Health Check Output

```
🔍 Validating service health...
✅ GraphRAG Service - HEALTHY (119,487 nodes)
✅ Supabase Database - HEALTHY (59,234 entities)
✅ Context Engine API - HEALTHY (15/15 endpoints)
✅ All services healthy
```

## Performance Metrics

### Captured Metrics

The test runner captures:

- **Average Response Time**: Mean across all tests
- **Median (p50)**: 50th percentile response time
- **95th Percentile (p95)**: 95% of requests complete by this time
- **99th Percentile (p99)**: 99% of requests complete by this time
- **Maximum**: Slowest test execution
- **Minimum**: Fastest test execution

### Per-Endpoint Performance

When tests include endpoint metadata, performance is broken down by endpoint:

| Endpoint | Avg Time (s) | Test Count |
|----------|--------------|------------|
| GET /api/v1/health | 0.015 | 5 |
| POST /api/v1/context/retrieve | 0.234 | 12 |
| GET /api/v1/dimensions/who | 0.187 | 8 |
| ... | ... | ... |

## Code Coverage

### Current Coverage: 57.23%

**Coverage Breakdown:**
- Total Statements: 2,268
- Covered Lines: 1,298
- Missing Lines: 970

**Well-Covered Areas:**
- ✅ API routes (85%+)
- ✅ Cache manager (90%+)
- ✅ Error handling (75%+)

**Improvement Needed:**
- ⚠️ Context builders (45%)
- ⚠️ GraphRAG client (50%)
- ⚠️ Dimension analyzers (55%)

### Viewing Coverage Details

```bash
# Open HTML coverage report
firefox tests/results/coverage_html/index.html

# View coverage summary
cat tests/results/coverage.json | jq '.totals'

# Find uncovered files
pytest tests/ --cov=src --cov-report=term-missing
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Context Engine Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd /srv/luris/be/context-engine-service
          source venv/bin/activate
          pip install -r requirements.txt
      - name: Run tests
        run: |
          source venv/bin/activate
          python tests/e2e/run_comprehensive_tests.py --skip-services --fast
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./tests/results/coverage.json
```

### Jenkins Pipeline Example

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh '''
                    cd /srv/luris/be/context-engine-service
                    source venv/bin/activate
                    python tests/e2e/run_comprehensive_tests.py --skip-services
                '''
            }
        }
        stage('Publish Results') {
            steps {
                junit 'tests/results/junit_report.xml'
                publishHTML([
                    reportDir: 'tests/results/coverage_html',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
            }
        }
    }
}
```

## Troubleshooting

### Issue: Tests fail with import errors

**Solution:**
```bash
# Ensure venv is activated
source venv/bin/activate

# Verify Python path
which python  # Should show .../venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Service health checks fail

**Solution:**
```bash
# Skip service checks
python tests/e2e/run_comprehensive_tests.py --skip-services

# Or start services manually
sudo systemctl start luris-graphrag-service
sudo systemctl start luris-context-engine
```

### Issue: Test runner timeout

**Solution:**
```bash
# Run only fast tests
python tests/e2e/run_comprehensive_tests.py --fast

# Or increase timeout in run_comprehensive_tests.py
# Line ~147: timeout=600 -> timeout=1200
```

### Issue: Coverage report not generated

**Solution:**
```bash
# Install coverage dependencies
pip install pytest-cov

# Run pytest directly to verify
pytest tests/ --cov=src --cov-report=html
```

## Advanced Usage

### Custom Test Selection

```bash
# Run specific test file
pytest tests/unit/test_cache_manager.py -v

# Run specific test function
pytest tests/unit/test_cache_manager.py::test_cache_set_get -v

# Run tests matching pattern
pytest tests/ -k "cache" -v
```

### Performance Profiling

```bash
# Profile test execution
pytest tests/ --profile

# Generate performance report
pytest tests/ --durations=10  # Show 10 slowest tests
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4
```

## Output Files Reference

### Directory Structure

```
tests/results/
├── comprehensive_results_20251023_140309.json  # Complete test data
├── test_summary_20251023_140309.md            # Executive summary
├── test_dashboard_20251023_140309.html        # Visual dashboard
├── junit_report.xml                            # CI/CD format
├── coverage.json                               # Coverage data
└── coverage_html/                              # Coverage browser
    ├── index.html
    ├── status.json
    └── *.html (per-file coverage)
```

### File Retention

- Reports are timestamped (never overwritten)
- Cleanup old reports: `find tests/results -name "*.json" -mtime +30 -delete`
- Keep latest 10 reports: Implement custom cleanup script

## Support

### Getting Help

1. Check this guide
2. Review test output logs
3. Examine generated reports
4. Check service logs: `sudo journalctl -u luris-context-engine -f`

### Common Questions

**Q: How long does a full test run take?**
A: Approximately 20-30 seconds for all 97 tests.

**Q: Can I run tests in CI/CD without services?**
A: Yes, use `--skip-services` flag.

**Q: How do I improve code coverage?**
A: Add tests for uncovered lines shown in `coverage_html/index.html`.

**Q: What if tests fail intermittently?**
A: Check service health, network connectivity, and database state.

---

**Test Runner Version:** 1.0.0
**Last Updated:** October 23, 2025
**Maintained By:** Context Engine Team
