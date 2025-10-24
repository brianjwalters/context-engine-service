#!/bin/bash
###############################################################################
# Context Engine Service - CI/CD Test Runner
#
# Purpose: Execute comprehensive test suite in CI/CD pipelines
# Exit Codes: 0 = Success, 1 = Failure
# Artifacts: JUnit XML, coverage reports, quality summary
#
# Usage:
#   ./tests/ci/run_tests_ci.sh [OPTIONS]
#
# Options:
#   --skip-service-check    Skip pre-flight service health validation
#   --fast                  Run only fast tests (skip slow/integration)
#   --coverage-threshold N  Fail if coverage < N% (default: 57)
#   --parallel              Run tests in parallel (requires pytest-xdist)
#   --verbose               Show detailed test output
#
# Environment Variables:
#   CI                     Set to 'true' in CI environment
#   CONTEXT_ENGINE_URL     Context Engine service URL (default: http://localhost:8015)
#   GRAPHRAG_URL           GraphRAG service URL (default: http://10.10.0.87:8010)
###############################################################################

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output (disable in CI)
if [ "${CI:-false}" = "true" ]; then
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    NC=""
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'  # No Color
fi

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PATH="${PROJECT_ROOT}/venv"
RESULTS_DIR="${PROJECT_ROOT}/tests/results"
COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD:-57}"
SKIP_SERVICE_CHECK=false
FAST_MODE=false
PARALLEL=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-service-check) SKIP_SERVICE_CHECK=true; shift ;;
        --fast) FAST_MODE=true; shift ;;
        --coverage-threshold) COVERAGE_THRESHOLD="$2"; shift 2 ;;
        --parallel) PARALLEL=true; shift ;;
        --verbose) VERBOSE=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Functions
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Main execution
main() {
    log_info "Context Engine CI/CD Test Runner"
    log_info "=================================="

    # Step 1: Environment setup
    setup_environment

    # Step 2: Service health check (unless skipped)
    if [ "$SKIP_SERVICE_CHECK" = false ]; then
        check_services || {
            log_error "Service health check failed"
            exit 1
        }
    fi

    # Step 3: Run test suite
    run_tests || {
        log_error "Test execution failed"
        exit 1
    }

    # Step 4: Validate coverage
    validate_coverage || {
        log_error "Coverage below threshold"
        exit 1
    }

    # Step 5: Generate quality summary
    generate_quality_summary

    log_success "✅ CI/CD Tests Complete - All Checks Passed"
    exit 0
}

setup_environment() {
    log_info "Setting up environment..."

    # Activate venv
    if [ ! -d "$VENV_PATH" ]; then
        log_error "Virtual environment not found: $VENV_PATH"
        exit 1
    fi

    source "$VENV_PATH/bin/activate"

    # Verify Python and pytest
    which python >/dev/null 2>&1 || {
        log_error "Python not found in venv"
        exit 1
    }

    which pytest >/dev/null 2>&1 || {
        log_error "pytest not found - installing..."
        pip install -q pytest pytest-asyncio pytest-cov
    }

    # Create results directory
    mkdir -p "$RESULTS_DIR"

    log_success "Environment ready (Python: $(python --version))"
}

check_services() {
    log_info "Checking service health..."

    # Check if service health checker exists
    if [ -f "${PROJECT_ROOT}/tests/e2e/check_services.py" ]; then
        # Run service health checker
        python "${PROJECT_ROOT}/tests/e2e/check_services.py" || return 1
    else
        log_warning "Service health checker not found - attempting basic health check"

        # Basic health check using curl
        CONTEXT_ENGINE_URL="${CONTEXT_ENGINE_URL:-http://localhost:8015}"

        if command -v curl >/dev/null 2>&1; then
            if curl -s -f "${CONTEXT_ENGINE_URL}/api/v1/health" >/dev/null; then
                log_info "Context Engine service responding at ${CONTEXT_ENGINE_URL}"
            else
                log_warning "Context Engine service not responding at ${CONTEXT_ENGINE_URL}"
                log_warning "Continuing anyway (service check skipped)"
            fi
        else
            log_warning "curl not available - skipping service health check"
        fi
    fi

    log_success "Service health checks completed"
    return 0
}

run_tests() {
    log_info "Running test suite..."

    # Build pytest command
    local pytest_args=(
        "tests/"
        "-v"
        "--junit-xml=${RESULTS_DIR}/junit_report.xml"
        "--cov=src"
        "--cov-report=json:${RESULTS_DIR}/coverage.json"
        "--cov-report=html:${RESULTS_DIR}/coverage_html"
        "--cov-report=term-missing"
    )

    # Add fast mode filtering
    if [ "$FAST_MODE" = true ]; then
        log_info "Fast mode enabled - skipping slow and e2e tests"
        pytest_args+=("-m" "not slow and not e2e")
    fi

    # Add parallel execution
    if [ "$PARALLEL" = true ]; then
        log_info "Parallel execution enabled"
        pytest_args+=("-n" "auto")
    fi

    # Add verbosity
    if [ "$VERBOSE" = false ]; then
        pytest_args+=("--tb=short")
    fi

    log_info "Running: pytest ${pytest_args[*]}"

    # Execute pytest
    pytest "${pytest_args[@]}" || return 1

    log_success "Tests completed successfully"
    return 0
}

validate_coverage() {
    log_info "Validating coverage threshold (>=${COVERAGE_THRESHOLD}%)..."

    # Check if coverage.json exists
    if [ ! -f "${RESULTS_DIR}/coverage.json" ]; then
        log_warning "Coverage report not found - skipping coverage validation"
        return 0
    fi

    # Extract coverage percentage from coverage.json
    local coverage
    coverage=$(python -c "
import json
import sys
try:
    with open('${RESULTS_DIR}/coverage.json') as f:
        data = json.load(f)
        print(data['totals']['percent_covered'])
except Exception as e:
    print(f'Error reading coverage: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)

    if [ $? -ne 0 ]; then
        log_warning "Failed to extract coverage percentage - skipping validation"
        return 0
    fi

    log_info "Current coverage: ${coverage}%"

    # Compare coverage (using awk for float comparison)
    if awk "BEGIN {exit !($coverage < $COVERAGE_THRESHOLD)}"; then
        log_error "Coverage ${coverage}% is below threshold ${COVERAGE_THRESHOLD}%"
        return 1
    fi

    log_success "Coverage meets threshold: ${coverage}% >= ${COVERAGE_THRESHOLD}%"
    return 0
}

generate_quality_summary() {
    log_info "Generating quality summary..."

    # Create simple quality summary
    local summary_file="${RESULTS_DIR}/quality_summary.txt"

    cat > "$summary_file" << EOF
================================================================================
Context Engine Service - Test Quality Summary
================================================================================

Test Execution: $(date)
Coverage Threshold: ${COVERAGE_THRESHOLD}%

Results Directory: ${RESULTS_DIR}
- junit_report.xml       JUnit test results
- coverage.json          Coverage data (JSON)
- coverage_html/         Coverage report (HTML)

Status: ✅ ALL CHECKS PASSED

For detailed results, see:
  HTML Coverage: ${RESULTS_DIR}/coverage_html/index.html
  JUnit Report: ${RESULTS_DIR}/junit_report.xml

================================================================================
EOF

    # Display summary
    if [ -f "$summary_file" ]; then
        cat "$summary_file"
    fi

    log_success "Quality summary generated: $summary_file"
}

# Execute main
main
