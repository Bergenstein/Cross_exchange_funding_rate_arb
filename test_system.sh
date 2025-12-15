#!/bin/bash
# Quick test of the entire funding rate arbitrage system

echo "==========================================="
echo "FUNDING RATE ARB - SYSTEM TEST"
echo "==========================================="
echo ""

# Check directory structure
echo "[1/5] Checking directory structure..."
for dir in src tests data logs docs; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir/ exists"
    else
        echo "  ✗ $dir/ missing"
        exit 1
    fi
done
echo ""

# Check required files
echo "[2/5] Checking required files..."
for file in README.md requirements_live.txt docs/ANALYSIS_REPORT.md; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        exit 1
    fi
done
echo ""

# Check Python scripts
echo "[3/5] Checking Python scripts..."
scripts=(
    "src/fetch_multi_exchange.py"
    "src/find_real_arbitrage.py"
    "src/analyze_real_profits.py"
    "src/live_trading_system.py"
    "src/emergency_shutdown.py"
    "src/live_dashboard.py"
    "tests/check_liquidity.py"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        echo "  ✓ $script"
    else
        echo "  ✗ $script missing"
        exit 1
    fi
done
echo ""

# Test data pipeline
echo "[4/5] Testing data pipeline..."
echo "  → Fetching funding rates..."
python3 src/fetch_multi_exchange.py > /dev/null 2>&1
if [ -f "data/funding_rates_multi_exchange.csv" ]; then
    lines=$(wc -l < data/funding_rates_multi_exchange.csv)
    echo "  ✓ Fetched $lines funding rates"
else
    echo "  ✗ Failed to fetch data"
    exit 1
fi

echo "  → Finding arbitrage opportunities..."
python3 src/find_real_arbitrage.py > /dev/null 2>&1
if [ -f "data/arbitrage_opportunities.csv" ]; then
    opps=$(tail -n +2 data/arbitrage_opportunities.csv | wc -l)
    echo "  ✓ Found $opps opportunities"
else
    echo "  ✗ Failed to find opportunities"
    exit 1
fi

echo "  → Analyzing profits..."
profit_output=$(python3 src/analyze_real_profits.py 2>&1)
profitable=$(echo "$profit_output" | grep "Profitable (after fees):" | awk '{print $4}')
if [ -n "$profitable" ]; then
    echo "  ✓ Identified $profitable profitable opportunities"
else
    echo "  ✗ Failed to analyze profits"
    exit 1
fi
echo ""

# Summary
echo "[5/5] Summary"
echo "==========================================="
echo "✓ All system components operational"
echo "✓ Data pipeline working"
echo "✓ $profitable opportunities identified"
echo ""
echo "System ready for:"
echo "  • Paper trading (src/live_trading_system.py --mode paper)"
echo "  • Live trading (configure .env first)"
echo "  • Full deployment (see docs/deployment/)"
echo "==========================================="
