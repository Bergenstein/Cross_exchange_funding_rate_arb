#!/usr/bin/env python3
"""
Check liquidity for the profitable opportunities.
Verify if they can actually be traded.
"""

import ccxt
import pandas as pd
import time

# Load opportunities
df = pd.read_csv('arbitrage_opportunities.csv')

# Get top profitable ones (>438% APY)
profitable = df[df['spread_apy'] > 438].head(17)

print('LIQUIDITY CHECK FOR PROFITABLE OPPORTUNITIES')
print('='*100)
print(f'Checking 17 opportunities with APY > 438%')
print()

# Initialize exchanges
exchanges = {
    'binance': ccxt.binance(),
    'bybit': ccxt.bybit(),
    'gateio': ccxt.gateio(),
    'okx': ccxt.okx(),
    'mexc': ccxt.mexc()
}

results = []

for idx, row in profitable.iterrows():
    symbol = row['base_symbol']
    long_ex = row['long_exchange']
    short_ex = row['short_exchange']
    long_symbol = row['long_symbol']
    short_symbol = row['short_symbol']
    spread = row['spread_apy']
    
    print(f"{symbol:<10} {spread:>8.0f}% APY", end=" ")
    
    try:
        # Get volume from long exchange
        ex_name = long_ex.lower().replace('.io', '').replace('io', '')
        if ex_name in exchanges:
            ex = exchanges[ex_name]
            
            # Fetch ticker
            ticker = ex.fetch_ticker(long_symbol.replace('_', '/'))
            volume_24h = ticker.get('quoteVolume', 0)
            
            # Categorize liquidity
            if volume_24h > 10_000_000:
                liq = "EXCELLENT"
                emoji = "✅"
            elif volume_24h > 1_000_000:
                liq = "GOOD"
                emoji = "✅"
            elif volume_24h > 100_000:
                liq = "MEDIUM"
                emoji = "⚠️"
            elif volume_24h > 10_000:
                liq = "LOW"
                emoji = "⚠️"
            else:
                liq = "VERY LOW"
                emoji = "❌"
            
            print(f"{emoji} ${volume_24h:>12,.0f} 24h volume ({liq})")
            
            results.append({
                'symbol': symbol,
                'spread_apy': spread,
                'volume_24h': volume_24h,
                'liquidity': liq,
                'tradeable': volume_24h > 100_000
            })
            
            time.sleep(0.1)  # Rate limiting
        else:
            print(f"⚠️  Exchange {ex_name} not initialized")
            results.append({
                'symbol': symbol,
                'spread_apy': spread,
                'volume_24h': 0,
                'liquidity': 'UNKNOWN',
                'tradeable': False
            })
    
    except Exception as e:
        print(f"❌ Error: {str(e)[:50]}")
        results.append({
            'symbol': symbol,
            'spread_apy': spread,
            'volume_24h': 0,
            'liquidity': 'ERROR',
            'tradeable': False
        })

print()
print('='*100)
print('SUMMARY:')
print()

tradeable = [r for r in results if r['tradeable']]
print(f"Tradeable (>$100K daily volume): {len(tradeable)}/{len(results)}")
print()

if tradeable:
    print("RECOMMENDED OPPORTUNITIES:")
    print('-'*100)
    for r in tradeable:
        print(f"  {r['symbol']:<10} {r['spread_apy']:>8.0f}% APY  ${r['volume_24h']:>12,.0f} volume  [{r['liquidity']}]")
    
    print()
    print(f"Total tradeable opportunities: {len(tradeable)}")
    print(f"Potential monthly profit: ${sum((r['spread_apy'] / 365 / 3 / 100 * 1000 - 4) * 3 * 30 for r in tradeable):,.2f}")
    print(f"Required capital: ${len(tradeable) * 2000:,}")

print('='*100)
