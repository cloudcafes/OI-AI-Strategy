# nifty_data_fetcher.py
import requests
import datetime
import time
from nifty_core_config import (
    SYMBOL, MAX_RETRIES, INITIAL_RETRY_DELAY, HEADERS, STOCK_HEADERS,
    parse_numeric_value, parse_float_value, format_greek_value,
    TOP_NIFTY_STOCKS, initialize_session, initialize_stock_session
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
        
        # Process ALL strikes for the nearest expiry (no filtering)
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        
        filtered_records = []
        
        for record in nearest_expiry_records:
            # Parse CE data without Greeks
            ce_data = record.get('CE', {})
            # Parse PE data without Greeks
            pe_data = record.get('PE', {})
            
            oi_data = {
                'nifty_value': round(current_nifty),
                'expiry_date': nearest_expiry,
                'strike_price': record['strikePrice'],
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
    """Calculate OI PCR and Volume PCR for ALL strikes with zero value safeguards"""
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_volume = 0
    total_pe_volume = 0
    
    for data in oi_data:
        total_ce_oi += data['ce_oi']
        total_pe_oi += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']
    
    # Calculate PCR values with zero safeguards
    try:
        oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
    except ZeroDivisionError:
        oi_pcr = 1.0
    
    try:
        volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 1.0
    except ZeroDivisionError:
        volume_pcr = 1.0
    
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
    """Parse stock option chain data without Greeks - ALL strikes"""
    try:
        current_stock_value = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Process ALL strikes for the nearest expiry (no filtering)
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        
        filtered_records = []
        
        for record in nearest_expiry_records:
            # Parse CE data without Greeks
            ce_data = record.get('CE', {})
            # Parse PE data without Greeks
            pe_data = record.get('PE', {})
            
            oi_data = {
                'symbol': symbol,
                'stock_value': round(current_stock_value, 2),
                'expiry_date': nearest_expiry,
                'strike_price': record['strikePrice'],
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
    """Calculate OI PCR and Volume PCR for stock with zero value safeguards"""
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_volume = 0
    total_pe_volume = 0
    
    for data in oi_data:
        total_ce_oi += data['ce_oi']
        total_pe_oi += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']
    
    # Calculate PCR values with zero safeguards
    try:
        oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
    except ZeroDivisionError:
        oi_pcr = 1.0
    
    try:
        volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 1.0
    except ZeroDivisionError:
        volume_pcr = 1.0
    
    return oi_pcr, volume_pcr

def fetch_banknifty_data():
    """Fetch BANKNIFTY option chain data without Greeks - ALL strikes"""
    try:
        print(f"Fetching BANKNIFTY option chain...")
        
        # Initialize session for BANKNIFTY
        session = initialize_session()
        
        # Fetch BANKNIFTY option chain
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY"
        response = session.get(url, headers=STOCK_HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Parse BANKNIFTY data - ALL strikes
        current_banknifty = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Process ALL strikes for the nearest expiry
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        
        banknifty_data = []
        
        for record in nearest_expiry_records:
            # Parse CE data without Greeks
            ce_data = record.get('CE', {})
            # Parse PE data without Greeks
            pe_data = record.get('PE', {})
            
            oi_data = {
                'symbol': 'BANKNIFTY',
                'underlying_value': round(current_banknifty, 2),
                'expiry_date': nearest_expiry,
                'strike_price': record['strikePrice'],
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
        
        # Calculate BANKNIFTY PCR values with zero safeguards
        oi_pcr, volume_pcr = calculate_pcr_values(banknifty_data)
        
        return {
            'data': banknifty_data,
            'oi_pcr': oi_pcr,
            'volume_pcr': volume_pcr,
            'current_value': current_banknifty,
            'expiry_date': nearest_expiry
        }
        
    except Exception as e:
        print(f"Error fetching BANKNIFTY data: {e}")
        return None

def fetch_all_stock_data():
    """Fetch data for all top 10 Nifty stocks - ALL strikes"""
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
            
            # Parse the data - ALL strikes
            oi_data = parse_stock_option_chain(data, symbol)
            
            # Calculate PCR values with zero safeguards
            oi_pcr, volume_pcr = calculate_stock_pcr_values(oi_data)
            
            # Store PCR values with data
            stock_data[symbol] = {
                'data': oi_data,
                'oi_pcr': oi_pcr,
                'volume_pcr': volume_pcr,
                'weight': TOP_NIFTY_STOCKS[symbol]['weight'],
                'current_price': oi_data[0]['stock_value'] if oi_data else 0
            }
            
            # Small delay to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue
    
    return stock_data

def fetch_market_data_for_multi_model():
    """
    Fetch complete market data for multi-model analysis
    Returns all necessary data in a single dictionary
    """
    session = None
    try:
        print("🔄 Fetching market data for multi-model analysis...")
        
        # Initialize session
        session = initialize_session()
        
        # Fetch Nifty data
        nifty_data = fetch_option_chain(session)
        oi_data = parse_option_chain(nifty_data)
        oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
        
        # Fetch BankNifty data
        banknifty_data = fetch_banknifty_data()
        
        # Fetch stock data
        stock_data = fetch_all_stock_data()
        
        # Prepare complete data package
        market_data = {
            'oi_data': oi_data,
            'oi_pcr': oi_pcr,
            'volume_pcr': volume_pcr,
            'current_nifty': oi_data[0]['nifty_value'] if oi_data else 0,
            'expiry_date': oi_data[0]['expiry_date'] if oi_data else "N/A",
            'banknifty_data': banknifty_data,
            'stock_data': stock_data,
            'fetch_time': datetime.datetime.now().isoformat(),
            'status': 'success'
        }
        
        print("✅ Market data fetched successfully for multi-model analysis")
        return market_data
        
    except Exception as e:
        print(f"❌ Error fetching market data for multi-model: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'fetch_time': datetime.datetime.now().isoformat()
        }
    finally:
        if session:
            session.close()

def test_data_fetcher():
    """Test function for data fetcher"""
    print("=== Testing Data Fetcher ===")
    
    try:
        # Test Nifty data fetching
        session = initialize_session()
        data = fetch_option_chain(session)
        oi_data = parse_option_chain(data)
        oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
        
        print(f"✅ Nifty data fetched: {len(oi_data)} strikes")
        print(f"✅ PCR values: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}")
        
        # Test BankNifty data
        banknifty_data = fetch_banknifty_data()
        if banknifty_data:
            print(f"✅ BankNifty data fetched: {len(banknifty_data['data'])} strikes")
        
        # Test stock data (first stock only for testing)
        test_symbol = list(TOP_NIFTY_STOCKS.keys())[0]
        stock_session = initialize_stock_session(test_symbol)
        stock_data = fetch_stock_option_chain(stock_session, test_symbol)
        parsed_stock_data = parse_stock_option_chain(stock_data, test_symbol)
        
        print(f"✅ Stock data fetched for {test_symbol}: {len(parsed_stock_data)} strikes")
        
        # Test multi-model data fetch
        multi_model_data = fetch_market_data_for_multi_model()
        if multi_model_data['status'] == 'success':
            print("✅ Multi-model data fetch successful")
        else:
            print(f"❌ Multi-model data fetch failed: {multi_model_data.get('error')}")
        
        print("✅ All data fetcher tests completed successfully")
        
    except Exception as e:
        print(f"❌ Data fetcher test failed: {e}")

if __name__ == "__main__":
    test_data_fetcher()