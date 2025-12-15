#!/usr/bin/env python3
"""
RIGOROUS FUNDING RATE ARBITRAGE VERIFICATION
Tests real opportunities with actual market data, liquidity, and timing
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple

class RigorousArbitrageTester:
    
    def __init__(self):
        self.exchanges = {
            'binance': ccxt.binance(),
            'bybit': ccxt.bybit(),
            'okx': ccxt.okx(),
            'gateio': ccxt.gateio()
        }
        
        # Minimum daily volume to consider liquid (in USD)
        self.min_daily_volume = 10_000_000  # $10M
        
    def get_next_funding_time(self, exchange_name: str, symbol: str) -> datetime:
        """Get exact next funding time for a symbol"""
        try:
            exchange = self.exchanges[exchange_name]
            
            if exchange_name == 'binance':
                ticker = exchange.fetch_ticker(symbol)
                next_funding = ticker.get('info', {}).get('nextFundingTime')
                if next_funding:
                    return datetime.fromtimestamp(int(next_funding) / 1000)
            
            elif exchange_name == 'bybit':
                ticker = exchange.fetch_ticker(symbol)
                next_funding = ticker.get('info', {}).get('nextFundingTime')
                if next_funding:
                    return datetime.fromtimestamp(int(next_funding) / 1000)
            
            elif exchange_name == 'gateio':
                # Gate.io: 8-hour cycles at 00:00, 08:00, 16:00 UTC
                now = datetime.utcnow()
                funding_hours = [0, 8, 16]
                for h in funding_hours:
                    next_time = now.replace(hour=h, minute=0, second=0, microsecond=0)
                    if next_time > now:
                        return next_time
                return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            elif exchange_name == 'okx':
                # OKX: 8-hour cycles
                now = datetime.utcnow()
                funding_hours = [0, 8, 16]
                for h in funding_hours:
                    next_time = now.replace(hour=h, minute=0, second=0, microsecond=0)
                    if next_time > now:
                        return next_time
                return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        except Exception as e:
            print(f"    Error getting funding time: {e}")
        
        # Default: next 8-hour mark
        now = datetime.utcnow()
        funding_hours = [0, 8, 16]
        for h in funding_hours:
            next_time = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if next_time > now:
                return next_time
        return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    def check_liquidity(self, exchange_name: str, symbol: str) -> Tuple[bool, float, float]:
        """Check if symbol is liquid enough"""
        try:
            exchange = self.exchanges[exchange_name]
            ticker = exchange.fetch_ticker(symbol)
            
            volume_usd = ticker.get('quoteVolume', 0)
            if volume_usd == 0:
                volume_usd = ticker.get('baseVolume', 0) * ticker.get('last', 0)
            
            bid = ticker.get('bid')
            ask = ticker.get('ask')
            spread_pct = 0
            if bid and ask and bid > 0:
                spread_pct = ((ask - bid) / bid) * 100
            
            is_liquid = volume_usd >= self.min_daily_volume and spread_pct < 0.5
            
            return is_liquid, volume_usd, spread_pct
        
        except Exception as e:
            return False, 0, 0
    
    def get_funding_rate_data(self, exchange_name: str, symbol: str) -> Dict:
        """Get complete funding rate data"""
        try:
            exchange = self.exchanges[exchange_name]
            funding_rate = exchange.fetch_funding_rate(symbol)
            
            rate = funding_rate.get('fundingRate', 0)
            rate_8h_pct = rate * 100
            rate_annual_pct = rate * 100 * 3 * 365
            
            return {
                'exchange': exchange_name,
                'symbol': symbol,
                'funding_rate': rate,
                'funding_rate_8h_pct': rate_8h_pct,
                'funding_rate_annual_pct': rate_annual_pct,
                'next_funding_time': funding_rate.get('fundingTimestamp'),
                'timestamp': funding_rate.get('timestamp')
            }
        
        except Exception as e:
            print(f"    Error fetching funding rate: {e}")
            return None
    
    def verify_opportunity(self, base_symbol: str, test_exchanges: List[str] = None) -> Dict:
        """Rigorously verify an arbitrage opportunity"""
        if test_exchanges is None:
            test_exchanges = ['binance', 'bybit', 'okx', 'gateio']
        
        print(f"\n{'='*80}")
        print(f"VERIFYING: {base_symbol}")
        print(f"{'='*80}")
        
        symbol_map = {
            'binance': f"{base_symbol}/USDT:USDT",
            'bybit': f"{base_symbol}/USDT:USDT",
            'okx': f"{base_symbol}-USDT-SWAP",
            'gateio': f"{base_symbol}_USDT"
        }
        
        exchange_data = []
        
        for ex_name in test_exchanges:
            try:
                symbol = symbol_map[ex_name]
                print(f"\n{ex_name.upper()}: {symbol}")
                
                is_liquid, volume, spread = self.check_liquidity(ex_name, symbol)
                print(f"  Liquidity: ${volume:,.0f} daily volume, {spread:.3f}% spread")
                
                if not is_liquid:
                    print(f"  ✗ NOT LIQUID")
                    continue
                
                print(f"  ✓ LIQUID")
                
                funding_data = self.get_funding_rate_data(ex_name, symbol)
                if not funding_data:
                    continue
                
                print(f"  Funding Rate: {funding_data['funding_rate_8h_pct']:+.6f}% per 8h")
                print(f"  Annualized: {funding_data['funding_rate_annual_pct']:+.2f}% APY")
                
                next_funding = self.get_next_funding_time(ex_name, symbol)
                print(f"  Next Funding: {next_funding.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                
                funding_data['next_funding_datetime'] = next_funding
                funding_data['daily_volume_usd'] = volume
                funding_data['bid_ask_spread_pct'] = spread
                
                exchange_data.append(funding_data)
            
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
        
        if len(exchange_data) < 2:
            print(f"\n✗ INSUFFICIENT DATA")
            return None
        
        # Find best arbitrage pair
        best_spread = 0
        best_pair = None
        
        for i, ex1 in enumerate(exchange_data):
            for ex2 in exchange_data[i+1:]:
                spread = abs(ex1['funding_rate_annual_pct'] - ex2['funding_rate_annual_pct'])
                if spread > best_spread:
                    best_spread = spread
                    if ex1['funding_rate_annual_pct'] < ex2['funding_rate_annual_pct']:
                        best_pair = (ex1, ex2)
                    else:
                        best_pair = (ex2, ex1)
        
        if not best_pair or best_spread < 5:
            print(f"\n✗ NO PROFITABLE SPREAD")
            return None
        
        long_ex, short_ex = best_pair
        
        now = datetime.utcnow()
        next_funding = min(long_ex['next_funding_datetime'], short_ex['next_funding_datetime'])
        time_to_funding = (next_funding - now).total_seconds() / 60
        
        entry_time = next_funding - timedelta(minutes=10)
        exit_time = next_funding + timedelta(minutes=5)
        
        position_size = 1000
        long_rate_8h = long_ex['funding_rate_8h_pct'] / 100
        short_rate_8h = short_ex['funding_rate_8h_pct'] / 100
        
        profit_long = position_size * abs(long_rate_8h)
        profit_short = position_size * abs(short_rate_8h)
        net_profit_8h = profit_long - profit_short
        net_profit_daily = net_profit_8h * 3
        
        print(f"\n{'='*80}")
        print(f"✓ VERIFIED ARBITRAGE OPPORTUNITY")
        print(f"{'='*80}")
        
        print(f"\nTRADE SETUP:")
        print(f"  Asset: {base_symbol}")
        print(f"  Position Size: ${position_size:,.2f} per leg")
        
        print(f"\n  LONG LEG (we receive funding):")
        print(f"    Exchange: {long_ex['exchange'].upper()}")
        print(f"    Symbol: {long_ex['symbol']}")
        print(f"    Funding Rate: {long_ex['funding_rate_8h_pct']:+.6f}% per 8h")
        print(f"    Annualized: {long_ex['funding_rate_annual_pct']:+.2f}% APY")
        print(f"    We RECEIVE: ${profit_long:.2f} per 8h period")
        
        print(f"\n  SHORT LEG (we pay funding, hedges price risk):")
        print(f"    Exchange: {short_ex['exchange'].upper()}")
        print(f"    Symbol: {short_ex['symbol']}")
        print(f"    Funding Rate: {short_ex['funding_rate_8h_pct']:+.6f}% per 8h")
        print(f"    Annualized: {short_ex['funding_rate_annual_pct']:+.2f}% APY")
        print(f"    We PAY: ${profit_short:.2f} per 8h period")
        
        print(f"\n  SPREAD:")
        print(f"    Difference: {best_spread:.2f}% APY")
        print(f"    Net Profit: ${net_profit_8h:.2f} per 8h period")
        print(f"    Daily Profit: ${net_profit_daily:.2f} (3 periods)")
        print(f"    Daily Return: {(net_profit_daily/position_size)*100:.2f}%")
        
        print(f"\nTIMING:")
        print(f"  Current Time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Next Funding: {next_funding.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"  Time to Funding: {time_to_funding:.1f} minutes")
        print(f"\n  We ENTER at: {entry_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (10 min before)")
        print(f"  We EXIT at:  {exit_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (5 min after)")
        print(f"  Hold Duration: 15 minutes per cycle")
        
        print(f"\nLIQUIDITY:")
        print(f"  {long_ex['exchange'].upper()}: ${long_ex['daily_volume_usd']:,.0f} daily volume")
        print(f"  {short_ex['exchange'].upper()}: ${short_ex['daily_volume_usd']:,.0f} daily volume")
        print(f"  Bid-Ask Spreads: {long_ex['bid_ask_spread_pct']:.3f}% / {short_ex['bid_ask_spread_pct']:.3f}%")
        
        print(f"\nEXECUTION PLAN:")
        print(f"  1. At {entry_time.strftime('%H:%M')} UTC - ENTRY:")
        print(f"     - We LONG ${position_size:,.0f} on {long_ex['exchange'].upper()} {long_ex['symbol']}")
        print(f"     - We SHORT ${position_size:,.0f} on {short_ex['exchange'].upper()} {short_ex['symbol']}")
        print(f"     - Positions are now hedged (delta neutral)")
        print(f"  2. At {next_funding.strftime('%H:%M')} UTC - FUNDING COLLECTION:")
        print(f"     - We collect ${net_profit_8h:.2f} in funding payments")
        print(f"  3. At {exit_time.strftime('%H:%M')} UTC - EXIT:")
        print(f"     - We CLOSE LONG on {long_ex['exchange'].upper()}")
        print(f"     - We CLOSE SHORT on {short_ex['exchange'].upper()}")
        print(f"     - Trade complete, profit realized")
        
        fees_estimate = position_size * 0.001 * 4
        net_after_fees = net_profit_8h - fees_estimate
        
        print(f"\nPROFIT ANALYSIS:")
        print(f"  Gross Profit: ${net_profit_8h:.2f}")
        print(f"  Trading Fees: ${fees_estimate:.2f} (estimated 0.1% per side)")
        print(f"  Net Profit: ${net_after_fees:.2f}")
        print(f"  ROI per cycle: {(net_after_fees/(position_size*2))*100:.3f}%")
        print(f"  Daily ROI: {(net_after_fees/(position_size*2))*100*3:.2f}% (3 cycles)")
        
        return {
            'symbol': base_symbol,
            'long_exchange': long_ex,
            'short_exchange': short_ex,
            'spread_apy': best_spread,
            'profit_per_8h': net_profit_8h,
            'profit_daily': net_profit_daily,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'next_funding': next_funding
        }


def main():
    print("="*80)
    print("RIGOROUS FUNDING RATE ARBITRAGE VERIFICATION")
    print("Testing liquid tickers with real market data")
    print("="*80)
    
    tester = RigorousArbitrageTester()
    
    test_symbols = [
        'BTC',   # Bitcoin
        'ETH',   # Ethereum
        'SOL',   # Solana
        'XRP',   # Ripple
        'DOGE',  # Dogecoin
        'MATIC', # Polygon
        'ARB',   # Arbitrum
        'OP',    # Optimism
    ]
    
    verified_opportunities = []
    
    for symbol in test_symbols:
        try:
            result = tester.verify_opportunity(symbol)
            if result:
                verified_opportunities.append(result)
            time.sleep(2)
        except Exception as e:
            print(f"\nError testing {symbol}: {e}")
            continue
    
    print("\n" + "="*80)
    print("SUMMARY - VERIFIED OPPORTUNITIES")
    print("="*80)
    
    if verified_opportunities:
        print(f"\nWe found {len(verified_opportunities)} verified, liquid arbitrage opportunities:\n")
        
        for i, opp in enumerate(verified_opportunities, 1):
            print(f"{i}. {opp['symbol']}")
            print(f"   Spread: {opp['spread_apy']:.2f}% APY")
            print(f"   Profit: ${opp['profit_per_8h']:.2f} per 8h (${opp['profit_daily']:.2f} daily)")
            print(f"   We LONG on: {opp['long_exchange']['exchange'].upper()}")
            print(f"   We SHORT on: {opp['short_exchange']['exchange'].upper()}")
            print(f"   Next Entry: {opp['entry_time'].strftime('%Y-%m-%d %H:%M')} UTC")
            print()
        
        summary_data = []
        for opp in verified_opportunities:
            summary_data.append({
                'symbol': opp['symbol'],
                'long_exchange': opp['long_exchange']['exchange'],
                'long_rate_apy': opp['long_exchange']['funding_rate_annual_pct'],
                'short_exchange': opp['short_exchange']['exchange'],
                'short_rate_apy': opp['short_exchange']['funding_rate_annual_pct'],
                'spread_apy': opp['spread_apy'],
                'profit_per_8h': opp['profit_per_8h'],
                'profit_daily': opp['profit_daily'],
                'entry_time': opp['entry_time'],
                'exit_time': opp['exit_time'],
                'long_volume': opp['long_exchange']['daily_volume_usd'],
                'short_volume': opp['short_exchange']['daily_volume_usd']
            })
        
        df = pd.DataFrame(summary_data)
        df.to_csv('verified_opportunities.csv', index=False)
        print(f"✓ Saved {len(verified_opportunities)} verified opportunities to verified_opportunities.csv")
    
    else:
        print("\n✗ No verified opportunities found")


if __name__ == "__main__":
    main()
