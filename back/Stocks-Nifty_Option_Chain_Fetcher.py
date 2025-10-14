import requests
import datetime
import time
import sqlite3
import os
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5
DB_FILE = "stock_oi_data.db"

# NIFTY 50 stocks with their symbols and approximate weightages
NIFTY_50_STOCKS = {
    'RELIANCE': {'name': 'RELIANCE INDUSTRIES LTD', 'weight': 0.0924},
    'HDFCBANK': {'name': 'HDFC BANK LTD', 'weight': 0.0876},
    'BHARTIARTL': {'name': 'BHARTI AIRTEL LTD', 'weight': 0.0421},
    'TCS': {'name': 'TATA CONSULTANCY SERVICES LTD', 'weight': 0.0512},
    'ICICIBANK': {'name': 'ICICI BANK LTD', 'weight': 0.0763},
    'SBIN': {'name': 'STATE BANK OF INDIA', 'weight': 0.0398},
    'BAJFINANCE': {'name': 'BAJAJ FINANCE LTD', 'weight': 0.0287},
    'INFY': {'name': 'INFOSYS LTD', 'weight': 0.0589},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest"
}

def create_session_with_retry():
    session = requests.Session()
    retry_strategy = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False
    return session

def initialize_session_for_stock(symbol):
    session = create_session_with_retry()
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        session.get(f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}", headers=HEADERS, timeout=10)
        return session
    except Exception as e:
        print(f"Session initialization for {symbol} failed: {e}")
        raise

def fetch_stock_option_chain(session, symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
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

def initialize_database():
    """Initialize SQLite database for stock OI data"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create table for OI data with symbol column
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            fetch_timestamp TEXT,
            stock_value REAL,
            expiry_date TEXT,
            strike_price REAL,
            ce_change_oi INTEGER,
            ce_volume INTEGER,
            ce_ltp REAL,
            ce_oi INTEGER,
            pe_change_oi INTEGER,
            pe_volume INTEGER,
            pe_ltp REAL,
            pe_oi INTEGER,
            chg_oi_diff INTEGER,
            created_at TEXT
        )
    ''')
    
    # Clean up any existing data to start fresh
    cursor.execute('DELETE FROM oi_data')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_FILE}")

def parse_numeric_value(value):
    """Parse numeric values that may contain commas and convert to integer"""
    if value is None:
        return 0
    
    if isinstance(value, (int, float)):
        return int(value)
    
    if isinstance(value, str):
        # Remove commas and any whitespace, then convert to float and then to int
        cleaned_value = value.replace(',', '').strip()
        if cleaned_value == '' or cleaned_value == '-':
            return 0
        try:
            # Convert to float first to handle decimal numbers, then to int
            return int(float(cleaned_value))
        except (ValueError, TypeError):
            return 0
    
    return 0

def format_oi_value(value):
    """Format OI value to k (thousands) or L (lacs) for better readability while preserving sign"""
    if value == 0:
        return "0"
    
    abs_value = abs(value)
    is_negative = value < 0
    
    if abs_value >= 100000:
        # Convert to lacs
        formatted = abs_value / 100000
        if formatted == int(formatted):
            formatted_str = f"{int(formatted)}L"
        else:
            formatted_str = f"{formatted:.1f}L"
    elif abs_value >= 1000:
        # Convert to thousands
        formatted = abs_value / 1000
        if formatted == int(formatted):
            formatted_str = f"{int(formatted)}k"
        else:
            formatted_str = f"{formatted:.1f}k"
    else:
        formatted_str = str(abs_value)
    
    # Add negative sign back if original value was negative
    return f"-{formatted_str}" if is_negative else formatted_str

def parse_stock_option_chain(data, symbol):
    try:
        current_stock_value = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Filter for nearest expiry only
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        strike_prices = sorted(list(set(record['strikePrice'] for record in nearest_expiry_records)))
        
        # Find closest strike and select 2 above + 2 below
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_stock_value))
        closest_index = strike_prices.index(closest_strike)
        selected_strikes = strike_prices[max(0, closest_index - 3):min(len(strike_prices), closest_index + 4)]
        
        filtered_records = []
        
        for strike in selected_strikes:
            record = next((r for r in nearest_expiry_records if r['strikePrice'] == strike), None)
            if record:
                oi_data = {
                    'symbol': symbol,
                    'stock_value': round(current_stock_value, 2),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    'ce_change_oi': parse_numeric_value(record['CE'].get('changeinOpenInterest', 0)) if 'CE' in record else 0,
                    'ce_volume': parse_numeric_value(record['CE'].get('totalTradedVolume', 0)) if 'CE' in record else 0,
                    'ce_ltp': round(record['CE'].get('lastPrice', 0), 2) if 'CE' in record else 0,
                    'ce_oi': parse_numeric_value(record['CE'].get('openInterest', 0)) if 'CE' in record else 0,
                    'pe_change_oi': parse_numeric_value(record['PE'].get('changeinOpenInterest', 0)) if 'PE' in record else 0,
                    'pe_volume': parse_numeric_value(record['PE'].get('totalTradedVolume', 0)) if 'PE' in record else 0,
                    'pe_ltp': round(record['PE'].get('lastPrice', 0), 2) if 'PE' in record else 0,
                    'pe_oi': parse_numeric_value(record['PE'].get('openInterest', 0)) if 'PE' in record else 0
                }
                filtered_records.append(oi_data)
        
        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain for {symbol}: {str(e)}")

def analyze_stock_trend(oi_data):
    """Analyze stock trend based on OI data - CORRECTED LOGIC FOR STOCKS"""
    if not oi_data:
        return {"score": 0, "direction": "NEUTRAL", "analysis": "No data available"}
    
    # Get current stock value
    current_stock = oi_data[0]['stock_value']
    
    # Find ATM strike (closest to current stock price)
    atm_strike = min(oi_data, key=lambda x: abs(x['strike_price'] - current_stock))['strike_price']
    
    # Analyze each strike using CORRECT STOCK OPTION LOGIC
    bullish_signals = 0
    bearish_signals = 0
    neutral_signals = 0
    
    for data in oi_data:
        ce_oi = data['ce_change_oi']
        pe_oi = data['pe_change_oi']
        
        # CORRECT STOCK OPTION LOGIC:
        # - Higher CE OI change = Call buying = BULLISH for stocks
        # - Higher PE OI change = Put buying = BEARISH for stocks
        
        if ce_oi > pe_oi:
            bullish_signals += 1
        elif pe_oi > ce_oi:
            bearish_signals += 1
        else:
            neutral_signals += 1
    
    total_signals = bullish_signals + bearish_signals + neutral_signals
    
    if total_signals == 0:
        return {"score": 0, "direction": "NEUTRAL", "analysis": "No signals detected"}
    
    # Calculate trend score (-1 to +1) - CORRECT for stocks
    # Positive score = bullish, Negative score = bearish
    trend_score = (bullish_signals - bearish_signals) / total_signals
    
    # Determine direction with better thresholds
    if trend_score > 0.2:
        direction = "BULLISH"
    elif trend_score < -0.2:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"
    
    # Generate analysis text
    analysis = f"Bullish Signals: {bullish_signals}, Bearish Signals: {bearish_signals}, Neutral: {neutral_signals}\n"
    analysis += f"Trend Score: {trend_score:.3f}, Direction: {direction}"
    analysis += f"\nStock Logic: CE OI > PE OI = Bullish, PE OI > CE OI = Bearish"
    
    return {
        "score": trend_score,
        "direction": direction,
        "analysis": analysis,
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals,
        "neutral_signals": neutral_signals
    }

def save_stock_oi_data_to_db(oi_data):
    """Save stock OI data to SQLite database"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        fetch_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Save OI data for all strike prices
        for data in oi_data:
            # Calculate chg_oi_diff (CE - PE) - CORRECT for stocks
            chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
            
            cursor.execute('''
                INSERT INTO oi_data (
                    symbol, fetch_timestamp, stock_value, expiry_date, strike_price,
                    ce_change_oi, ce_volume, ce_ltp, ce_oi,
                    pe_change_oi, pe_volume, pe_ltp, pe_oi, chg_oi_diff, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['symbol'], fetch_timestamp, data['stock_value'], data['expiry_date'], data['strike_price'],
                data['ce_change_oi'], data['ce_volume'], data['ce_ltp'], data['ce_oi'],
                data['pe_change_oi'], data['pe_volume'], data['pe_ltp'], data['pe_oi'],
                chg_oi_diff, datetime.datetime.now().isoformat()
            ))
        
        conn.commit()
        print(f"OI data saved for {data['symbol']}")
        
        return True
        
    except Exception as e:
        print(f"Error saving to database: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def display_stock_data(symbol):
    """Display the stock OI data from database"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Get data for the symbol
        cursor.execute('''
            SELECT * FROM oi_data 
            WHERE symbol = ? 
            ORDER BY strike_price
        ''', (symbol,))
        
        rows = cursor.fetchall()
        
        if rows:
            stock_name = NIFTY_50_STOCKS[symbol]['name']
            current_price = rows[0][3]  # stock_value from first row
            
            print(f"\n{'='*120}")
            print(f"OI Data for {stock_name} ({symbol}) - Current Price: {current_price}")
            print(f"{'='*120}")
            print(f"{'CALL OPTION':^50} | {'STRIKE':^10} | {'PUT OPTION':^38} | {'CHG OI DIFF':>16}")
            print(f"{'Chg OI':>10} {'Volume':>10} {'LTP':>10} {'OI':>10} {' ':^6} | {'Price':^10} | {'Chg OI':>10} {'Volume':>10} {'LTP':>10} {'OI':>8} | {'CE-PE':>12}")
            print("-" * 120)
            
            for row in rows:
                strike_price = row[5]
                ce_oi = row[6]
                ce_volume = row[7]
                ce_ltp = row[8]
                ce_oi_total = row[9]
                pe_oi = row[10]
                pe_volume = row[11]
                pe_ltp = row[12]
                pe_oi_total = row[13]
                chg_oi_diff = row[14]
                
                # Format all values
                ce_oi_formatted = format_oi_value(ce_oi)
                ce_volume_formatted = format_oi_value(ce_volume)
                ce_ltp_formatted = f"{ce_ltp:.1f}" if ce_ltp else "0.0"
                ce_oi_total_formatted = format_oi_value(ce_oi_total)
                
                pe_oi_formatted = format_oi_value(pe_oi)
                pe_volume_formatted = format_oi_value(pe_volume)
                pe_ltp_formatted = f"{pe_ltp:.1f}" if pe_ltp else "0.0"
                pe_oi_total_formatted = format_oi_value(pe_oi_total)
                
                chg_oi_diff_formatted = format_oi_value(chg_oi_diff)
                
                # Format the row with exact padding
                ce_data = f"{ce_oi_formatted:>10} {ce_volume_formatted:>10} {ce_ltp_formatted:>10} {ce_oi_total_formatted:>10}"
                pe_data = f"{pe_oi_formatted:>10} {pe_volume_formatted:>10} {pe_ltp_formatted:>10} {pe_oi_total_formatted:>8}"
                
                print(f"{ce_data} {' ':^6} | {strike_price:>9} | {pe_data} | {chg_oi_diff_formatted:>12}")
            
            print("=" * 120)
        
    except Exception as e:
        print(f"Error displaying data for {symbol}: {e}")
    finally:
        conn.close()

def calculate_nifty_prediction(stock_trends):
    """Calculate collective NIFTY impact based on stock trends and weightages"""
    total_weighted_score = 0
    total_weight = 0
    
    contributors = []
    
    for symbol, trend_data in stock_trends.items():
        if symbol in NIFTY_50_STOCKS:
            weight = NIFTY_50_STOCKS[symbol]['weight']
            score = trend_data['score']
            
            weighted_score = score * weight
            total_weighted_score += weighted_score
            total_weight += weight
            
            contributors.append({
                'symbol': symbol,
                'name': NIFTY_50_STOCKS[symbol]['name'],
                'weight': weight,
                'score': score,
                'weighted_score': weighted_score,
                'direction': trend_data['direction']
            })
    
    # Sort contributors by absolute weighted score (largest impact first)
    contributors.sort(key=lambda x: abs(x['weighted_score']), reverse=True)
    
    # Determine NIFTY direction
    if total_weighted_score > 0.02:
        direction = "UPWARD (BULLISH)"
        confidence = "HIGH" if total_weighted_score > 0.1 else "MEDIUM"
    elif total_weighted_score < -0.02:
        direction = "DOWNWARD (BEARISH)"
        confidence = "HIGH" if total_weighted_score < -0.1 else "MEDIUM"
    else:
        direction = "SIDEWAYS (NEUTRAL)"
        confidence = "LOW"
    
    # Check heavyweight alignment
    heavyweights = ['RELIANCE', 'HDFCBANK', 'ICICIBANK', 'INFY', 'TCS']
    hw_alignment = 0
    hw_count = 0
    
    for hw in heavyweights:
        if hw in stock_trends:
            hw_alignment += stock_trends[hw]['score']
            hw_count += 1
    
    if hw_count > 0:
        hw_alignment /= hw_count
        # Adjust confidence based on heavyweight alignment
        if (total_weighted_score > 0 and hw_alignment > 0) or (total_weighted_score < 0 and hw_alignment < 0):
            confidence = "HIGH"  # Heavyweights align with overall trend
        elif abs(total_weighted_score) > 0.05:
            confidence = "MEDIUM"  # Moderate signal despite heavyweight contradiction
        else:
            confidence = "LOW"  # Weak signal with heavyweight contradiction
    
    return {
        'net_signal': total_weighted_score,
        'direction': direction,
        'confidence': confidence,
        'contributors': contributors[:10],  # Top 10 contributors
        'heavyweight_alignment': hw_alignment
    }

def main():
    print("Starting NIFTY 50 Stock Option Chain Analyzer")
    print(f"Data will be saved to {DB_FILE}")
    print("This may take a few minutes to fetch data for all 50 stocks...")
    
    # Initialize database
    initialize_database()
    
    stock_trends = {}
    successful_fetches = 0
    failed_fetches = 0
    
    # Fetch and analyze data for each stock
    for symbol in NIFTY_50_STOCKS.keys():
        try:
            print(f"\nFetching data for {symbol}...")
            
            # Initialize session for this stock
            session = initialize_session_for_stock(symbol)
            
            # Fetch option chain data
            data = fetch_stock_option_chain(session, symbol)
            
            # Parse the data
            oi_data = parse_stock_option_chain(data, symbol)
            
            # Save to database
            if save_stock_oi_data_to_db(oi_data):
                # Analyze trend with CORRECTED logic
                trend_analysis = analyze_stock_trend(oi_data)
                stock_trends[symbol] = trend_analysis
                
                # Display data
                display_stock_data(symbol)
                
                print(f"Trend Analysis: {trend_analysis['analysis']}")
                
                successful_fetches += 1
            else:
                failed_fetches += 1
            
            # Small delay to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            failed_fetches += 1
            continue
    
    # Calculate NIFTY prediction
    print(f"\n{'='*80}")
    print("NIFTY 50 COLLECTIVE IMPACT ANALYSIS")
    print(f"{'='*80}")
    print(f"Successful fetches: {successful_fetches}/50")
    print(f"Failed fetches: {failed_fetches}/50")
    
    if stock_trends:
        nifty_prediction = calculate_nifty_prediction(stock_trends)
        
        print(f"\nNIFTY PREDICTION:")
        print(f"Net Signal: {nifty_prediction['net_signal']:.4f}")
        print(f"Direction: {nifty_prediction['direction']}")
        print(f"Confidence: {nifty_prediction['confidence']}")
        
        print(f"\nTOP CONTRIBUTORS:")
        for i, contributor in enumerate(nifty_prediction['contributors'], 1):
            impact_type = "BULLISH" if contributor['weighted_score'] > 0 else "BEARISH"
            print(f"{i:2d}. {contributor['symbol']:12} ({contributor['direction']:8}) "
                  f"Score: {contributor['score']:6.3f} * {contributor['weight']:5.3f} = "
                  f"{contributor['weighted_score']:7.4f} ({impact_type})")
        
        # Additional insights
        print(f"\nKEY INSIGHTS:")
        bullish_stocks = [s for s, t in stock_trends.items() if t['direction'] == 'BULLISH']
        bearish_stocks = [s for s, t in stock_trends.items() if t['direction'] == 'BEARISH']
        neutral_stocks = [s for s, t in stock_trends.items() if t['direction'] == 'NEUTRAL']
        
        print(f"Bullish stocks: {len(bullish_stocks)}")
        print(f"Bearish stocks: {len(bearish_stocks)}")
        print(f"Neutral stocks: {len(neutral_stocks)}")
        
        if nifty_prediction['heavyweight_alignment'] > 0.1:
            print("Heavyweights (RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS) are generally BULLISH")
        elif nifty_prediction['heavyweight_alignment'] < -0.1:
            print("Heavyweights (RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS) are generally BEARISH")
        else:
            print("Heavyweights (RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS) are MIXED/NEUTRAL")
        
        # Final recommendation
        print(f"\nFINAL RECOMMENDATION:")
        if nifty_prediction['direction'].startswith("UPWARD"):
            print("Consider BULLISH strategies for NIFTY")
        elif nifty_prediction['direction'].startswith("DOWNWARD"):
            print("Consider BEARISH strategies for NIFTY")
        else:
            print("Consider NEUTRAL/RANGE-BOUND strategies for NIFTY")
    
    else:
        print("No data available for analysis")
    
    print(f"\nAnalysis complete. Data saved to {DB_FILE}")

if __name__ == "__main__":
    main()