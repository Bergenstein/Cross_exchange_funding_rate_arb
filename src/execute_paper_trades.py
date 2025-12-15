#!/usr/bin/env python3
"""
Real Paper Trading System for Funding Rate Arbitrage
Executes paper trades on actual opportunities
"""

import pandas as pd
import json
from datetime import datetime, timedelta
import time
import requests

class PaperTradingSystem:
    
    def __init__(self, capital_per_trade=1000):
        self.capital_per_trade = capital_per_trade
        self.positions = []
        self.closed_trades = []
        self.state_file = 'paper_trade_state.json'
        self.load_state()
    
    def load_state(self):
        """Load existing positions from file"""
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                self.positions = data.get('positions', [])
                self.closed_trades = data.get('closed_trades', [])
                print(f"✓ Loaded {len(self.positions)} open positions")
        except FileNotFoundError:
            print("✓ Starting fresh (no previous state)")
    
    def save_state(self):
        """Save positions to file"""
        with open(self.state_file, 'w') as f:
            json.dump({
                'positions': self.positions,
                'closed_trades': self.closed_trades,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def get_current_funding_rate(self, exchange, symbol):
        """Fetch current funding rate for a symbol"""
        try:
            if exchange == 'binance':
                url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
                response = requests.get(url, timeout=5)
                data = response.json()
                return float(data['lastFundingRate']) * 100 * 3 * 365
            
            elif exchange == 'bybit':
                url = f"https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('result') and data['result'].get('list'):
                    return float(data['result']['list'][0]['fundingRate']) * 100 * 3 * 365
            
            elif exchange == 'gateio':
                url = f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{symbol}"
                response = requests.get(url, timeout=5)
                data = response.json()
                return float(data['funding_rate']) * 100 * 3 * 365
            
            elif exchange == 'mexc':
                url = f"https://contract.mexc.com/api/v1/contract/ticker?symbol={symbol}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('data'):
                    return float(data['data']['fundingRate']) * 100 * 3 * 365
            
            elif exchange == 'okx':
                url = f"https://www.okx.com/api/v5/public/funding-rate?instId={symbol}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('data'):
                    return float(data['data'][0]['fundingRate']) * 100 * 3 * 365
        
        except Exception as e:
            print(f"  Error fetching rate for {exchange} {symbol}: {e}")
            return None
        
        return None
    
    def open_position(self, opportunity):
        """Open a paper trade position"""
        
        # Get current rates
        long_rate = self.get_current_funding_rate(opportunity['long_exchange'], opportunity['long_symbol'])
        short_rate = self.get_current_funding_rate(opportunity['short_exchange'], opportunity['short_symbol'])
        
        if long_rate is None or short_rate is None:
            print(f"  ✗ Could not fetch current rates for {opportunity['base_symbol']}")
            return False
        
        current_spread = short_rate - long_rate
        
        position = {
            'id': len(self.positions) + 1,
            'base_symbol': opportunity['base_symbol'],
            'long_exchange': opportunity['long_exchange'],
            'long_symbol': opportunity['long_symbol'],
            'short_exchange': opportunity['short_exchange'],
            'short_symbol': opportunity['short_symbol'],
            'entry_spread_apy': current_spread,
            'entry_long_rate_apy': long_rate,
            'entry_short_rate_apy': short_rate,
            'capital': self.capital_per_trade,
            'entry_time': datetime.now().isoformat(),
            'last_update': datetime.now().isoformat(),
            'total_funding_collected': 0,
            'num_funding_periods': 0
        }
        
        self.positions.append(position)
        self.save_state()
        
        print(f"\n  ✓ OPENED Position #{position['id']}: {position['base_symbol']}")
        print(f"    Long:  {position['long_exchange']:10s} @ {long_rate:>7.2f}% APY")
        print(f"    Short: {position['short_exchange']:10s} @ {short_rate:>7.2f}% APY")
        print(f"    Spread: {current_spread:>7.2f}% APY")
        print(f"    Capital: ${self.capital_per_trade:,.2f}")
        
        return True
    
    def update_positions(self):
        """Update all open positions with current funding rates"""
        
        if not self.positions:
            print("\n✓ No open positions to update")
            return
        
        print(f"\n{'='*80}")
        print(f"UPDATING {len(self.positions)} OPEN POSITIONS")
        print(f"{'='*80}")
        
        for position in self.positions:
            print(f"\nPosition #{position['id']}: {position['base_symbol']}")
            
            # Get current rates
            long_rate = self.get_current_funding_rate(position['long_exchange'], position['long_symbol'])
            short_rate = self.get_current_funding_rate(position['short_exchange'], position['short_symbol'])
            
            if long_rate is None or short_rate is None:
                print(f"  ✗ Could not update rates")
                continue
            
            current_spread = short_rate - long_rate
            
            # Calculate funding payment (assuming 8h period)
            hours_since_last = 8  # Simplified - in reality track exact time
            funding_payment = (position['capital'] * current_spread / 100) * (hours_since_last / (365 * 24))
            
            position['total_funding_collected'] += funding_payment
            position['num_funding_periods'] += 1
            position['last_update'] = datetime.now().isoformat()
            position['current_spread_apy'] = current_spread
            position['current_long_rate_apy'] = long_rate
            position['current_short_rate_apy'] = short_rate
            
            print(f"  Long:  {position['long_exchange']:10s} @ {long_rate:>7.2f}% APY")
            print(f"  Short: {position['short_exchange']:10s} @ {short_rate:>7.2f}% APY")
            print(f"  Current Spread: {current_spread:>7.2f}% APY")
            print(f"  Funding Collected: ${position['total_funding_collected']:>7.2f}")
            print(f"  Entry Spread: {position['entry_spread_apy']:>7.2f}% APY")
        
        self.save_state()
        print(f"\n{'='*80}")
    
    def close_position(self, position_id, reason="Manual close"):
        """Close a position"""
        
        position = next((p for p in self.positions if p['id'] == position_id), None)
        if not position:
            print(f"✗ Position #{position_id} not found")
            return False
        
        position['close_time'] = datetime.now().isoformat()
        position['close_reason'] = reason
        position['final_pnl'] = position['total_funding_collected']
        
        self.closed_trades.append(position)
        self.positions = [p for p in self.positions if p['id'] != position_id]
        self.save_state()
        
        print(f"\n✓ CLOSED Position #{position_id}: {position['base_symbol']}")
        print(f"  Total Funding: ${position['total_funding_collected']:>7.2f}")
        print(f"  Reason: {reason}")
        
        return True
    
    def show_summary(self):
        """Show portfolio summary"""
        
        print(f"\n{'='*80}")
        print("PAPER TRADING PORTFOLIO SUMMARY")
        print(f"{'='*80}")
        
        print(f"\nOPEN POSITIONS: {len(self.positions)}")
        if self.positions:
            total_capital = sum(p['capital'] for p in self.positions)
            total_funding = sum(p.get('total_funding_collected', 0) for p in self.positions)
            print(f"  Total Capital: ${total_capital:,.2f}")
            print(f"  Total Funding: ${total_funding:,.2f}")
            print(f"  Return: {(total_funding/total_capital*100) if total_capital > 0 else 0:.2f}%")
        
        print(f"\nCLOSED TRADES: {len(self.closed_trades)}")
        if self.closed_trades:
            total_pnl = sum(t['final_pnl'] for t in self.closed_trades)
            print(f"  Total P&L: ${total_pnl:,.2f}")
        
        print(f"\n{'='*80}")


def main():
    print("=" * 80)
    print("REAL FUNDING RATE ARBITRAGE - PAPER TRADING SYSTEM")
    print("=" * 80)
    
    # Load opportunities
    try:
        opps = pd.read_csv('data/arbitrage_opportunities.csv')
    except FileNotFoundError:
        print("\n✗ ERROR: data/arbitrage_opportunities.csv not found!")
        print("Run: python3 find_real_arbitrage.py first")
        return
    
    print(f"\n✓ Loaded {len(opps)} arbitrage opportunities")
    
    # Initialize paper trading system
    trader = PaperTradingSystem(capital_per_trade=1000)
    
    # Show current portfolio
    trader.show_summary()
    
    print("\n" + "=" * 80)
    print("AVAILABLE ACTIONS:")
    print("=" * 80)
    print("1. Open positions on top 5 opportunities")
    print("2. Update all open positions")
    print("3. Show portfolio summary")
    print("4. Close all positions")
    print("5. Auto-trade (open top 5 and monitor)")
    print("=" * 80)
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        # Open positions on top 5 opportunities
        print("\n" + "=" * 80)
        print("OPENING POSITIONS ON TOP 5 OPPORTUNITIES")
        print("=" * 80)
        
        for idx, row in opps.head(5).iterrows():
            trader.open_position(row.to_dict())
            time.sleep(1)  # Rate limit
        
        trader.show_summary()
    
    elif choice == '2':
        trader.update_positions()
        trader.show_summary()
    
    elif choice == '3':
        trader.show_summary()
    
    elif choice == '4':
        print("\n" + "=" * 80)
        print("CLOSING ALL POSITIONS")
        print("=" * 80)
        for pos in trader.positions[:]:
            trader.close_position(pos['id'], "User requested close all")
        trader.show_summary()
    
    elif choice == '5':
        print("\n" + "=" * 80)
        print("AUTO-TRADING MODE (Opening top 5 + monitoring)")
        print("=" * 80)
        
        # Open top 5 if no positions
        if len(trader.positions) == 0:
            print("\nOpening positions...")
            for idx, row in opps.head(5).iterrows():
                trader.open_position(row.to_dict())
                time.sleep(1)
        
        # Monitor loop
        print("\nMonitoring (Ctrl+C to stop)...")
        try:
            while True:
                trader.update_positions()
                trader.show_summary()
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Next update in 300 seconds...")
                time.sleep(300)  # Update every 5 minutes
        except KeyboardInterrupt:
            print("\n\n✓ Monitoring stopped")
            trader.show_summary()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
