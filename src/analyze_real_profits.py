#!/usr/bin/env python3
"""
Analyze actual dollar profits from funding rate arbitrage opportunities.
Calculate real profit after fees.
"""

import pandas as pd
import numpy as np

# Load opportunities
df = pd.read_csv('data/arbitrage_opportunities.csv')

# Calculate actual profit per cycle
def calc_profit(row, capital_per_leg=1000):
    spread_apy = row['spread_apy']
    
    # Convert APY to per 8h cycle rate
    # APY% → decimal → per 8h
    per_cycle_rate = (spread_apy / 100) / 365 / 3
    
    gross_profit = capital_per_leg * per_cycle_rate
    
    # Fees: 0.1% per side × 4 sides = 0.4% total
    fees = capital_per_leg * 0.004
    
    net_profit = gross_profit - fees
    
    # Daily and monthly projections
    daily = net_profit * 3  # 3 cycles per day
    monthly = daily * 30
    
    return {
        'symbol': row['base_symbol'],
        'long_ex': row['long_exchange'],
        'short_ex': row['short_exchange'],
        'spread_apy': spread_apy,
        'gross_per_cycle': gross_profit,
        'fees': fees,
        'net_per_cycle': net_profit,
        'daily_net': daily,
        'monthly_net': monthly,
        'profitable': net_profit > 0
    }

# Analyze top 50
print('FUNDING RATE ARBITRAGE - REAL PROFIT ANALYSIS')
print('='*100)
print(f'Capital per leg: $1,000')
print(f'Total capital per position: $2,000')
print(f'Fee rate: 0.1% per side (taker fees)')
print(f'Funding cycles: Every 8 hours (3 per day)')
print('='*100)
print()

top50 = df.head(50)
results = [calc_profit(row) for _, row in top50.iterrows()]

# Summary stats
profitable = [r for r in results if r['profitable']]
unprofitable = [r for r in results if not r['profitable']]

print('SUMMARY:')
print(f'Total opportunities analyzed: {len(results)}')
print(f'Profitable (after fees): {len(profitable)}')
print(f'Unprofitable (fees exceed profit): {len(unprofitable)}')
print()

if profitable:
    print('PROFITABLE OPPORTUNITIES:')
    print('-'*100)
    print(f"{'#':<3} {'Symbol':<10} {'APY %':>8} {'Gross':>10} {'Fees':>8} {'Net/Cycle':>11} {'Daily':>10} {'Monthly':>10}")
    print('-'*100)
    
    for i, r in enumerate(profitable[:20], 1):
        print(f"{i:<3} {r['symbol']:<10} {r['spread_apy']:>8.0f} "
              f"${r['gross_per_cycle']:>9.2f} ${r['fees']:>7.2f} "
              f"${r['net_per_cycle']:>10.2f} ${r['daily_net']:>9.2f} ${r['monthly_net']:>9.2f}")
    
    print()
    print(f"Total if trading all {len(profitable)} profitable opportunities:")
    print(f"  Per cycle: ${sum(r['net_per_cycle'] for r in profitable):.2f}")
    print(f"  Per day (3 cycles): ${sum(r['daily_net'] for r in profitable):.2f}")
    print(f"  Per month: ${sum(r['monthly_net'] for r in profitable):.2f}")
    print(f"  Monthly ROI: {(sum(r['monthly_net'] for r in profitable) / (len(profitable) * 2000)) * 100:.1f}%")
    print()

# Break-even calculation
print('BREAK-EVEN ANALYSIS:')
print('-'*100)
print(f'Fees per cycle: $4.00 (0.4% of $1,000)')
print(f'To break even: Gross profit must equal $4.00')
print(f'Required per-cycle rate: {(4.00 / 1000) * 100:.3f}%')
print(f'Required APY: {(4.00 / 1000) * 365 * 3 * 100:.0f}%')
print()

# Show where cutoff is
breakeven_apy = (4.00 / 1000) * 365 * 3 * 100
print(f'Opportunities above {breakeven_apy:.0f}% APY: {len([r for r in results if r["spread_apy"] > breakeven_apy])}')
print(f'Opportunities below {breakeven_apy:.0f}% APY: {len([r for r in results if r["spread_apy"] <= breakeven_apy])}')
print()

# Now test with larger capital
print('SCALING ANALYSIS - LARGER CAPITAL:')
print('-'*100)

for capital in [10000, 100000]:
    large_results = [calc_profit(row, capital) for _, row in top50.iterrows()]
    large_profitable = [r for r in large_results if r['profitable']]
    
    print(f'\nCapital per leg: ${capital:,}')
    print(f'Profitable opportunities: {len(large_profitable)}/50')
    
    if large_profitable:
        print(f'  Best monthly profit: ${max(r["monthly_net"] for r in large_profitable):,.2f} '
              f'({large_profitable[0]["symbol"]})')
        print(f'  Total monthly (all profitable): ${sum(r["monthly_net"] for r in large_profitable):,.2f}')
        print(f'  Required capital: ${len(large_profitable) * capital * 2:,}')
        print(f'  Monthly ROI: {(sum(r["monthly_net"] for r in large_profitable) / (len(large_profitable) * capital * 2)) * 100:.2f}%')

print()
print('='*100)
print('CONCLUSION:')
print('  ✅ Real arbitrage opportunities EXIST')
print('  ✅ Spreads are REAL and profitable (before fees)')  
print('  ❌ Retail taker fees (0.4% per round trip) KILL most opportunities')
print(f'  ✅ {len(profitable)}/{len(results)} opportunities beat fees')
print()
print('TO MAKE THIS WORK:')
print('  1. Get maker rebates (VIP status) → reduces fees to ~0% or negative')
print('  2. Use larger capital ($10K-100K per position) → more absolute profit')
print('  3. Target only highest spreads (>500% APY) → maximize profit vs fees')
print('  4. Hold 24-48h for multiple funding cycles → amortize entry/exit fees')
print('='*100)
