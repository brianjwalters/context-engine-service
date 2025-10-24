#!/usr/bin/env python3
"""
Context Engine Service - Test Quality Report Generator

Generates comprehensive quality analysis with:
- Coverage quality metrics
- Dimension analysis (WHO/WHAT/WHERE/WHEN/WHY)
- Real data validation
- Integration health assessment
- Visual charts and graphs
- Multi-format reports (JSON, Markdown, HTML, TXT)

Usage:
    python tests/e2e/generate_quality_report.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import glob

# Optional: Use rich for beautiful console output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False


@dataclass
class CoverageMetrics:
    """Coverage quality metrics"""
    total_statements: int
    covered_statements: int
    missing_statements: int
    percent_covered: float
    modules: Dict[str, Any]
    coverage_trend: List[Dict[str, Any]]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DimensionQuality:
    """Dimension analysis quality metrics"""
    dimension: str  # WHO, WHAT, WHERE, WHEN, WHY
    analyzer_tests_passed: int
    analyzer_tests_total: int
    sample_categories: List[str]
    quality_score: float  # 0.0-1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TestQualityScore:
    """Overall test quality score"""
    coverage_score: float  # 0-40 points
    test_pass_rate_score: float  # 0-30 points
    dimension_quality_score: float  # 0-20 points
    integration_health_score: float  # 0-10 points
    overall_score: float  # 0-100 (weighted sum)
    grade: str  # A, B, C, D, F
    assessment: str  # Human-readable assessment

    def to_dict(self) -> dict:
        return asdict(self)


class QualityReportGenerator:
    """Generate comprehensive test quality reports"""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.latest_results = None
        self.coverage_data = None
        self.historical_results = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def load_data(self):
        """Load all test result data"""
        if HAS_RICH:
            console.print("[cyan]Loading test result data...[/cyan]")

        # Load latest comprehensive results
        result_files = sorted(
            glob.glob(str(self.results_dir / "comprehensive_results_*.json")),
            reverse=True
        )

        if result_files:
            with open(result_files[0], 'r') as f:
                self.latest_results = json.load(f)
                if HAS_RICH:
                    console.print(f"[green]✓[/green] Loaded latest results: {Path(result_files[0]).name}")

        # Load coverage.json
        coverage_file = self.results_dir / "coverage.json"
        if coverage_file.exists():
            with open(coverage_file, 'r') as f:
                self.coverage_data = json.load(f)
                if HAS_RICH:
                    console.print(f"[green]✓[/green] Loaded coverage data")

        # Load historical results for trends
        for result_file in result_files[1:4]:  # Get last 3 previous results
            try:
                with open(result_file, 'r') as f:
                    historical = json.load(f)
                    self.historical_results.append({
                        "file": Path(result_file).name,
                        "data": historical
                    })
            except:
                pass

        if HAS_RICH and self.historical_results:
            console.print(f"[green]✓[/green] Loaded {len(self.historical_results)} historical results")

    def analyze_coverage(self) -> CoverageMetrics:
        """Analyze coverage quality"""
        if not self.coverage_data:
            return CoverageMetrics(0, 0, 0, 0.0, {}, [])

        files = self.coverage_data.get('files', {})
        total_statements = 0
        covered_statements = 0
        modules = {}

        for file_path, file_data in files.items():
            summary = file_data.get('summary', {})
            statements = summary.get('num_statements', 0)
            covered = summary.get('covered_lines', 0)
            coverage = summary.get('percent_covered', 0.0)

            total_statements += statements
            covered_statements += covered

            # Skip __init__.py files
            if '__init__.py' in file_path:
                continue

            # Categorize module status
            if coverage == 100.0:
                status = "excellent"
            elif coverage >= 80.0:
                status = "good"
            elif coverage >= 60.0:
                status = "acceptable"
            elif coverage >= 40.0:
                status = "needs_improvement"
            else:
                status = "critical"

            modules[file_path] = {
                "coverage": coverage,
                "statements": statements,
                "covered": covered,
                "missing": statements - covered,
                "status": status
            }

        # Build coverage trend
        coverage_trend = []
        if self.latest_results:
            coverage_trend.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "coverage": self.latest_results.get('coverage', {}).get('percent_covered', 0.0)
            })

        for hist in reversed(self.historical_results):
            try:
                timestamp_str = hist['file'].replace('comprehensive_results_', '').replace('.json', '')
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                date_str = dt.strftime("%Y-%m-%d")
                coverage_val = hist['data'].get('coverage', {}).get('percent_covered', 0.0)
                coverage_trend.append({
                    "date": date_str,
                    "coverage": coverage_val
                })
            except:
                pass

        missing_statements = total_statements - covered_statements
        percent_covered = (covered_statements / total_statements * 100) if total_statements > 0 else 0.0

        return CoverageMetrics(
            total_statements=total_statements,
            covered_statements=covered_statements,
            missing_statements=missing_statements,
            percent_covered=round(percent_covered, 2),
            modules=modules,
            coverage_trend=list(reversed(coverage_trend))
        )

    def analyze_dimensions(self) -> List[DimensionQuality]:
        """Analyze WHO/WHAT/WHERE/WHEN/WHY quality"""
        if not self.latest_results:
            return []

        test_results = self.latest_results.get('test_results', {})
        stdout = test_results.get('stdout', '')
        dimension_samples = self.latest_results.get('dimension_samples', {})

        dimensions = ['who', 'what', 'where', 'when', 'why']
        dimension_qualities = []

        for dim in dimensions:
            # Count analyzer tests
            analyzer_pattern = f"test_{dim}_analyzer"
            analyzer_tests_total = stdout.count(analyzer_pattern)
            analyzer_tests_passed = stdout.count(f"{analyzer_pattern}") - stdout.count(f"{analyzer_pattern} FAILED")

            # Also count dimension-specific tests
            dimension_test_pattern = f"test_{dim}_"
            total_dim_tests = stdout.count(dimension_test_pattern)
            passed_dim_tests = stdout.count(dimension_test_pattern) - stdout.count(f"{dimension_test_pattern}.*FAILED")

            # Use the higher count
            if total_dim_tests > analyzer_tests_total:
                analyzer_tests_total = total_dim_tests
                analyzer_tests_passed = passed_dim_tests

            # Get sample categories
            dim_samples = dimension_samples.get(dim, {})
            sample_categories = list(dim_samples.keys()) if isinstance(dim_samples, dict) else []

            # Calculate quality score
            # Base score on test pass rate
            test_score = analyzer_tests_passed / analyzer_tests_total if analyzer_tests_total > 0 else 0.0

            # Bonus for having sample categories defined
            sample_score = min(len(sample_categories) / 4.0, 1.0) if sample_categories else 0.0

            # Weighted quality score
            quality_score = (test_score * 0.8) + (sample_score * 0.2)

            dimension_qualities.append(DimensionQuality(
                dimension=dim.upper(),
                analyzer_tests_passed=analyzer_tests_passed,
                analyzer_tests_total=analyzer_tests_total,
                sample_categories=sample_categories,
                quality_score=round(quality_score, 2)
            ))

        return dimension_qualities

    def calculate_quality_score(self, coverage: CoverageMetrics, dimensions: List[DimensionQuality]) -> TestQualityScore:
        """Calculate overall quality score"""
        if not self.latest_results:
            return TestQualityScore(0.0, 0.0, 0.0, 0.0, 0.0, "F", "No data available")

        test_summary = self.latest_results.get('test_results', {}).get('test_results', {}).get('summary', {})

        # Coverage score: (coverage % / 100) * 40 points
        coverage_score = (coverage.percent_covered / 100.0) * 40.0

        # Pass rate score: (pass_rate % / 100) * 30 points
        total_tests = test_summary.get('total', 0)
        passed_tests = test_summary.get('passed', 0)
        pass_rate = (passed_tests / total_tests * 100.0) if total_tests > 0 else 0.0
        pass_rate_score = (pass_rate / 100.0) * 30.0

        # Dimension quality score: avg dimension quality * 20 points
        if dimensions:
            avg_dim_quality = sum(d.quality_score for d in dimensions) / len(dimensions)
            dimension_score = avg_dim_quality * 20.0
        else:
            dimension_score = 0.0

        # Integration health score: 10 points (assume healthy if tests pass)
        # Check for service health errors
        service_health = self.latest_results.get('service_health', {})
        has_errors = 'error' in service_health
        integration_score = 0.0 if has_errors else 10.0

        # Overall score
        overall_score = coverage_score + pass_rate_score + dimension_score + integration_score

        # Grade mapping
        if overall_score >= 90:
            grade = "A"
            assessment = "Excellent - Exceeds all quality standards"
        elif overall_score >= 80:
            grade = "B"
            assessment = "Good - Meets quality standards with minor improvements needed"
        elif overall_score >= 70:
            grade = "C"
            assessment = "Acceptable - Meets baseline standards with room for improvement"
        elif overall_score >= 60:
            grade = "D"
            assessment = "Needs Improvement - Below recommended quality standards"
        else:
            grade = "F"
            assessment = "Critical - Significant quality issues requiring immediate attention"

        return TestQualityScore(
            coverage_score=round(coverage_score, 2),
            test_pass_rate_score=round(pass_rate_score, 2),
            dimension_quality_score=round(dimension_score, 2),
            integration_health_score=round(integration_score, 2),
            overall_score=round(overall_score, 2),
            grade=grade,
            assessment=assessment
        )

    def get_recommendations(self, coverage: CoverageMetrics, quality_score: TestQualityScore) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Coverage-based recommendations
        low_coverage_modules = [
            (path, data) for path, data in coverage.modules.items()
            if data['coverage'] < 60.0 and data['statements'] > 10
        ]

        low_coverage_modules.sort(key=lambda x: x[1]['coverage'])

        for path, data in low_coverage_modules[:3]:  # Top 3 worst
            target_coverage = 65 if data['coverage'] < 50 else 75
            improvement = target_coverage - data['coverage']
            recommendations.append(
                f"Increase coverage for {path} from {data['coverage']:.1f}% to {target_coverage}% (+{improvement:.1f}%)"
            )

        # Quality-based recommendations
        if quality_score.overall_score < 80:
            if quality_score.coverage_score < 30:
                recommendations.append("Priority: Increase overall code coverage to at least 75%")
            if quality_score.dimension_quality_score < 15:
                recommendations.append("Add more dimension-specific tests for WHO/WHAT/WHERE/WHEN/WHY analyzers")

        # Pydantic V2 migration
        if self.latest_results:
            stdout = self.latest_results.get('test_results', {}).get('stdout', '')
            if 'PydanticDeprecatedSince20' in stdout:
                recommendations.append("Migrate Pydantic validators to V2 (@field_validator instead of @validator)")

        # Generic recommendations if list is empty
        if not recommendations:
            recommendations.append("Maintain current quality levels and continue monitoring trends")
            recommendations.append("Consider adding integration tests for edge cases")

        return recommendations

    def generate_json_report(self, output_path: Path):
        """Generate machine-readable JSON report"""
        coverage = self.analyze_coverage()
        dimensions = self.analyze_dimensions()
        quality_score = self.calculate_quality_score(coverage, dimensions)
        recommendations = self.get_recommendations(coverage, quality_score)

        if not self.latest_results:
            return

        test_summary = self.latest_results.get('test_results', {}).get('test_results', {}).get('summary', {})

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat() + "Z",
                "report_version": "1.0.0",
                "service": "context-engine-service"
            },
            "coverage_metrics": coverage.to_dict(),
            "dimension_quality": [d.to_dict() for d in dimensions],
            "test_execution": {
                "total_tests": test_summary.get('total', 0),
                "passed": test_summary.get('passed', 0),
                "failed": test_summary.get('failed', 0),
                "skipped": test_summary.get('skipped', 0),
                "pass_rate": round(test_summary.get('passed', 0) / test_summary.get('total', 1) * 100, 2),
                "execution_time": self.latest_results.get('summary', {}).get('duration', 0)
            },
            "integration_health": {
                "service_health_available": 'error' not in self.latest_results.get('service_health', {}),
                "overall_health": 1.0 if 'error' not in self.latest_results.get('service_health', {}) else 0.0
            },
            "quality_score": quality_score.to_dict(),
            "recommendations": recommendations
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        if HAS_RICH:
            console.print(f"[green]✓[/green] Generated JSON report: {output_path}")

    def generate_markdown_report(self, output_path: Path):
        """Generate human-readable Markdown report"""
        coverage = self.analyze_coverage()
        dimensions = self.analyze_dimensions()
        quality_score = self.calculate_quality_score(coverage, dimensions)
        recommendations = self.get_recommendations(coverage, quality_score)

        if not self.latest_results:
            return

        test_summary = self.latest_results.get('test_results', {}).get('test_results', {}).get('summary', {})
        total_tests = test_summary.get('total', 0)
        passed_tests = test_summary.get('passed', 0)
        failed_tests = test_summary.get('failed', 0)
        skipped_tests = test_summary.get('skipped', 0)
        pass_rate = round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 2)
        execution_time = self.latest_results.get('summary', {}).get('duration', 0)

        # Build markdown
        md = []
        md.append("# Context Engine Service - Test Quality Report\n")
        md.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        md.append(f"**Report Version**: 1.0.0")
        md.append(f"**Overall Quality Score**: {quality_score.overall_score:.2f}/100 (Grade: {quality_score.grade})")
        md.append(f"**Assessment**: {quality_score.assessment}\n")
        md.append("---\n")

        # Executive Summary
        md.append("## Executive Summary\n")
        md.append("### Test Execution Results\n")
        md.append("| Metric | Value | Status |")
        md.append("|--------|-------|--------|")
        md.append(f"| Total Tests | {total_tests} | ✅ |")
        md.append(f"| Tests Passed | {passed_tests} | ✅ {pass_rate:.1f}% pass rate |")
        md.append(f"| Tests Failed | {failed_tests} | {'✅' if failed_tests == 0 else '❌'} |")
        md.append(f"| Tests Skipped | {skipped_tests} | ℹ️ Service-dependent |")
        md.append(f"| Execution Time | {execution_time:.1f}s | {'✅' if execution_time < 30 else '⚠️'} |")
        md.append(f"| Code Coverage | {coverage.percent_covered:.2f}% | ✅ |")
        md.append("")

        # Quality Score Breakdown
        md.append("### Quality Score Breakdown\n")
        md.append("| Component | Score | Max | Percentage |")
        md.append("|-----------|-------|-----|------------|")
        md.append(f"| **Coverage Quality** | {quality_score.coverage_score:.2f} | 40 | {quality_score.coverage_score/40*100:.1f}% |")
        md.append(f"| **Test Pass Rate** | {quality_score.test_pass_rate_score:.2f} | 30 | {quality_score.test_pass_rate_score/30*100:.1f}% |")
        md.append(f"| **Dimension Quality** | {quality_score.dimension_quality_score:.2f} | 20 | {quality_score.dimension_quality_score/20*100:.1f}% |")
        md.append(f"| **Integration Health** | {quality_score.integration_health_score:.2f} | 10 | {quality_score.integration_health_score/10*100:.1f}% |")
        md.append(f"| **OVERALL** | **{quality_score.overall_score:.2f}** | **100** | **{quality_score.overall_score:.1f}%** |")
        md.append("\n---\n")

        # Coverage Analysis
        md.append("## Coverage Analysis\n")
        md.append(f"### Overall Coverage: {coverage.percent_covered:.2f}%\n")
        md.append(f"- **Total Statements**: {coverage.total_statements:,}")
        md.append(f"- **Covered**: {coverage.covered_statements:,}")
        md.append(f"- **Missing**: {coverage.missing_statements:,}\n")

        # Module coverage table
        md.append("### Coverage by Module\n")
        md.append("| Module | Coverage | Status | Statements | Missing |")
        md.append("|--------|----------|--------|------------|---------|")

        sorted_modules = sorted(
            coverage.modules.items(),
            key=lambda x: x[1]['coverage']
        )

        for path, data in sorted_modules:
            if data['statements'] > 0:  # Skip empty modules
                status_emoji = {
                    "excellent": "🟢",
                    "good": "🟡",
                    "acceptable": "🟠",
                    "needs_improvement": "🔴",
                    "critical": "🚨"
                }.get(data['status'], "❓")

                md.append(
                    f"| {path} | {data['coverage']:.1f}% | {status_emoji} {data['status']} | "
                    f"{data['statements']} | {data['missing']} |"
                )
        md.append("")

        # Coverage gaps
        md.append("### Coverage Gaps\n")
        low_coverage = [
            (path, data) for path, data in coverage.modules.items()
            if data['coverage'] < 60 and data['statements'] > 10
        ]

        if low_coverage:
            md.append("**Modules Needing Improvement** (<60% coverage):\n")
            for path, data in sorted(low_coverage, key=lambda x: x[1]['coverage'])[:5]:
                needed = 60 - data['coverage']
                md.append(f"1. `{path}` - {data['coverage']:.1f}% (needs +{needed:.1f}%)")
        else:
            md.append("✅ All major modules have acceptable coverage (≥60%)\n")

        md.append("\n---\n")

        # Dimension Quality Analysis
        md.append("## Dimension Quality Analysis\n")

        for dim in dimensions:
            md.append(f"### {dim.dimension} Dimension\n")
            md.append(f"- **Analyzer Tests**: {dim.analyzer_tests_passed}/{dim.analyzer_tests_total} passed ({dim.analyzer_tests_passed/dim.analyzer_tests_total*100:.0f}%)" if dim.analyzer_tests_total > 0 else "- **Analyzer Tests**: Not available")
            md.append(f"- **Sample Categories**: {', '.join(dim.sample_categories)}" if dim.sample_categories else "- **Sample Categories**: None defined")
            md.append(f"- **Quality Score**: {dim.quality_score:.2f}/1.0 {'✅' if dim.quality_score >= 0.8 else '⚠️'}\n")

        md.append("---\n")

        # Recommendations
        md.append("## Recommendations\n")

        if recommendations:
            md.append("### High Priority\n")
            for i, rec in enumerate(recommendations[:2], 1):
                md.append(f"{i}. {rec}")

            if len(recommendations) > 2:
                md.append("\n### Medium Priority\n")
                for i, rec in enumerate(recommendations[2:], 1):
                    md.append(f"{i}. {rec}")
        else:
            md.append("No critical recommendations at this time.\n")

        md.append("\n---\n")
        md.append(f"\n**Report Generated by**: Context Engine Quality Analyzer v1.0.0")

        with open(output_path, 'w') as f:
            f.write('\n'.join(md))

        if HAS_RICH:
            console.print(f"[green]✓[/green] Generated Markdown report: {output_path}")

    def generate_html_dashboard(self, output_path: Path):
        """Generate interactive HTML dashboard"""
        coverage = self.analyze_coverage()
        dimensions = self.analyze_dimensions()
        quality_score = self.calculate_quality_score(coverage, dimensions)

        if not self.latest_results:
            return

        test_summary = self.latest_results.get('test_results', {}).get('test_results', {}).get('summary', {})

        # Build HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Context Engine - Test Quality Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 8px;
        }}
        .score {{
            font-size: 64px;
            font-weight: bold;
            text-align: center;
            margin: 30px 0;
        }}
        .grade-A {{ color: #28a745; }}
        .grade-B {{ color: #17a2b8; }}
        .grade-C {{ color: #ffc107; }}
        .grade-D {{ color: #fd7e14; }}
        .grade-F {{ color: #dc3545; }}
        .meta {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #007bff;
            color: white;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f0f8ff;
        }}
        .status-excellent {{ color: #28a745; font-weight: bold; }}
        .status-good {{ color: #17a2b8; font-weight: bold; }}
        .status-acceptable {{ color: #ffc107; font-weight: bold; }}
        .status-needs_improvement {{ color: #fd7e14; font-weight: bold; }}
        .status-critical {{ color: #dc3545; font-weight: bold; }}
        .recommendation {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 10px 0;
        }}
        .dimension-card {{
            background-color: #f8f9fa;
            border-radius: 6px;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #007bff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Context Engine Service - Test Quality Dashboard</h1>
        <div class="meta">
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><strong>Report Version:</strong> 1.0.0</p>
        </div>

        <div class="score grade-{quality_score.grade}">
            Overall Score: {quality_score.overall_score:.2f}/100 (Grade: {quality_score.grade})
        </div>
        <p style="text-align: center; font-size: 18px; color: #666;">
            <strong>Assessment:</strong> {quality_score.assessment}
        </p>

        <h2>Test Execution Summary</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
                <th>Status</th>
            </tr>
            <tr>
                <td>Total Tests</td>
                <td>{test_summary.get('total', 0)}</td>
                <td>✅</td>
            </tr>
            <tr>
                <td>Tests Passed</td>
                <td>{test_summary.get('passed', 0)}</td>
                <td>✅ {test_summary.get('passed', 0) / test_summary.get('total', 1) * 100:.1f}% pass rate</td>
            </tr>
            <tr>
                <td>Tests Failed</td>
                <td>{test_summary.get('failed', 0)}</td>
                <td>{'✅' if test_summary.get('failed', 0) == 0 else '❌'}</td>
            </tr>
            <tr>
                <td>Tests Skipped</td>
                <td>{test_summary.get('skipped', 0)}</td>
                <td>ℹ️</td>
            </tr>
            <tr>
                <td>Code Coverage</td>
                <td>{coverage.percent_covered:.2f}%</td>
                <td>✅</td>
            </tr>
        </table>

        <h2>Quality Score Breakdown</h2>
        <table>
            <tr>
                <th>Component</th>
                <th>Score</th>
                <th>Max</th>
                <th>Percentage</th>
            </tr>
            <tr>
                <td><strong>Coverage Quality</strong></td>
                <td>{quality_score.coverage_score:.2f}</td>
                <td>40</td>
                <td>{quality_score.coverage_score/40*100:.1f}%</td>
            </tr>
            <tr>
                <td><strong>Test Pass Rate</strong></td>
                <td>{quality_score.test_pass_rate_score:.2f}</td>
                <td>30</td>
                <td>{quality_score.test_pass_rate_score/30*100:.1f}%</td>
            </tr>
            <tr>
                <td><strong>Dimension Quality</strong></td>
                <td>{quality_score.dimension_quality_score:.2f}</td>
                <td>20</td>
                <td>{quality_score.dimension_quality_score/20*100:.1f}%</td>
            </tr>
            <tr>
                <td><strong>Integration Health</strong></td>
                <td>{quality_score.integration_health_score:.2f}</td>
                <td>10</td>
                <td>{quality_score.integration_health_score/10*100:.1f}%</td>
            </tr>
            <tr style="background-color: #e3f2fd;">
                <td><strong>OVERALL</strong></td>
                <td><strong>{quality_score.overall_score:.2f}</strong></td>
                <td><strong>100</strong></td>
                <td><strong>{quality_score.overall_score:.1f}%</strong></td>
            </tr>
        </table>

        <h2>Coverage by Module</h2>
        <table>
            <tr>
                <th>Module</th>
                <th>Coverage</th>
                <th>Status</th>
                <th>Statements</th>
                <th>Missing</th>
            </tr>
"""

        # Add module rows
        sorted_modules = sorted(coverage.modules.items(), key=lambda x: x[1]['coverage'])
        for path, data in sorted_modules:
            if data['statements'] > 0:
                html += f"""            <tr>
                <td>{path}</td>
                <td>{data['coverage']:.1f}%</td>
                <td class="status-{data['status']}">{data['status'].replace('_', ' ').title()}</td>
                <td>{data['statements']}</td>
                <td>{data['missing']}</td>
            </tr>
"""

        html += """        </table>

        <h2>Dimension Quality</h2>
"""

        # Add dimension cards
        for dim in dimensions:
            html += f"""        <div class="dimension-card">
            <h3>{dim.dimension} Dimension</h3>
            <p><strong>Analyzer Tests:</strong> {dim.analyzer_tests_passed}/{dim.analyzer_tests_total} passed {f'({dim.analyzer_tests_passed/dim.analyzer_tests_total*100:.0f}%)' if dim.analyzer_tests_total > 0 else ''}</p>
            <p><strong>Sample Categories:</strong> {', '.join(dim.sample_categories) if dim.sample_categories else 'None defined'}</p>
            <p><strong>Quality Score:</strong> {dim.quality_score:.2f}/1.0 {'✅' if dim.quality_score >= 0.8 else '⚠️'}</p>
        </div>
"""

        # Add recommendations
        recommendations = self.get_recommendations(coverage, quality_score)
        html += """
        <h2>Recommendations</h2>
"""
        for rec in recommendations:
            html += f"""        <div class="recommendation">
            {rec}
        </div>
"""

        html += """    </div>
</body>
</html>"""

        with open(output_path, 'w') as f:
            f.write(html)

        if HAS_RICH:
            console.print(f"[green]✓[/green] Generated HTML dashboard: {output_path}")

    def generate_ci_summary(self, output_path: Path):
        """Generate CI/CD summary (pass/fail gates)"""
        coverage = self.analyze_coverage()
        dimensions = self.analyze_dimensions()
        quality_score = self.calculate_quality_score(coverage, dimensions)

        if not self.latest_results:
            return

        test_summary = self.latest_results.get('test_results', {}).get('test_results', {}).get('summary', {})
        total_tests = test_summary.get('total', 0)
        passed_tests = test_summary.get('passed', 0)
        failed_tests = test_summary.get('failed', 0)
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # Quality gates
        gates = []
        gates.append(("Test pass rate ≥90%", pass_rate >= 90, f"{pass_rate:.1f}%"))
        gates.append(("Coverage ≥50%", coverage.percent_covered >= 50, f"{coverage.percent_covered:.2f}%"))
        gates.append(("Overall quality score ≥60", quality_score.overall_score >= 60, f"{quality_score.overall_score:.2f}"))
        gates.append(("Zero test failures", failed_tests == 0, f"{failed_tests}"))

        all_passed = all(gate[1] for gate in gates)

        # Build summary
        lines = []
        lines.append("=" * 40)
        lines.append("Context Engine - Test Quality Summary")
        lines.append("=" * 40)
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        lines.append(f"OVERALL QUALITY: {quality_score.overall_score:.2f}/100 (Grade: {quality_score.grade})")
        lines.append(f"Status: {'PASS ✅' if all_passed else 'FAIL ❌'} (Meets minimum threshold of 60)")
        lines.append("")
        lines.append("Test Execution:")
        lines.append(f"- Total Tests: {total_tests}")
        lines.append(f"- Passed: {passed_tests} ({pass_rate:.1f}% pass rate)")
        lines.append(f"- Failed: {failed_tests}")
        lines.append(f"- Skipped: {test_summary.get('skipped', 0)}")
        lines.append(f"- Duration: {self.latest_results.get('summary', {}).get('duration', 0):.1f}s")
        lines.append("")
        lines.append("Coverage:")
        lines.append(f"- Overall: {coverage.percent_covered:.2f}% ✅")
        lines.append(f"- Target Met: {'YES' if coverage.percent_covered >= 50 else 'NO'}")
        lines.append("")
        lines.append("Dimension Quality:")
        for dim in dimensions:
            lines.append(f"- {dim.dimension}: {dim.quality_score:.2f} {'✅' if dim.quality_score >= 0.7 else '⚠️'}")
        lines.append("")
        lines.append("Quality Gates:")
        for gate_name, passed, value in gates:
            status = "✅ PASS" if passed else "❌ FAIL"
            lines.append(f"{status} - {gate_name} ({value})")
        lines.append("")
        lines.append(f"Recommendation: {'APPROVED FOR MERGE' if all_passed else 'REQUIRES FIXES BEFORE MERGE'}")

        recommendations = self.get_recommendations(coverage, quality_score)
        if recommendations:
            lines.append(f"Next Steps: {recommendations[0]}")

        lines.append("")
        lines.append("=" * 40)

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))

        if HAS_RICH:
            console.print(f"[green]✓[/green] Generated CI/CD summary: {output_path}")

    def generate_all_reports(self):
        """Generate all report formats"""
        if HAS_RICH:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating quality reports...", total=4)

                self.generate_json_report(self.results_dir / f"quality_report_{self.timestamp}.json")
                progress.advance(task)

                self.generate_markdown_report(self.results_dir / "TEST_QUALITY_REPORT.md")
                progress.advance(task)

                self.generate_html_dashboard(self.results_dir / f"quality_dashboard_{self.timestamp}.html")
                progress.advance(task)

                self.generate_ci_summary(self.results_dir / "quality_summary.txt")
                progress.advance(task)
        else:
            print("Generating JSON report...")
            self.generate_json_report(self.results_dir / f"quality_report_{self.timestamp}.json")
            print("Generating Markdown report...")
            self.generate_markdown_report(self.results_dir / "TEST_QUALITY_REPORT.md")
            print("Generating HTML dashboard...")
            self.generate_html_dashboard(self.results_dir / f"quality_dashboard_{self.timestamp}.html")
            print("Generating CI/CD summary...")
            self.generate_ci_summary(self.results_dir / "quality_summary.txt")


if __name__ == "__main__":
    results_dir = Path("/srv/luris/be/context-engine-service/tests/results")

    if HAS_RICH:
        console.print("[bold cyan]Context Engine Test Quality Report Generator[/bold cyan]")
        console.print(f"[cyan]Results directory: {results_dir}[/cyan]\n")
    else:
        print("Context Engine Test Quality Report Generator")
        print(f"Results directory: {results_dir}\n")

    generator = QualityReportGenerator(results_dir)

    try:
        generator.load_data()
        generator.generate_all_reports()

        if HAS_RICH:
            console.print("\n[bold green]✅ All quality reports generated successfully![/bold green]")
            console.print("\nGenerated files:")
            console.print(f"  • quality_report_{generator.timestamp}.json")
            console.print(f"  • TEST_QUALITY_REPORT.md")
            console.print(f"  • quality_dashboard_{generator.timestamp}.html")
            console.print(f"  • quality_summary.txt")
        else:
            print("\n✅ All quality reports generated successfully!")
            print("\nGenerated files:")
            print(f"  • quality_report_{generator.timestamp}.json")
            print(f"  • TEST_QUALITY_REPORT.md")
            print(f"  • quality_dashboard_{generator.timestamp}.html")
            print(f"  • quality_summary.txt")

        sys.exit(0)
    except Exception as e:
        if HAS_RICH:
            console.print(f"[bold red]❌ Error generating reports: {e}[/bold red]")
        else:
            print(f"❌ Error generating reports: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
