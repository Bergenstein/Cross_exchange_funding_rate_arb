#!/usr/bin/env python3
"""
Liquidity Checker for Funding Rate Arbitrage Opportunities
Checks order book depth for both spot and perpetual markets.
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Tuple

class LiquidityChecker:
    def __init__(self):
        self.binance_spot_base = "https://api.binance.com/api/v3"
        self.binance_futures_base = "https://fapi.binance.com/fapi/v1"
        
    def get_order_book_depth(self, symbol: str, is_futures: bool = False, limit: int = 100) -> Dict:
        """Get order book depth for a symbol"""
        try:
            if is_futures:
                url = f"{self.binance_futures_base}/depth"
            else:
                url = f"{self.binance_spot_base}/depth"
            
            params = {"symbol": symbol, "limit": limit}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching order book for {symbol}: {e}")
            return {}
    
    def calculate_depth_metrics(self, order_book: Dict, price_levels: int = 10) -> Dict:
        """Calculate liquidity metrics from order book"""
        if not order_book or 'bids' not in order_book or 'asks' not in order_book:
            return {
                'bid_depth_usd': 0,
                'ask_depth_usd': 0,
                'total_depth_usd': 0,
                'spread_pct': 0,
                'bid_levels': 0,
                'ask_levels': 0
            }
        
        bids = order_book['bids'][:price_levels]
        asks = order_book['asks'][:price_levels]
        
        # Calculate USD depth
        bid_depth_usd = sum(float(price) * float(qty) for price, qty in bids)
        ask_depth_usd = sum(float(price) * float(qty) for price, qty in asks)
        
        # Calculate spread
        best_bid = float(bids[0][0]) if bids else 0
        best_ask = float(asks[0][0]) if asks else 0
        spread_pct = ((best_ask - best_bid) / best_bid * 100) if best_bid > 0 else 0
        
        return {
            'bid_depth_usd': bid_depth_usd,
            'ask_depth_usd': ask_depth_usd,
            'total_depth_usd': bid_depth_usd + ask_depth_usd,
            'spread_pct': spread_pct,
            'bid_levels': len(bids),
            'ask_levels': len(asks),
            'best_bid': best_bid,
            'best_ask': best_ask
        }
    
    def check_spot_availability(self, symbol: str) -> Tuple[bool, str]:
        """Check if spot trading pair exists"""
        # Convert BTCUSDT to BTC/USDT format for checking
        if not symbol.endswith('USDT'):
            return False, "Not a USDT pair"
        
        try:
            url = f"{self.binance_spot_base}/exchangeInfo"
            params = {"symbol": symbol}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('symbols'):
                    symbol_info = data['symbols'][0]
                    status = symbol_info.get('status', 'UNKNOWN')
                    if status == 'TRADING':
                        return True, "Available"
                    else:
                        return False, f"Status: {status}"
            return False, "Not found"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def analyze_pair_liquidity(self, perp_symbol: str) -> Dict:
        """Analyze liquidity for both spot and perpetual markets"""
        print(f"Analyzing {perp_symbol}...")
        
        # Check if spot market exists
        spot_available, spot_status = self.check_spot_availability(perp_symbol)
        
        result = {
            'symbol': perp_symbol,
            'spot_available': spot_available,
            'spot_status': spot_status,
            'perp_liquid': False,
            'spot_liquid': False,
            'tradeable': False
        }
        
        # Get perpetual order book
        perp_book = self.get_order_book_depth(perp_symbol, is_futures=True)
        perp_metrics = self.calculate_depth_metrics(perp_book)
        result.update({f'perp_{k}': v for k, v in perp_metrics.items()})
        
        # Get spot order book if available
        if spot_available:
            time.sleep(0.2)  # Rate limiting
            spot_book = self.get_order_book_depth(perp_symbol, is_futures=False)
            spot_metrics = self.calculate_depth_metrics(spot_book)
            result.update({f'spot_{k}': v for k, v in spot_metrics.items()})
        else:
            # Fill with zeros
            result.update({
                'spot_bid_depth_usd': 0,
                'spot_ask_depth_usd': 0,
                'spot_total_depth_usd': 0,
                'spot_spread_pct': 0,
                'spot_bid_levels': 0,
                'spot_ask_levels': 0,
                'spot_best_bid': 0,
                'spot_best_ask': 0
            })
        
        # Liquidity thresholds
        min_depth_usd = 10000  # $10k minimum depth
        max_spread_pct = 0.5   # 0.5% maximum spread
        
        result['perp_liquid'] = (
            result['perp_total_depth_usd'] >= min_depth_usd and
            result['perp_spread_pct'] <= max_spread_pct
        )
        
        result['spot_liquid'] = (
            result['spot_total_depth_usd'] >= min_depth_usd and
            result['spot_spread_pct'] <= max_spread_pct
        )
        
        result['tradeable'] = spot_available and result['perp_liquid'] and result['spot_liquid']
        
        return result

def main():
    print("=" * 80)
    print("LIQUIDITY VERIFICATION FOR FUNDING RATE ARBITRAGE")
    print("=" * 80)
    
    # Load funding rates
    try:
        df = pd.read_csv('funding_rates.csv')
        print(f"\n✓ Loaded {len(df)} funding rates from CSV")
    except FileNotFoundError:
        print("\nERROR: funding_rates.csv not found. Run fetch_funding_rates.py first.")
        return
    
    # Filter to Binance only (for now)
    binance_df = df[df['exchange'] == 'binance'].copy()
    print(f"✓ Filtering to {len(binance_df)} Binance symbols")
    
    # Get top opportunities
    print("\n" + "=" * 80)
    print("Selecting top opportunities to check...")
    print("=" * 80)
    
    # Top 10 positive (>30% APY)
    high_positive = binance_df[binance_df['funding_rate_annual_pct'] > 30].nlargest(10, 'funding_rate_annual_pct')
    
    # Top 10 negative (<-30% APY)  
    high_negative = binance_df[binance_df['funding_rate_annual_pct'] < -30].nsmallest(10, 'funding_rate_annual_pct')
    
    # Moderate (30-50% APY)
    moderate = binance_df[
        (binance_df['funding_rate_annual_pct'] >= 30) & 
        (binance_df['funding_rate_annual_pct'] <= 50)
    ].nlargest(5, 'funding_rate_annual_pct')
    
    # Combine and remove duplicates
    symbols_to_check = pd.concat([high_positive, high_negative, moderate]).drop_duplicates(subset=['symbol'])
    
    print(f"\n✓ Selected {len(symbols_to_check)} unique symbols to check")
    print(f"  - {len(high_positive)} high positive (>30% APY)")
    print(f"  - {len(high_negative)} high negative (<-30% APY)")
    print(f"  - {len(moderate)} moderate (30-50% APY)")
    
    # Check liquidity
    checker = LiquidityChecker()
    results = []
    
    print("\n" + "=" * 80)
    print("CHECKING LIQUIDITY...")
    print("=" * 80 + "\n")
    
    for idx, row in symbols_to_check.iterrows():
        symbol = row['symbol']
        liquidity = checker.analyze_pair_liquidity(symbol)
        liquidity['funding_rate_annual_pct'] = row['funding_rate_annual_pct']
        results.append(liquidity)
        time.sleep(0.5)  # Rate limiting
    
    # Convert to DataFrame
    results_df = pd.DataFrame(results)
    
    # Save results
    results_df.to_csv('liquidity_analysis.csv', index=False)
    
    # Display summary
    print("\n" + "=" * 80)
    print("LIQUIDITY ANALYSIS SUMMARY")
    print("=" * 80)
    
    tradeable = results_df[results_df['tradeable'] == True]
    print(f"\n✓ TRADEABLE OPPORTUNITIES: {len(tradeable)}/{len(results_df)}")
    
    if len(tradeable) > 0:
        print("\nTop Tradeable Opportunities (by funding rate APY):")
        print("-" * 80)
        display_cols = ['symbol', 'funding_rate_annual_pct', 'perp_total_depth_usd', 
                       'spot_total_depth_usd', 'perp_spread_pct', 'spot_spread_pct']
        print(tradeable[display_cols].sort_values('funding_rate_annual_pct', 
                                                   key=abs, 
                                                   ascending=False).to_string(index=False))
    
    # Reasons for non-tradeable
    non_tradeable = results_df[results_df['tradeable'] == False]
    if len(non_tradeable) > 0:
        print(f"\n\n⚠️  NON-TRADEABLE: {len(non_tradeable)}")
        print("-" * 80)
        
        no_spot = non_tradeable[non_tradeable['spot_available'] == False]
        print(f"  - No spot market: {len(no_spot)}")
        
        illiquid_perp = non_tradeable[non_tradeable['perp_liquid'] == False]
        print(f"  - Illiquid perpetual: {len(illiquid_perp)}")
        
        illiquid_spot = non_tradeable[
            (non_tradeable['spot_available'] == True) & 
            (non_tradeable['spot_liquid'] == False)
        ]
        print(f"  - Illiquid spot: {len(illiquid_spot)}")
        
        print("\nExamples of non-tradeable pairs:")
        print(non_tradeable[['symbol', 'funding_rate_annual_pct', 'spot_available', 
                            'spot_status', 'perp_liquid', 'spot_liquid']].head(10).to_string(index=False))
    
    print("\n" + "=" * 80)
    print(f"✓ Complete analysis saved to liquidity_analysis.csv")
    print("=" * 80)
    
    # Calculate max position sizes for tradeable opportunities
    if len(tradeable) > 0:
        print("\n" + "=" * 80)
        print("RECOMMENDED POSITION SIZES")
        print("=" * 80)
        print("\nBased on 10% of minimum market depth:\n")
        
        for _, row in tradeable.iterrows():
            min_depth = min(row['perp_total_depth_usd'], row['spot_total_depth_usd'])
            max_position = min_depth * 0.1  # 10% of depth
            print(f"{row['symbol']:15} APY: {row['funding_rate_annual_pct']:8.2f}%  "
                  f"Max Position: ${max_position:,.0f}")

if __name__ == "__main__":
    main()
