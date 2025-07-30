#!/usr/bin/env python3
"""
Visualize performance test results from verbose JSON output.

This script creates beautiful histogram visualizations of response time distributions.
"""

import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
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
    "primary": "#2E86AB",  # Blue
    "secondary": "#A23B72",  # Purple
    "accent": "#F18F01",  # Orange
    "success": "#2A9D8F",  # Teal
    "danger": "#E76F51",  # Red
    "background": "#F8F9FA",  # Light gray
    "grid": "#E9ECEF",  # Lighter gray
    "text": "#212529",  # Dark gray
}


class PerformanceVisualizer:
    def __init__(self, json_file: str, output_dir: str = "visualizations"):
        with open(json_file, "r") as f:
            self.data = json.load(f)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def extract_timings(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract individual timings from a result."""
        timings = []

        if "individual_timings" in result and result["individual_timings"]:
            return result["individual_timings"]

        if "block_metrics" in result:
            for block_metric in result["block_metrics"]:
                if (
                    "individual_timings" in block_metric
                    and block_metric["individual_timings"]
                ):
                    for timing in block_metric["individual_timings"]:
                        timing["block_index"] = block_metric.get("block_index")
                        timings.append(timing)

        return timings

    def create_beautiful_histogram(
        self,
        response_times: List[float],
        endpoint: str,
        output_filename: str,
        show_failed: bool = False,
        failed_count: int = 0,
    ):
        """Create a beautiful, modern histogram for response times."""

        # Create figure with white background
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        if response_times:
            # Convert to milliseconds
            response_times_ms = [rt * 1000 for rt in response_times]

            # Calculate statistics
            mean_time = np.mean(response_times_ms)
            median_time = np.median(response_times_ms)
            p95_time = np.percentile(response_times_ms, 95)
            p99_time = np.percentile(response_times_ms, 99)

            # Determine optimal number of bins
            n_bins = min(50, int(np.sqrt(len(response_times_ms)) * 2))

            # Create the histogram
            n, bins, patches = ax.hist(
                response_times_ms,
                bins=n_bins,
                color=COLORS["primary"],
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            )

            # Color gradient for bars
            cm = plt.cm.get_cmap("Blues")
            bin_centers = 0.5 * (bins[:-1] + bins[1:])
            col = bin_centers - min(bin_centers)
            col /= max(col)
            for c, p in zip(col, patches):
                plt.setp(p, "facecolor", cm(0.3 + c * 0.7))

            # Add statistical lines
            ax.axvline(
                mean_time,
                color=COLORS["accent"],
                linestyle="--",
                linewidth=2.5,
                alpha=0.9,
                label=f"Mean: {mean_time:.1f}ms",
            )
            ax.axvline(
                median_time,
                color=COLORS["success"],
                linestyle="--",
                linewidth=2.5,
                alpha=0.9,
                label=f"Median: {median_time:.1f}ms",
            )
            ax.axvline(
                p95_time,
                color=COLORS["secondary"],
                linestyle="--",
                linewidth=2.5,
                alpha=0.9,
                label=f"P95: {p95_time:.1f}ms",
            )
            ax.axvline(
                p99_time,
                color=COLORS["danger"],
                linestyle="--",
                linewidth=2.5,
                alpha=0.9,
                label=f"P99: {p99_time:.1f}ms",
            )

            # Style the plot
            ax.set_xlabel(
                "Response Time (ms)", fontweight="medium", color=COLORS["text"]
            )
            ax.set_ylabel("Frequency", fontweight="medium", color=COLORS["text"])

            # Add title with endpoint name
            title = f"Response Time Distribution\n{endpoint}"
            if show_failed and failed_count > 0:
                title += (
                    f"\n({len(response_times_ms)} successful, {failed_count} failed)"
                )
            ax.set_title(title, fontweight="bold", color=COLORS["text"], pad=20)

            # Customize grid
            ax.grid(True, alpha=0.3, color=COLORS["grid"], linestyle="-", linewidth=0.5)
            ax.set_axisbelow(True)

            # Remove top and right spines
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(COLORS["grid"])
            ax.spines["bottom"].set_color(COLORS["grid"])

            # Customize tick colors
            ax.tick_params(colors=COLORS["text"])

            # Add legend with custom styling
            legend = ax.legend(
                loc="upper right",
                frameon=True,
                fancybox=True,
                shadow=True,
                borderpad=1,
                framealpha=0.95,
            )
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_edgecolor(COLORS["grid"])

            # Add subtle text box with key metrics
            textstr = f"Requests: {len(response_times_ms)}\nMin: {min(response_times_ms):.1f}ms\nMax: {max(response_times_ms):.1f}ms"
            props = dict(
                boxstyle="round,pad=0.5",
                facecolor="white",
                edgecolor=COLORS["grid"],
                alpha=0.95,
            )
            ax.text(
                0.02,
                0.98,
                textstr,
                transform=ax.transAxes,
                fontsize=11,
                verticalalignment="top",
                bbox=props,
                color=COLORS["text"],
            )

        else:
            # No data available
            ax.text(
                0.5,
                0.5,
                "No successful requests\nto visualize",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=16,
                color=COLORS["text"],
                style="italic",
            )
            ax.set_title(
                f"Response Time Distribution\n{endpoint}",
                fontweight="bold",
                color=COLORS["text"],
                pad=20,
            )
            ax.set_xlabel(
                "Response Time (ms)", fontweight="medium", color=COLORS["text"]
            )
            ax.set_ylabel("Frequency", fontweight="medium", color=COLORS["text"])

            # Remove all spines for empty plot
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.set_xticks([])
            ax.set_yticks([])

        # Adjust layout and save
        plt.tight_layout()
        plt.savefig(
            os.path.join(self.output_dir, output_filename),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close()

        print(f"✓ Saved: {os.path.join(self.output_dir, output_filename)}")

    def create_combined_histogram(self):
        """Create a beautiful combined histogram showing all endpoints."""
        # Collect all response times by endpoint
        endpoint_data = {}

        for result in self.data["results"]:
            endpoint = result["endpoint"]
            timings = self.extract_timings(result)

            if timings:
                successful_times = [t["response_time"] for t in timings if t["success"]]
                failed_count = len([t for t in timings if not t["success"]])
                endpoint_data[endpoint] = {
                    "times": successful_times,
                    "failed": failed_count,
                }

        if not endpoint_data:
            print("No timing data available for visualization")
            return

        # Create subplots
        n_endpoints = len(endpoint_data)
        fig, axes = plt.subplots(n_endpoints, 1, figsize=(12, 6 * n_endpoints))
        fig.patch.set_facecolor("white")

        if n_endpoints == 1:
            axes = [axes]

        # Create histogram for each endpoint
        for idx, (endpoint, data) in enumerate(endpoint_data.items()):
            ax = axes[idx]
            ax.set_facecolor("white")

            response_times_ms = [rt * 1000 for rt in data["times"]]

            if response_times_ms:
                # Calculate statistics
                mean_time = np.mean(response_times_ms)
                median_time = np.median(response_times_ms)
                p95_time = np.percentile(response_times_ms, 95)
                p99_time = np.percentile(response_times_ms, 99)

                # Create histogram with gradient colors
                n_bins = min(40, int(np.sqrt(len(response_times_ms)) * 1.5))
                n, bins, patches = ax.hist(
                    response_times_ms,
                    bins=n_bins,
                    alpha=0.8,
                    edgecolor="white",
                    linewidth=1.2,
                )

                # Apply color gradient
                cm = plt.cm.get_cmap("viridis")
                bin_centers = 0.5 * (bins[:-1] + bins[1:])
                col = bin_centers - min(bin_centers)
                col /= max(col) if max(col) > 0 else 1
                for c, p in zip(col, patches):
                    plt.setp(p, "facecolor", cm(0.2 + c * 0.6))

                # Add statistical lines
                ax.axvline(
                    mean_time,
                    color=COLORS["accent"],
                    linestyle="--",
                    linewidth=2,
                    alpha=0.8,
                    label=f"Mean: {mean_time:.1f}ms",
                )
                ax.axvline(
                    p95_time,
                    color=COLORS["secondary"],
                    linestyle="--",
                    linewidth=2,
                    alpha=0.8,
                    label=f"P95: {p95_time:.1f}ms",
                )

                # Styling
                ax.set_xlabel("Response Time (ms)", fontweight="medium")
                ax.set_ylabel("Frequency", fontweight="medium")
                ax.set_title(f"{endpoint}", fontweight="bold", fontsize=14, pad=10)

                # Grid and spines
                ax.grid(True, alpha=0.2, linestyle="-", linewidth=0.5)
                ax.set_axisbelow(True)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

                # Legend
                ax.legend(
                    loc="upper right",
                    frameon=True,
                    fancybox=True,
                    shadow=False,
                    framealpha=0.9,
                )

                # Stats box
                stats_text = f"n={len(response_times_ms)}"
                if data["failed"] > 0:
                    stats_text += f" ({data['failed']} failed)"
                ax.text(
                    0.02,
                    0.95,
                    stats_text,
                    transform=ax.transAxes,
                    fontsize=10,
                    verticalalignment="top",
                    bbox=dict(
                        boxstyle="round,pad=0.3",
                        facecolor="white",
                        edgecolor="gray",
                        alpha=0.8,
                    ),
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No successful requests",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    fontsize=12,
                    style="italic",
                )
                ax.set_title(f"{endpoint}", fontweight="bold", fontsize=14)

        # Add main title
        fig.suptitle(
            "Performance Test Results - Response Time Distributions",
            fontsize=18,
            fontweight="bold",
            y=1.02,
        )

        plt.tight_layout()
        plt.savefig(
            os.path.join(self.output_dir, "all_endpoints_histogram.png"),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close()

        print(
            f"✓ Saved: {os.path.join(self.output_dir, 'all_endpoints_histogram.png')}"
        )

    def generate_summary_stats(self):
        """Generate a summary statistics file."""
        stats_path = os.path.join(self.output_dir, "summary_statistics.txt")

        with open(stats_path, "w") as f:
            f.write("Performance Test Summary Statistics\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"Test Name: {self.data['test_summary']['test_name']}\n")
            f.write(
                f"Total Endpoints: {self.data['test_summary']['total_endpoints']}\n"
            )
            f.write(
                f"Concurrent Requests: {self.data['test_summary']['concurrent_requests']}\n"
            )
            f.write(
                f"Requests per Endpoint: {self.data['test_summary']['total_requests_per_endpoint']}\n\n"
            )

            for result in self.data["results"]:
                f.write(f"\n{result['endpoint']}\n")
                f.write("-" * len(result["endpoint"]) + "\n")

                timings = self.extract_timings(result)
                if timings:
                    response_times = [
                        t["response_time"] * 1000 for t in timings if t["success"]
                    ]
                    failed_count = len([t for t in timings if not t["success"]])

                    if response_times:
                        f.write(f"  Successful Requests: {len(response_times)}\n")
                        f.write(f"  Failed Requests: {failed_count}\n")
                        f.write(
                            f"  Success Rate: {len(response_times) / (len(response_times) + failed_count) * 100:.1f}%\n"
                        )
                        f.write(
                            f"  Mean Response Time: {np.mean(response_times):.2f}ms\n"
                        )
                        f.write(
                            f"  Median Response Time: {np.median(response_times):.2f}ms\n"
                        )
                        f.write(
                            f"  Min Response Time: {np.min(response_times):.2f}ms\n"
                        )
                        f.write(
                            f"  Max Response Time: {np.max(response_times):.2f}ms\n"
                        )
                        f.write(
                            f"  P95 Response Time: {np.percentile(response_times, 95):.2f}ms\n"
                        )
                        f.write(
                            f"  P99 Response Time: {np.percentile(response_times, 99):.2f}ms\n"
                        )
                        f.write(
                            f"  Standard Deviation: {np.std(response_times):.2f}ms\n"
                        )
                else:
                    f.write("  No timing data available (run with --verbose flag)\n")

        print(f"✓ Saved: {stats_path}")

    def generate_all_visualizations(self):
        """Generate all histogram visualizations."""
        print("\n🎨 Generating beautiful histogram visualizations...\n")

        # Create individual histograms for each endpoint
        for idx, result in enumerate(self.data["results"]):
            endpoint = result["endpoint"]
            timings = self.extract_timings(result)

            if timings:
                successful_times = [t["response_time"] for t in timings if t["success"]]
                failed_count = len([t for t in timings if not t["success"]])

                # Clean filename from endpoint path
                clean_endpoint = endpoint.replace("/", "_").strip("_")
                filename = f"histogram_{clean_endpoint}.png"

                self.create_beautiful_histogram(
                    successful_times,
                    endpoint,
                    filename,
                    show_failed=True,
                    failed_count=failed_count,
                )

        # Create combined histogram
        self.create_combined_histogram()

        # Generate summary statistics
        self.generate_summary_stats()

        print(f"\n✨ All visualizations completed!")
        print(f"📁 Output directory: {self.output_dir}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Create beautiful histogram visualizations from performance test results"
    )
    parser.add_argument(
        "json_file", help="Path to the JSON results file (must be from verbose mode)"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="visualizations",
        help="Directory to save visualizations (default: visualizations)",
    )

    args = parser.parse_args()

    try:
        visualizer = PerformanceVisualizer(args.json_file, args.output_dir)
        visualizer.generate_all_visualizations()
    except FileNotFoundError:
        print(f"❌ Error: File '{args.json_file}' not found.")
        return 1
    except KeyError as e:
        print(f"❌ Error: Missing expected data in JSON file: {e}")
        print("   Make sure the JSON file was generated with --verbose flag")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
