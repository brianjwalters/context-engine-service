#!/usr/bin/env python3
"""
Comprehensive Test Runner for Context Engine Service

Executes all 105 integration tests with real services and generates
detailed reports showing WHO/WHAT/WHERE/WHEN/WHY dimension data.

Usage:
    python run_comprehensive_tests.py [--skip-services] [--fast] [--report]

Options:
    --skip-services: Skip service health checks (for CI/CD)
    --fast: Run only fast tests (<1s each)
    --report: Generate HTML report
    --verbose: Show detailed test output
"""

import sys
import json
import time
import asyncio
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from tests.e2e.check_services import ServiceHealthChecker
except ImportError:
    ServiceHealthChecker = None
    print("⚠️  Warning: ServiceHealthChecker not available")


class ComprehensiveTestRunner:
    """Orchestrates complete test suite execution with rich reporting"""

    def __init__(
        self,
        skip_services: bool = False,
        fast_mode: bool = False,
        generate_report: bool = True,
        verbose: bool = False
    ):
        self.skip_services = skip_services
        self.fast_mode = fast_mode
        self.generate_report = generate_report
        self.verbose = verbose
        self.start_time = time.time()

        self.results = {
            "metadata": {
                "execution_time": datetime.now().isoformat(),
                "test_runner_version": "1.0.0",
                "project": "context-engine-service",
                "environment": "e2e"
            },
            "service_health": {},
            "test_results": {},
            "performance_metrics": {},
            "dimension_samples": {},
            "coverage": {},
            "summary": {}
        }

        self.results_dir = Path("/srv/luris/be/context-engine-service/tests/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _parse_pytest_output(self, stdout: str) -> Dict[str, Any]:
        """Parse pytest output to extract test counts and results"""
        import re

        # Look for test summary line like: "105 passed in 12.34s"
        summary_pattern = r"(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?.*in\s+([\d.]+)s"
        match = re.search(summary_pattern, stdout)

        if match:
            passed = int(match.group(1))
            failed = int(match.group(2)) if match.group(2) else 0
            skipped = int(match.group(3)) if match.group(3) else 0
            total = passed + failed + skipped

            return {
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped
                },
                "tests": []  # Would need verbose output to parse individual tests
            }

        # Fallback - try to find collected count
        collected_pattern = r"collected\s+(\d+)\s+items?"
        collected_match = re.search(collected_pattern, stdout)

        if collected_match:
            total = int(collected_match.group(1))
            return {
                "summary": {
                    "total": total,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0
                },
                "tests": []
            }

        return {
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "error": "Could not parse test output"
            },
            "tests": []
        }

    async def validate_services(self) -> bool:
        """Validate all required services are running"""
        if self.skip_services:
            print("⏭️  Skipping service health checks")
            self.results["service_health"] = {"skipped": True}
            return True

        if ServiceHealthChecker is None:
            print("⚠️  ServiceHealthChecker not available, skipping validation")
            self.results["service_health"] = {"unavailable": True}
            return True

        print("🔍 Validating service health...")
        checker = ServiceHealthChecker()

        try:
            all_healthy = await checker.check_all_services()
            self.results["service_health"] = checker.get_health_report()

            if not all_healthy:
                print("\n❌ Service health check FAILED")
                print("   Required services are not running")
                print("   Run: python tests/e2e/check_services.py")
                return False

            print("✅ All services healthy\n")
            return True
        except Exception as e:
            print(f"⚠️  Service health check error: {e}")
            self.results["service_health"] = {"error": str(e)}
            return True  # Continue anyway

    def run_test_suite(self, test_pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute pytest with comprehensive result capture

        Args:
            test_pattern: Optional pattern to filter tests (e.g., "test_cache*")

        Returns:
            Dict with test results, performance, coverage
        """
        print(f"🧪 Executing test suite...")

        # Build pytest command
        cmd = [
            "pytest",
            "tests/",
            "-v" if self.verbose else "-q",
            "--tb=short",
            "--junit-xml=" + str(self.results_dir / "junit_report.xml"),
            "--cov=src",
            f"--cov-report=html:{self.results_dir}/coverage_html",
            f"--cov-report=json:{self.results_dir}/coverage.json",
            "--cov-report=term-missing",
        ]

        # Add fast mode filter
        if self.fast_mode:
            cmd.extend(["-m", "not slow"])

        # Add test pattern filter
        if test_pattern:
            cmd.extend(["-k", test_pattern])

        # Execute tests
        print(f"   Command: {' '.join(cmd)}")
        start = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd="/srv/luris/be/context-engine-service",
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            duration = time.time() - start

            if self.verbose:
                print(result.stdout)

            # Parse results from pytest stdout
            test_results = self._parse_pytest_output(result.stdout)

            return {
                "exit_code": result.returncode,
                "duration_seconds": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_results": test_results
            }

        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "duration_seconds": 600,
                "error": "Test suite timeout after 10 minutes",
                "test_results": {"summary": {"error": "timeout"}}
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "duration_seconds": time.time() - start,
                "error": str(e),
                "test_results": {"summary": {"error": str(e)}}
            }

    def analyze_results(self, test_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze test results and extract key metrics

        Returns:
            Dict with aggregated metrics, dimension data, performance stats
        """
        results = test_output.get("test_results", {})

        # Extract test counts
        summary = results.get("summary", {})
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)

        # Calculate pass rate
        pass_rate = (passed / total * 100) if total > 0 else 0

        # Extract performance metrics
        tests = results.get("tests", [])
        response_times = []
        endpoint_performance = {}
        failed_tests = []

        for test in tests:
            # Get test duration
            call_info = test.get("call", {})
            duration = call_info.get("duration", 0)
            response_times.append(duration)

            # Track failures
            outcome = test.get("outcome", "")
            if outcome == "failed":
                failed_tests.append({
                    "name": test.get("nodeid", "unknown"),
                    "error": call_info.get("longrepr", "No error message")
                })

            # Group by endpoint if metadata available
            metadata = test.get("metadata", {})
            endpoint = metadata.get("endpoint")
            if endpoint:
                if endpoint not in endpoint_performance:
                    endpoint_performance[endpoint] = []
                endpoint_performance[endpoint].append(duration)

        # Calculate performance statistics
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            # Calculate percentiles
            sorted_times = sorted(response_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95_idx = int(len(sorted_times) * 0.95)
            p95 = sorted_times[p95_idx] if p95_idx < len(sorted_times) else max_time
            p99_idx = int(len(sorted_times) * 0.99)
            p99 = sorted_times[p99_idx] if p99_idx < len(sorted_times) else max_time
        else:
            avg_time = max_time = min_time = p50 = p95 = p99 = 0

        # Calculate endpoint averages
        endpoint_avg = {}
        for endpoint, times in endpoint_performance.items():
            endpoint_avg[endpoint] = {
                "avg_s": round(sum(times) / len(times), 3),
                "count": len(times)
            }

        return {
            "test_counts": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate_percent": round(pass_rate, 2)
            },
            "performance": {
                "avg_response_time_s": round(avg_time, 3),
                "max_response_time_s": round(max_time, 3),
                "min_response_time_s": round(min_time, 3),
                "p50_s": round(p50, 3),
                "p95_s": round(p95, 3),
                "p99_s": round(p99, 3),
                "endpoint_performance": endpoint_avg
            },
            "duration": round(test_output.get("duration_seconds", 0), 2),
            "failed_tests": failed_tests
        }

    def extract_dimension_data(self) -> Dict[str, Any]:
        """
        Extract WHO/WHAT/WHERE/WHEN/WHY dimension samples from test results

        Returns:
            Dict with sample entities from each dimension
        """
        # Load comprehensive endpoint test results
        endpoint_results_file = self.results_dir / "comprehensive_endpoint_tests.json"

        if not endpoint_results_file.exists():
            return {
                "error": "Endpoint test results not found",
                "note": "Run test_all_endpoints.py first to generate dimension samples"
            }

        try:
            with open(endpoint_results_file) as f:
                endpoint_data = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load endpoint results: {e}"}

        # Extract dimension samples
        dimension_samples = {
            "who": {
                "courts": [],
                "parties": [],
                "judges": [],
                "attorneys": []
            },
            "what": {
                "statutes": [],
                "case_citations": [],
                "legal_issues": [],
                "causes_of_action": []
            },
            "where": {
                "jurisdictions": [],
                "venues": [],
                "courts": []
            },
            "when": {
                "dates": [],
                "deadlines": [],
                "timeline_events": []
            },
            "why": {
                "precedents": [],
                "legal_theories": [],
                "arguments": [],
                "reasoning": []
            }
        }

        # Parse results and extract samples
        for result in endpoint_data.get("results", []):
            if not isinstance(result, dict):
                continue

            dimensions = result.get("dimensions", {})

            # WHO dimension
            if "who" in dimensions and isinstance(dimensions["who"], dict):
                who = dimensions["who"]
                for key in ["courts", "parties", "judges", "attorneys"]:
                    if key in who and isinstance(who[key], list):
                        dimension_samples["who"][key].extend(who[key][:3])

            # WHAT dimension
            if "what" in dimensions and isinstance(dimensions["what"], dict):
                what = dimensions["what"]
                for key in ["statutes", "case_citations", "legal_issues", "causes_of_action"]:
                    if key in what and isinstance(what[key], list):
                        dimension_samples["what"][key].extend(what[key][:3])

            # WHERE dimension
            if "where" in dimensions and isinstance(dimensions["where"], dict):
                where = dimensions["where"]
                for key in ["jurisdictions", "venues", "courts"]:
                    if key in where and isinstance(where[key], list):
                        dimension_samples["where"][key].extend(where[key][:3])

            # WHEN dimension
            if "when" in dimensions and isinstance(dimensions["when"], dict):
                when = dimensions["when"]
                for key in ["dates", "deadlines", "timeline_events"]:
                    if key in when and isinstance(when[key], list):
                        dimension_samples["when"][key].extend(when[key][:3])

            # WHY dimension
            if "why" in dimensions and isinstance(dimensions["why"], dict):
                why = dimensions["why"]
                for key in ["precedents", "legal_theories", "arguments", "reasoning"]:
                    if key in why and isinstance(why[key], list):
                        dimension_samples["why"][key].extend(why[key][:3])

        # Deduplicate samples
        for dimension in dimension_samples.values():
            for key in dimension:
                dimension[key] = list(set(dimension[key]))[:10]  # Top 10 unique

        return dimension_samples

    def load_coverage_data(self) -> Dict[str, Any]:
        """Load code coverage data from JSON report"""
        coverage_file = self.results_dir / "coverage.json"

        if not coverage_file.exists():
            return {"error": "Coverage report not found"}

        try:
            with open(coverage_file) as f:
                coverage_data = json.load(f)

            # Extract key metrics
            totals = coverage_data.get("totals", {})
            return {
                "percent_covered": round(totals.get("percent_covered", 0), 2),
                "num_statements": totals.get("num_statements", 0),
                "covered_lines": totals.get("covered_lines", 0),
                "missing_lines": totals.get("missing_lines", 0),
                "excluded_lines": totals.get("excluded_lines", 0),
                "coverage_html_path": str(self.results_dir / "coverage_html" / "index.html")
            }
        except Exception as e:
            return {"error": f"Failed to load coverage: {e}"}

    def generate_markdown_report(self, filepath: Path, analysis: Dict[str, Any]):
        """Generate executive summary in Markdown format"""
        test_counts = analysis["test_counts"]
        perf = analysis["performance"]

        content = f"""# Context Engine E2E Test Results

**Execution Time:** {self.results["metadata"]["execution_time"]}
**Test Runner Version:** {self.results["metadata"]["test_runner_version"]}
**Duration:** {analysis["duration"]}s

## Test Summary

| Metric | Value |
|--------|-------|
| Total Tests | {test_counts["total"]} |
| Passed | ✅ {test_counts["passed"]} |
| Failed | ❌ {test_counts["failed"]} |
| Skipped | ⏭️ {test_counts["skipped"]} |
| **Pass Rate** | **{test_counts["pass_rate_percent"]}%** |

## Performance Metrics

| Metric | Value |
|--------|-------|
| Average Response Time | {perf["avg_response_time_s"]}s |
| Median (p50) | {perf["p50_s"]}s |
| 95th Percentile (p95) | {perf["p95_s"]}s |
| 99th Percentile (p99) | {perf["p99_s"]}s |
| Max Response Time | {perf["max_response_time_s"]}s |
| Min Response Time | {perf["min_response_time_s"]}s |

## Code Coverage

"""

        if "coverage" in self.results:
            coverage = self.results["coverage"]
            if "error" not in coverage:
                content += f"""| Metric | Value |
|--------|-------|
| Coverage Percentage | {coverage["percent_covered"]}% |
| Total Statements | {coverage["num_statements"]} |
| Covered Lines | {coverage["covered_lines"]} |
| Missing Lines | {coverage["missing_lines"]} |

📊 **HTML Coverage Report:** `{coverage["coverage_html_path"]}`

"""

        # Endpoint Performance
        if perf.get("endpoint_performance"):
            content += "## Endpoint Performance\n\n"
            content += "| Endpoint | Avg Time (s) | Test Count |\n"
            content += "|----------|--------------|------------|\n"

            for endpoint, stats in sorted(perf["endpoint_performance"].items()):
                content += f"| {endpoint} | {stats['avg_s']} | {stats['count']} |\n"

            content += "\n"

        # Failed Tests
        if analysis.get("failed_tests"):
            content += "## Failed Tests\n\n"
            for test in analysis["failed_tests"][:10]:  # Top 10 failures
                content += f"### {test['name']}\n\n"
                content += f"```\n{test['error'][:500]}...\n```\n\n"

        # Dimension Samples
        if "dimension_samples" in self.results and "error" not in self.results["dimension_samples"]:
            content += "## WHO/WHAT/WHERE/WHEN/WHY Dimension Samples\n\n"

            dimensions = self.results["dimension_samples"]

            content += "### WHO (Participants)\n"
            who = dimensions.get("who", {})
            for key, values in who.items():
                if values:
                    content += f"- **{key.capitalize()}:** {', '.join(map(str, values[:5]))}\n"

            content += "\n### WHAT (Legal Elements)\n"
            what = dimensions.get("what", {})
            for key, values in what.items():
                if values:
                    content += f"- **{key.replace('_', ' ').title()}:** {', '.join(map(str, values[:5]))}\n"

            content += "\n### WHERE (Locations)\n"
            where = dimensions.get("where", {})
            for key, values in where.items():
                if values:
                    content += f"- **{key.capitalize()}:** {', '.join(map(str, values[:5]))}\n"

            content += "\n### WHEN (Temporal)\n"
            when = dimensions.get("when", {})
            for key, values in when.items():
                if values:
                    content += f"- **{key.capitalize()}:** {', '.join(map(str, values[:5]))}\n"

            content += "\n### WHY (Reasoning)\n"
            why = dimensions.get("why", {})
            for key, values in why.items():
                if values:
                    content += f"- **{key.replace('_', ' ').title()}:** {', '.join(map(str, values[:5]))}\n"

        content += f"""
## Service Health

"""

        if self.results["service_health"].get("skipped"):
            content += "⏭️ Service health checks were skipped\n"
        elif "services" in self.results["service_health"]:
            for service, status in self.results["service_health"]["services"].items():
                icon = "✅" if status.get("healthy") else "❌"
                content += f"- {icon} **{service}**: {status.get('status', 'unknown')}\n"

        content += f"""
## Files Generated

- JSON Report: `{self.results_dir}/comprehensive_results_*.json`
- Coverage HTML: `{self.results_dir}/coverage_html/index.html`
- Test Report JSON: `{self.results_dir}/test_report.json`

---

*Generated by Context Engine Comprehensive Test Runner v{self.results["metadata"]["test_runner_version"]}*
"""

        with open(filepath, 'w') as f:
            f.write(content)

    def generate_html_report(self, filepath: Path, analysis: Dict[str, Any]):
        """Generate visual HTML dashboard"""
        test_counts = analysis["test_counts"]
        perf = analysis["performance"]

        pass_color = "#4caf50" if test_counts["pass_rate_percent"] >= 95 else "#ff9800"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Context Engine Test Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .card h3 {{
            margin: 0 0 15px 0;
            color: #333;
            font-size: 1em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        .card .label {{
            color: #666;
            margin-top: 5px;
        }}
        .success {{ color: #4caf50; }}
        .error {{ color: #f44336; }}
        .warning {{ color: #ff9800; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #eee;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .progress-fill {{
            height: 100%;
            background: {pass_color};
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Context Engine Test Dashboard</h1>
        <p>Execution Time: {self.results["metadata"]["execution_time"]}</p>
        <p>Duration: {analysis["duration"]}s | Test Runner v{self.results["metadata"]["test_runner_version"]}</p>
    </div>

    <div class="dashboard">
        <div class="card">
            <h3>Total Tests</h3>
            <div class="value">{test_counts["total"]}</div>
            <div class="label">Test Cases Executed</div>
        </div>

        <div class="card">
            <h3>Passed</h3>
            <div class="value success">{test_counts["passed"]}</div>
            <div class="label">Successful Tests</div>
        </div>

        <div class="card">
            <h3>Failed</h3>
            <div class="value error">{test_counts["failed"]}</div>
            <div class="label">Failed Tests</div>
        </div>

        <div class="card">
            <h3>Pass Rate</h3>
            <div class="value" style="color: {pass_color};">{test_counts["pass_rate_percent"]}%</div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {test_counts['pass_rate_percent']}%;">
                    {test_counts["pass_rate_percent"]}%
                </div>
            </div>
        </div>
    </div>

    <div class="card" style="margin-bottom: 20px;">
        <h3>Performance Metrics</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Average Response Time</td>
                <td>{perf["avg_response_time_s"]}s</td>
            </tr>
            <tr>
                <td>Median (p50)</td>
                <td>{perf["p50_s"]}s</td>
            </tr>
            <tr>
                <td>95th Percentile</td>
                <td>{perf["p95_s"]}s</td>
            </tr>
            <tr>
                <td>99th Percentile</td>
                <td>{perf["p99_s"]}s</td>
            </tr>
            <tr>
                <td>Maximum</td>
                <td>{perf["max_response_time_s"]}s</td>
            </tr>
            <tr>
                <td>Minimum</td>
                <td>{perf["min_response_time_s"]}s</td>
            </tr>
        </table>
    </div>
"""

        # Coverage section
        if "coverage" in self.results and "error" not in self.results["coverage"]:
            coverage = self.results["coverage"]
            cov_color = "#4caf50" if coverage["percent_covered"] >= 80 else "#ff9800"

            html_content += f"""
    <div class="card" style="margin-bottom: 20px;">
        <h3>Code Coverage</h3>
        <div class="value" style="color: {cov_color};">{coverage["percent_covered"]}%</div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {coverage['percent_covered']}%; background: {cov_color};">
                {coverage["percent_covered"]}%
            </div>
        </div>
        <table style="margin-top: 20px;">
            <tr>
                <td>Total Statements</td>
                <td>{coverage["num_statements"]}</td>
            </tr>
            <tr>
                <td>Covered Lines</td>
                <td class="success">{coverage["covered_lines"]}</td>
            </tr>
            <tr>
                <td>Missing Lines</td>
                <td class="error">{coverage["missing_lines"]}</td>
            </tr>
        </table>
        <p style="margin-top: 15px;">
            <a href="{coverage['coverage_html_path']}" target="_blank">View Detailed Coverage Report →</a>
        </p>
    </div>
"""

        # Endpoint performance
        if perf.get("endpoint_performance"):
            html_content += """
    <div class="card">
        <h3>Endpoint Performance</h3>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>Avg Time (s)</th>
                <th>Test Count</th>
            </tr>
"""
            for endpoint, stats in sorted(perf["endpoint_performance"].items()):
                html_content += f"""
            <tr>
                <td>{endpoint}</td>
                <td>{stats['avg_s']}</td>
                <td>{stats['count']}</td>
            </tr>
"""
            html_content += """
        </table>
    </div>
"""

        html_content += """
    <footer style="text-align: center; margin-top: 40px; color: #666;">
        <p>Generated by Context Engine Comprehensive Test Runner</p>
    </footer>
</body>
</html>
"""

        with open(filepath, 'w') as f:
            f.write(html_content)

    def print_executive_summary(self, analysis: Dict[str, Any]):
        """Print executive summary to console"""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            use_rich = True
        except ImportError:
            use_rich = False

        test_counts = analysis["test_counts"]
        perf = analysis["performance"]

        if use_rich:
            console = Console()

            # Header
            console.print("\n")
            console.print(Panel.fit(
                "[bold cyan]Context Engine E2E Test Results[/bold cyan]\n"
                f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Duration: {analysis['duration']}s"
            ))

            # Test Summary Table
            table = Table(title="Test Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Tests", str(test_counts["total"]))
            table.add_row("Passed", f"[green]{test_counts['passed']}[/green]")
            table.add_row("Failed", f"[red]{test_counts['failed']}[/red]")
            table.add_row("Skipped", str(test_counts["skipped"]))
            table.add_row("Pass Rate", f"{test_counts['pass_rate_percent']}%")

            console.print(table)

            # Performance Summary
            console.print(f"\n⚡ [bold]Performance:[/bold]")
            console.print(f"   Avg Response Time: {perf['avg_response_time_s']}s")
            console.print(f"   p95 Response Time: {perf['p95_s']}s")
            console.print(f"   Max Response Time: {perf['max_response_time_s']}s")

            # Coverage
            if "coverage" in self.results and "error" not in self.results["coverage"]:
                coverage = self.results["coverage"]
                console.print(f"\n📊 [bold]Code Coverage:[/bold] {coverage['percent_covered']}%")
        else:
            # Fallback to plain text
            print("\n" + "="*60)
            print("Context Engine E2E Test Results")
            print("="*60)
            print(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Duration: {analysis['duration']}s")
            print("\nTest Summary:")
            print(f"  Total Tests: {test_counts['total']}")
            print(f"  Passed: {test_counts['passed']}")
            print(f"  Failed: {test_counts['failed']}")
            print(f"  Skipped: {test_counts['skipped']}")
            print(f"  Pass Rate: {test_counts['pass_rate_percent']}%")
            print("\nPerformance:")
            print(f"  Avg Response Time: {perf['avg_response_time_s']}s")
            print(f"  p95 Response Time: {perf['p95_s']}s")
            print(f"  Max Response Time: {perf['max_response_time_s']}s")
            print("="*60 + "\n")

    async def run(self) -> int:
        """
        Execute complete test suite with reporting

        Returns:
            Exit code (0 = success, 1 = failure)
        """
        print("\n" + "="*60)
        print("Context Engine Comprehensive Test Runner")
        print("="*60 + "\n")

        # Step 1: Validate services
        if not await self.validate_services():
            return 1

        # Step 2: Run test suite
        test_output = self.run_test_suite()
        self.results["test_results"] = test_output

        # Step 3: Analyze results
        analysis = self.analyze_results(test_output)
        self.results["summary"] = analysis

        # Step 4: Extract dimension data
        dimension_data = self.extract_dimension_data()
        self.results["dimension_samples"] = dimension_data

        # Step 5: Load coverage data
        coverage_data = self.load_coverage_data()
        self.results["coverage"] = coverage_data

        # Step 6: Generate reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON report
        json_file = self.results_dir / f"comprehensive_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 JSON Report: {json_file}")

        # Generate markdown report
        md_file = self.results_dir / f"test_summary_{timestamp}.md"
        self.generate_markdown_report(md_file, analysis)
        print(f"📄 Markdown Report: {md_file}")

        # Generate HTML report if requested
        if self.generate_report:
            html_file = self.results_dir / f"test_dashboard_{timestamp}.html"
            self.generate_html_report(html_file, analysis)
            print(f"📄 HTML Dashboard: {html_file}")

        # Step 7: Print executive summary
        self.print_executive_summary(analysis)

        # Determine exit code
        exit_code = 0 if test_output["exit_code"] == 0 else 1

        total_duration = time.time() - self.start_time
        print(f"\n✨ Test execution complete in {total_duration:.2f}s")

        return exit_code


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for Context Engine Service"
    )
    parser.add_argument(
        "--skip-services",
        action="store_true",
        help="Skip service health checks"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run only fast tests"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        default=True,
        help="Generate HTML report (default: True)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed test output"
    )

    args = parser.parse_args()

    runner = ComprehensiveTestRunner(
        skip_services=args.skip_services,
        fast_mode=args.fast,
        generate_report=args.report,
        verbose=args.verbose
    )

    exit_code = asyncio.run(runner.run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
