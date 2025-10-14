# Part 3: Nifty_Option_Chain_Fetcher_Part3.py (With BANKNIFTY Support)
import datetime
import time
import signal
import sys
import sqlite3
import os
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import from previous parts
from Nifty_Option_Chain_Fetcher_Part1 import (
    SYMBOL, FETCH_INTERVAL, DB_FILE, MAX_FETCH_CYCLES, running,
    signal_handler, initialize_database, initialize_session,
    get_chg_oi_diff_history, format_oi_value, format_greek_value, get_next_cycle,
    parse_numeric_value, parse_float_value
)

# Import all necessary functions from Part 2
from Nifty_Option_Chain_Fetcher_Part2 import (
    fetch_option_chain, parse_option_chain, calculate_pcr_values
)

# Import AI analyzer from Part 4
from Nifty_Option_Chain_Fetcher_Part4 import NiftyAIAnalyzer

# Initialize AI analyzer globally
ai_analyzer = NiftyAIAnalyzer()

# Top 10 NIFTY 50 stocks with their symbols and weightages
TOP_NIFTY_STOCKS = {
    'RELIANCE': {'name': 'RELIANCE INDUSTRIES LTD', 'weight': 0.0924},
    'HDFCBANK': {'name': 'HDFC BANK LTD', 'weight': 0.0876},
    'BHARTIARTL': {'name': 'BHARTI AIRTEL LTD', 'weight': 0.0421},
    'TCS': {'name': 'TATA CONSULTANCY SERVICES LTD', 'weight': 0.0512},
    'ICICIBANK': {'name': 'ICICI BANK LTD', 'weight': 0.0763},
    'SBIN': {'name': 'STATE BANK OF INDIA', 'weight': 0.0398},
    'BAJFINANCE': {'name': 'BAJAJ FINANCE LTD', 'weight': 0.0287},
    'INFY': {'name': 'INFOSYS LTD', 'weight': 0.0589},
    'ITC': {'name': 'ITC LTD', 'weight': 0.0271},
    'LT': {'name': 'LARSEN & TOUBRO LTD', 'weight': 0.0263}
}

# Stock-specific headers
STOCK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest"
}

def create_stock_session_with_retry():
    """Create session with retry strategy for stocks"""
    session = requests.Session()
    retry_strategy = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False
    return session

def initialize_stock_session(symbol):
    """Initialize session for stock data fetching"""
    session = create_stock_session_with_retry()
    try:
        session.get("https://www.nseindia.com", headers=STOCK_HEADERS, timeout=10)
        session.get(f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}", headers=STOCK_HEADERS, timeout=10)
        return session
    except Exception as e:
        print(f"Stock session initialization for {symbol} failed: {e}")
        raise

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
    """Parse stock option chain data with Greeks"""
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
                # Parse CE data with Greeks
                ce_data = record.get('CE', {})
                # Parse PE data with Greeks
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'symbol': symbol,
                    'stock_value': round(current_stock_value, 2),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data with Greeks
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    'ce_delta': parse_float_value(ce_data.get('delta', 0)),
                    'ce_gamma': parse_float_value(ce_data.get('gamma', 0)),
                    'ce_theta': parse_float_value(ce_data.get('theta', 0)),
                    'ce_vega': parse_float_value(ce_data.get('vega', 0)),
                    # PE Data with Greeks
                    'pe_change_oi': parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume': parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp': parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi': parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv': parse_float_value(pe_data.get('impliedVolatility', 0)),
                    'pe_delta': parse_float_value(pe_data.get('delta', 0)),
                    'pe_gamma': parse_float_value(pe_data.get('gamma', 0)),
                    'pe_theta': parse_float_value(pe_data.get('theta', 0)),
                    'pe_vega': parse_float_value(pe_data.get('vega', 0)),
                }
                filtered_records.append(oi_data)
        
        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain for {symbol}: {str(e)}")

def calculate_stock_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for stock"""
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
    """Fetch BANKNIFTY option chain data"""
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
                # Parse CE data with Greeks
                ce_data = record.get('CE', {})
                # Parse PE data with Greeks
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'symbol': 'BANKNIFTY',
                    'underlying_value': round(current_banknifty, 2),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data with Greeks
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    'ce_delta': parse_float_value(ce_data.get('delta', 0)),
                    'ce_gamma': parse_float_value(ce_data.get('gamma', 0)),
                    'ce_theta': parse_float_value(ce_data.get('theta', 0)),
                    'ce_vega': parse_float_value(ce_data.get('vega', 0)),
                    # PE Data with Greeks
                    'pe_change_oi': parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume': parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp': parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi': parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv': parse_float_value(pe_data.get('impliedVolatility', 0)),
                    'pe_delta': parse_float_value(pe_data.get('delta', 0)),
                    'pe_gamma': parse_float_value(pe_data.get('gamma', 0)),
                    'pe_theta': parse_float_value(pe_data.get('theta', 0)),
                    'pe_vega': parse_float_value(pe_data.get('vega', 0)),
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

def display_banknifty_data(banknifty_data):
    """Display BANKNIFTY OI data with Greeks"""
    if not banknifty_data:
        return
    
    current_value = banknifty_data['current_value']
    
    print(f"\n{'='*170}")
    print(f"OI Data for BANKNIFTY - Current: {current_value}")
    print(f"{'='*170}")
    print(f"{'CALL OPTION':<70}|   STRIKE   |{'PUT OPTION':<72}|  {'CHG OI DIFF':<18}")
    print(
        f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  {'Delta'.rjust(7)}  {'Gamma'.rjust(7)}  |  "
        f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  "
        f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  {'Delta'.rjust(7)}  {'Gamma'.rjust(7)}  |  {'CE-PE'.rjust(16)}"
    )
    print("-" * 170)
    
    for data in banknifty_data['data']:
        strike_price = data['strike_price']
        
        # Format all values
        ce_oi_formatted = format_oi_value(data['ce_change_oi'])
        ce_volume_formatted = format_oi_value(data['ce_volume'])
        ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
        ce_oi_total_formatted = format_oi_value(data['ce_oi'])
        ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
        ce_delta_formatted = format_greek_value(data['ce_delta'])
        ce_gamma_formatted = format_greek_value(data['ce_gamma'], 4)
        
        pe_oi_formatted = format_oi_value(data['pe_change_oi'])
        pe_volume_formatted = format_oi_value(data['pe_volume'])
        pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
        pe_oi_total_formatted = format_oi_value(data['pe_oi'])
        pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
        pe_delta_formatted = format_greek_value(data['pe_delta'])
        pe_gamma_formatted = format_greek_value(data['pe_gamma'], 4)
        
        chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
        chg_oi_diff_formatted = format_oi_value(chg_oi_diff)
        
        # Format the row
        formatted_row = (
            f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
            f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  {ce_delta_formatted.rjust(7)}  {ce_gamma_formatted.rjust(7)}  |  "
            f"{str(strike_price).center(9)}  |  "
            f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
            f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  {pe_delta_formatted.rjust(7)}  {pe_gamma_formatted.rjust(7)}  |  "
            f"{chg_oi_diff_formatted.rjust(16)}"
        )
        
        print(formatted_row)
    
    print("=" * 170)
    print(f"BANKNIFTY PCR: OI PCR = {banknifty_data['oi_pcr']:.2f}, Volume PCR = {banknifty_data['volume_pcr']:.2f}")

def display_stock_data(stock_data):
    """Display stock OI data with Greeks in required format"""
    symbol = stock_data[0]['symbol']
    stock_info = TOP_NIFTY_STOCKS[symbol]
    current_price = stock_data[0]['stock_value']
    
    print(f"\n{'='*170}")
    print(f"OI Data for {stock_info['name']} ({symbol}) - Current Price: {current_price}")
    print(f"{'='*170}")
    print(f"{'CALL OPTION':<70}|   STRIKE   |{'PUT OPTION':<72}|  {'CHG OI DIFF':<18}")
    print(
        f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  {'Delta'.rjust(7)}  {'Gamma'.rjust(7)}  |  "
        f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  "
        f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  {'Delta'.rjust(7)}  {'Gamma'.rjust(7)}  |  {'CE-PE'.rjust(16)}"
    )
    print("-" * 170)
    
    for data in stock_data:
        strike_price = data['strike_price']
        
        # Format all values
        ce_oi_formatted = format_oi_value(data['ce_change_oi'])
        ce_volume_formatted = format_oi_value(data['ce_volume'])
        ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
        ce_oi_total_formatted = format_oi_value(data['ce_oi'])
        ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
        ce_delta_formatted = format_greek_value(data['ce_delta'])
        ce_gamma_formatted = format_greek_value(data['ce_gamma'], 4)
        
        pe_oi_formatted = format_oi_value(data['pe_change_oi'])
        pe_volume_formatted = format_oi_value(data['pe_volume'])
        pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
        pe_oi_total_formatted = format_oi_value(data['pe_oi'])
        pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
        pe_delta_formatted = format_greek_value(data['pe_delta'])
        pe_gamma_formatted = format_greek_value(data['pe_gamma'], 4)
        
        chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
        chg_oi_diff_formatted = format_oi_value(chg_oi_diff)
        
        # Format the row
        formatted_row = (
            f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
            f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  {ce_delta_formatted.rjust(7)}  {ce_gamma_formatted.rjust(7)}  |  "
            f"{str(strike_price).center(9)}  |  "
            f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
            f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  {pe_delta_formatted.rjust(7)}  {pe_gamma_formatted.rjust(7)}  |  "
            f"{chg_oi_diff_formatted.rjust(16)}"
        )
        
        print(formatted_row)
    
    print("=" * 170)

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
        
        # Save OI data for all strike prices with Greek values
        for data in oi_data:
            # Calculate chg_oi_diff (CE - PE) - CORRECT CALCULATION
            chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
            
            cursor.execute('''
                INSERT INTO oi_data (
                    fetch_cycle, fetch_timestamp, nifty_value, expiry_date, strike_price,
                    ce_change_oi, ce_volume, ce_ltp, ce_oi, ce_iv, ce_delta, ce_gamma, ce_theta, ce_vega,
                    pe_change_oi, pe_volume, pe_ltp, pe_oi, pe_iv, pe_delta, pe_gamma, pe_theta, pe_vega,
                    chg_oi_diff, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fetch_cycle, fetch_timestamp, data['nifty_value'], data['expiry_date'], data['strike_price'],
                data['ce_change_oi'], data['ce_volume'], data['ce_ltp'], data['ce_oi'], 
                data['ce_iv'], data['ce_delta'], data['ce_gamma'], data['ce_theta'], data['ce_vega'],
                data['pe_change_oi'], data['pe_volume'], data['pe_ltp'], data['pe_oi'],
                data['pe_iv'], data['pe_delta'], data['pe_gamma'], data['pe_theta'], data['pe_vega'],
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

def display_latest_data():
    """Display the latest fetch cycle data from database with Greek values"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Get current cycle and total fetches
        cursor.execute("SELECT value FROM app_state WHERE key = 'current_cycle'")
        current_cycle = cursor.fetchone()[0] - 1  # Show the cycle we just saved
        if current_cycle < 1:
            current_cycle = MAX_FETCH_CYCLES
        
        cursor.execute("SELECT value FROM app_state WHERE key = 'total_fetches'")
        total_fetches = cursor.fetchone()[0]
        
        # Get data for current cycle
        cursor.execute('''
            SELECT * FROM oi_data 
            WHERE fetch_cycle = ? 
            ORDER BY strike_price
        ''', (current_cycle,))
        
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nOI Data with Greeks:")
            print("=" * 170)
            # Updated header with optimized spacing
            print(f"{'CALL OPTION':<70}|   STRIKE   |{'PUT OPTION':<72}|  {'CHG OI DIFF':<18}{'CHG OI DIFF HISTORY':>25}")
            print(
                f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  {'Delta'.rjust(7)}  {'Gamma'.rjust(7)}  |  "
                f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  "
                f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  {'Delta'.rjust(7)}  {'Gamma'.rjust(7)}  |  {'CE-PE'.rjust(16)}  {'(latest first)'.ljust(25)}"
            )
            print("-" * 170)
            
            for row in rows:
                strike_price = row[5]
                # CE Data
                ce_oi = row[6]
                ce_volume = row[7]
                ce_ltp = row[8]
                ce_oi_total = row[9]
                ce_iv = row[10]
                ce_delta = row[11]
                ce_gamma = row[12]
                # PE Data
                pe_oi = row[15]
                pe_volume = row[16]
                pe_ltp = row[17]
                pe_oi_total = row[18]
                pe_iv = row[19]
                pe_delta = row[20]
                pe_gamma = row[21]
                chg_oi_diff = row[24]

                # Format all values
                ce_oi_formatted = format_oi_value(ce_oi)
                ce_volume_formatted = format_oi_value(ce_volume)
                ce_ltp_formatted = f"{ce_ltp:.1f}" if ce_ltp else "0"
                ce_oi_total_formatted = format_oi_value(ce_oi_total)
                ce_iv_formatted = format_greek_value(ce_iv, 1)
                ce_delta_formatted = format_greek_value(ce_delta)
                ce_gamma_formatted = format_greek_value(ce_gamma, 4)
                
                pe_oi_formatted = format_oi_value(pe_oi)
                pe_volume_formatted = format_oi_value(pe_volume)
                pe_ltp_formatted = f"{pe_ltp:.1f}" if pe_ltp else "0"
                pe_oi_total_formatted = format_oi_value(pe_oi_total)
                pe_iv_formatted = format_greek_value(pe_iv, 1)
                pe_delta_formatted = format_greek_value(pe_delta)
                pe_gamma_formatted = format_greek_value(pe_gamma, 4)
                
                chg_oi_diff_formatted = format_oi_value(chg_oi_diff)
                
                # Get CHG OI DIFF history
                chg_oi_history = get_chg_oi_diff_history(strike_price, current_cycle)
                history_str = ", ".join(chg_oi_history) if chg_oi_history else "No history"
                
                # Format the row using the optimized padding
                formatted_row = (
                    f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                    f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  {ce_delta_formatted.rjust(7)}  {ce_gamma_formatted.rjust(7)}  |  "
                    f"{str(strike_price).center(9)}  |  "
                    f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                    f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  {pe_delta_formatted.rjust(7)}  {pe_gamma_formatted.rjust(7)}  |  "
                    f"{chg_oi_diff_formatted.rjust(16)}  {history_str.ljust(25)}"
                )
                
                print(formatted_row)
            
            print("=" * 170)
            print("Note: IV in %, Delta/Gamma rounded to 3-4 decimals")
        
    except Exception as e:
        print(f"Error displaying data: {e}")
    finally:
        conn.close()

def fetch_all_stock_data():
    """Fetch data for all top 10 Nifty stocks"""
    stock_data = {}
    
    print(f"\n{'='*80}")
    print("FETCHING TOP 10 NIFTY STOCKS DATA...")
    print(f"{'='*80}")
    
    for symbol in TOP_NIFTY_STOCKS.keys():
        try:
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
            
            # Display stock data
            display_stock_data(oi_data)
            
            # Display PCR values only
            print(f"PCR for {symbol}: OI PCR = {oi_pcr:.2f}, Volume PCR = {volume_pcr:.2f}")
            print(f"{'-'*80}")
            
            # Small delay to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    return stock_data

def data_collection_loop():
    global running
    session = None
    first_run = True
    
    # Initialize database
    initialize_database()
    
    try:
        while running:
            try:
                if session is None:
                    if not first_run:
                        print("Reinitializing Nifty session...")
                    session = initialize_session()
                
                # Fetch Nifty data
                print(f"Fetching {SYMBOL} option chain...")
                data = fetch_option_chain(session)
                oi_data = parse_option_chain(data)
                
                # Save to database and get PCR values
                oi_pcr, volume_pcr, fetch_cycle, total_fetches = save_oi_data_to_db(oi_data)
                
                # Display Nifty data
                display_latest_data()
                
                # Display Nifty PCR values only
                print(f"PCR ANALYSIS (ATM ±2 strikes):")
                print(f" OI PCR: {oi_pcr:.2f}")
                print(f" Volume PCR: {volume_pcr:.2f}")
                
                # Fetch BANKNIFTY data
                banknifty_data = fetch_banknifty_data()
                if banknifty_data:
                    display_banknifty_data(banknifty_data)
                
                # Fetch all stock data
                stock_data = fetch_all_stock_data()
                
                # Get AI analysis with combined data
                print("\n" + "="*80)
                print("REQUESTING AI ANALYSIS...")
                print("="*80)
                
                # Get AI analysis - only call once
                try:
                    ai_analysis = ai_analyzer.get_ai_analysis(
                        oi_data=oi_data,
                        current_cycle=fetch_cycle,
                        total_fetches=total_fetches,
                        oi_pcr=oi_pcr,
                        volume_pcr=volume_pcr,
                        current_nifty=oi_data[0]['nifty_value'],
                        stock_data=stock_data,
                        banknifty_data=banknifty_data
                    )
                    print(ai_analysis)
                except Exception as ai_error:
                    print(f"⚠️ AI analysis failed: {ai_error}")
                    print("Continuing with next cycle...")
                
                print("="*80)
                
                # Display brief info
                print(f"Nifty: {oi_data[0]['nifty_value']}, Expiry: {oi_data[0]['expiry_date']}")
                if banknifty_data:
                    print(f"BankNifty: {banknifty_data['current_value']}")
                if first_run:
                    print(f"Database: {DB_FILE}")
                    first_run = False
                    print("Press Ctrl+C to stop")
                
                # FIXED COUNTDOWN - Minimal output version
                print(f"✅ Cycle {fetch_cycle} completed. Waiting {FETCH_INTERVAL}s...", flush=True)
                
                # Silent countdown - no periodic output
                for i in range(FETCH_INTERVAL):
                    if not running:
                        break
                    time.sleep(1)
                
                if running:
                    print("🔄 Starting next cycle...", flush=True)
                        
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received in main loop.")
                raise
            except Exception as e:
                print(f"Error: {e}")
                session = None  # Reset session on error
                # Check if we should continue after error
                if running:
                    print("Waiting 10 seconds before retry...")
                    for i in range(10):
                        if not running:
                            break
                        time.sleep(1)
                    
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down gracefully...")
    finally:
        running = False
        if session:
            print("Closing session...")
            session.close()
        print("Data collection stopped completely")

def main():
    print(f"Starting {SYMBOL} OI Data Logger with Greek Values & AI Analysis")
    print(f"Including BANKNIFTY and Top 10 NIFTY Stocks with Weightage Analysis")
    print(f"Data will be saved to {DB_FILE} every {FETCH_INTERVAL} seconds")
    print(f"Maintaining exactly {MAX_FETCH_CYCLES} fetch cycles (1-10 in circular manner)")
    print("DeepSeek AI analysis will be performed for each cycle with combined Nifty + BankNifty + Stocks data")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        data_collection_loop()
    except KeyboardInterrupt:
        print("\nMain: Keyboard interrupt caught")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Application shutdown complete")
        # Force exit to ensure script terminates
        os._exit(0)

if __name__ == "__main__":
    main()