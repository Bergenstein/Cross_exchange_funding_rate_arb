#!/usr/bin/env python3
"""
Live Trading System for Funding Rate Arbitrage
Production-ready system with real order execution
"""

import ccxt
import pandas as pd
import numpy as np
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv
import threading
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('live_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ExchangeManager:
    """Manages connections to multiple exchanges"""
    
    def __init__(self, mode='paper'):
        self.mode = mode
        self.exchanges = {}
        self.initialize_exchanges()
    
    def initialize_exchanges(self):
        """Initialize exchange connections"""
        
        # Binance
        if os.getenv('BINANCE_API_KEY'):
            self.exchanges['binance'] = ccxt.binance({
                'apiKey': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_SECRET'),
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            if self.mode == 'paper':
                self.exchanges['binance'].set_sandbox_mode(True)
            logger.info("✓ Binance connected")
        
        # Bybit
        if os.getenv('BYBIT_API_KEY'):
            self.exchanges['bybit'] = ccxt.bybit({
                'apiKey': os.getenv('BYBIT_API_KEY'),
                'secret': os.getenv('BYBIT_SECRET'),
                'enableRateLimit': True
            })
            if self.mode == 'paper':
                self.exchanges['bybit'].set_sandbox_mode(True)
            logger.info("✓ Bybit connected")
        
        # Gate.io
        if os.getenv('GATEIO_API_KEY'):
            self.exchanges['gateio'] = ccxt.gateio({
                'apiKey': os.getenv('GATEIO_API_KEY'),
                'secret': os.getenv('GATEIO_SECRET'),
                'enableRateLimit': True
            })
            logger.info("✓ Gate.io connected")
        
        # OKX
        if os.getenv('OKX_API_KEY'):
            self.exchanges['okx'] = ccxt.okx({
                'apiKey': os.getenv('OKX_API_KEY'),
                'secret': os.getenv('OKX_SECRET'),
                'password': os.getenv('OKX_PASSWORD'),
                'enableRateLimit': True
            })
            logger.info("✓ OKX connected")
        
        if not self.exchanges:
            raise ValueError("No exchange API keys found! Check .env file")
    
    def get_exchange(self, exchange_name: str):
        """Get exchange instance"""
        return self.exchanges.get(exchange_name)
    
    def get_funding_rate(self, exchange_name: str, symbol: str) -> Optional[float]:
        """Fetch current funding rate"""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                return None
            
            if exchange_name == 'binance':
                ticker = exchange.fapiPublic_get_premiumindex({'symbol': symbol})
                return float(ticker['lastFundingRate']) * 100 * 3 * 365
            
            elif exchange_name == 'bybit':
                ticker = exchange.fetch_ticker(symbol)
                if 'info' in ticker and 'fundingRate' in ticker['info']:
                    return float(ticker['info']['fundingRate']) * 100 * 3 * 365
            
            elif exchange_name == 'gateio':
                # Gate.io specific API call
                ticker = exchange.fetch_ticker(symbol)
                if 'info' in ticker and 'funding_rate' in ticker['info']:
                    return float(ticker['info']['funding_rate']) * 100 * 3 * 365
            
            return None
        except Exception as e:
            logger.error(f"Error fetching funding rate for {exchange_name} {symbol}: {e}")
            return None
    
    def get_balance(self, exchange_name: str) -> Dict:
        """Get account balance"""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                return {}
            
            balance = exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance for {exchange_name}: {e}")
            return {}
    
    def place_order(self, exchange_name: str, symbol: str, side: str, amount: float, 
                   order_type: str = 'market') -> Optional[Dict]:
        """Place an order"""
        try:
            exchange = self.get_exchange(exchange_name)
            if not exchange:
                return None
            
            logger.info(f"Placing {side} order: {amount} {symbol} on {exchange_name}")
            
            order = exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount
            )
            
            logger.info(f"✓ Order placed: {order['id']}")
            return order
        
        except Exception as e:
            logger.error(f"Error placing order on {exchange_name}: {e}")
            return None
    
    def close_position(self, exchange_name: str, symbol: str, side: str, amount: float) -> bool:
        """Close a position"""
        try:
            # Place opposite order to close
            close_side = 'sell' if side == 'long' else 'buy'
            order = self.place_order(exchange_name, symbol, close_side, amount)
            return order is not None
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False


class OpportunityScanner:
    """Scans for arbitrage opportunities"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.min_spread_apy = 30.0  # Minimum spread to enter
        self.opportunities_file = 'current_opportunities.json'
    
    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol name"""
        return symbol.upper().replace('USDT', '').replace('-PERP', '').replace('_UMCBL', '') \
                     .replace('-SWAP', '').replace('USD', '').replace('PERP', '') \
                     .replace('_', '').replace('-', '').strip()
    
    def scan_all_exchanges(self) -> List[Dict]:
        """Scan all exchanges for opportunities"""
        logger.info("Scanning for arbitrage opportunities...")
        
        all_rates = []
        
        for exchange_name in self.exchange_manager.exchanges.keys():
            try:
                exchange = self.exchange_manager.get_exchange(exchange_name)
                markets = exchange.load_markets()
                
                for symbol in markets.keys():
                    if 'USDT' in symbol or 'USD' in symbol:
                        rate = self.exchange_manager.get_funding_rate(exchange_name, symbol)
                        if rate is not None:
                            all_rates.append({
                                'exchange': exchange_name,
                                'symbol': symbol,
                                'normalized': self.normalize_symbol(symbol),
                                'rate_apy': rate
                            })
                
                time.sleep(0.5)  # Rate limiting
            
            except Exception as e:
                logger.error(f"Error scanning {exchange_name}: {e}")
                continue
        
        # Find cross-exchange opportunities
        df = pd.DataFrame(all_rates)
        opportunities = []
        
        if len(df) > 0:
            for norm_symbol in df['normalized'].unique():
                symbol_data = df[df['normalized'] == norm_symbol]
                
                if len(symbol_data) >= 2:
                    max_row = symbol_data.loc[symbol_data['rate_apy'].idxmax()]
                    min_row = symbol_data.loc[symbol_data['rate_apy'].idxmin()]
                    spread = max_row['rate_apy'] - min_row['rate_apy']
                    
                    if spread >= self.min_spread_apy:
                        opportunities.append({
                            'base_symbol': norm_symbol,
                            'long_exchange': min_row['exchange'],
                            'long_symbol': min_row['symbol'],
                            'long_rate_apy': min_row['rate_apy'],
                            'short_exchange': max_row['exchange'],
                            'short_symbol': max_row['symbol'],
                            'short_rate_apy': max_row['rate_apy'],
                            'spread_apy': spread,
                            'timestamp': datetime.now().isoformat()
                        })
        
        # Save opportunities
        with open(self.opportunities_file, 'w') as f:
            json.dump(opportunities, f, indent=2)
        
        logger.info(f"✓ Found {len(opportunities)} opportunities")
        return opportunities


class PositionManager:
    """Manages open positions"""
    
    def __init__(self, exchange_manager: ExchangeManager):
        self.exchange_manager = exchange_manager
        self.positions = []
        self.positions_file = 'live_positions.json'
        self.max_position_size = 1000  # USD per position
        self.max_positions = 5
        self.load_positions()
    
    def load_positions(self):
        """Load positions from file"""
        try:
            with open(self.positions_file, 'r') as f:
                data = json.load(f)
                self.positions = data.get('positions', [])
            logger.info(f"✓ Loaded {len(self.positions)} positions")
        except FileNotFoundError:
            logger.info("No existing positions")
    
    def save_positions(self):
        """Save positions to file"""
        with open(self.positions_file, 'w') as f:
            json.dump({
                'positions': self.positions,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def can_open_position(self) -> bool:
        """Check if we can open a new position"""
        return len(self.positions) < self.max_positions
    
    def open_position(self, opportunity: Dict) -> bool:
        """Open a new arbitrage position"""
        
        if not self.can_open_position():
            logger.warning("Max positions reached, cannot open new position")
            return False
        
        try:
            # Calculate position size based on available balance
            long_balance = self.exchange_manager.get_balance(opportunity['long_exchange'])
            short_balance = self.exchange_manager.get_balance(opportunity['short_exchange'])
            
            available_capital = min(
                long_balance.get('USDT', {}).get('free', 0),
                short_balance.get('USDT', {}).get('free', 0),
                self.max_position_size
            )
            
            if available_capital < 100:
                logger.warning(f"Insufficient capital: ${available_capital}")
                return False
            
            # Get current prices to calculate amounts
            long_exchange = self.exchange_manager.get_exchange(opportunity['long_exchange'])
            short_exchange = self.exchange_manager.get_exchange(opportunity['short_exchange'])
            
            long_ticker = long_exchange.fetch_ticker(opportunity['long_symbol'])
            short_ticker = short_exchange.fetch_ticker(opportunity['short_symbol'])
            
            long_price = long_ticker['last']
            short_price = short_ticker['last']
            
            # Calculate amounts (use average price)
            avg_price = (long_price + short_price) / 2
            amount = available_capital / avg_price
            
            # Place orders
            logger.info(f"Opening position: {opportunity['base_symbol']}")
            logger.info(f"  Capital: ${available_capital:.2f}")
            logger.info(f"  Amount: {amount:.6f}")
            
            # Long on exchange with negative rate
            long_order = self.exchange_manager.place_order(
                opportunity['long_exchange'],
                opportunity['long_symbol'],
                'buy',
                amount
            )
            
            if not long_order:
                logger.error("Failed to place long order")
                return False
            
            # Short on exchange with positive rate
            short_order = self.exchange_manager.place_order(
                opportunity['short_exchange'],
                opportunity['short_symbol'],
                'sell',
                amount
            )
            
            if not short_order:
                logger.error("Failed to place short order, closing long...")
                # Close the long position
                self.exchange_manager.close_position(
                    opportunity['long_exchange'],
                    opportunity['long_symbol'],
                    'long',
                    amount
                )
                return False
            
            # Record position
            position = {
                'id': len(self.positions) + 1,
                'base_symbol': opportunity['base_symbol'],
                'long_exchange': opportunity['long_exchange'],
                'long_symbol': opportunity['long_symbol'],
                'long_order_id': long_order['id'],
                'long_amount': amount,
                'long_entry_price': long_price,
                'short_exchange': opportunity['short_exchange'],
                'short_symbol': opportunity['short_symbol'],
                'short_order_id': short_order['id'],
                'short_amount': amount,
                'short_entry_price': short_price,
                'entry_spread_apy': opportunity['spread_apy'],
                'entry_time': datetime.now().isoformat(),
                'capital': available_capital,
                'total_funding_collected': 0,
                'status': 'open'
            }
            
            self.positions.append(position)
            self.save_positions()
            
            logger.info(f"✓ Position opened: {opportunity['base_symbol']}")
            logger.info(f"  Long:  {opportunity['long_exchange']} @ ${long_price:.2f}")
            logger.info(f"  Short: {opportunity['short_exchange']} @ ${short_price:.2f}")
            logger.info(f"  Spread: {opportunity['spread_apy']:.2f}% APY")
            
            return True
        
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return False
    
    def update_positions(self):
        """Update all open positions"""
        
        for position in self.positions:
            if position['status'] != 'open':
                continue
            
            try:
                # Get current rates
                long_rate = self.exchange_manager.get_funding_rate(
                    position['long_exchange'],
                    position['long_symbol']
                )
                short_rate = self.exchange_manager.get_funding_rate(
                    position['short_exchange'],
                    position['short_symbol']
                )
                
                if long_rate is not None and short_rate is not None:
                    current_spread = short_rate - long_rate
                    position['current_spread_apy'] = current_spread
                    position['current_long_rate_apy'] = long_rate
                    position['current_short_rate_apy'] = short_rate
                    position['last_update'] = datetime.now().isoformat()
                    
                    # Check if we should close (spread dropped too much)
                    if current_spread < 10:  # Exit threshold
                        logger.warning(f"Spread dropped to {current_spread:.2f}% for {position['base_symbol']}")
                        self.close_position(position['id'], "Low spread")
            
            except Exception as e:
                logger.error(f"Error updating position {position['id']}: {e}")
        
        self.save_positions()
    
    def close_position(self, position_id: int, reason: str) -> bool:
        """Close a position"""
        
        position = next((p for p in self.positions if p['id'] == position_id), None)
        if not position or position['status'] != 'open':
            return False
        
        try:
            logger.info(f"Closing position {position_id}: {position['base_symbol']}")
            logger.info(f"  Reason: {reason}")
            
            # Close long
            long_closed = self.exchange_manager.close_position(
                position['long_exchange'],
                position['long_symbol'],
                'long',
                position['long_amount']
            )
            
            # Close short
            short_closed = self.exchange_manager.close_position(
                position['short_exchange'],
                position['short_symbol'],
                'short',
                position['short_amount']
            )
            
            if long_closed and short_closed:
                position['status'] = 'closed'
                position['close_time'] = datetime.now().isoformat()
                position['close_reason'] = reason
                self.save_positions()
                logger.info(f"✓ Position {position_id} closed")
                return True
            else:
                logger.error("Failed to close one or both legs")
                return False
        
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """Get portfolio summary"""
        open_positions = [p for p in self.positions if p['status'] == 'open']
        closed_positions = [p for p in self.positions if p['status'] == 'closed']
        
        total_capital = sum(p['capital'] for p in open_positions)
        total_funding = sum(p.get('total_funding_collected', 0) for p in open_positions)
        
        return {
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_capital_deployed': total_capital,
            'total_funding_collected': total_funding,
            'positions': open_positions
        }


class LiveTradingSystem:
    """Main live trading system"""
    
    def __init__(self, mode='paper'):
        self.mode = mode
        self.exchange_manager = ExchangeManager(mode)
        self.scanner = OpportunityScanner(self.exchange_manager)
        self.position_manager = PositionManager(self.exchange_manager)
        self.scheduler = BackgroundScheduler()
        self.running = False
    
    def start(self):
        """Start the trading system"""
        logger.info("="*80)
        logger.info(f"STARTING LIVE TRADING SYSTEM - MODE: {self.mode.upper()}")
        logger.info("="*80)
        
        # Schedule tasks
        self.scheduler.add_job(self.scan_and_trade, 'interval', minutes=5, id='scan_trade')
        self.scheduler.add_job(self.update_positions, 'interval', minutes=15, id='update_positions')
        self.scheduler.add_job(self.report_status, 'interval', hours=1, id='report_status')
        
        self.scheduler.start()
        self.running = True
        
        # Run once immediately
        self.scan_and_trade()
        
        logger.info("✓ Trading system started")
        logger.info("  Scanning every 5 minutes")
        logger.info("  Updating positions every 15 minutes")
        logger.info("  Status reports every 1 hour")
    
    def scan_and_trade(self):
        """Scan for opportunities and execute trades"""
        try:
            logger.info("Starting opportunity scan...")
            opportunities = self.scanner.scan_all_exchanges()
            
            if not opportunities:
                logger.info("No opportunities found")
                return
            
            # Sort by spread
            opportunities.sort(key=lambda x: x['spread_apy'], reverse=True)
            
            # Try to open position on best opportunity
            for opp in opportunities[:3]:  # Try top 3
                if self.position_manager.can_open_position():
                    logger.info(f"Attempting to open position: {opp['base_symbol']} ({opp['spread_apy']:.2f}% APY)")
                    
                    if self.position_manager.open_position(opp):
                        break  # Only open one at a time
                else:
                    logger.info("Max positions reached, skipping new positions")
                    break
        
        except Exception as e:
            logger.error(f"Error in scan_and_trade: {e}")
    
    def update_positions(self):
        """Update all positions"""
        try:
            logger.info("Updating positions...")
            self.position_manager.update_positions()
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
    
    def report_status(self):
        """Report system status"""
        try:
            summary = self.position_manager.get_summary()
            
            logger.info("="*80)
            logger.info("SYSTEM STATUS REPORT")
            logger.info("="*80)
            logger.info(f"Mode: {self.mode.upper()}")
            logger.info(f"Open Positions: {summary['open_positions']}")
            logger.info(f"Closed Positions: {summary['closed_positions']}")
            logger.info(f"Capital Deployed: ${summary['total_capital_deployed']:,.2f}")
            logger.info(f"Funding Collected: ${summary['total_funding_collected']:,.2f}")
            logger.info("="*80)
        
        except Exception as e:
            logger.error(f"Error in status report: {e}")
    
    def stop(self):
        """Stop the trading system"""
        logger.info("Stopping trading system...")
        self.scheduler.shutdown()
        self.running = False
        logger.info("✓ Trading system stopped")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Funding Rate Arbitrage Trading System')
    parser.add_argument('--mode', choices=['paper', 'live'], default='paper',
                       help='Trading mode: paper (testnet) or live (real money)')
    
    args = parser.parse_args()
    
    if args.mode == 'live':
        response = input("⚠️  WARNING: You are about to start LIVE TRADING with REAL MONEY. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
    
    # Create system
    system = LiveTradingSystem(mode=args.mode)
    
    try:
        system.start()
        
        # Keep running
        while True:
            time.sleep(60)
    
    except KeyboardInterrupt:
        logger.info("\n\nShutdown requested...")
        system.stop()
        logger.info("✓ System shutdown complete")


if __name__ == "__main__":
    main()
