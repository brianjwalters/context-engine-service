#!/usr/bin/env python3
"""
Service Health Check Script for Context Engine E2E Tests

Verifies all required services are running before test execution.
Exit code 0 = all services healthy
Exit code 1 = one or more critical services down

Usage:
    python check_services.py
    ./check_services.py
"""

import sys
import asyncio
import httpx
from typing import Tuple, List
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from rich.console import Console
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  'rich' package not installed. Install with: pip install rich")

from src.clients.supabase_client import create_supabase_client


class ServiceHealthChecker:
    """Comprehensive health checker for all Context Engine dependencies"""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.results: List[Tuple[str, bool, str]] = []

    def print_message(self, message: str, style: str = ""):
        """Print message with or without rich formatting"""
        if self.console:
            self.console.print(message, style=style)
        else:
            # Strip rich markup for plain output
            clean_message = message.replace("[bold cyan]", "").replace("[/bold cyan]", "")
            clean_message = clean_message.replace("[bold green]", "").replace("[/bold green]", "")
            clean_message = clean_message.replace("[bold red]", "").replace("[/bold red]", "")
            clean_message = clean_message.replace("[yellow]", "").replace("[/yellow]", "")
            print(clean_message)

    async def check_http_service(
        self,
        name: str,
        url: str,
        required: bool = True,
        validate_json: bool = False
    ) -> Tuple[str, bool, str]:
        """
        Check HTTP service health

        Args:
            name: Service name for display
            url: Health check endpoint URL
            required: Whether service is critical (affects exit code)
            validate_json: Whether to validate JSON response

        Returns:
            Tuple of (service_name, is_healthy, status_message)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)

            if response.status_code == 200:
                # Additional validation for JSON responses
                if validate_json:
                    try:
                        data = response.json()
                        # Check for common health indicators
                        if isinstance(data, dict):
                            status = data.get('status', data.get('healthy', 'unknown'))
                            return (name, True, f"✅ Healthy ({status})")
                    except Exception:
                        pass

                return (name, True, f"✅ Healthy (200 OK)")
            else:
                status = "❌ CRITICAL" if required else "⚠️  Warning"
                return (name, not required, f"{status} - HTTP {response.status_code}")

        except httpx.ConnectError:
            status = "❌ CRITICAL" if required else "⚠️  Optional"
            return (name, not required, f"{status} - Connection refused")
        except httpx.TimeoutException:
            status = "❌ CRITICAL" if required else "⚠️  Optional"
            return (name, not required, f"{status} - Timeout (>5s)")
        except Exception as e:
            status = "❌ CRITICAL" if required else "⚠️  Optional"
            error_msg = str(e)[:50]
            return (name, not required, f"{status} - {error_msg}")

    async def check_vllm_models(self, name: str, url: str) -> Tuple[str, bool, str]:
        """
        Check vLLM service and list available models

        Args:
            name: Service name for display
            url: Models endpoint URL (/v1/models)

        Returns:
            Tuple of (service_name, is_healthy, status_message)
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)

            if response.status_code == 200:
                try:
                    data = response.json()
                    models = data.get('data', [])
                    if models:
                        model_name = models[0].get('id', 'unknown')
                        return (name, True, f"✅ Healthy (model: {model_name})")
                    else:
                        return (name, True, f"✅ Healthy (no models loaded)")
                except Exception:
                    return (name, True, f"✅ Healthy (200 OK)")
            else:
                return (name, False, f"⚠️  Optional - HTTP {response.status_code}")

        except Exception as e:
            return (name, False, f"⚠️  Optional - {str(e)[:40]}")

    async def check_database(self) -> Tuple[str, bool, str]:
        """
        Check Supabase database connection and data availability

        Returns:
            Tuple of (service_name, is_healthy, status_message)
        """
        try:
            client = create_supabase_client(service_name="health-check")

            # Check graph.nodes count
            nodes_result = await client.schema('graph').table('nodes') \
                .select('count', count='exact') \
                .execute()
            nodes_count = nodes_result.count if nodes_result.count is not None else 0

            # Check law.entities count
            entities_result = await client.schema('law').table('entities') \
                .select('count', count='exact') \
                .execute()
            entities_count = entities_result.count if entities_result.count is not None else 0

            message = f"✅ Connected ({nodes_count:,} nodes, {entities_count:,} entities)"
            return ("Supabase Database", True, message)

        except Exception as e:
            error_msg = str(e)[:60]
            return ("Supabase Database", False, f"❌ CRITICAL - {error_msg}")

    async def check_graph_data_quality(self) -> Tuple[str, bool, str]:
        """
        Check graph data quality (client_id compliance)

        Returns:
            Tuple of (service_name, is_healthy, status_message)
        """
        try:
            client = create_supabase_client(service_name="health-check")

            # Check for nodes missing client_id
            nulls_result = await client.schema('graph').table('nodes') \
                .select('count', count='exact') \
                .is_('client_id', 'null') \
                .execute()
            null_count = nulls_result.count if nulls_result.count is not None else 0

            if null_count == 0:
                return ("Graph Data Quality", True, "✅ 100% client_id compliance")
            else:
                return ("Graph Data Quality", True, f"⚠️  {null_count} nodes missing client_id")

        except Exception as e:
            # Non-critical check
            return ("Graph Data Quality", True, f"⚠️  Could not verify - {str(e)[:40]}")

    def display_results_table(self, results: List[Tuple[str, bool, str]]):
        """Display results in a formatted table"""
        if self.console and RICH_AVAILABLE:
            table = Table(title="Service Health Status", show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan", width=25)
            table.add_column("Status", style="green", width=50)

            for name, is_healthy, message in results:
                # Color code based on status
                if "✅" in message:
                    style = "green"
                elif "❌ CRITICAL" in message:
                    style = "red"
                else:
                    style = "yellow"

                table.add_row(name, f"[{style}]{message}[/{style}]")

            self.console.print(table)
        else:
            # Plain text table
            print("\n" + "=" * 80)
            print(f"{'Service':<25} {'Status':<50}")
            print("=" * 80)
            for name, is_healthy, message in results:
                print(f"{name:<25} {message:<50}")
            print("=" * 80)

    async def run_checks(self) -> bool:
        """
        Run all health checks

        Returns:
            True if all required services are healthy, False otherwise
        """
        self.print_message("\n[bold cyan]🔍 Checking Service Health...[/bold cyan]\n")

        # Define services to check (order matters for display)
        checks = [
            # Critical services (required=True)
            self.check_http_service(
                "GraphRAG Service",
                "http://localhost:8010/api/v1/health",
                required=True,
                validate_json=True
            ),
            self.check_http_service(
                "Context Engine",
                "http://localhost:8015/api/v1/health",
                required=True,
                validate_json=True
            ),
            self.check_http_service(
                "Prompt Service",
                "http://localhost:8003/api/v1/health",
                required=True,
                validate_json=True
            ),
            self.check_database(),
            self.check_graph_data_quality(),

            # Optional vLLM services (required=False)
            self.check_vllm_models(
                "vLLM Instruct (8080)",
                "http://localhost:8080/v1/models"
            ),
            self.check_vllm_models(
                "vLLM Thinking (8082)",
                "http://localhost:8082/v1/models"
            ),
            self.check_vllm_models(
                "vLLM Embeddings (8081)",
                "http://localhost:8081/v1/models"
            ),
        ]

        # Run checks concurrently
        results = await asyncio.gather(*checks)

        # Display results table
        self.display_results_table(results)

        # Determine overall health
        all_healthy = all(is_healthy for _, is_healthy, _ in results)
        critical_failures = [
            (name, message) for name, is_healthy, message in results
            if not is_healthy and "CRITICAL" in message
        ]

        # Print summary
        print()  # Blank line
        if all_healthy:
            self.print_message("[bold green]✅ All required services are healthy![/bold green]")
        elif not critical_failures:
            self.print_message("[bold green]✅ All critical services are healthy![/bold green]")
            self.print_message("[yellow]⚠️  Some optional services are unavailable (tests may have limited functionality)[/yellow]")
        else:
            self.print_message("[bold red]❌ One or more critical services are down![/bold red]")
            self.print_message("[yellow]Please start missing services before running tests:[/yellow]")
            for name, message in critical_failures:
                self.print_message(f"   • {name}: {message}")

        print()  # Blank line

        # Return True if no critical failures
        return len(critical_failures) == 0


async def main():
    """Main entry point"""
    checker = ServiceHealthChecker()

    try:
        all_healthy = await checker.run_checks()
        sys.exit(0 if all_healthy else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Health check interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print(f"\n❌ Unexpected error during health check: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
