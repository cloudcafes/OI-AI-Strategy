import requests
import datetime
import time
import signal
import sys
import urllib3
import os
import platform
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Core Configuration
SYMBOL = "NIFTY"
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5
FETCH_INTERVAL = 600

# AI Analysis Configuration
ENABLE_AI_ANALYSIS = False
ENABLE_SINGLE_AI_QUERY = True
ENABLE_MULTI_AI_QUERY = True
AI_QUERY_MODE = "both"  # "single" | "multi" | "both"

# System Operation Configuration
ENABLE_LOOP_FETCHING = False
ENABLE_STOCK_DISPLAY = False
ENABLE_MULTI_EXPIRY = True

# Expiry Type Constants
CURRENT_WEEK = "current_week"
NEXT_WEEK = "next_week"
MONTHLY = "monthly"
EXPIRY_TYPES = [CURRENT_WEEK, NEXT_WEEK, MONTHLY]

# Expiry Classification Parameters
NEXT_WEEK_DAY_RANGE = (5, 9)
MONTHLY_THRESHOLD_DAYS = 20

# Platform-specific Directory Configuration
if platform.system() == "Windows":
    EOD_BASE_DIR = r"C:\dev\python-projects\OI-AI-Strategy\multi-expiry-logs"
    MULTI_EXPIRY_LOGS_DIR = r"C:\dev\python-projects\OI-AI-Strategy\multi-expiry-logs"
else:
    EOD_BASE_DIR = "/root/OI-AI-Strategy/multi-expiry-logs"
    MULTI_EXPIRY_LOGS_DIR = "/root/OI-AI-Strategy/multi-expiry-logs"

# HTTP Headers Configuration
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/get-quotes/derivatives?symbol=NIFTY",
    "X-Requested-With": "XMLHttpRequest"
}

STOCK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest"
}

# Top Nifty Stocks Configuration
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

# Global State
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    print("\nReceived shutdown signal...")
    running = False
    sys.exit(0)

def create_session_with_retry():
    """Create HTTP session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.verify = False
    return session

def initialize_session():
    """Initialize session for NSE API calls"""
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
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504]
    )
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

def should_enable_multi_expiry():
    """Check if multi-expiry analysis should be performed"""
    return ENABLE_MULTI_EXPIRY

def should_enable_single_ai_query():
    """Check if single AI query should be performed"""
    return ENABLE_SINGLE_AI_QUERY

def should_enable_multi_ai_query():
    """Check if multi AI query should be performed"""
    return ENABLE_MULTI_AI_QUERY

def get_ai_query_mode():
    """Get the current AI query mode"""
    return AI_QUERY_MODE

def get_fetch_interval():
    """Get the fetch interval based on configuration"""
    return FETCH_INTERVAL

def get_expiry_type_constants():
    """Return expiry type constants"""
    return {
        'CURRENT_WEEK': CURRENT_WEEK,
        'NEXT_WEEK': NEXT_WEEK,
        'MONTHLY': MONTHLY,
        'ALL_TYPES': EXPIRY_TYPES
    }

def get_expiry_classification_params():
    """Return parameters used for expiry classification"""
    return {
        'next_week_day_range': NEXT_WEEK_DAY_RANGE,
        'monthly_threshold_days': MONTHLY_THRESHOLD_DAYS
    }

def get_eod_base_directory():
    """Return the platform-specific EOD base directory"""
    return EOD_BASE_DIR

def get_multi_expiry_logs_directory():
    """Return the platform-specific multi-expiry logs directory"""
    return MULTI_EXPIRY_LOGS_DIR

def validate_configuration():
    """Validate configuration settings for consistency"""
    issues = []
    
    # Check AI configuration consistency
    if ENABLE_AI_ANALYSIS and not (ENABLE_SINGLE_AI_QUERY or ENABLE_MULTI_AI_QUERY):
        issues.append("AI analysis enabled but both query types are disabled")
    
    # Check mode consistency
    if AI_QUERY_MODE not in ["single", "multi", "both"]:
        issues.append(f"Invalid AI_QUERY_MODE: {AI_QUERY_MODE}. Must be 'single', 'multi', or 'both'")
    
    # Check directory accessibility
    try:
        if not os.path.exists(EOD_BASE_DIR):
            os.makedirs(EOD_BASE_DIR, exist_ok=True)
        if not os.path.exists(MULTI_EXPIRY_LOGS_DIR):
            os.makedirs(MULTI_EXPIRY_LOGS_DIR, exist_ok=True)
    except Exception as e:
        issues.append(f"Directory creation failed: {e}")
    
    return issues

# Validate configuration on import
config_issues = validate_configuration()
if config_issues:
    print("⚠️ Configuration issues detected:")
    for issue in config_issues:
        print(f"   - {issue}")
else:
    print("✅ Configuration validated successfully")

# Print current configuration
if __name__ == "__main__":
    print("\n=== Current Configuration ===")
    print(f"Platform: {platform.system()}")
    print(f"EOD Base Directory: {EOD_BASE_DIR}")
    print(f"Multi-Expiry Logs Directory: {MULTI_EXPIRY_LOGS_DIR}")
    print(f"AI Analysis Enabled: {ENABLE_AI_ANALYSIS}")
    print(f"Single AI Query: {ENABLE_SINGLE_AI_QUERY}")
    print(f"Multi AI Query: {ENABLE_MULTI_AI_QUERY}")
    print(f"AI Query Mode: {AI_QUERY_MODE}")
    print(f"Multi-Expiry Enabled: {ENABLE_MULTI_EXPIRY}")
    print("=============================\n")