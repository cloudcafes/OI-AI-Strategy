import os
import sys
import platform

# ---------------------------------------------------------
# 1. CORE SYSTEM CONFIGURATION
# ---------------------------------------------------------
SYMBOL = "NIFTY"
FETCH_INTERVAL = 1800  # Seconds between fetches in loop mode

# System Master Switches
ENABLE_AI_ANALYSIS = True
ENABLE_LOOP_FETCHING = False
ENABLE_STOCK_DISPLAY = False

# ---------------------------------------------------------
# 2. API KEYS & CREDENTIALS
# ---------------------------------------------------------
# Best practice: Uses environment variables if available, otherwise falls back to hardcoded keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "hardcoded")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "hardcoded")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "hardcoded")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "hardcoded")
EMAIL_TO = os.getenv("EMAIL_TO", "talkdev@gmail.com")

# ---------------------------------------------------------
# 3. DYNAMIC DIRECTORIES & PATHS
# ---------------------------------------------------------
# Automatically map to the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AI_LOGS_DIR = os.path.join(BASE_DIR, "ai-query-logs")
GEMINI_LOGS_DIR = os.path.join(BASE_DIR, "gemini-logs")

# Ensure directories exist upon startup
os.makedirs(AI_LOGS_DIR, exist_ok=True)
os.makedirs(GEMINI_LOGS_DIR, exist_ok=True)

# ---------------------------------------------------------
# 4. HTTP HEADERS (For Playwright / NSE APIs)
# ---------------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "X-Requested-With": "XMLHttpRequest"
}

STOCK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest"
}

# ---------------------------------------------------------
# 5. TOP NIFTY STOCKS TRACKING LIST
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# 6. GLOBAL STATE & SIGNAL HANDLING
# ---------------------------------------------------------
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    print("\n🛑 Received shutdown signal. Terminating loops safely...")
    running = False

# ---------------------------------------------------------
# 7. OPTIMIZED UTILITY FUNCTIONS
# ---------------------------------------------------------
def parse_numeric_value(value):
    """Optimized integer parsing with fast fallbacks."""
    if not value or value == '-': 
        return 0
    try:
        return int(value)
    except ValueError:
        try:
            return int(float(str(value).replace(',', '')))
        except (ValueError, TypeError):
            return 0

def parse_float_value(value):
    """Optimized float parsing."""
    if not value or value == '-': 
        return 0.0
    try:
        return float(value)
    except ValueError:
        try:
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return 0.0

def format_greek_value(value, decimal_places=3):
    """Fast string formatting for Greeks."""
    if not value: 
        return "0"
    try:
        return f"{float(value):.{decimal_places}f}"
    except (ValueError, TypeError):
        return "0"

def print_configuration_status():
    """Prints the active status of the system."""
    print(f"\n{'='*40}")
    print(f"🤖 CURRENT SYSTEM CONFIGURATION")
    print(f"{'='*40}")
    print(f"Platform:       {platform.system()}")
    print(f"Target Symbol:  {SYMBOL}")
    print(f"AI Analysis:    {'ENABLED' if ENABLE_AI_ANALYSIS else 'DISABLED'}")
    print(f"Loop Mode:      {'ENABLED' if ENABLE_LOOP_FETCHING else 'DISABLED'}")
    print(f"Stock Data:     {'ENABLED' if ENABLE_STOCK_DISPLAY else 'DISABLED'}")
    print(f"{'='*40}\n")

if __name__ == "__main__":
    print_configuration_status()