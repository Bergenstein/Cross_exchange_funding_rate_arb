#!/usr/bin/env python3
"""
Multi-exchange funding rate fetcher - Get REAL data from 10+ exchanges
"""

import requests
import pandas as pd
from datetime import datetime
import time
from typing import List, Dict

class ExchangeFetcher:
    
    @staticmethod
    def fetch_binance() -> List[Dict]:
        """Binance Futures"""
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            for item in data:
                if 'symbol' in item and 'lastFundingRate' in item:
                    fr = float(item['lastFundingRate'])
                    rates.append({
                        'exchange': 'binance',
                        'symbol': item['symbol'],
                        'funding_rate': fr,
                        'funding_rate_8h_pct': fr * 100,
                        'funding_rate_annual_pct': fr * 100 * 3 * 365,
                        'next_funding_time': item.get('nextFundingTime', ''),
                        'mark_price': float(item.get('markPrice', 0))
                    })
            return rates
        except Exception as e:
            print(f"  ✗ Binance error: {e}")
            return []
    
    @staticmethod
    def fetch_bybit() -> List[Dict]:
        """Bybit Perpetuals"""
        try:
            url = "https://api.bybit.com/v5/market/tickers?category=linear"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            if data.get('result') and data['result'].get('list'):
                for item in data['result']['list']:
                    if 'symbol' in item and 'fundingRate' in item and item['fundingRate']:
                        fr = float(item['fundingRate'])
                        rates.append({
                            'exchange': 'bybit',
                            'symbol': item['symbol'],
                            'funding_rate': fr,
                            'funding_rate_8h_pct': fr * 100,
                            'funding_rate_annual_pct': fr * 100 * 3 * 365,
                            'next_funding_time': item.get('nextFundingTime', ''),
                            'mark_price': float(item.get('markPrice', 0))
                        })
            return rates
        except Exception as e:
            print(f"  ✗ Bybit error: {e}")
            return []
    
    @staticmethod
    def fetch_okx() -> List[Dict]:
        """OKX Perpetuals"""
        try:
            # First get list of instruments
            url = "https://www.okx.com/api/v5/public/instruments?instType=SWAP"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            instruments = response.json()
            
            rates = []
            if instruments.get('data'):
                # Get funding rates for each instrument (batch)
                inst_ids = [inst['instId'] for inst in instruments['data'][:100]]  # Limit to 100
                
                for inst_id in inst_ids:
                    try:
                        fr_url = f"https://www.okx.com/api/v5/public/funding-rate?instId={inst_id}"
                        fr_response = requests.get(fr_url, timeout=5)
                        fr_data = fr_response.json()
                        
                        if fr_data.get('data') and len(fr_data['data']) > 0:
                            item = fr_data['data'][0]
                            fr = float(item['fundingRate'])
                            rates.append({
                                'exchange': 'okx',
                                'symbol': inst_id,
                                'funding_rate': fr,
                                'funding_rate_8h_pct': fr * 100,
                                'funding_rate_annual_pct': fr * 100 * 3 * 365,
                                'next_funding_time': item.get('nextFundingTime', ''),
                                'mark_price': 0
                            })
                        time.sleep(0.05)  # Rate limit
                    except:
                        continue
            return rates
        except Exception as e:
            print(f"  ✗ OKX error: {e}")
            return []
    
    @staticmethod
    def fetch_gateio() -> List[Dict]:
        """Gate.io Perpetuals - FIXED: Accounts for variable funding intervals"""
        try:
            url = "https://api.gateio.ws/api/v4/futures/usdt/contracts"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            for item in data:
                if 'name' in item and 'funding_rate' in item and 'funding_interval' in item:
                    fr = float(item['funding_rate'])
                    interval_seconds = int(item['funding_interval'])
                    interval_hours = interval_seconds / 3600
                    
                    # Normalize to 8-hour rate for comparison
                    fr_8h = fr * (8 / interval_hours)
                    
                    # Calculate correct APY based on actual interval
                    payments_per_year = (24 / interval_hours) * 365
                    apy = fr * 100 * payments_per_year
                    
                    rates.append({
                        'exchange': 'gateio',
                        'symbol': item['name'],
                        'funding_rate': fr,
                        'funding_rate_8h_pct': fr_8h * 100,  # Normalized to 8h
                        'funding_rate_annual_pct': apy,
                        'next_funding_time': item.get('funding_next_apply', ''),
                        'mark_price': float(item.get('mark_price', 0)),
                        'funding_interval_hours': interval_hours
                    })
            return rates
        except Exception as e:
            print(f"  ✗ Gate.io error: {e}")
            return []
    
    @staticmethod
    def fetch_bitget() -> List[Dict]:
        """Bitget Futures"""
        try:
            url = "https://api.bitget.com/api/mix/v1/market/contracts?productType=umcbl"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            if data.get('data'):
                for item in data['data']:
                    if 'symbol' in item:
                        # Get funding rate for each symbol
                        try:
                            fr_url = f"https://api.bitget.com/api/mix/v1/market/current-fundRate?symbol={item['symbol']}"
                            fr_response = requests.get(fr_url, timeout=5)
                            fr_data = fr_response.json()
                            
                            if fr_data.get('data') and 'fundingRate' in fr_data['data']:
                                fr = float(fr_data['data']['fundingRate'])
                                rates.append({
                                    'exchange': 'bitget',
                                    'symbol': item['symbol'],
                                    'funding_rate': fr,
                                    'funding_rate_8h_pct': fr * 100,
                                    'funding_rate_annual_pct': fr * 100 * 3 * 365,
                                    'next_funding_time': '',
                                    'mark_price': 0
                                })
                            time.sleep(0.05)
                        except:
                            continue
            return rates
        except Exception as e:
            print(f"  ✗ Bitget error: {e}")
            return []
    
    @staticmethod
    def fetch_mexc() -> List[Dict]:
        """MEXC Futures"""
        try:
            url = "https://contract.mexc.com/api/v1/contract/ticker"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            if data.get('data'):
                for item in data['data']:
                    if 'symbol' in item and 'fundingRate' in item:
                        fr = float(item['fundingRate'])
                        rates.append({
                            'exchange': 'mexc',
                            'symbol': item['symbol'],
                            'funding_rate': fr,
                            'funding_rate_8h_pct': fr * 100,
                            'funding_rate_annual_pct': fr * 100 * 3 * 365,
                            'next_funding_time': '',
                            'mark_price': float(item.get('lastPrice', 0))
                        })
            return rates
        except Exception as e:
            print(f"  ✗ MEXC error: {e}")
            return []
    
    @staticmethod
    def fetch_kucoin() -> List[Dict]:
        """KuCoin Futures"""
        try:
            url = "https://api-futures.kucoin.com/api/v1/contracts/active"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            if data.get('data'):
                for item in data['data']:
                    if 'symbol' in item and 'fundingFeeRate' in item:
                        fr = float(item['fundingFeeRate'])
                        rates.append({
                            'exchange': 'kucoin',
                            'symbol': item['symbol'],
                            'funding_rate': fr,
                            'funding_rate_8h_pct': fr * 100,
                            'funding_rate_annual_pct': fr * 100 * 3 * 365,
                            'next_funding_time': '',
                            'mark_price': float(item.get('markPrice', 0))
                        })
            return rates
        except Exception as e:
            print(f"  ✗ KuCoin error: {e}")
            return []
    
    @staticmethod
    def fetch_kraken() -> List[Dict]:
        """Kraken Futures"""
        try:
            url = "https://futures.kraken.com/derivatives/api/v3/tickers"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            if data.get('tickers'):
                for item in data['tickers']:
                    if 'symbol' in item and 'fundingRate' in item:
                        fr = float(item['fundingRate'])
                        rates.append({
                            'exchange': 'kraken',
                            'symbol': item['symbol'],
                            'funding_rate': fr,
                            'funding_rate_8h_pct': fr * 100,
                            'funding_rate_annual_pct': fr * 100 * 3 * 365,
                            'next_funding_time': '',
                            'mark_price': float(item.get('markPrice', 0))
                        })
            return rates
        except Exception as e:
            print(f"  ✗ Kraken error: {e}")
            return []
    
    @staticmethod
    def fetch_deribit() -> List[Dict]:
        """Deribit Perpetuals"""
        try:
            # Get instruments
            url = "https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=future&expired=false"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            rates = []
            if data.get('result'):
                for item in data['result']:
                    if item.get('settlement_period') == 'perpetual':
                        # Get funding rate
                        try:
                            fr_url = f"https://www.deribit.com/api/v2/public/get_funding_rate_value?instrument_name={item['instrument_name']}"
                            fr_response = requests.get(fr_url, timeout=5)
                            fr_data = fr_response.json()
                            
                            if fr_data.get('result') is not None:
                                fr = float(fr_data['result'])
                                rates.append({
                                    'exchange': 'deribit',
                                    'symbol': item['instrument_name'],
                                    'funding_rate': fr,
                                    'funding_rate_8h_pct': fr * 100,
                                    'funding_rate_annual_pct': fr * 100 * 3 * 365,
                                    'next_funding_time': '',
                                    'mark_price': 0
                                })
                            time.sleep(0.1)
                        except:
                            continue
            return rates
        except Exception as e:
            print(f"  ✗ Deribit error: {e}")
            return []


def main():
    print("=" * 80)
    print("FETCHING REAL FUNDING RATES FROM MULTIPLE EXCHANGES")
    print("=" * 80)
    
    exchanges = [
        ('Binance', ExchangeFetcher.fetch_binance),
        ('Bybit', ExchangeFetcher.fetch_bybit),
        ('OKX', ExchangeFetcher.fetch_okx),
        ('Gate.io', ExchangeFetcher.fetch_gateio),
        ('Bitget', ExchangeFetcher.fetch_bitget),
        ('MEXC', ExchangeFetcher.fetch_mexc),
        ('KuCoin', ExchangeFetcher.fetch_kucoin),
        ('Kraken', ExchangeFetcher.fetch_kraken),
        ('Deribit', ExchangeFetcher.fetch_deribit),
    ]
    
    all_rates = []
    
    for idx, (name, fetch_func) in enumerate(exchanges, 1):
        print(f"\n{idx}. Fetching from {name}...")
        rates = fetch_func()
        if rates:
            print(f"   ✓ Got {len(rates)} symbols")
            all_rates.extend(rates)
        else:
            print(f"   ✗ No data")
        time.sleep(0.2)
    
    if not all_rates:
        print("\n✗ ERROR: No data from any exchange!")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_rates)
    df['timestamp'] = datetime.now().isoformat()
    
    # Save to CSV
    filename = 'data/funding_rates_multi_exchange.csv'
    df.to_csv(filename, index=False)
    
    print("\n" + "=" * 80)
    print(f"✓ SAVED {len(df)} funding rates to {filename}")
    print(f"✓ Exchanges: {sorted(df['exchange'].unique().tolist())}")
    print(f"✓ Unique symbols: {df['symbol'].nunique()}")
    print("=" * 80)
    
    # Show top opportunities per exchange
    print("\nTOP 5 POSITIVE RATES PER EXCHANGE:")
    print("-" * 80)
    for exchange in sorted(df['exchange'].unique()):
        ex_data = df[df['exchange'] == exchange]
        top = ex_data.nlargest(5, 'funding_rate_annual_pct')
        if not top.empty:
            print(f"\n{exchange.upper()}:")
            for _, row in top.iterrows():
                print(f"  {row['symbol']:20s} {row['funding_rate_annual_pct']:>8.2f}% APY")
    
    print("\n" + "=" * 80)
    print("TOP 5 NEGATIVE RATES PER EXCHANGE:")
    print("-" * 80)
    for exchange in sorted(df['exchange'].unique()):
        ex_data = df[df['exchange'] == exchange]
        top = ex_data.nsmallest(5, 'funding_rate_annual_pct')
        if not top.empty:
            print(f"\n{exchange.upper()}:")
            for _, row in top.iterrows():
                print(f"  {row['symbol']:20s} {row['funding_rate_annual_pct']:>8.2f}% APY")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
