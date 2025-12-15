#!/usr/bin/env python3
"""
Real Cross-Exchange Funding Rate Arbitrage Analyzer
Finds actual ar    # Load data
    try:
        df = pd.read_csv('data/funding_rates_multi_exchange.csv')
    except FileNotFoundError:
        print("ERROR: data/funding_rates_multi_exchange.csv not found!")
        print("Run fetch_multi_exchange.py first.")
        return opportunities across exchanges
"""

import pandas as pd
import numpy as np
from datetime import datetime

def normalize_symbol(symbol: str) -> str:
    """Normalize symbol names across exchanges"""
    # Remove common suffixes
    symbol = symbol.upper()
    symbol = symbol.replace('USDT', '').replace('-PERP', '').replace('_UMCBL', '')
    symbol = symbol.replace('-SWAP', '').replace('USD', '').replace('PERP', '')
    symbol = symbol.replace('_', '').replace('-', '').strip()
    return symbol

def find_cross_exchange_opportunities(df: pd.DataFrame, min_spread_apy: float = 20.0):
    """Find arbitrage opportunities across exchanges for the same symbol"""
    
    print("=" * 80)
    print("CROSS-EXCHANGE FUNDING RATE ARBITRAGE ANALYSIS")
    print("=" * 80)
    
    # Normalize symbols
    df['normalized_symbol'] = df['symbol'].apply(normalize_symbol)
    
    # Find symbols that exist on multiple exchanges
    symbol_counts = df.groupby('normalized_symbol')['exchange'].nunique()
    multi_exchange_symbols = symbol_counts[symbol_counts >= 2].index.tolist()
    
    print(f"\n✓ Found {len(multi_exchange_symbols)} symbols listed on 2+ exchanges")
    
    opportunities = []
    
    for norm_symbol in multi_exchange_symbols:
        symbol_data = df[df['normalized_symbol'] == norm_symbol].copy()
        
        if len(symbol_data) < 2:
            continue
        
        # Find max and min funding rates
        max_row = symbol_data.loc[symbol_data['funding_rate_annual_pct'].idxmax()]
        min_row = symbol_data.loc[symbol_data['funding_rate_annual_pct'].idxmin()]
        
        spread = max_row['funding_rate_annual_pct'] - min_row['funding_rate_annual_pct']
        
        if spread >= min_spread_apy:
            opportunities.append({
                'base_symbol': norm_symbol,
                'long_exchange': min_row['exchange'],
                'long_symbol': min_row['symbol'],
                'long_rate_apy': min_row['funding_rate_annual_pct'],
                'short_exchange': max_row['exchange'],
                'short_symbol': max_row['symbol'],
                'short_rate_apy': max_row['funding_rate_annual_pct'],
                'spread_apy': spread,
                'num_exchanges': len(symbol_data)
            })
    
    return pd.DataFrame(opportunities)

def analyze_single_exchange_extreme_rates(df: pd.DataFrame):
    """Find extreme funding rates on single exchanges (delta neutral)"""
    
    print("\n" + "=" * 80)
    print("SINGLE EXCHANGE EXTREME RATES (Delta Neutral Opportunities)")
    print("=" * 80)
    
    # High positive rates (short perp + long spot)
    high_positive = df[df['funding_rate_annual_pct'] > 50].copy()
    high_positive = high_positive.sort_values('funding_rate_annual_pct', ascending=False)
    
    print(f"\n✓ HIGH POSITIVE RATES (>50% APY) - SHORT PERP + LONG SPOT:")
    print(f"  Found {len(high_positive)} opportunities")
    if len(high_positive) > 0:
        print("\n  Top 10:")
        for idx, row in high_positive.head(10).iterrows():
            print(f"    {row['exchange']:10s} {row['symbol']:20s} {row['funding_rate_annual_pct']:>8.2f}% APY")
    
    # High negative rates (long perp + short spot)
    high_negative = df[df['funding_rate_annual_pct'] < -50].copy()
    high_negative = high_negative.sort_values('funding_rate_annual_pct', ascending=True)
    
    print(f"\n✓ HIGH NEGATIVE RATES (<-50% APY) - LONG PERP + SHORT SPOT:")
    print(f"  Found {len(high_negative)} opportunities")
    if len(high_negative) > 0:
        print("\n  Top 10:")
        for idx, row in high_negative.head(10).iterrows():
            print(f"    {row['exchange']:10s} {row['symbol']:20s} {row['funding_rate_annual_pct']:>8.2f}% APY")

def main():
    # Load data
    try:
        df = pd.read_csv('funding_rates_multi_exchange.csv')
    except FileNotFoundError:
        print("ERROR: funding_rates_multi_exchange.csv not found!")
        print("Run: python3 fetch_multi_exchange.py first")
        return
    
    print(f"\n✓ Loaded {len(df)} funding rates")
    print(f"✓ Exchanges: {sorted(df['exchange'].unique().tolist())}")
    print(f"✓ Total symbols: {df['symbol'].nunique()}")
    
    # Find cross-exchange opportunities
    cross_ex_opps = find_cross_exchange_opportunities(df, min_spread_apy=20.0)
    
    if len(cross_ex_opps) > 0:
        print(f"\n✓ FOUND {len(cross_ex_opps)} CROSS-EXCHANGE ARBITRAGE OPPORTUNITIES!")
        print("\nTop 20 by spread:")
        print("=" * 120)
        
        cross_ex_opps_sorted = cross_ex_opps.sort_values('spread_apy', ascending=False)
        
        for idx, row in cross_ex_opps_sorted.head(20).iterrows():
            print(f"\n{row['base_symbol']:15s} | Spread: {row['spread_apy']:>7.2f}% APY")
            print(f"  LONG:  {row['long_exchange']:10s} {row['long_symbol']:20s} @ {row['long_rate_apy']:>7.2f}% APY")
            print(f"  SHORT: {row['short_exchange']:10s} {row['short_symbol']:20s} @ {row['short_rate_apy']:>7.2f}% APY")
        
        # Save to CSV
        filename = 'data/arbitrage_opportunities.csv'
        cross_ex_opps_sorted.to_csv(filename, index=False)
        print(f"\n✓ Saved all opportunities to {filename}")
    else:
        print("\n✗ No cross-exchange opportunities found with >20% APY spread")
    
    # Also show single-exchange extreme rates
    analyze_single_exchange_extreme_rates(df)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
