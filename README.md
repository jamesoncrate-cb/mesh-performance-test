# Performance Testing for mesh-reth-sdk

This directory contains performance testing tools for the mesh-reth-sdk project.

## Overview

The performance testing suite allows you to test the performance of various Rosetta API endpoints with configurable parameters including concurrent requests, total requests, timeouts, and block ranges.

## Features

- **Concurrent Request Testing**: Test endpoints with configurable concurrency levels
- **Block Range Testing**: Test block-dependent endpoints across a range of blocks
- **Detailed Metrics**: Response times (avg, min, max, p95, p99), throughput, success rates
- **Warm-up Requests**: Optional warm-up phase before actual testing
- **JSON Report Generation**: Detailed results saved to JSON files
- **Verbose Mode**: Track individual request timings for detailed analysis
- **Visualization Suite**: Generate comprehensive performance charts and graphs

## Installation

```bash
cd performance
pip install -r requirements.txt
```

## Configuration

The test configuration is defined in YAML files (e.g., `config/data-test-config.yml`). Key configuration options include:

### Basic Configuration
```yaml
test-name: "data-test"
base-url: "http://localhost:8081"
performance:
  concurrent-requests: 10
  total-requests: 100
  timeout-seconds: 30
  warm-up-requests: 10
```

### Block Range Configuration (New Feature)
```yaml
block-range:
  enabled: true
  start: 1
  end: 1000
```

When block range is enabled, endpoints that use block indices will be tested for each block in the specified range. Mark endpoints that should use block ranges with the `uses-block-index` flag:

```yaml
endpoints:
  - path: "/block"
    method: "POST"
    uses-block-index: true  # This endpoint will be tested for each block in the range
    payload:
      network_identifier:
        blockchain: "Ethereum"
        network: "Mainnet"
      block_identifier:
        index: 22631963  # This will be replaced with each block in the range
```

## Usage

### Running Performance Tests

1. **Basic test run**:
   ```bash
   python data_test.py
   ```

2. **With custom configuration**:
   ```bash
   python data_test.py --config path/to/config.yml
   ```

3. **With verbose mode** (saves individual request timings):
   ```bash
   python data_test.py --verbose --output results/verbose-test.json
   ```

4. **Full example with block ranges**:
   ```bash
   python data_test.py --config config/block-range-example.yml --verbose --output results/block-range-test.json
   ```

### Generating Visualizations

After running tests with the `--verbose` flag, you can generate beautiful histogram visualizations:

```bash
python visualize_results.py results/verbose-test.json --output-dir my-visualizations
```

This will generate:
- **Individual Histograms**: Beautiful response time distribution histograms for each endpoint
- **Combined Histogram**: All endpoints displayed in a single comprehensive view
- **Summary Statistics**: Detailed text file with key performance metrics

## Example: Complete Performance Testing Workflow

1. **Run a verbose test with block ranges**:
   ```bash
   python data_test.py --config config/block-range-example.yml --verbose --output results/my-test.json
   ```

2. **Generate visualizations**:
   ```bash
   python visualize_results.py results/my-test.json --output-dir results/my-test-visualizations
   ```

3. **View the results**:
   - Check `results/my-test.json` for raw data
   - Browse `results/my-test-visualizations/` for:
     - `histogram_<endpoint>.png` - Individual endpoint histograms
     - `all_endpoints_histogram.png` - Combined view of all endpoints
     - `summary_statistics.txt` - Detailed performance metrics

## Understanding Verbose Mode

When running with `--verbose` or `-v` flag:
- Individual request timings are saved for each request
- Each timing includes:
  - Request ID
  - Timestamp
  - Response time
  - Success/failure status
  - HTTP status code
  - Error message (if any)
- This data enables detailed visualization and analysis
- File size will be larger due to additional data

## Visualization Features

### Beautiful Histograms
The visualization script creates modern, aesthetically pleasing histograms featuring:
- **Gradient color schemes** - Visual appeal with color gradients
- **Statistical markers** - Mean, median, P95, and P99 lines
- **Clean design** - Minimal grid lines and professional styling
- **Informative labels** - Clear titles and axis labels
- **Summary boxes** - Key metrics displayed on each chart

### Design Elements
- Modern color palette with carefully selected colors
- Professional typography and spacing
- High-resolution output (300 DPI)
- White background for clean printing
- Subtle shadows and rounded corners for visual depth

## Comparing Performance Test Results

### Overview
The `compare_results.py` script allows you to compare two performance test runs and visualize the differences. This is useful for:
- Comparing performance before and after optimizations
- Analyzing the impact of configuration changes
- Tracking performance trends over time
- Identifying regressions or improvements

### Usage

```bash
python compare_results.py results/test1.json results/test2.json --output-dir comparisons
```

### Features

1. **Percentile Comparison Charts**: Beautiful bar charts comparing P50, P95, and P99 response times
   - Side-by-side bars for easy comparison
   - Percentage change indicators
   - Color-coded improvements (green) and regressions (red)

2. **Individual Endpoint Analysis**: Detailed comparison charts for each endpoint showing:
   - Mean, P50, P95, and P99 metrics
   - Percentage changes for each metric
   - Request count differences

3. **Comprehensive Report**: Text-based comparison report including:
   - Overall improvement/regression summary
   - Detailed metrics for each endpoint
   - Success rate comparisons
   - Clear indicators for performance changes

### Example Workflow

1. **Run baseline test**:
   ```bash
   python data_test.py --verbose --output results/baseline.json
   ```

2. **Make optimizations to your code**

3. **Run optimized test**:
   ```bash
   python data_test.py --verbose --output results/optimized.json
   ```

4. **Compare results**:
   ```bash
   python compare_results.py results/baseline.json results/optimized.json --output-dir results/comparison
   ```

5. **Review outputs**:
   - `percentile_comparison.png` - Main comparison chart showing P50/P95/P99
   - `endpoint_comparison_*.png` - Individual endpoint comparisons
   - `comparison_report.txt` - Detailed text report

### Interpreting Results

- **Green percentages**: Performance improvements (lower response times)
- **Red percentages**: Performance regressions (higher response times)
- **≈ Similar**: Changes less than 5% (considered negligible)
- **↓ Improved**: Significant improvement (>5% faster)
- **↑ Regressed**: Significant regression (>5% slower)

## Tips for Effective Performance Testing

1. **Start Small**: Begin with low concurrency and small block ranges
2. **Use Verbose Mode Wisely**: Only for detailed analysis (larger file sizes)
3. **Multiple Runs**: Run tests multiple times for consistent results
4. **Monitor Resources**: Watch server CPU/memory during tests
5. **Analyze Patterns**: Use visualizations to identify performance bottlenecks
6. **Compare Results**: Save results with descriptive names for comparison

## Troubleshooting

### "No timing data available" in visualizations
- Make sure you ran the test with `--verbose` flag
- Check that the JSON file contains `individual_timings` data

### Large JSON files
- Verbose mode can create large files (MB to GB for extensive tests)
- Consider reducing total requests or block ranges for initial tests

### Visualization errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that the JSON file is from a verbose test run
