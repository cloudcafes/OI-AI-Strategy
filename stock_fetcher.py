# stock-fetcher.py
# Fixed data fetching with proper session handling

import requests
import time
import urllib3
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import configuration
from stock_config import HEADERS, RATE_LIMIT_DELAY, MAX_RETRIES, REQUEST_TIMEOUT

def create_session_with_retry():
    """Create session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1,
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False
    return session

def initialize_session():
    """Initialize session for NSE API with proper cookie handling"""
    session = create_session_with_retry()
    try:
        # Get main page to set cookies
        main_response = session.get(
            "https://www.nseindia.com", 
            headers=HEADERS, 
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        main_response.raise_for_status()
        
        # Get market data page to further establish session
        market_response = session.get(
            "https://www.nseindia.com/market-data/live-market-indices",
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT
        )
        market_response.raise_for_status()
        
        print("✅ Session initialized with cookies")
        return session
    except Exception as e:
        print(f"❌ Session initialization failed: {e}")
        raise

def parse_numeric_value(value):
    """Parse numeric values that may contain commas and convert to integer"""
    if value is None:
        return 0
    
    if isinstance(value, (int, float)):
        return int(value)
    
    if isinstance(value, str):
        cleaned_value = value.replace(',', '').strip()
        if cleaned_value == '' or cleaned_value == '-':
            return 0
        try:
            return int(float(cleaned_value))
        except (ValueError, TypeError):
            return 0
    
    return 0

def parse_float_value(value):
    """Parse numeric values that may contain commas and convert to float"""
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        cleaned_value = value.replace(',', '').strip()
        if cleaned_value == '' or cleaned_value == '-':
            return 0.0
        try:
            return float(cleaned_value)
        except (ValueError, TypeError):
            return 0.0
    
    return 0.0

def fetch_stock_option_chain(session, symbol):
    """Fetch option chain data for individual stock with proper headers"""
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    
    # Add random delay to avoid rate limiting
    time.sleep(random.uniform(1, 2))
    
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 401:
                # Session expired, reinitialize
                print(f"🔄 Session expired for {symbol}, reinitializing...")
                global_session = initialize_session()
                response = global_session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            
            response.raise_for_status()
            
            # Check if response contains valid data
            data = response.json()
            if 'records' not in data:
                raise ValueError(f"No records in response for {symbol}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RATE_LIMIT_DELAY * (2 ** attempt)
                print(f"🔄 Retry {attempt + 1} for {symbol} after {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                raise Exception(f"Failed to fetch {symbol} after {MAX_RETRIES} attempts: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid data format for {symbol}: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error fetching {symbol}: {str(e)}")

def parse_stock_option_chain(data, symbol):
    """Parse stock option chain data - extract relevant fields only"""
    try:
        if not data or 'records' not in data:
            raise ValueError(f"No records found in data for {symbol}")
        
        current_stock_value = data['records']['underlyingValue']
        records = data['records']['data']
        
        if not records:
            raise ValueError(f"No option chain data available for {symbol}")
        
        # Get nearest expiry
        expiry_dates = data['records']['expiryDates']
        if not expiry_dates:
            raise ValueError(f"No expiry dates found for {symbol}")
        
        nearest_expiry = expiry_dates[0]
        
        # Filter for nearest expiry only
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        
        if not nearest_expiry_records:
            # If no records for nearest expiry, try any expiry
            nearest_expiry_records = records[:10]  # Limit to first 10 records
        
        # Get all strike prices and find ATM strikes
        strike_prices = sorted(list(set(record['strikePrice'] for record in nearest_expiry_records)))
        
        if not strike_prices:
            raise ValueError(f"No strike prices found for {symbol}")
        
        # Find closest strike to current price (ATM)
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_stock_value))
        closest_index = strike_prices.index(closest_strike)
        
        # Select ATM ±2 strikes (5 strikes total)
        start_index = max(0, closest_index - 2)
        end_index = min(len(strike_prices), closest_index + 3)
        selected_strikes = strike_prices[start_index:end_index]
        
        filtered_records = []
        
        for strike in selected_strikes:
            record = next((r for r in nearest_expiry_records if r['strikePrice'] == strike), None)
            if record:
                # Parse CE data
                ce_data = record.get('CE', {})
                # Parse PE data
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'symbol': symbol,
                    'stock_value': round(current_stock_value, 2),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    # PE Data
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

def get_stock_data(symbol, session=None):
    """Main function to get stock data - handles session management"""
    close_session = False
    if session is None:
        session = initialize_session()
        close_session = True
    
    try:
        # Fetch raw data
        raw_data = fetch_stock_option_chain(session, symbol)
        
        # Parse and filter data
        parsed_data = parse_stock_option_chain(raw_data, symbol)
        
        return parsed_data
        
    except Exception as e:
        print(f"❌ Error processing {symbol}: {e}")
        return None
    finally:
        if close_session and session:
            session.close()

def format_greek_value(value, decimal_places=3):
    """Format Greek values with specified decimal places"""
    if value is None or value == 0:
        return "0"
    
    try:
        return f"{float(value):.{decimal_places}f}"
    except (ValueError, TypeError):
        return "0"