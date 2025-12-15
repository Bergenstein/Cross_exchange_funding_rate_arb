#!/usr/bin/env python3
"""
Monitoring dashboard - real-time view of positions and performance
"""

import json
import os
from datetime import datetime
from typing import Dict, List
import time

def load_positions() -> List[Dict]:
    """Load current positions"""
    try:
        with open('live_positions.json', 'r') as f:
            data = json.load(f)
            return data.get('positions', [])
    except:
        return []

def load_opportunities() -> List[Dict]:
    """Load current opportunities"""
    try:
        with open('current_opportunities.json', 'r') as f:
            return json.load(f)
    except:
        return []

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def display_dashboard():
    """Display real-time dashboard"""
    
    clear_screen()
    
    print("="*100)
    print(" "*35 + "FUNDING RATE ARBITRAGE - LIVE DASHBOARD")
    print("="*100)
    print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load data
    positions = load_positions()
    opportunities = load_opportunities()
    
    # Open positions
    open_positions = [p for p in positions if p.get('status') == 'open']
    closed_positions = [p for p in positions if p.get('status') in ['closed', 'emergency_closed']]
    
    # Calculate totals
    total_capital = sum(p.get('capital', 0) for p in open_positions)
    total_funding = sum(p.get('total_funding_collected', 0) for p in open_positions)
    
    # Portfolio Summary
    print("─"*100)
    print("PORTFOLIO SUMMARY")
    print("─"*100)
    print(f"Open Positions:      {len(open_positions)}")
    print(f"Closed Positions:    {len(closed_positions)}")
    print(f"Capital Deployed:    ${total_capital:,.2f}")
    print(f"Funding Collected:   ${total_funding:,.2f}")
    if total_capital > 0:
        print(f"Return on Capital:   {(total_funding/total_capital*100):.2f}%")
    print()
    
    # Open Positions Detail
    if open_positions:
        print("─"*100)
        print("OPEN POSITIONS")
        print("─"*100)
        print(f"{'ID':<4} {'Symbol':<10} {'Entry Spread':<13} {'Current Spread':<15} {'Funding':<12} {'Days Open':<10}")
        print("─"*100)
        
        for pos in open_positions:
            pos_id = pos.get('id', 'N/A')
            symbol = pos.get('base_symbol', 'N/A')
            entry_spread = pos.get('entry_spread_apy', 0)
            current_spread = pos.get('current_spread_apy', entry_spread)
            funding = pos.get('total_funding_collected', 0)
            
            # Calculate days open
            entry_time = datetime.fromisoformat(pos.get('entry_time', datetime.now().isoformat()))
            days_open = (datetime.now() - entry_time).days
            
            print(f"{pos_id:<4} {symbol:<10} {entry_spread:>10.2f}%  {current_spread:>12.2f}%  ${funding:>9.2f}  {days_open:>8} days")
        
        print()
        
        # Position Details
        for pos in open_positions[:5]:  # Show details for first 5
            print(f"\nPosition #{pos.get('id')}: {pos.get('base_symbol')}")
            print(f"  Long:  {pos.get('long_exchange'):<10} {pos.get('long_symbol'):<15} @ {pos.get('current_long_rate_apy', 0):>7.2f}% APY")
            print(f"  Short: {pos.get('short_exchange'):<10} {pos.get('short_symbol'):<15} @ {pos.get('current_short_rate_apy', 0):>7.2f}% APY")
            print(f"  Capital: ${pos.get('capital', 0):,.2f}")
    else:
        print("─"*100)
        print("No open positions")
    
    print()
    
    # Available Opportunities
    if opportunities:
        print("─"*100)
        print("TOP AVAILABLE OPPORTUNITIES")
        print("─"*100)
        print(f"{'Symbol':<12} {'Long Exchange':<15} {'Short Exchange':<15} {'Spread APY':<12}")
        print("─"*100)
        
        for opp in opportunities[:10]:
            print(f"{opp['base_symbol']:<12} {opp['long_exchange']:<15} {opp['short_exchange']:<15} {opp['spread_apy']:>10.2f}%")
    else:
        print("─"*100)
        print("No opportunities available")
    
    print()
    print("="*100)
    print("Press Ctrl+C to exit")
    print("="*100)

def main():
    """Main dashboard loop"""
    try:
        while True:
            display_dashboard()
            time.sleep(30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n\nDashboard closed.")

if __name__ == "__main__":
    main()
