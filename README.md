# Funding Rate Arbitrage Trading System

Cross-exchange funding rate arbitrage for cryptocurrency perpetual futures. Captures funding rate differentials using delta-neutral positions.

**Status**: Production ready | **Opportunities**: 14 profitable | **Expected ROI**: 15-75% monthly

---

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements_live.txt

# Configure API keys
cp .env.template .env
nano .env  # Add your exchange API keys

# Fetch current funding rates
python3 src/fetch_multi_exchange.py

# Analyze opportunities
python3 src/find_real_arbitrage.py
python3 src/analyze_real_profits.py

# Paper trade (recommended first)
python3 src/live_trading_system.py --mode paper

# Monitor performance
python3 src/live_dashboard.py
```

## Performance Summary

**Profitable Opportunities:** 14 pairs exceed 438% APY spread threshold (required to beat fees)

**Expected Returns:**
- Conservative (5 pairs, $10K): 15% monthly
- Moderate (10 pairs, $20K): 18% monthly
- Aggressive (14 pairs, $28K): 75% monthly

**Top Opportunity:** WET with 14,939% APY spread = $11,919/month on $2K capital

See `docs/ANALYSIS_REPORT.md` for complete analysis.

## System Architecture

### Core Components

**Data Collection:**
- `src/fetch_multi_exchange.py` - Fetches funding rates from 9 exchanges
- Output: `data/funding_rates_multi_exchange.csv` (3,000+ rates)

**Analysis:**
- `src/find_real_arbitrage.py` - Detects cross-exchange spreads
- `src/analyze_real_profits.py` - Calculates fee-adjusted profits
- Output: `data/arbitrage_opportunities.csv` (ranked opportunities)

**Trading:**
- `src/live_trading_system.py` - Automated trading bot (paper/live modes)
- `src/emergency_shutdown.py` - Close all positions immediately
- `src/live_dashboard.py` - Real-time monitoring

**Testing:**
- `src/execute_paper_trades.py` - Paper trading simulator
- `tests/check_liquidity.py` - Liquidity verification

### Directory Structure

```
Funding_Rate_Arb/
├── README.md                    # This file
├── requirements_live.txt        # Python dependencies
├── .env                         # API keys (create from .env.template)
│
├── src/                         # Source code
│   ├── fetch_multi_exchange.py
│   ├── find_real_arbitrage.py
│   ├── analyze_real_profits.py
│   ├── live_trading_system.py
│   ├── emergency_shutdown.py
│   ├── live_dashboard.py
│   └── execute_paper_trades.py
│
├── tests/                       # Testing utilities
│   ├── check_liquidity.py
│   └── rigorous_verification.py
│
├── data/                        # Generated data files
│   ├── funding_rates_multi_exchange.csv
│   ├── arbitrage_opportunities.csv
│   ├── positions.json
│   └── paper_trade_state.json
│
├── logs/                        # Log files
│   ├── live_trading.log
│   └── paper_test.log
│
├── docs/                        # Documentation
│   ├── ANALYSIS_REPORT.md      # Detailed analysis
│   └── deployment/
│       └── ec2_setup.sh
│
└── build/                       # C++ components (optional)
    └── ...
```

## Configuration

### Environment Variables (.env)

```bash
# Exchange API Keys
BINANCE_API_KEY=your_key
BINANCE_SECRET_KEY=your_secret

BYBIT_API_KEY=your_key
BYBIT_SECRET_KEY=your_secret

# Add keys for: OKX, Gate.io, MEXC as needed

# Risk Parameters
MAX_POSITION_SIZE=1000      # USD per leg
MIN_SPREAD_APY=500          # Minimum spread to enter
MAX_POSITIONS=10            # Concurrent positions
STOP_LOSS_PCT=50            # Exit if spread narrows by %
```

**Security:**
- Enable trading permissions only
- Disable withdrawals
- Use IP whitelist where available
- Store keys securely

## Strategy Mechanics

### Position Structure

**Delta-neutral arbitrage:**
1. LONG on exchange with negative funding (we receive)
2. SHORT on exchange with positive funding (we pay, hedge price risk)
3. Collect net funding spread
4. Price movements cancel out

**Example:**
```
Exchange A: MOVE perpetual at -862% APY (long position)
Exchange B: MOVE perpetual at -164% APY (short position)
Net spread: 698% APY
Net profit: $2.38 per $1K per 8-hour cycle (after $4 fees)
```

### Timing

**Funding payments:** Every 8 hours at 00:00, 08:00, 16:00 UTC

**Execution window:**
- Entry: 10 minutes before funding time
- Funding collected: On the hour
- Exit: 5 minutes after funding
- Hold duration: ~15 minutes

### Profitability

**Break-even threshold:** 438% APY spread required

**Calculation:**
- Trading fees: 0.1% per side × 4 sides = 0.4% = $4.00 on $1,000
- Required gross: $4.00 per cycle = 0.4% per cycle = 438% APY

**Current market:** 17 opportunities exceed threshold

## Usage

### Data Collection

```bash
# Fetch live funding rates
python3 src/fetch_multi_exchange.py

# Output: data/funding_rates_multi_exchange.csv
# Expected: 3,000+ rates from 9 exchanges
```

### Opportunity Analysis

```bash
# Find arbitrage spreads
python3 src/find_real_arbitrage.py

# Calculate profits after fees
python3 src/analyze_real_profits.py

# Outputs:
# - data/arbitrage_opportunities.csv (216 opportunities)
# - Console report with 17 profitable pairs
```

### Paper Trading

```bash
# Start paper trading
python3 src/live_trading_system.py --mode paper

# Monitor in separate terminal
tail -f logs/paper_test.log

# View dashboard
python3 src/live_dashboard.py
```

**Paper trading runs continuously:**
- Scans for opportunities every 5 minutes
- Opens positions when MIN_SPREAD_APY met
- Closes after funding collected
- Tracks performance in `data/paper_trade_state.json`

### Live Trading

**Prerequisites:**
1. Successful paper trading for 24-48 hours
2. API keys configured and tested
3. Sufficient balance on exchanges ($2K+ per position)
4. Liquidity verified on target pairs

```bash
# Start live trading
python3 src/live_trading_system.py --mode live

# Monitor
tail -f logs/live_trading.log
python3 src/live_dashboard.py

# Emergency stop (close all positions)
python3 src/emergency_shutdown.py
```

## Risk Management

### Position Limits

- **Max position size:** $1,000 per leg (configurable)
- **Max concurrent positions:** 10
- **Min spread to enter:** 500% APY (safety margin above 438% threshold)
- **Stop loss:** Exit if spread narrows by 50%

### Liquidity Requirements

- **Minimum volume:** $1M daily per exchange
- **Max position size:** <1% of daily volume
- **Bid-ask spread:** <0.5% at entry
- **Verification:** Use `tests/check_liquidity.py` before trading

### Exchange Diversification

- **Spread positions across 5+ exchanges**
- Reduces counterparty risk
- Minimizes impact of single exchange downtime
- Diversifies rate change exposure

### Execution Risk

**Slippage mitigation:**
- Use limit orders when possible (maker fees)
- Check order book depth before entry
- Start with small positions
- Scale up gradually

**Monitoring:**
- Auto-scan every 5 minutes
- Real-time rate updates
- API health checks
- Error logging

## Testing Protocol

### 1. Liquidity Verification

```bash
python3 tests/check_liquidity.py

# Checks for each opportunity:
# - 24h trading volume
# - Bid-ask spread
# - Order book depth
# - Current funding rate
```

### 2. Paper Trading (48 hours minimum)

```bash
python3 src/live_trading_system.py --mode paper

# Monitor:
# - Positions opened/closed
# - Funding collected
# - Net P&L
# - No API errors
```

### 3. Small Live Test

```bash
# Reduce position size in .env
MAX_POSITION_SIZE=500
MIN_SPREAD_APY=600

# Trade 1-2 positions
python3 src/live_trading_system.py --mode live

# Verify actual profit matches predicted
# Check for slippage, timing issues
```

### 4. Scale Up

```bash
# Increase position size gradually
MAX_POSITION_SIZE=1000
MAX_POSITIONS=5

# Add more pairs over time
# Monitor actual ROI vs expected
```

## Expected Performance

### Conservative Portfolio (Recommended)

**Parameters:**
- 5 positions (top liquidity pairs)
- $1,000 per leg × 5 = $10,000 capital
- Pairs: MYX, MAGIC, MOVE, LSK, CLO

**Expected:**
- Daily profit: $51
- Monthly profit: $1,530
- Monthly ROI: 15.3%

### Aggressive Portfolio

**Parameters:**
- 17 positions (all profitable pairs)
- $1,000 per leg × 17 = $34,000 capital
- All pairs with >438% APY spread

**Expected:**
- Daily profit: $728
- Monthly profit: $21,850
- Monthly ROI: 64.3%

**Note:** Requires liquidity verification on all pairs. Some may need reduced position sizes.

## Deployment

### Local Development

```bash
# Run in screen session (survives terminal disconnect)
screen -S funding-arb
python3 src/live_trading_system.py --mode live

# Detach: Ctrl+A then D
# Reattach: screen -r funding-arb
```

### AWS EC2 (24/7 operation)

```bash
# Launch t3.small instance (2 vCPU, 2GB RAM)
# Ubuntu 22.04 LTS
# Cost: ~$15/month

# Setup
sudo apt update
sudo apt install python3-pip -y
pip3 install -r requirements_live.txt

# Upload files
scp -r ./* ec2-user@your-ip:~/funding-arb/

# Configure and run
cd ~/funding-arb
nano .env  # Add API keys
screen -S funding-arb
python3 src/live_trading_system.py --mode live
```

See `docs/deployment/ec2_setup.sh` for full automation.

## Troubleshooting

### No Opportunities Found

**Check:**
1. Data fetched successfully: `wc -l data/funding_rates_multi_exchange.csv` (should be 3000+)
2. Spread threshold not too high: Lower `MIN_SPREAD_APY` in .env
3. Exchange connectivity: Test API keys with small fetch

**Fix:**
```bash
python3 src/fetch_multi_exchange.py
python3 src/find_real_arbitrage.py
```

### API Errors

**Common causes:**
- Invalid API keys
- Insufficient permissions (need futures trading)
- IP not whitelisted
- Rate limits exceeded

**Fix:**
1. Verify keys in .env
2. Check exchange API settings
3. Add IP to whitelist
4. System has rate limiting built-in (wait 5-10 minutes)

### Positions Not Opening

**Check:**
1. Account balances sufficient
2. Margin mode correct (cross margin recommended)
3. Minimum order sizes met
4. Market conditions (spread may have narrowed)

**Debug:**
```bash
tail -100 logs/paper_test.log  # or live_trading.log
```

### Bot Stopped

**Check:**
1. Process running: `ps aux | grep live_trading_system`
2. Logs for errors: `tail -100 logs/live_trading.log`
3. System resources: `free -h`, `df -h`

**Restart:**
```bash
python3 src/live_trading_system.py --mode live
```

## File Inventory

### Essential Files

```
Core System:
  src/live_trading_system.py       23KB   Main bot
  src/emergency_shutdown.py         3KB   Emergency closer
  src/live_dashboard.py             4KB   Monitor
  .env                             338B   Configuration
  requirements_live.txt            290B   Dependencies

Data Collection:
  src/fetch_multi_exchange.py      15KB   Multi-exchange fetcher
  src/find_real_arbitrage.py        6KB   Spread detector
  src/analyze_real_profits.py       4KB   Profit calculator

Generated Data:
  data/funding_rates_multi_exchange.csv  270KB  Raw rates (3,076)
  data/arbitrage_opportunities.csv        14KB  Opportunities (216)
  data/positions.json                      3KB  Current positions
```

### Optional Components

```
C++ Retriever (alternative to Python):
  build/arb_retriever.cc           12KB   C++ implementation
  build/test_arb_retriever         executable

Documentation:
  docs/ANALYSIS_REPORT.md          45KB   Full analysis
```

## System Requirements

- Python 3.8+
- 2GB RAM minimum
- Stable internet (latency <100ms to exchanges)
- Exchange accounts with API access
- Futures trading enabled on accounts

## Dependencies

```
ccxt>=4.0.0              # Exchange API library
pandas>=1.5.0            # Data manipulation
python-dotenv>=1.0.0     # Environment config
apscheduler>=3.10.0      # Task scheduling
requests>=2.28.0         # HTTP client
```

Install: `pip3 install -r requirements_live.txt`

## Support

**Check logs first:**
```bash
tail -100 logs/paper_test.log
tail -100 logs/live_trading.log
```

**Common issues:**
- API errors: Check exchange status pages
- No opportunities: Lower MIN_SPREAD_APY threshold
- Execution failures: Verify liquidity with `tests/check_liquidity.py`

**Resources:**
- Exchange API documentation
- CCXT documentation: ccxt.com
- Analysis report: `docs/ANALYSIS_REPORT.md`

## License

Provided for educational purposes. Trading cryptocurrency involves substantial risk. Only trade with capital you can afford to lose. The authors are not responsible for financial losses.

## Changelog

**v1.0 - December 15, 2025**
- Initial release
- 9 exchanges integrated
- 17 profitable opportunities identified
- Paper and live trading modes
- Real-time monitoring dashboard
- Emergency shutdown capability
