import yaml
import asyncio
import aiohttp
import time
import statistics
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
import argparse
import copy


@dataclass
class PerformanceMetrics:
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float
    success_rate: float
    error_rate: float
    errors: List[str]
    block_index: Optional[int] = None
    individual_timings: Optional[List[Dict[str, Any]]] = None  # For verbose mode


@dataclass
class AggregatedMetrics:
    endpoint: str
    block_range: Optional[tuple] = None
    total_blocks_tested: int = 0
    total_requests_all_blocks: int = 0
    successful_requests_all_blocks: int = 0
    failed_requests_all_blocks: int = 0
    avg_response_time_all_blocks: float = 0
    min_response_time_all_blocks: float = 0
    max_response_time_all_blocks: float = 0
    throughput_all_blocks: float = 0
    success_rate_all_blocks: float = 0
    error_rate_all_blocks: float = 0
    block_metrics: List[PerformanceMetrics] = field(default_factory=list)


class PerformanceTester:
    def __init__(self, config_path: str, verbose: bool = False):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.base_url = self.config.get("base-url", "https://example.com")
        self.perf_config = self.config.get("performance", {})
        self.concurrent_requests = self.perf_config.get("concurrent-requests", 10)
        self.total_requests = self.perf_config.get("total-requests", 100)
        self.timeout = self.perf_config.get("timeout-seconds", 30)
        self.warm_up_requests = self.perf_config.get("warm-up-requests", 10)
        self.verbose = verbose

        # Block range configuration
        self.block_range_config = self.config.get("block-range", {})
        self.use_block_range = self.block_range_config.get("enabled", False)
        self.block_start = self.block_range_config.get("start", 1)
        self.block_end = self.block_range_config.get("end", 1)

    def update_block_index(
        self, payload: Dict[str, Any], block_index: int
    ) -> Dict[str, Any]:
        """Recursively update block_identifier.index in the payload"""
        updated_payload = copy.deepcopy(payload)

        def update_dict(d: Dict[str, Any]):
            if "block_identifier" in d and isinstance(d["block_identifier"], dict):
                if "index" in d["block_identifier"]:
                    d["block_identifier"]["index"] = block_index

            for key, value in d.items():
                if isinstance(value, dict):
                    update_dict(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            update_dict(item)

        update_dict(updated_payload)
        return updated_payload

    async def make_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: Dict[str, Any],
        request_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint['path']}"
        start_time = time.time()

        try:
            async with session.request(
                method=endpoint["method"],
                url=url,
                json=endpoint.get("payload", {}),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                await response.text()
                end_time = time.time()

                result = {
                    "success": True,
                    "response_time": end_time - start_time,
                    "status_code": response.status,
                    "error": None,
                    "timestamp": start_time,
                }
                if request_id is not None:
                    result["request_id"] = request_id
                return result
        except Exception as e:
            end_time = time.time()
            result = {
                "success": False,
                "response_time": end_time - start_time,
                "status_code": None,
                "error": str(e),
                "timestamp": start_time,
            }
            if request_id is not None:
                result["request_id"] = request_id
            return result

    async def warm_up(self, endpoint: Dict[str, Any]):
        print(f"Warming up {endpoint['path']} with {self.warm_up_requests} requests...")
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.make_request(session, endpoint)
                for _ in range(self.warm_up_requests)
            ]
            await asyncio.gather(*tasks)

    async def test_endpoint_concurrency(
        self, endpoint: Dict[str, Any], block_index: Optional[int] = None
    ) -> PerformanceMetrics:
        if block_index is not None:
            print(
                f"Testing {endpoint['path']} - Block {block_index} - {self.total_requests} requests with {self.concurrent_requests} concurrent"
            )
        else:
            print(
                f"Testing {endpoint['path']} - {self.total_requests} requests with {self.concurrent_requests} concurrent"
            )

        # Create endpoint with updated block index if needed
        test_endpoint = endpoint.copy()
        if block_index is not None and "payload" in test_endpoint:
            test_endpoint["payload"] = self.update_block_index(
                test_endpoint["payload"], block_index
            )

        await self.warm_up(test_endpoint)

        results = []
        errors = []

        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.concurrent_requests)

            async def bounded_request(req_id: int):
                async with semaphore:
                    return await self.make_request(
                        session, test_endpoint, req_id if self.verbose else None
                    )

            start_time = time.time()
            tasks = [bounded_request(i) for i in range(self.total_requests)]
            results = await asyncio.gather(*tasks)
            end_time = time.time()

        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]

        response_times = [r["response_time"] for r in successful_results]
        errors = [r["error"] for r in failed_results if r["error"]]

        total_time = end_time - start_time

        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = (
                statistics.quantiles(response_times, n=20)[18]
                if len(response_times) > 1
                else response_times[0]
            )
            p99_response_time = (
                statistics.quantiles(response_times, n=100)[98]
                if len(response_times) > 1
                else response_times[0]
            )
        else:
            avg_response_time = min_response_time = max_response_time = (
                p95_response_time
            ) = p99_response_time = 0

        # Store individual timings if verbose mode is enabled
        individual_timings = None
        if self.verbose:
            individual_timings = results

        return PerformanceMetrics(
            endpoint=endpoint["path"],
            total_requests=self.total_requests,
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput=len(successful_results) / total_time,
            success_rate=(len(successful_results) / self.total_requests) * 100,
            error_rate=(len(failed_results) / self.total_requests) * 100,
            errors=list(set(errors)),
            block_index=block_index,
            individual_timings=individual_timings,
        )

    def aggregate_block_metrics(
        self, endpoint: Dict[str, Any], block_metrics: List[PerformanceMetrics]
    ) -> AggregatedMetrics:
        """Aggregate metrics across multiple blocks"""
        total_requests = sum(m.total_requests for m in block_metrics)
        total_successful = sum(m.successful_requests for m in block_metrics)
        total_failed = sum(m.failed_requests for m in block_metrics)

        all_response_times = []
        for m in block_metrics:
            if m.avg_response_time > 0:
                all_response_times.extend([m.avg_response_time] * m.successful_requests)

        avg_response_time = (
            statistics.mean(all_response_times) if all_response_times else 0
        )
        min_response_time = (
            min(m.min_response_time for m in block_metrics if m.min_response_time > 0)
            if block_metrics
            else 0
        )
        max_response_time = max(m.max_response_time for m in block_metrics)
        avg_throughput = statistics.mean([m.throughput for m in block_metrics])

        return AggregatedMetrics(
            endpoint=endpoint["path"],
            block_range=(self.block_start, self.block_end),
            total_blocks_tested=len(block_metrics),
            total_requests_all_blocks=total_requests,
            successful_requests_all_blocks=total_successful,
            failed_requests_all_blocks=total_failed,
            avg_response_time_all_blocks=avg_response_time,
            min_response_time_all_blocks=min_response_time,
            max_response_time_all_blocks=max_response_time,
            throughput_all_blocks=avg_throughput,
            success_rate_all_blocks=(
                (total_successful / total_requests * 100) if total_requests > 0 else 0
            ),
            error_rate_all_blocks=(
                (total_failed / total_requests * 100) if total_requests > 0 else 0
            ),
            block_metrics=block_metrics,
        )

    async def run_all_tests(self) -> List[Any]:
        all_results = []

        for endpoint in self.config["endpoints"]:
            print(f"\n{'=' * 60}")
            print(f"Testing endpoint: {endpoint['path']}")
            print(f"{'=' * 60}")

            uses_block_index = endpoint.get("uses-block-index", False)

            if self.use_block_range and uses_block_index:
                # Test with block range
                print(f"Using block range: {self.block_start} to {self.block_end}")
                block_metrics = []

                for block_index in range(self.block_start, self.block_end + 1):
                    metrics = await self.test_endpoint_concurrency(
                        endpoint, block_index
                    )
                    block_metrics.append(metrics)
                    self.print_metrics(metrics)

                # Aggregate results
                aggregated = self.aggregate_block_metrics(endpoint, block_metrics)
                all_results.append(aggregated)
                self.print_aggregated_metrics(aggregated)
            else:
                # Test without block range
                metrics = await self.test_endpoint_concurrency(endpoint)
                all_results.append(metrics)
                self.print_metrics(metrics)

        return all_results

    def print_metrics(self, metrics: PerformanceMetrics):
        block_info = (
            f" (Block {metrics.block_index})" if metrics.block_index is not None else ""
        )
        print(f"\nPerformance Results for {metrics.endpoint}{block_info}:")
        print(f"  Total Requests: {metrics.total_requests}")
        print(f"  Successful: {metrics.successful_requests}")
        print(f"  Failed: {metrics.failed_requests}")
        print(f"  Success Rate: {metrics.success_rate:.2f}%")
        print(f"  Error Rate: {metrics.error_rate:.2f}%")
        print(f"  Average Response Time: {metrics.avg_response_time * 1000:.2f}ms")
        print(f"  Min Response Time: {metrics.min_response_time * 1000:.2f}ms")
        print(f"  Max Response Time: {metrics.max_response_time * 1000:.2f}ms")
        print(f"  95th Percentile: {metrics.p95_response_time * 1000:.2f}ms")
        print(f"  99th Percentile: {metrics.p99_response_time * 1000:.2f}ms")
        print(f"  Throughput: {metrics.throughput:.2f} req/sec")

        if metrics.errors:
            print("  Errors encountered:")
            for error in metrics.errors:
                print(f"    - {error}")

    def print_aggregated_metrics(self, aggregated: AggregatedMetrics):
        print(f"\n{'=' * 40}")
        print(f"AGGREGATED RESULTS for {aggregated.endpoint}")
        if aggregated.block_range:
            print(
                f"Block Range: {aggregated.block_range[0]} to {aggregated.block_range[1]}"
            )
        print(f"Total Blocks Tested: {aggregated.total_blocks_tested}")
        print(f"{'=' * 40}")
        print(f"  Total Requests (all blocks): {aggregated.total_requests_all_blocks}")
        print(f"  Successful (all blocks): {aggregated.successful_requests_all_blocks}")
        print(f"  Failed (all blocks): {aggregated.failed_requests_all_blocks}")
        print(f"  Overall Success Rate: {aggregated.success_rate_all_blocks:.2f}%")
        print(f"  Overall Error Rate: {aggregated.error_rate_all_blocks:.2f}%")
        print(
            f"  Average Response Time: {aggregated.avg_response_time_all_blocks * 1000:.2f}ms"
        )
        print(
            f"  Min Response Time: {aggregated.min_response_time_all_blocks * 1000:.2f}ms"
        )
        print(
            f"  Max Response Time: {aggregated.max_response_time_all_blocks * 1000:.2f}ms"
        )
        print(f"  Average Throughput: {aggregated.throughput_all_blocks:.2f} req/sec")

    def generate_report(self, all_results: List[Any], output_file: Any):
        report = {
            "test_summary": {
                "test_name": self.config.get("test-name", "performance-test"),
                "total_endpoints": len(all_results),
                "concurrent_requests": self.concurrent_requests,
                "total_requests_per_endpoint": self.total_requests,
                "timeout_seconds": self.timeout,
            },
            "results": [],
        }

        for result in all_results:
            if isinstance(result, AggregatedMetrics):
                report_item = {
                    "endpoint": result.endpoint,
                    "block_range": result.block_range,
                    "total_blocks_tested": result.total_blocks_tested,
                    "total_requests_all_blocks": result.total_requests_all_blocks,
                    "successful_requests_all_blocks": result.successful_requests_all_blocks,
                    "failed_requests_all_blocks": result.failed_requests_all_blocks,
                    "avg_response_time_all_blocks": result.avg_response_time_all_blocks,
                    "min_response_time_all_blocks": result.min_response_time_all_blocks,
                    "max_response_time_all_blocks": result.max_response_time_all_blocks,
                    "throughput_all_blocks": result.throughput_all_blocks,
                    "success_rate_all_blocks": result.success_rate_all_blocks,
                    "error_rate_all_blocks": result.error_rate_all_blocks,
                    "block_metrics": [],
                }

                # Include block metrics with optional individual timings
                for m in result.block_metrics:
                    block_metric = asdict(m)
                    if not self.verbose and "individual_timings" in block_metric:
                        block_metric.pop("individual_timings")
                    report_item["block_metrics"].append(block_metric)

                report["results"].append(report_item)
            elif isinstance(result, PerformanceMetrics):
                metric_dict = asdict(result)
                if not self.verbose and "individual_timings" in metric_dict:
                    metric_dict.pop("individual_timings")
                report["results"].append(metric_dict)

        if output_file:
            # Create results directory if it doesn't exist
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            with open(output_file, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\nDetailed report saved to: {output_file}")

        print(f"\n{'=' * 80}")
        print("SUMMARY REPORT")
        print(f"{'=' * 80}")

        # Calculate totals for both PerformanceMetrics and AggregatedMetrics
        total_requests = 0
        total_successful = 0
        throughputs = []
        response_times = []

        for result in all_results:
            if isinstance(result, PerformanceMetrics):
                total_requests += result.total_requests
                total_successful += result.successful_requests
                throughputs.append(result.throughput)
                if result.avg_response_time > 0:
                    response_times.append(result.avg_response_time)
            elif isinstance(result, AggregatedMetrics):
                total_requests += result.total_requests_all_blocks
                total_successful += result.successful_requests_all_blocks
                throughputs.append(result.throughput_all_blocks)
                if result.avg_response_time_all_blocks > 0:
                    response_times.append(result.avg_response_time_all_blocks)

        overall_success_rate = (
            (total_successful / total_requests * 100) if total_requests > 0 else 0
        )
        avg_throughput = statistics.mean(throughputs) if throughputs else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0

        print(f"Overall Success Rate: {overall_success_rate:.2f}%")
        print(f"Average Throughput: {avg_throughput:.2f} req/sec")
        print(f"Average Response Time: {avg_response_time * 1000:.2f}ms")

        print("\nEndpoint Performance Summary:")
        for result in all_results:
            if isinstance(result, PerformanceMetrics):
                print(
                    f"  {result.endpoint:<20} | "
                    f"Success: {result.success_rate:6.2f}% | "
                    f"Avg RT: {result.avg_response_time * 1000:7.2f}ms | "
                    f"Throughput: {result.throughput:6.2f} req/sec"
                )
            elif isinstance(result, AggregatedMetrics):
                print(
                    f"  {result.endpoint:<20} | "
                    f"Success: {result.success_rate_all_blocks:6.2f}% | "
                    f"Avg RT: {result.avg_response_time_all_blocks * 1000:7.2f}ms | "
                    f"Throughput: {result.throughput_all_blocks:6.2f} req/sec"
                )


async def main():
    parser = argparse.ArgumentParser(
        description="Run performance tests for mesh-reth-sdk"
    )
    parser.add_argument(
        "--config",
        default="config/data-test-config.yml",
        help="Path to the test configuration file",
    )
    parser.add_argument("--output", help="Output file for detailed JSON report")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose mode to save individual request timings",
    )

    args = parser.parse_args()

    # Generate default output filename with timestamp if not specified
    if not args.output:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        args.output = f"results/{timestamp}.json"

    try:
        tester = PerformanceTester(args.config, verbose=args.verbose)
        print(f"Starting performance tests with configuration: {args.config}")
        print("Test Parameters:")
        print(f"  Base URL: {tester.base_url}")
        print(f"  Concurrent Requests: {tester.concurrent_requests}")
        print(f"  Total Requests per Endpoint: {tester.total_requests}")
        print(f"  Timeout: {tester.timeout}s")
        print(f"  Warm-up Requests: {tester.warm_up_requests}")
        print(f"  Verbose Mode: {tester.verbose}")

        all_results = await tester.run_all_tests()
        tester.generate_report(all_results, args.output)

    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found.")
        return 1
    except Exception as e:
        print(f"Error running performance tests: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
