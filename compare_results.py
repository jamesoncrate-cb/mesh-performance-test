#!/usr/bin/env python3
"""
Compare two performance test results and visualize the differences.

This script creates bar charts comparing p50, p95, and p99 response times
between two test runs.
"""

import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import os
from matplotlib import rcParams

# Configure matplotlib for better-looking plots
rcParams["font.family"] = "sans-serif"
rcParams["font.sans-serif"] = [
    "Arial",
    "DejaVu Sans",
    "Liberation Sans",
    "Bitstream Vera Sans",
    "sans-serif",
]
rcParams["font.size"] = 12
rcParams["axes.labelsize"] = 14
rcParams["axes.titlesize"] = 16
rcParams["xtick.labelsize"] = 11
rcParams["ytick.labelsize"] = 11
rcParams["legend.fontsize"] = 11
rcParams["figure.titlesize"] = 18

# Modern color palette
COLORS = {
    "test1": "#2E86AB",  # Blue
    "test2": "#C45508",  # Orange
    "accent": "#F18F01",  # Orange
    "success": "#2A9D8F",  # Teal
    "danger": "#E76F51",  # Red
    "background": "#F8F9FA",  # Light gray
    "grid": "#E9ECEF",  # Lighter gray
    "text": "#212529",  # Dark gray
}


class PerformanceComparator:
    def __init__(
        self, json_file1: str, json_file2: str, output_dir: str = "comparisons"
    ):
        with open(json_file1, "r") as f:
            self.data1 = json.load(f)
        with open(json_file2, "r") as f:
            self.data2 = json.load(f)

        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Extract test names or use file names
        self.test1_name = self._get_test_name(self.data1, json_file1)
        self.test2_name = self._get_test_name(self.data2, json_file2)

    def _get_test_name(self, data: Dict, filename: str) -> str:
        """Extract test name from data or use filename."""
        if "test_summary" in data and "test_name" in data["test_summary"]:
            return data["test_summary"]["test_name"]
        return os.path.basename(filename).replace(".json", "")

    def extract_timings(self, result: Dict[str, Any]) -> List[float]:
        """Extract successful response times from a result."""
        timings = []

        if "individual_timings" in result and result["individual_timings"]:
            for timing in result["individual_timings"]:
                if timing["success"]:
                    timings.append(timing["response_time"])

        if "block_metrics" in result:
            for block_metric in result["block_metrics"]:
                if (
                    "individual_timings" in block_metric
                    and block_metric["individual_timings"]
                ):
                    for timing in block_metric["individual_timings"]:
                        if timing["success"]:
                            timings.append(timing["response_time"])

        return timings

    def calculate_percentiles(
        self, response_times: List[float]
    ) -> Tuple[float, float, float]:
        """Calculate p50, p95, and p99 in milliseconds."""
        if not response_times:
            return 0, 0, 0

        times_ms = [rt * 1000 for rt in response_times]
        p50 = np.percentile(times_ms, 50)
        p95 = np.percentile(times_ms, 95)
        p99 = np.percentile(times_ms, 99)

        return p50, p95, p99

    def create_comparison_bar_chart(self):
        """Create bar charts comparing p50, p95, and p99 for all endpoints."""
        # Collect metrics for both test runs
        endpoints = set()
        metrics1 = {}
        metrics2 = {}

        # Process first test
        for result in self.data1["results"]:
            endpoint = result["endpoint"]
            endpoints.add(endpoint)
            response_times = self.extract_timings(result)
            p50, p95, p99 = self.calculate_percentiles(response_times)
            metrics1[endpoint] = {
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "count": len(response_times),
            }

        # Process second test
        for result in self.data2["results"]:
            endpoint = result["endpoint"]
            endpoints.add(endpoint)
            response_times = self.extract_timings(result)
            p50, p95, p99 = self.calculate_percentiles(response_times)
            metrics2[endpoint] = {
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "count": len(response_times),
            }

        # Sort endpoints for consistent ordering
        endpoints = sorted(list(endpoints))

        # Create figure with subplots for each percentile
        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        fig.patch.set_facecolor("white")

        percentiles = ["p50", "p95", "p99"]
        titles = [
            "Median (P50) Response Time",
            "95th Percentile Response Time",
            "99th Percentile Response Time",
        ]

        for idx, (ax, percentile, title) in enumerate(zip(axes, percentiles, titles)):
            ax.set_facecolor("white")

            # Prepare data for bar chart
            test1_values = []
            test2_values = []
            labels = []

            for endpoint in endpoints:
                # Clean endpoint name for display
                clean_name = endpoint.split("/")[-1] or endpoint.split("/")[-2]
                labels.append(clean_name)

                test1_values.append(metrics1.get(endpoint, {}).get(percentile, 0))
                test2_values.append(metrics2.get(endpoint, {}).get(percentile, 0))

            # Create grouped bar chart
            x = np.arange(len(labels))
            width = 0.35

            bars1 = ax.bar(
                x - width / 2,
                test1_values,
                width,
                label=self.test1_name,
                color=COLORS["test1"],
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            )
            bars2 = ax.bar(
                x + width / 2,
                test2_values,
                width,
                label=self.test2_name,
                color=COLORS["test2"],
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            )

            # Add value labels on bars
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.annotate(
                            f"{height:.0f}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha="center",
                            va="bottom",
                            fontsize=9,
                            fontweight="medium",
                        )

            # Calculate and show percentage differences
            for i, (v1, v2) in enumerate(zip(test1_values, test2_values)):
                if v1 > 0 and v2 > 0:
                    pct_diff = ((v2 - v1) / v1) * 100
                    color = COLORS["success"] if pct_diff < 0 else COLORS["danger"]
                    ax.text(
                        i,
                        max(v1, v2) * 1.1,
                        f"{pct_diff:+.1f}%",
                        ha="center",
                        va="bottom",
                        fontsize=10,
                        color=color,
                        fontweight="bold",
                    )

            # Styling
            ax.set_xlabel("Endpoint", fontweight="medium", color=COLORS["text"])
            ax.set_ylabel(
                "Response Time (ms)", fontweight="medium", color=COLORS["text"]
            )
            ax.set_title(title, fontweight="bold", color=COLORS["text"], pad=15)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=45, ha="right")

            # Grid and spines
            ax.grid(
                True,
                axis="y",
                alpha=0.3,
                color=COLORS["grid"],
                linestyle="-",
                linewidth=0.5,
            )
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(COLORS["grid"])
            ax.spines["bottom"].set_color(COLORS["grid"])

            # Legend
            ax.legend(
                loc="upper left",
                frameon=True,
                fancybox=True,
                shadow=True,
                borderpad=1,
                framealpha=0.95,
            )

        # Main title
        fig.suptitle(
            f"Performance Comparison: {self.test1_name} vs {self.test2_name}",
            fontsize=20,
            fontweight="bold",
            y=0.98,
        )

        plt.tight_layout()
        plt.savefig(
            os.path.join(self.output_dir, "percentile_comparison.png"),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close()

        print(f"✓ Saved: {os.path.join(self.output_dir, 'percentile_comparison.png')}")

    def create_endpoint_comparison_charts(self):
        """Create individual comparison charts for each endpoint."""
        # Collect metrics for both test runs
        endpoints_data = {}

        # Process both tests
        for result in self.data1["results"]:
            endpoint = result["endpoint"]
            response_times = self.extract_timings(result)
            p50, p95, p99 = self.calculate_percentiles(response_times)
            endpoints_data.setdefault(endpoint, {})["test1"] = {
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "count": len(response_times),
                "mean": (
                    np.mean([rt * 1000 for rt in response_times])
                    if response_times
                    else 0
                ),
            }

        for result in self.data2["results"]:
            endpoint = result["endpoint"]
            response_times = self.extract_timings(result)
            p50, p95, p99 = self.calculate_percentiles(response_times)
            endpoints_data.setdefault(endpoint, {})["test2"] = {
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "count": len(response_times),
                "mean": (
                    np.mean([rt * 1000 for rt in response_times])
                    if response_times
                    else 0
                ),
            }

        # Create chart for each endpoint
        for endpoint, data in endpoints_data.items():
            fig, ax = plt.subplots(figsize=(10, 8))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")

            metrics = ["Mean", "P50", "P95", "P99"]
            test1_data = data.get("test1", {})
            test2_data = data.get("test2", {})

            test1_values = [
                test1_data.get("mean", 0),
                test1_data.get("p50", 0),
                test1_data.get("p95", 0),
                test1_data.get("p99", 0),
            ]

            test2_values = [
                test2_data.get("mean", 0),
                test2_data.get("p50", 0),
                test2_data.get("p95", 0),
                test2_data.get("p99", 0),
            ]

            x = np.arange(len(metrics))
            width = 0.35

            bars1 = ax.bar(
                x - width / 2,
                test1_values,
                width,
                label=self.test1_name,
                color=COLORS["test1"],
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            )
            bars2 = ax.bar(
                x + width / 2,
                test2_values,
                width,
                label=self.test2_name,
                color=COLORS["test2"],
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            )

            # Add value labels
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.annotate(
                            f"{height:.1f}ms",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha="center",
                            va="bottom",
                            fontsize=10,
                            fontweight="medium",
                        )

            # Calculate improvements/regressions
            improvements = []
            for i, (v1, v2) in enumerate(zip(test1_values, test2_values)):
                if v1 > 0:
                    pct_diff = ((v2 - v1) / v1) * 100
                    improvements.append(f"{metrics[i]}: {pct_diff:+.1f}%")

            # Add improvement text
            if improvements:
                improvement_text = "\n".join(improvements)
                props = dict(
                    boxstyle="round,pad=0.5",
                    facecolor="white",
                    edgecolor=COLORS["grid"],
                    alpha=0.95,
                )
                ax.text(
                    0.98,
                    0.97,
                    improvement_text,
                    transform=ax.transAxes,
                    fontsize=11,
                    verticalalignment="top",
                    horizontalalignment="right",
                    bbox=props,
                    color=COLORS["text"],
                )

            # Styling
            ax.set_xlabel("Metric", fontweight="medium", color=COLORS["text"])
            ax.set_ylabel(
                "Response Time (ms)", fontweight="medium", color=COLORS["text"]
            )
            ax.set_title(
                f"Comparison for {endpoint}",
                fontweight="bold",
                color=COLORS["text"],
                pad=15,
            )
            ax.set_xticks(x)
            ax.set_xticklabels(metrics)

            # Grid and spines
            ax.grid(
                True,
                axis="y",
                alpha=0.3,
                color=COLORS["grid"],
                linestyle="-",
                linewidth=0.5,
            )
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            # Legend
            ax.legend(
                loc="upper left",
                frameon=True,
                fancybox=True,
                shadow=True,
                borderpad=1,
                framealpha=0.95,
            )

            # Save
            clean_endpoint = endpoint.replace("/", "_").strip("_")
            filename = f"endpoint_comparison_{clean_endpoint}.png"
            plt.tight_layout()
            plt.savefig(
                os.path.join(self.output_dir, filename),
                dpi=300,
                bbox_inches="tight",
                facecolor="white",
            )
            plt.close()

            print(f"✓ Saved: {os.path.join(self.output_dir, filename)}")

    def generate_comparison_report(self):
        """Generate a text report comparing the two test runs."""
        report_path = os.path.join(self.output_dir, "comparison_report.txt")

        with open(report_path, "w") as f:
            f.write("Performance Test Comparison Report\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"Test 1: {self.test1_name}\n")
            f.write(f"Test 2: {self.test2_name}\n\n")

            # Overall summary
            f.write("Overall Summary\n")
            f.write("-" * 15 + "\n")

            total_improvements = 0
            total_regressions = 0

            # Detailed comparison by endpoint
            f.write("\n\nDetailed Comparison by Endpoint\n")
            f.write("=" * 50 + "\n")

            all_endpoints = set()
            metrics_by_endpoint = {}

            # Collect metrics from both tests
            for result in self.data1["results"]:
                endpoint = result["endpoint"]
                all_endpoints.add(endpoint)
                response_times = self.extract_timings(result)
                if response_times:
                    p50, p95, p99 = self.calculate_percentiles(response_times)
                    metrics_by_endpoint.setdefault(endpoint, {})["test1"] = {
                        "p50": p50,
                        "p95": p95,
                        "p99": p99,
                        "count": len(response_times),
                        "mean": np.mean([rt * 1000 for rt in response_times]),
                    }

            for result in self.data2["results"]:
                endpoint = result["endpoint"]
                all_endpoints.add(endpoint)
                response_times = self.extract_timings(result)
                if response_times:
                    p50, p95, p99 = self.calculate_percentiles(response_times)
                    metrics_by_endpoint.setdefault(endpoint, {})["test2"] = {
                        "p50": p50,
                        "p95": p95,
                        "p99": p99,
                        "count": len(response_times),
                        "mean": np.mean([rt * 1000 for rt in response_times]),
                    }

            # Write comparison for each endpoint
            for endpoint in sorted(all_endpoints):
                f.write(f"\n{endpoint}\n")
                f.write("-" * len(endpoint) + "\n")

                metrics = metrics_by_endpoint.get(endpoint, {})
                test1_metrics = metrics.get("test1", {})
                test2_metrics = metrics.get("test2", {})

                if test1_metrics and test2_metrics:
                    # Compare metrics
                    for metric in ["mean", "p50", "p95", "p99"]:
                        v1 = test1_metrics.get(metric, 0)
                        v2 = test2_metrics.get(metric, 0)
                        if v1 > 0:
                            pct_diff = ((v2 - v1) / v1) * 100
                            status = "↓ Improved" if pct_diff < 0 else "↑ Regressed"
                            if abs(pct_diff) < 5:
                                status = "≈ Similar"

                            f.write(
                                f"  {metric.upper():>4}: {v1:>7.1f}ms → {v2:>7.1f}ms "
                                f"({pct_diff:+6.1f}%) {status}\n"
                            )

                            if pct_diff < -5:
                                total_improvements += 1
                            elif pct_diff > 5:
                                total_regressions += 1

                    f.write(
                        f"  Requests: {test1_metrics['count']} → {test2_metrics['count']}\n"
                    )
                else:
                    if test1_metrics:
                        f.write("  Only present in Test 1\n")
                    else:
                        f.write("  Only present in Test 2\n")

            # Update overall summary
            f.seek(0)
            content = f.read()
            f.seek(0)

            summary_line = f"Total Improvements: {total_improvements} | Total Regressions: {total_regressions}\n\n"
            content = content.replace(
                "Overall Summary\n" + "-" * 15 + "\n",
                "Overall Summary\n" + "-" * 15 + "\n" + summary_line,
            )
            f.write(content)

        print(f"✓ Saved: {report_path}")

    def generate_all_comparisons(self):
        """Generate all comparison visualizations and reports."""
        print(f"\n📊 Comparing performance results...")
        print(f"   Test 1: {self.test1_name}")
        print(f"   Test 2: {self.test2_name}\n")

        # Create main comparison chart
        self.create_comparison_bar_chart()

        # Create individual endpoint charts
        self.create_endpoint_comparison_charts()

        # Generate text report
        self.generate_comparison_report()

        print(f"\n✨ All comparisons completed!")
        print(f"📁 Output directory: {self.output_dir}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare two performance test results and create visualization charts"
    )
    parser.add_argument("json_file1", help="Path to the first JSON results file")
    parser.add_argument("json_file2", help="Path to the second JSON results file")
    parser.add_argument(
        "--output-dir",
        "-o",
        default="comparisons",
        help="Directory to save comparison visualizations (default: comparisons)",
    )

    args = parser.parse_args()

    try:
        comparator = PerformanceComparator(
            args.json_file1, args.json_file2, args.output_dir
        )
        comparator.generate_all_comparisons()
    except FileNotFoundError as e:
        print(f"❌ Error: File not found - {e}")
        return 1
    except KeyError as e:
        print(f"❌ Error: Missing expected data in JSON file: {e}")
        print("   Make sure both JSON files were generated with --verbose flag")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
