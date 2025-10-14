import requests
import datetime
import time
import signal
import sys
import urllib3
import sqlite3
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
SYMBOL = "NIFTY"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5
FETCH_INTERVAL = 30
DB_FILE = "oi_data-temp.db"
MAX_FETCH_CYCLES = 10  # Keep exactly 10 fetch cycles (1 to 10)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/get-quotes/derivatives?symbol=NIFTY",
    "X-Requested-With": "XMLHttpRequest"
}

running = True

def signal_handler(sig, frame):
    global running
    print("\nReceived shutdown signal...")
    running = False

def create_session_with_retry():
    session = requests.Session()
    retry_strategy = Retry(total=3, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False
    return session

def initialize_session():
    session = create_session_with_retry()
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        session.get("https://www.nseindia.com/get-quotes/derivatives?symbol=NIFTY", headers=HEADERS, timeout=10)
        return session
    except Exception as e:
        print(f"Session initialization failed: {e}")
        raise

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

def fetch_nifty_futures(session):
    """Fetch Nifty futures data using multiple API approaches"""
    try:
        # Approach 1: Try the quote derivative API
        try:
            url = "https://www.nseindia.com/api/quote-derivative?symbol=NIFTY"
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Look for futures in the stocks array
            for stock in data.get('stocks', []):
                metadata = stock.get('metadata', {})
                if metadata.get('instrumentType') == 'FUTIDX':
                    trade_info = stock.get('marketDeptOrderBook', {}).get('tradeInfo', {})
                    spot_price = data.get('underlyingValue', 0)
                    futures_price = trade_info.get('lastPrice', 0)
                    
                    return {
                        'futures_price': futures_price,
                        'futures_oi': parse_numeric_value(metadata.get('openInterest', 0)),
                        'futures_change_oi': parse_numeric_value(metadata.get('changeinOpenInterest', 0)),
                        'futures_volume': parse_numeric_value(metadata.get('numberOfContractsTraded', 0)),
                        'expiry_date': metadata.get('expiryDate', ''),
                        'basis': futures_price - spot_price
                    }
        except:
            pass
        
        # Approach 2: Extract from option chain data
        try:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={SYMBOL}"
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            spot_price = data['records']['underlyingValue']
            
            # Look for futures data in records
            for record in data['records']['data']:
                if ('CE' not in record and 'PE' not in record and 
                    record.get('expiryDate') == data['records']['expiryDates'][0]):
                    
                    futures_price = record.get('lastPrice', spot_price)
                    
                    return {
                        'futures_price': futures_price,
                        'futures_oi': parse_numeric_value(record.get('openInterest', 0)),
                        'futures_change_oi': parse_numeric_value(record.get('changeinOpenInterest', 0)),
                        'futures_volume': parse_numeric_value(record.get('totalTradedVolume', 0)),
                        'expiry_date': record.get('expiryDate', ''),
                        'basis': futures_price - spot_price
                    }
        except:
            pass
        
        # Approach 3: Use the historical API to get current futures data
        try:
            import datetime
            today = datetime.datetime.now().strftime('%d-%m-%Y')
            url = f"https://www.nseindia.com/api/historical/fo/derivatives?symbol=NIFTY&from={today}&to={today}"
            response = session.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and len(data['data']) > 0:
                    futures_data = data['data'][0]
                    spot_price = data.get('underlyingValue', futures_data.get('LTP', 0))
                    
                    return {
                        'futures_price': futures_data.get('LTP', 0),
                        'futures_oi': parse_numeric_value(futures_data.get('OI', 0)),
                        'futures_change_oi': parse_numeric_value(futures_data.get('CHG_IN_OI', 0)),
                        'futures_volume': parse_numeric_value(futures_data.get('VOLUME', 0)),
                        'expiry_date': futures_data.get('EXPIRY_DT', ''),
                        'basis': futures_data.get('LTP', 0) - spot_price
                    }
        except:
            pass
        
        print("All futures data fetch methods failed")
        return None
        
    except Exception as e:
        print(f"Error fetching futures data: {e}")
        return None

def initialize_database():
    """Initialize SQLite database with futures support"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create table for OI data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_cycle INTEGER,
            fetch_timestamp TEXT,
            nifty_value REAL,
            expiry_date TEXT,
            strike_price INTEGER,
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
    
    # Create table for futures data
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS futures_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_cycle INTEGER,
            fetch_timestamp TEXT,
            nifty_spot REAL,
            futures_price REAL,
            futures_oi INTEGER,
            futures_change_oi INTEGER,
            futures_volume INTEGER,
            basis REAL,
            expiry_date TEXT,
            trend_strength TEXT,
            created_at TEXT
        )
    ''')
    
    # Create simple cycle tracker
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_state (
            key TEXT PRIMARY KEY,
            value INTEGER
        )
    ''')
    
    # Initialize or reset current cycle to 1
    cursor.execute('''
        INSERT OR REPLACE INTO app_state (key, value)
        VALUES ('current_cycle', 1), ('total_fetches', 0)
    ''')
    
    # Clean up any existing data to start fresh
    cursor.execute('DELETE FROM oi_data')
    cursor.execute('DELETE FROM futures_data')
    
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_FILE}")
    print("Cycle counter reset to 1")

def get_next_cycle():
    """Get the next cycle number (1-10 in circular manner)"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Get current cycle
    cursor.execute("SELECT value FROM app_state WHERE key = 'current_cycle'")
    current_cycle = cursor.fetchone()[0]
    
    # Get total fetches
    cursor.execute("SELECT value FROM app_state WHERE key = 'total_fetches'")
    total_fetches = cursor.fetchone()[0]
    
    # Calculate next cycle
    next_cycle = current_cycle + 1
    if next_cycle > MAX_FETCH_CYCLES:
        next_cycle = 1
    
    # Update current cycle and total fetches
    cursor.execute("UPDATE app_state SET value = ? WHERE key = 'current_cycle'", (next_cycle,))
    cursor.execute("UPDATE app_state SET value = ? WHERE key = 'total_fetches'", (total_fetches + 1,))
    
    conn.commit()
    conn.close()
    
    return current_cycle, total_fetches + 1

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

def get_chg_oi_diff_history(strike_price, current_cycle):
    """Get the last 5 CHG OI DIFF values for a strike price"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Get last 5 CHG OI DIFF values for this strike (excluding current cycle)
        cursor.execute('''
            SELECT chg_oi_diff 
            FROM oi_data 
            WHERE strike_price = ? AND fetch_cycle < ?
            ORDER BY fetch_cycle DESC 
            LIMIT 5
        ''', (strike_price, current_cycle))
        
        history_records = cursor.fetchall()
        
        # Format the history values
        formatted_history = []
        for record in history_records:
            formatted_history.append(format_oi_value(record[0]))
        
        return formatted_history
        
    except Exception as e:
        return []
    finally:
        conn.close()

def calculate_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for ATM ±2 strikes"""
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

def analyze_futures_trend(futures_data, spot_price):
    """Analyze futures trend strength and direction"""
    if not futures_data:
        return "NO_DATA", "Unknown", "Futures data unavailable"
    
    futures_price = futures_data['futures_price']
    futures_oi = futures_data['futures_oi']
    futures_change_oi = futures_data['futures_change_oi']
    basis = futures_data['basis']
    
    # Analyze basis (Futures - Spot)
    if basis > 10:
        basis_sentiment = "BULLISH"
        basis_strength = "STRONG"
    elif basis > 0:
        basis_sentiment = "BULLISH" 
        basis_strength = "MODERATE"
    elif basis < -10:
        basis_sentiment = "BEARISH"
        basis_strength = "STRONG"
    elif basis < 0:
        basis_sentiment = "BEARISH"
        basis_strength = "MODERATE"
    else:
        basis_sentiment = "NEUTRAL"
        basis_strength = "WEAK"
    
    # Analyze OI-Price relationship
    if futures_change_oi > 0 and futures_price > spot_price:
        oi_signal = "LONG_BUILDUP"
        oi_strength = "VERY_STRONG"
        trend = "BULLISH"
    elif futures_change_oi > 0 and futures_price < spot_price:
        oi_signal = "SHORT_BUILDUP" 
        oi_strength = "VERY_STRONG"
        trend = "BEARISH"
    elif futures_change_oi < 0 and futures_price > spot_price:
        oi_signal = "SHORT_COVERING"
        oi_strength = "MODERATE"
        trend = "BULLISH"
    elif futures_change_oi < 0 and futures_price < spot_price:
        oi_signal = "LONG_UNWINDING"
        oi_strength = "MODERATE"
        trend = "BEARISH"
    else:
        oi_signal = "NEUTRAL"
        oi_strength = "WEAK"
        trend = "SIDEWAYS"
    
    # Combine signals
    if trend == basis_sentiment:
        final_trend = f"STRONG_{trend}"
        confidence = "HIGH"
    else:
        final_trend = f"MIXED_{trend}_BIAS"
        confidence = "MEDIUM"
    
    analysis = f"Futures: {final_trend} (Basis: {basis_sentiment}, OI: {oi_signal})"
    
    return trend, confidence, analysis

def get_pcr_signals(oi_pcr, volume_pcr):
    """Generate signals based on PCR values using the new conditions"""
    
    # Condition 1: Extreme Bullish Sentiment
    if oi_pcr > 1.3 and volume_pcr > 1.5:
        return (
            "EXTREME BULLISH - Strong upside breakout likely",
            "Very High (70%+)",
            "Strong put writing across ATM ±2 strikes shows institutional confidence",
            "Look for breakout above VWAP or prior high for 0.6-1.0% upside move"
        )
    
    # Condition 2: Strong Bullish Sentiment
    elif 1.1 <= oi_pcr <= 1.3 and 1.1 <= volume_pcr <= 1.5:
        return (
            "STRONG BULLISH - Upside continuation expected",
            "High (63-68%)",
            "Steady put buildup shows smart money expecting upside",
            "Confirm with price breaking day high or VWAP"
        )
    
    # Condition 3: Weak Volume / Cautious Bullish
    elif 1.1 <= oi_pcr <= 1.2 and volume_pcr < 1.0:
        return (
            "CAUTIOUS BULLISH - Upside stalling",
            "Medium (40-45%)",
            "OI shows bullish positioning but low volume suggests disinterest",
            "Wait for strong breakout confirmation before bullish trades"
        )
    
    # Condition 4: Neutral or No Edge
    elif 0.9 <= oi_pcr <= 1.1 and 0.9 <= volume_pcr <= 1.1:
        return (
            "NEUTRAL - Sideways range-bound",
            "Moderate (45%)",
            "Balanced positioning between calls and puts",
            "Better for scalping or range trades, avoid direction bets"
        )
    
    # Condition 5: Bearish Set-Up
    elif oi_pcr < 0.9 and volume_pcr < 0.8:
        return (
            "BEARISH - Downside expected",
            "High (65-68%)",
            "Rising call OI or dropping put volume confirms bearish sentiment",
            "Look for breaks below VWAP or sell-on-rise setups"
        )
    
    # Condition 6: High Probability Breakdown
    elif oi_pcr < 0.75 and volume_pcr < 0.7:
        return (
            "EXTREME BEARISH - Panic selling/breakdown",
            "Very High (70-75%)",
            "Very low put activity shows no confidence in market stability",
            "High probability of continued fall below VWAP"
        )
    
    # Condition 7: Bear Trap or Short-Covering Possibility
    elif oi_pcr < 0.9 and volume_pcr > 1.2:
        return (
            "BEAR TRAP - Possible reversal upside",
            "Medium (55-60%)",
            "Bearish OI but high put volume shows panic put buying",
            "Watch for quick recovery candles or bullish divergences"
        )
    
    # Condition 8: Bull Trap or Sluggish Bull Phase
    elif oi_pcr > 1.1 and volume_pcr < 0.8:
        return (
            "BULL TRAP - Possible reversal downside",
            "Medium (53-60%)",
            "Bullish OI but low volume suggests weakening upside",
            "Likely pullback if price fails to clear day high"
        )
    
    # Default condition for unclassified scenarios
    else:
        return (
            "MIXED SIGNALS - Wait for confirmation",
            "Low",
            "Conflicting signals between OI and volume PCR",
            "Wait for clearer setup or price confirmation"
        )

def analyze_nifty_momentum(conn, current_nifty, current_cycle, oi_pcr, volume_pcr, futures_data):
    """Analyze Nifty momentum with futures integration"""
    cursor = conn.cursor()
    
    # Get all strikes for current cycle
    cursor.execute('''
        SELECT strike_price, ce_change_oi, pe_change_oi, chg_oi_diff
        FROM oi_data 
        WHERE fetch_cycle = ?
        ORDER BY strike_price
    ''', (current_cycle,))
    
    current_data = cursor.fetchall()
    
    if not current_data:
        return "Insufficient data for analysis"
    
    # Find ATM strike (closest to current nifty)
    atm_strike = min(current_data, key=lambda x: abs(x[0] - current_nifty))[0]
    
    # Get data for key strikes (ATM, one above, one below)
    strikes_data = {}
    for strike, ce_oi, pe_oi, chg_diff in current_data:
        strikes_data[strike] = {
            'ce_change_oi': ce_oi,
            'pe_change_oi': pe_oi,
            'chg_oi_diff': chg_diff
        }
    
    # Analyze based on Nifty index option logic with futures
    analysis = perform_nifty_analysis(current_nifty, strikes_data, atm_strike, oi_pcr, volume_pcr, futures_data)
    
    # Add momentum buildup analysis
    momentum_analysis = analyze_momentum_buildup(conn, current_cycle, list(strikes_data.keys()))
    analysis += f"\nMOMENTUM BUILDUP ANALYSIS:\n{momentum_analysis}"
    
    return analysis

def perform_nifty_analysis(current_nifty, strikes_data, atm_strike, oi_pcr, volume_pcr, futures_data):
    """Perform Nifty-specific option chain analysis with futures integration"""
    
    analysis = ""
    
    # Add Futures Analysis
    if futures_data:
        futures_trend, futures_confidence, futures_analysis = analyze_futures_trend(futures_data, current_nifty)
        analysis += f"FUTURES ANALYSIS:\n"
        analysis += f" Price: {futures_data['futures_price']:.2f} | OI: {format_oi_value(futures_data['futures_oi'])} | Chg OI: {format_oi_value(futures_data['futures_change_oi'])}\n"
        analysis += f" Basis: {futures_data['basis']:+.2f} (Futures - Spot)\n"
        analysis += f" Signal: {futures_analysis}\n"
        analysis += f" Confidence: {futures_confidence}\n\n"
    else:
        analysis += "FUTURES ANALYSIS: Data unavailable\n\n"
        futures_trend = "UNKNOWN"
        futures_confidence = "LOW"
    
    # Get PCR signals using new conditions
    pcr_signal, pcr_confidence, pcr_behavior, pcr_context = get_pcr_signals(oi_pcr, volume_pcr)
    
    # Add PCR values and signals to analysis
    analysis += f"PCR ANALYSIS (ATM ±2 strikes):\n"
    analysis += f" OI PCR: {oi_pcr:.2f}\n"
    analysis += f" Volume PCR: {volume_pcr:.2f}\n"
    analysis += f" SIGNAL: {pcr_signal}\n"
    analysis += f" CONFIDENCE: {pcr_confidence}\n"
    analysis += f" BEHAVIOR: {pcr_behavior}\n"
    analysis += f" CONTEXT: {pcr_context}\n\n"
    
    # Get strikes around current price
    strikes = sorted(strikes_data.keys())
    atm_index = strikes.index(atm_strike)
    
    lower_strike = strikes[atm_index - 1] if atm_index > 0 else None
    upper_strike = strikes[atm_index + 1] if atm_index < len(strikes) - 1 else None
    
    # Analyze each strike
    bullish_signals = 0
    bearish_signals = 0
    neutral_signals = 0
    
    for strike in strikes:
        data = strikes_data[strike]
        ce_oi = data['ce_change_oi']
        pe_oi = data['pe_change_oi']
        
        # Nifty Index Option Logic:
        # - Higher PE OI change = Support building = BULLISH for that strike
        # - Higher CE OI change = Resistance building = BEARISH for that strike
        
        if pe_oi > ce_oi:
            bullish_signals += 1
        elif ce_oi > pe_oi:
            bearish_signals += 1
        else:
            neutral_signals += 1
    
    # Overall direction analysis
    analysis += f"STRIKE-BY-STRIKE ANALYSIS:\n"
    analysis += f" Bullish Signals (PE dominance): {bullish_signals}\n"
    analysis += f" Bearish Signals (CE dominance): {bearish_signals}\n"
    analysis += f" Neutral Signals: {neutral_signals}\n"
    
    # Combine PCR signals with OI analysis for final interpretation
    final_direction = ""
    final_confidence = ""
    final_target = ""
    final_reason = ""
    
    # Determine base direction from OI analysis
    if bullish_signals > bearish_signals:
        base_direction = "UPWARD"
        base_confidence = "HIGH" if bullish_signals >= 3 else "MEDIUM"
        base_target = upper_strike if upper_strike else "Higher levels"
        base_reason = "More strikes showing support buildup (PE dominance)"
    elif bearish_signals > bullish_signals:
        base_direction = "DOWNWARD" 
        base_confidence = "HIGH" if bearish_signals >= 3 else "MEDIUM"
        base_target = lower_strike if lower_strike else "Lower levels"
        base_reason = "More strikes showing resistance buildup (CE dominance)"
    else:
        base_direction = "SIDEWAYS"
        base_confidence = "LOW"
        base_target = "Range-bound"
        base_reason = "Balanced OI changes across strikes"
    
    # INTEGRATE FUTURES + PCR + OI ANALYSIS
    if futures_trend in ["BULLISH", "STRONG_BULLISH"] and base_direction == "UPWARD" and "BULLISH" in pcr_signal:
        final_direction = "STRONG BULLISH CONFIRMATION"
        final_confidence = "VERY HIGH"
        final_target = base_target
        final_reason = f"Futures, PCR & OI all confirm bullish trend"
        
    elif futures_trend in ["BEARISH", "STRONG_BEARISH"] and base_direction == "DOWNWARD" and "BEARISH" in pcr_signal:
        final_direction = "STRONG BEARISH CONFIRMATION"
        final_confidence = "VERY HIGH"
        final_target = base_target
        final_reason = f"Futures, PCR & OI all confirm bearish trend"
        
    elif futures_trend in ["BULLISH", "STRONG_BULLISH"] and base_direction == "DOWNWARD":
        final_direction = "BULLISH REVERSAL LIKELY"
        final_confidence = "HIGH"
        final_target = "Upside reversal"
        final_reason = f"Futures show strength against OI resistance. {base_reason}"
        
    elif futures_trend in ["BEARISH", "STRONG_BEARISH"] and base_direction == "UPWARD":
        final_direction = "BEARISH REVERSAL LIKELY"
        final_confidence = "HIGH"
        final_target = "Downside reversal"
        final_reason = f"Futures show weakness against OI support. {base_reason}"
        
    elif "BULLISH" in pcr_signal and base_direction == "UPWARD":
        final_direction = "BULLISH BIAS"
        final_confidence = pcr_confidence.split(' ')[0]
        final_target = base_target
        final_reason = f"PCR confirms {base_reason.lower()}"
        
    elif "BEARISH" in pcr_signal and base_direction == "DOWNWARD":
        final_direction = "BEARISH BIAS"
        final_confidence = pcr_confidence.split(' ')[0]
        final_target = base_target
        final_reason = f"PCR confirms {base_reason.lower()}"
        
    else:
        # Mixed or neutral signals
        final_direction = base_direction
        final_confidence = base_confidence
        final_target = base_target
        final_reason = base_reason
    
    analysis += f"\nFINAL INTERPRETATION (with Futures):\n"
    analysis += f" DIRECTION: {final_direction}\n"
    analysis += f" CONFIDENCE: {final_confidence}\n"
    analysis += f" TARGET: {final_target}\n"
    analysis += f" REASON: {final_reason}\n"
    
    return analysis

def analyze_momentum_buildup(conn, current_cycle, strikes):
    """Analyze momentum buildup across last 9 cycles"""
    cursor = conn.cursor()
    
    # Get data for last 9 cycles
    cursor.execute('''
        SELECT fetch_cycle, strike_price, ce_change_oi, pe_change_oi
        FROM oi_data 
        WHERE fetch_cycle IN (
            SELECT DISTINCT fetch_cycle 
            FROM oi_data 
            WHERE fetch_cycle <= ?
            ORDER BY fetch_cycle DESC 
            LIMIT 9
        )
        AND strike_price IN ({})
        ORDER BY fetch_cycle DESC, strike_price
    '''.format(','.join('?' * len(strikes))), [current_cycle] + strikes)
    
    momentum_data = cursor.fetchall()
    
    if len(momentum_data) < 5:  # Need at least 5 data points
        return "Insufficient historical data for momentum analysis"
    
    # Analyze trends for each strike
    strike_trends = {}
    for strike in strikes:
        strike_data = [(cycle, ce, pe) for cycle, st, ce, pe in momentum_data if st == strike]
        if len(strike_data) >= 3:
            trend = analyze_strike_trend(strike_data)
            strike_trends[strike] = trend
    
    # Generate momentum summary
    analysis = ""
    strengthening_bullish = 0
    strengthening_bearish = 0
    
    for strike, trend in strike_trends.items():
        if trend == "bullish_strengthening":
            analysis += f" Strike {strike}: Bullish momentum strengthening\n"
            strengthening_bullish += 1
        elif trend == "bearish_strengthening":
            analysis += f" Strike {strike}: Bearish momentum strengthening\n"
            strengthening_bearish += 1
        elif trend == "bullish_consistent":
            analysis += f" Strike {strike}: Consistent bullish pressure\n"
        elif trend == "bearish_consistent":
            analysis += f" Strike {strike}: Consistent bearish pressure\n"
        else:
            analysis += f" Strike {strike}: Mixed/weak signals\n"
    
    # Overall momentum conclusion
    if strengthening_bullish > strengthening_bearish:
        analysis += f"\nSTRONG BULLISH MOMENTUM: {strengthening_bullish} strikes showing strengthening support"
    elif strengthening_bearish > strengthening_bullish:
        analysis += f"\nSTRONG BEARISH MOMENTUM: {strengthening_bearish} strikes showing strengthening resistance"
    else:
        analysis += f"\nBALANCED MOMENTUM: No clear strengthening trend"
    
    return analysis

def analyze_strike_trend(strike_data):
    """Analyze trend for a specific strike across cycles"""
    # Convert to list of (pe_oi - ce_oi) differences
    differences = [pe - ce for _, ce, pe in strike_data]
    
    # Check if consistently positive (bullish) or negative (bearish)
    all_positive = all(diff > 0 for diff in differences)
    all_negative = all(diff < 0 for diff in differences)
    
    # Check if strengthening (increasing absolute values)
    if all_positive:
        if differences[0] > differences[-1]:  # Most recent is strongest
            return "bullish_strengthening"
        else:
            return "bullish_consistent"
    elif all_negative:
        if differences[0] < differences[-1]:  # Most recent is strongest (more negative)
            return "bearish_strengthening"
        else:
            return "bearish_consistent"
    else:
        return "mixed"

def save_oi_data_to_db(oi_data, futures_data):
    """Save OI data and futures data to SQLite database"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    try:
        # Get next fetch cycle number
        fetch_cycle, total_fetches = get_next_cycle()
        fetch_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"Using Cycle: {fetch_cycle}/10 (Total: {total_fetches})")
        
        # Delete existing data for this cycle (if any) before inserting new data
        cursor.execute('DELETE FROM oi_data WHERE fetch_cycle = ?', (fetch_cycle,))
        cursor.execute('DELETE FROM futures_data WHERE fetch_cycle = ?', (fetch_cycle,))
        
        # Calculate PCR values before saving
        oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
        
        # Save OI data for all strike prices
        for data in oi_data:
            # Calculate chg_oi_diff (CE - PE) - CORRECT CALCULATION
            chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
            
            cursor.execute('''
                INSERT INTO oi_data (
                    fetch_cycle, fetch_timestamp, nifty_value, expiry_date, strike_price,
                    ce_change_oi, ce_volume, ce_ltp, ce_oi,
                    pe_change_oi, pe_volume, pe_ltp, pe_oi, chg_oi_diff, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fetch_cycle, fetch_timestamp, data['nifty_value'], data['expiry_date'], data['strike_price'],
                data['ce_change_oi'], data['ce_volume'], data['ce_ltp'], data['ce_oi'],
                data['pe_change_oi'], data['pe_volume'], data['pe_ltp'], data['pe_oi'],
                chg_oi_diff, datetime.datetime.now().isoformat()
            ))
        
        # Save futures data
        if futures_data:
            futures_trend, futures_confidence, futures_analysis = analyze_futures_trend(futures_data, oi_data[0]['nifty_value'])
            
            cursor.execute('''
                INSERT INTO futures_data (
                    fetch_cycle, fetch_timestamp, nifty_spot, futures_price, futures_oi,
                    futures_change_oi, futures_volume, basis, expiry_date, trend_strength, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                fetch_cycle, fetch_timestamp, oi_data[0]['nifty_value'], futures_data['futures_price'],
                futures_data['futures_oi'], futures_data['futures_change_oi'], futures_data['futures_volume'],
                futures_data['basis'], futures_data['expiry_date'], futures_trend, datetime.datetime.now().isoformat()
            ))
        
        # Perform Nifty-specific momentum analysis with PCR and futures integration
        current_nifty = oi_data[0]['nifty_value']
        momentum_analysis = analyze_nifty_momentum(conn, current_nifty, fetch_cycle, oi_pcr, volume_pcr, futures_data)
        
        conn.commit()
        print(f"OI data saved (Cycle: {fetch_cycle})")
        
        return momentum_analysis
        
    except Exception as e:
        print(f"Error saving to database: {e}")
        conn.rollback()
        return f"Error in analysis: {e}"
    finally:
        conn.close()

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
                oi_data = {
                    'nifty_value': round(current_nifty),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    'ce_change_oi': parse_numeric_value(record['CE'].get('changeinOpenInterest', 0)) if 'CE' in record else 0,
                    'ce_volume': parse_numeric_value(record['CE'].get('totalTradedVolume', 0)) if 'CE' in record else 0,
                    'ce_ltp': parse_numeric_value(record['CE'].get('lastPrice', 0)) if 'CE' in record else 0,
                    'ce_oi': parse_numeric_value(record['CE'].get('openInterest', 0)) if 'CE' in record else 0,
                    'pe_change_oi': parse_numeric_value(record['PE'].get('changeinOpenInterest', 0)) if 'PE' in record else 0,
                    'pe_volume': parse_numeric_value(record['PE'].get('totalTradedVolume', 0)) if 'PE' in record else 0,
                    'pe_ltp': parse_numeric_value(record['PE'].get('lastPrice', 0)) if 'PE' in record else 0,
                    'pe_oi': parse_numeric_value(record['PE'].get('openInterest', 0)) if 'PE' in record else 0
                }
                filtered_records.append(oi_data)
        
        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain: {str(e)}")

def display_latest_data():
    """Display the latest fetch cycle data from database"""
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
        
        # Get futures data for current cycle
        cursor.execute('''
            SELECT * FROM futures_data 
            WHERE fetch_cycle = ?
        ''', (current_cycle,))
        
        futures_row = cursor.fetchone()
        
        # Get data for current cycle
        cursor.execute('''
            SELECT * FROM oi_data 
            WHERE fetch_cycle = ? 
            ORDER BY strike_price
        ''', (current_cycle,))
        
        rows = cursor.fetchall()
        
        if rows:
            print(f"\nOI Data (Cycle: {current_cycle}/10, Total Fetches: {total_fetches})")
            
            # Display Futures Data if available
            if futures_row:
                print("=" * 160)
                print("FUTURES DATA:")
                print(f"  Nifty Spot: {futures_row[3]:.2f} | Futures: {futures_row[4]:.2f} | Basis: {futures_row[8]:+.2f}")
                print(f"  Futures OI: {format_oi_value(futures_row[5])} | Chg OI: {format_oi_value(futures_row[6])} | Trend: {futures_row[10]}")
                print("=" * 160)
            else:
                print("=" * 160)
                print("FUTURES DATA: Not available")
                print("=" * 160)
            
            # Updated header with exact formatting
            print(f"{'CALL OPTION':^50} | {'STRIKE':^10} | {'PUT OPTION':^38} | {'CHG OI DIFF':>16} {'CHG OI DIFF HISTORY':>30}")
            print(f"{'Chg OI':>10} {'Volume':>10} {'LTP':>10} {'OI':>10} {' ':^6} | {'Price':^10} | {'Chg OI':>10} {'Volume':>10} {'LTP':>10} {'OI':>8} | {'CE-PE':>12} {'(latest first)':>30}")
            print("-" * 160)
            
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
                ce_ltp_formatted = str(ce_ltp)
                ce_oi_total_formatted = format_oi_value(ce_oi_total)
                
                pe_oi_formatted = format_oi_value(pe_oi)
                pe_volume_formatted = format_oi_value(pe_volume)
                pe_ltp_formatted = str(pe_ltp)
                pe_oi_total_formatted = format_oi_value(pe_oi_total)
                
                chg_oi_diff_formatted = format_oi_value(chg_oi_diff)
                
                # Get CHG OI DIFF history
                chg_oi_history = get_chg_oi_diff_history(strike_price, current_cycle)
                history_str = ", ".join(chg_oi_history) if chg_oi_history else "No history"
                
                # Format the row with exact padding
                ce_data = f"{ce_oi_formatted:>10} {ce_volume_formatted:>10} {ce_ltp_formatted:>10} {ce_oi_total_formatted:>10}"
                pe_data = f"{pe_oi_formatted:>10} {pe_volume_formatted:>10} {pe_ltp_formatted:>10} {pe_oi_total_formatted:>8}"
                
                print(f"{ce_data} {' ':^6} | {strike_price:>9} | {pe_data} | {chg_oi_diff_formatted:>12} {history_str:>30}")
            
            print("=" * 160)
        
    except Exception as e:
        print(f"Error displaying data: {e}")
    finally:
        conn.close()

def data_collection_loop():
    global running
    session = None
    
    # Initialize database (this will reset cycles to 1)
    initialize_database()
    
    while running:
        try:
            if session is None:
                session = initialize_session()
            
            print(f"\nFetching {SYMBOL} option chain...")
            data = fetch_option_chain(session)
            oi_data = parse_option_chain(data)
            
            print("Fetching Nifty futures data...")
            futures_data = fetch_nifty_futures(session)
            
            if futures_data:
                print(f"Futures data found: {futures_data['futures_price']:.2f} (Basis: {futures_data['basis']:+.2f})")
            else:
                print("Futures data not available - using options-only analysis")
            
            # Save to database and get momentum analysis
            momentum_analysis = save_oi_data_to_db(oi_data, futures_data)
            
            # Display latest data
            display_latest_data()
            
            # Display momentum analysis
            print(momentum_analysis)
            
            # Display brief info
            print(f"Nifty: {oi_data[0]['nifty_value']}, Expiry: {oi_data[0]['expiry_date']}")
            print(f"Database: {DB_FILE}")
            
            # Wait for next interval
            print(f"Next update in {FETCH_INTERVAL} seconds...")
            for i in range(FETCH_INTERVAL):
                if not running:
                    break
                time.sleep(1)
                    
        except KeyboardInterrupt:
            running = False
        except Exception as e:
            print(f"Error: {e}")
            session = None
            time.sleep(10)

def main():
    print(f"Starting {SYMBOL} OI Data Logger with Futures Integration")
    print(f"Data will be saved to {DB_FILE} every {FETCH_INTERVAL} seconds")
    print(f"Maintaining exactly {MAX_FETCH_CYCLES} fetch cycles (1-10 in circular manner)")
    print("Press Ctrl+C to stop")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        data_collection_loop()
        print("\nApplication stopped")
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()