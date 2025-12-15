#!/usr/bin/env python3
"""
Emergency shutdown script - closes all positions immediately
"""

import ccxt
import os
from dotenv import load_dotenv
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def load_positions():
    """Load current positions"""
    try:
        with open('live_positions.json', 'r') as f:
            data = json.load(f)
            return data.get('positions', [])
    except:
        return []

def close_all_positions():
    """Emergency close all positions"""
    
    logger.info("="*80)
    logger.info("EMERGENCY SHUTDOWN - CLOSING ALL POSITIONS")
    logger.info("="*80)
    
    positions = load_positions()
    
    if not positions:
        logger.info("No positions to close")
        return
    
    # Initialize exchanges
    exchanges = {}
    
    if os.getenv('BINANCE_API_KEY'):
        exchanges['binance'] = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_SECRET'),
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
    
    if os.getenv('BYBIT_API_KEY'):
        exchanges['bybit'] = ccxt.bybit({
            'apiKey': os.getenv('BYBIT_API_KEY'),
            'secret': os.getenv('BYBIT_SECRET'),
            'enableRateLimit': True
        })
    
    if os.getenv('GATEIO_API_KEY'):
        exchanges['gateio'] = ccxt.gateio({
            'apiKey': os.getenv('GATEIO_API_KEY'),
            'secret': os.getenv('GATEIO_SECRET'),
            'enableRateLimit': True
        })
    
    # Close each position
    for position in positions:
        if position.get('status') != 'open':
            continue
        
        try:
            logger.info(f"\nClosing position: {position['base_symbol']}")
            
            # Close long
            long_exchange = exchanges.get(position['long_exchange'])
            if long_exchange:
                logger.info(f"  Closing long on {position['long_exchange']}")
                long_exchange.create_order(
                    symbol=position['long_symbol'],
                    type='market',
                    side='sell',
                    amount=position['long_amount']
                )
                logger.info("  ✓ Long closed")
            
            # Close short
            short_exchange = exchanges.get(position['short_exchange'])
            if short_exchange:
                logger.info(f"  Closing short on {position['short_exchange']}")
                short_exchange.create_order(
                    symbol=position['short_symbol'],
                    type='market',
                    side='buy',
                    amount=position['short_amount']
                )
                logger.info("  ✓ Short closed")
            
            position['status'] = 'emergency_closed'
        
        except Exception as e:
            logger.error(f"  ✗ Error closing {position['base_symbol']}: {e}")
    
    # Save updated positions
    with open('live_positions.json', 'w') as f:
        json.dump({'positions': positions}, f, indent=2)
    
    logger.info("\n" + "="*80)
    logger.info("EMERGENCY SHUTDOWN COMPLETE")
    logger.info("="*80)

if __name__ == "__main__":
    response = input("⚠️  Are you sure you want to close ALL positions? (yes/no): ")
    if response.lower() == 'yes':
        close_all_positions()
    else:
        print("Cancelled.")
