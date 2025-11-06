# nifty_data_fetcher.py
import requests
import datetime
import time
from nifty_core_config import (
    SYMBOL, MAX_RETRIES, INITIAL_RETRY_DELAY, HEADERS, STOCK_HEADERS,
    parse_numeric_value, parse_float_value, format_greek_value,
    TOP_NIFTY_STOCKS, initialize_session, initialize_stock_session,
    should_enable_multi_expiry, get_expiry_type_constants, get_expiry_classification_params
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

def classify_expiry_dates(expiry_dates):
    """
    Classify expiry dates into current_week, next_week, monthly
    Returns dict with classified expiry dates
    """
    if not expiry_dates or len(expiry_dates) == 0:
        return {}
    
    constants = get_expiry_type_constants()
    params = get_expiry_classification_params()
    
    classified = {}
    
    try:
        # Current week is always the first expiry
        current_week = expiry_dates[0]
        classified[constants['CURRENT_WEEK']] = current_week
        
        # Parse dates for comparison
        current_date = datetime.datetime.strptime(current_week, "%d-%b-%Y")
        
        # Find next week and monthly expiries
        next_week_candidate = None
        monthly_candidate = None
        
        for expiry_date in expiry_dates[1:]:  # Skip current week
            expiry_datetime = datetime.datetime.strptime(expiry_date, "%d-%b-%Y")
            days_diff = (expiry_datetime - current_date).days
            
            # Check if this could be next week (5-9 days from current)
            if params['next_week_day_range'][0] <= days_diff <= params['next_week_day_range'][1]:
                if not next_week_candidate:
                    next_week_candidate = expiry_date
            
            # Check if this could be monthly (more than threshold days)
            if days_diff >= params['monthly_threshold_days']:
                if not monthly_candidate:
                    monthly_candidate = expiry_date
                # If we have multiple monthly candidates, take the first one (nearest monthly)
        
        # Assign classified expiries
        if next_week_candidate:
            classified[constants['NEXT_WEEK']] = next_week_candidate
        
        if monthly_candidate:
            classified[constants['MONTHLY']] = monthly_candidate
            
        # Handle dual classification (if next_week and monthly are same)
        if (next_week_candidate and monthly_candidate and 
            next_week_candidate == monthly_candidate):
            # Keep both classifications - same expiry appears in both categories
            print(f"📅 Dual classification: {monthly_candidate} is both next_week and monthly")
            
    except Exception as e:
        print(f"⚠️ Expiry classification failed: {e}")
        # Fallback: only current week
        if expiry_dates:
            classified[constants['CURRENT_WEEK']] = expiry_dates[0]
    
    return classified

def parse_option_chain(data):
    """
    Parse option chain data with multi-expiry support
    Returns structured data with current_week, next_week, monthly datasets
    """
    try:
        current_nifty = data['records']['underlyingValue']
        records = data['records']['data']
        expiry_dates = data['records']['expiryDates']
        
        # Classify expiry dates
        classified_expiries = {}
        if should_enable_multi_expiry():
            classified_expiries = classify_expiry_dates(expiry_dates)
        else:
            # Fallback to single expiry mode
            constants = get_expiry_type_constants()
            classified_expiries[constants['CURRENT_WEEK']] = expiry_dates[0]
        
        # Process data for each classified expiry
        expiry_data = {}
        constants = get_expiry_type_constants()
        
        for expiry_type, expiry_date in classified_expiries.items():
            # Filter records for this expiry
            expiry_records = [record for record in records if record['expiryDate'] == expiry_date]
            
            filtered_records = []
            for record in expiry_records:
                # Parse CE data without Greeks
                ce_data = record.get('CE', {})
                # Parse PE data without Greeks
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'nifty_value': round(current_nifty),
                    'expiry_date': expiry_date,
                    'expiry_type': expiry_type,
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
            
            expiry_data[expiry_type] = filtered_records
        
        # Print classification results
        print(f"📅 Expiry Classification: {len(classified_expiries)} types identified")
        for expiry_type, expiry_date in classified_expiries.items():
            record_count = len(expiry_data.get(expiry_type, []))
            print(f"   {expiry_type}: {expiry_date} ({record_count} strikes)")
        
        return expiry_data
        
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

def calculate_pcr_for_expiry_data(expiry_data):
    """
    Calculate PCR values for multi-expiry data structure
    Returns dict with PCR values for each expiry type
    """
    pcr_values = {}
    
    for expiry_type, oi_data in expiry_data.items():
        if oi_data:  # Only calculate if data exists
            oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
            pcr_values[expiry_type] = {
                'oi_pcr': oi_pcr,
                'volume_pcr': volume_pcr,
                'strike_count': len(oi_data)
            }
        else:
            pcr_values[expiry_type] = {
                'oi_pcr': 1.0,
                'volume_pcr': 1.0,
                'strike_count': 0
            }
    
    return pcr_values

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
    """Fetch BANKNIFTY option chain data without Greeks - ALL strikes (monthly only)"""
    try:
        print(f"Fetching BANKNIFTY option chain...")
        
        # Initialize session for BANKNIFTY
        session = initialize_session()
        
        # Fetch BANKNIFTY option chain
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=BANKNIFTY"
        response = session.get(url, headers=STOCK_HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Parse BANKNIFTY data - ALL strikes (monthly only)
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
                'expiry_type': 'monthly',  # BankNifty always monthly
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
        
        # Return in same structured format for consistency
        expiry_data = {
            'monthly': banknifty_data
        }
        
        pcr_values = {
            'monthly': {
                'oi_pcr': oi_pcr,
                'volume_pcr': volume_pcr,
                'strike_count': len(banknifty_data)
            }
        }
        
        return {
            'data': expiry_data,
            'pcr_values': pcr_values,
            'current_value': current_banknifty,
            'expiry_date': nearest_expiry
        }
        
    except Exception as e:
        print(f"Error fetching BANKNIFTY data: {e}")
        return None

def fetch_all_stock_data():
    """Fetch data for all top 10 Nifty stocks - ALL strikes (monthly only)"""
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
            
            # Store PCR values with data (monthly only for stocks)
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