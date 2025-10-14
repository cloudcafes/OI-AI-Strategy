# Part 1: Nifty_Option_Chain_Fetcher_Part1.py
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
FETCH_INTERVAL = 600
DB_FILE = "oi_data-temp.db"
MAX_FETCH_CYCLES = 10  # Keep exactly 10 fetch cycles (1 to 10)
DISPLAY_STOCKS_ON_CONSOLE = 0

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
    # Force exit if not responding
    sys.exit(0)

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

def initialize_database():
    """Initialize SQLite database and reset cycles to start from 1"""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create table for OI data with Greek values columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS oi_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_cycle INTEGER,
            fetch_timestamp TEXT,
            nifty_value INTEGER,
            expiry_date TEXT,
            strike_price INTEGER,
            ce_change_oi INTEGER,
            ce_volume INTEGER,
            ce_ltp REAL,
            ce_oi INTEGER,
            ce_iv REAL,
            ce_delta REAL,
            ce_gamma REAL,
            ce_theta REAL,
            ce_vega REAL,
            pe_change_oi INTEGER,
            pe_volume INTEGER,
            pe_ltp REAL,
            pe_oi INTEGER,
            pe_iv REAL,
            pe_delta REAL,
            pe_gamma REAL,
            pe_theta REAL,
            pe_vega REAL,
            chg_oi_diff INTEGER,
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
    
    conn.commit()
    conn.close()
    #print(f"Database initialized: {DB_FILE}")
    #print("Cycle counter reset to 1")

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

def parse_float_value(value):
    """Parse numeric values that may contain commas and convert to float"""
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Remove commas and any whitespace
        cleaned_value = value.replace(',', '').strip()
        if cleaned_value == '' or cleaned_value == '-':
            return 0.0
        try:
            return float(cleaned_value)
        except (ValueError, TypeError):
            return 0.0
    
    return 0.0

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

def format_greek_value(value, decimal_places=3):
    """Format Greek values with specified decimal places"""
    if value is None or value == 0:
        return "0"
    
    try:
        return f"{float(value):.{decimal_places}f}"
    except (ValueError, TypeError):
        return "0"

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