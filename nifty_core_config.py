# nifty_core_config.py
import requests
import datetime
import time
import signal
import sys
import urllib3
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
SYMBOL = "NIFTY"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5
FETCH_INTERVAL = 800

# Feature flags
ENABLE_AI_ANALYSIS = False
ENABLE_LOOP_FETCHING = True
ENABLE_STOCK_DISPLAY = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/get-quotes/derivatives?symbol=NIFTY",
    "X-Requested-With": "XMLHttpRequest"
}

# Stock-specific headers
STOCK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest"
}

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

def format_greek_value(value, decimal_places=3):
    """Format Greek values with specified decimal places"""
    if value is None or value == 0:
        return "0"
    
    try:
        return f"{float(value):.{decimal_places}f}"
    except (ValueError, TypeError):
        return "0"

def should_run_ai_analysis():
    """Check if AI analysis should be performed"""
    return ENABLE_AI_ANALYSIS

def should_run_loop():
    """Check if continuous loop fetching should be performed"""
    return ENABLE_LOOP_FETCHING

def should_display_stocks():
    """Check if stock data should be displayed"""
    return ENABLE_STOCK_DISPLAY

def get_fetch_interval():
    """Get the fetch interval based on configuration"""
    return FETCH_INTERVAL