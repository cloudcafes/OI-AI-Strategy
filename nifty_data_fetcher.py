# nifty_data_fetcher.py
import requests
import datetime
import time
import sqlite3
from nifty_core_config import (
    SYMBOL, MAX_RETRIES, INITIAL_RETRY_DELAY, HEADERS, STOCK_HEADERS,
    parse_numeric_value, parse_float_value, DB_FILE, get_next_cycle, format_greek_value,
    TOP_NIFTY_STOCKS, should_calculate_pcr, initialize_session, initialize_stock_session
)

def fetch_option_chain(session):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={SYMBOL}"
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))
            else:
                raise Exception(f"Failed after {MAX_RETRIES} attempts: {str(e)}")

def parse_option_chain(data):
    try:
        current_nifty = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Filter for nearest expiry only
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        strike_prices = sorted(list(set(record['strikePrice'] for record in nearest_expiry_records)))
        
        # Find closest strike and select ATM ±2 strikes only
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_nifty))
        closest_index = strike_prices.index(closest_strike)
        
        # Get ATM ±2 strikes (total 5 strikes)
        selected_strikes = strike_prices[max(0, closest_index - 2):min(len(strike_prices), closest_index + 3)]
        
        filtered_records = []
        
        for strike in selected_strikes:
            record = next((r for r in nearest_expiry_records if r['strikePrice'] == strike), None)
            if record:
                # Parse CE data without Greeks (delta, gamma, theta, vega removed)
                ce_data = record.get('CE', {})
                # Parse PE data without Greeks (delta, gamma, theta, vega removed)
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'nifty_value': round(current_nifty),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data - only IV kept, other Greeks removed
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    # PE Data - only IV kept, other Greeks removed
                    'pe_change_oi': parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume': parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp': parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi': parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv': parse_float_value(pe_data.get('impliedVolatility', 0)),
                }
                filtered_records.append(oi_data)
        
        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain: {str(e)}")

def calculate_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for ATM ±2 strikes"""
    if not should_calculate_pcr():
        return 0, 0
        
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_volume = 0
    total_pe_volume = 0
    
    for data in oi_data:
        total_ce_oi += data['ce_oi']
        total_pe_oi += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']
    
    # Calculate PCR values
    oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 0
    
    return oi_pcr, volume_pcr

def fetch_stock_option_chain(session, symbol):
    """Fetch option chain data for individual stock"""
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    for attempt in range(3):
        try:
            response = session.get(url, headers=STOCK_HEADERS, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt < 2:
                time.sleep(5 * (2 ** attempt))
            else:
                raise Exception(f"Failed after 3 attempts for {symbol}: {str(e)}")

def parse_stock_option_chain(data, symbol):
    """Parse stock option chain data without Greeks (delta, gamma, theta, vega removed)"""
    try:
        current_stock_value = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Filter for nearest expiry only
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        strike_prices = sorted(list(set(record['strikePrice'] for record in nearest_expiry_records)))
        
        # Find closest strike and select ATM ±2 strikes
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_stock_value))
        closest_index = strike_prices.index(closest_strike)
        selected_strikes = strike_prices[max(0, closest_index - 2):min(len(strike_prices), closest_index + 3)]
        
        filtered_records = []
        
        for strike in selected_strikes:
            record = next((r for r in nearest_expiry_records if r['strikePrice'] == strike), None)
            if record:
                # Parse CE data without Greeks
                ce_data = record.get('CE', {})
                # Parse PE data without Greeks
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'symbol': symbol,
                    'stock_value': round(current_stock_value, 2),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data - only IV kept, other Greeks removed
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    # PE Data - only IV kept, other Greeks removed
                    'pe_change_oi': parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume': parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp': parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi': parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv': parse_float_value(pe_data.get('impliedVolatility', 0)),
                }
                filtered_records.append(oi_data)
        
        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain for {symbol}: {str(e)}")

def calculate_stock_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for stock"""
    if not should_calculate_pcr():
        return 0, 0
        
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_volume = 0
    total_pe_volume = 0
    
    for data in oi_data:
        total_ce_oi += data['ce_oi']
        total_pe_oi += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']
    
    # Calculate PCR values
    oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 0
    
    return oi_pcr, volume_pcr

def fetch_banknifty_data():
    """Fetch BANKNIFTY option chain data without Greeks"""
    try:
        print(f"Fetching BANKNIFTY option chain...")
        
        # Initialize session for BANKNIFTY
        session = initialize_session()
        
        # Fetch BANKNIFTY option chain
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY"
        response = session.get(url, headers=STOCK_HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Parse BANKNIFTY data similar to NIFTY
        current_banknifty = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Filter for nearest expiry only
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        strike_prices = sorted(list(set(record['strikePrice'] for record in nearest_expiry_records)))
        
        # Find closest strike and select ATM ±2 strikes
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_banknifty))
        closest_index = strike_prices.index(closest_strike)
        selected_strikes = strike_prices[max(0, closest_index - 2):min(len(strike_prices), closest_index + 3)]
        
        banknifty_data = []
        
        for strike in selected_strikes:
            record = next((r for r in nearest_expiry_records if r['strikePrice'] == strike), None)
            if record:
                # Parse CE data without Greeks
                ce_data = record.get('CE', {})
                # Parse PE data without Greeks
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'symbol': 'BANKNIFTY',
                    'underlying_value': round(current_banknifty, 2),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data - only IV kept, other Greeks removed
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    # PE Data - only IV kept, other Greeks removed
                    'pe_change_oi': parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume': parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp': parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi': parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv': parse_float_value(pe_data.get('impliedVolatility', 0)),
                }
                banknifty_data.append(oi_data)
        
        # Calculate BANKNIFTY PCR values
        oi_pcr, volume_pcr = calculate_pcr_values(banknifty_data)
        
        return {
            'data': banknifty_data,
            'oi_pcr': oi_pcr,
            'volume_pcr': volume_pcr,
            'current_value': current_banknifty
        }
        
    except Exception as e:
        print(f"Error fetching BANKNIFTY data: {e}")
        return None

def fetch_all_stock_data():
    """Fetch data for all top 10 Nifty stocks"""
    stock_data = {}
    
    from nifty_core_config import should_display_stocks
    
    if should_display_stocks():
        print(f"\n{'='*80}")
        print("FETCHING TOP 10 NIFTY STOCKS DATA...")
        print(f"{'='*80}")
    
    for symbol in TOP_NIFTY_STOCKS.keys():
        try:
            if should_display_stocks():
                print(f"Fetching {symbol}...")
            
            # Initialize session for this stock
            session = initialize_stock_session(symbol)
            
            # Fetch option chain data
            data = fetch_stock_option_chain(session, symbol)
            
            # Parse the data
            oi_data = parse_stock_option_chain(data, symbol)
            
            # Calculate PCR values
            oi_pcr, volume_pcr = calculate_stock_pcr_values(oi_data)
            
            # Store PCR values with data
            stock_data[symbol] = {
                'data': oi_data,
                'oi_pcr': oi_pcr,
                'volume_pcr': volume_pcr,
                'weight': TOP_NIFTY_STOCKS[symbol]['weight']
            }
            
            # Small delay to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    return stock_data

def save_oi_data_to_db(oi_data):
    """Save OI data to SQLite database with proper cycle management"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Get next fetch cycle number
        fetch_cycle, total_fetches = get_next_cycle()
        fetch_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Calculate PCR values before saving
        oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
        
        # Delete existing data for this cycle (if any) before inserting new data
        cursor.execute('DELETE FROM oi_data WHERE fetch_cycle = ?', (fetch_cycle,))
        
        # Save OI data for all strike prices without Greek values
        for data in oi_data:
            # Calculate chg_oi_diff (CE - PE) - CORRECT CALCULATION
            chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
            
            cursor.execute('''
                INSERT INTO oi_data (
                    fetch_cycle, fetch_timestamp, nifty_value, expiry_date, strike_price,
                    ce_change_oi, ce_volume, ce_ltp, ce_oi, ce_iv,
                    pe_change_oi, pe_volume, pe_ltp, pe_oi, pe_iv,
                    chg_oi_diff, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fetch_cycle, fetch_timestamp, data['nifty_value'], data['expiry_date'], data['strike_price'],
                data['ce_change_oi'], data['ce_volume'], data['ce_ltp'], data['ce_oi'], data['ce_iv'],
                data['pe_change_oi'], data['pe_volume'], data['pe_ltp'], data['pe_oi'], data['pe_iv'],
                chg_oi_diff, datetime.datetime.now().isoformat()
            ))
        
        conn.commit()
        
        return oi_pcr, volume_pcr, fetch_cycle, total_fetches
        
    except Exception as e:
        print(f"Error saving to database: {e}")
        conn.rollback()
        return 0, 0, 0, 0
    finally:
        conn.close()