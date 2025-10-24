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

# Multi-Model Feature Flags
ENABLE_MULTI_MODEL = True  # Enable multi-model analysis
ENABLE_AI_ANALYSIS = True  # Legacy single AI analysis
ENABLE_LOOP_FETCHING = False
ENABLE_STOCK_DISPLAY = False

# Multi-Model Configuration
MULTI_MODEL_ENABLED = True
MODEL_EXECUTION_ORDER = ["deepseek_r1", "cloud_deepseek", "llama3", "mistral"]

# Individual Model Enable Flags
MODEL_DEEPSEEK_R1_ENABLED = True
MODEL_CLOUD_DEEPSEEK_ENABLED = False
MODEL_LLAMA3_ENABLED = False
MODEL_MISTRAL_ENABLED = False

# Local AI Configuration
LOCAL_AI_ENABLED = True
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "deepseek-r1:latest"
OLLAMA_TIMEOUT = 600

# Cloud AI Configuration
CLOUD_AI_ENABLED = False
DEEPSEEK_API_KEY = "sk-df60b28326444de6859976f6e603fd9c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT = 300

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

# Model-specific parameters
MODEL_PARAMETERS = {
    "deepseek_r1": {
        "temperature": 0.1,
        "top_p": 1.0,
        "max_tokens": 1200,
        "timeout": 120
    },
    "cloud_deepseek": {
        "temperature": 0,
        "top_p": 1.0,
        "max_tokens": 1200,
        "timeout": 300
    },
    "llama3": {
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 1000,
        "timeout": 120
    },
    "mistral": {
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 1000,
        "timeout": 120
    }
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
    retry_strategy = Retry(
        total=3,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1
    )
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
    session = create_session_with_retry()
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

# Feature flag functions
def should_run_ai_analysis():
    """Check if legacy single AI analysis should be performed"""
    return ENABLE_AI_ANALYSIS

def should_run_multi_model_analysis():
    """Check if multi-model analysis should be performed"""
    return ENABLE_MULTI_MODEL

def should_run_loop():
    """Check if continuous loop fetching should be performed"""
    return ENABLE_LOOP_FETCHING

def should_display_stocks():
    """Check if stock data should be displayed"""
    return ENABLE_STOCK_DISPLAY

def get_fetch_interval():
    """Get the fetch interval based on configuration"""
    return FETCH_INTERVAL

def is_multi_model_enabled():
    """Check if multi-model system is enabled"""
    return MULTI_MODEL_ENABLED

def get_model_execution_order():
    """Get the model execution order"""
    return MODEL_EXECUTION_ORDER

def is_model_enabled(model_name):
    """Check if a specific model is enabled"""
    model_flags = {
        "deepseek_r1": MODEL_DEEPSEEK_R1_ENABLED,
        "cloud_deepseek": MODEL_CLOUD_DEEPSEEK_ENABLED,
        "llama3": MODEL_LLAMA3_ENABLED,
        "mistral": MODEL_MISTRAL_ENABLED
    }
    return model_flags.get(model_name, False)

def get_model_parameters(model_name):
    """Get parameters for a specific model"""
    return MODEL_PARAMETERS.get(model_name, {})

def is_local_ai_enabled():
    """Check if local AI (Ollama) is enabled"""
    return LOCAL_AI_ENABLED

def is_cloud_ai_enabled():
    """Check if cloud AI is enabled"""
    return CLOUD_AI_ENABLED

def get_ollama_config():
    """Get Ollama configuration"""
    return {
        "base_url": OLLAMA_BASE_URL,
        "default_model": OLLAMA_DEFAULT_MODEL,
        "timeout": OLLAMA_TIMEOUT
    }

def get_cloud_ai_config():
    """Get cloud AI configuration"""
    return {
        "api_key": DEEPSEEK_API_KEY,
        "base_url": DEEPSEEK_BASE_URL,
        "model": DEEPSEEK_MODEL,
        "timeout": DEEPSEEK_TIMEOUT
    }

def get_enabled_models():
    """Get list of enabled models"""
    enabled_models = []
    if MODEL_DEEPSEEK_R1_ENABLED:
        enabled_models.append("deepseek_r1")
    if MODEL_CLOUD_DEEPSEEK_ENABLED:
        enabled_models.append("cloud_deepseek")
    if MODEL_LLAMA3_ENABLED:
        enabled_models.append("llama3")
    if MODEL_MISTRAL_ENABLED:
        enabled_models.append("mistral")
    return enabled_models

def get_model_display_name(model_name):
    """Get display name for a model"""
    display_names = {
        "deepseek_r1": "🧠 DeepSeek R1",
        "cloud_deepseek": "☁️ DeepSeek Cloud",
        "llama3": "🦙 Llama 3",
        "mistral": "🌪️ Mistral"
    }
    return display_names.get(model_name, model_name)

def get_model_description(model_name):
    """Get description for a model"""
    descriptions = {
        "deepseek_r1": "Local DeepSeek R1 model via Ollama",
        "cloud_deepseek": "Cloud DeepSeek API",
        "llama3": "Local Llama 3 model via Ollama",
        "mistral": "Local Mistral model via Ollama"
    }
    return descriptions.get(model_name, "AI Model")

def validate_configuration():
    """Validate the configuration and return any issues"""
    issues = []
    
    # Check if any models are enabled
    enabled_models = get_enabled_models()
    if not enabled_models:
        issues.append("No models are enabled. At least one model must be enabled.")
    
    # Check local AI configuration if local models are enabled
    local_models = ["deepseek_r1", "llama3", "mistral"]
    has_local_models = any(model in enabled_models for model in local_models)
    
    if has_local_models and not LOCAL_AI_ENABLED:
        issues.append("Local models are enabled but LOCAL_AI_ENABLED is False")
    
    # Check cloud AI configuration if cloud model is enabled
    if "cloud_deepseek" in enabled_models and not CLOUD_AI_ENABLED:
        issues.append("Cloud DeepSeek is enabled but CLOUD_AI_ENABLED is False")
    
    # Check API key for cloud model
    if "cloud_deepseek" in enabled_models and not DEEPSEEK_API_KEY:
        issues.append("Cloud DeepSeek is enabled but DEEPSEEK_API_KEY is not set")
    
    return issues

def print_configuration_summary():
    """Print a summary of the current configuration"""
    print("\n=== Nifty Multi-Model Configuration ===")
    print(f"Multi-Model System: {'✅ ENABLED' if MULTI_MODEL_ENABLED else '❌ DISABLED'}")
    print(f"Legacy Single AI: {'✅ ENABLED' if ENABLE_AI_ANALYSIS else '❌ DISABLED'}")
    print(f"Loop Fetching: {'✅ ENABLED' if ENABLE_LOOP_FETCHING else '❌ DISABLED'}")
    print(f"Stock Display: {'✅ ENABLED' if ENABLE_STOCK_DISPLAY else '❌ DISABLED'}")
    
    print("\n🔧 Model Configuration:")
    enabled_models = get_enabled_models()
    for model in get_model_execution_order():
        status = "✅ ENABLED" if model in enabled_models else "❌ DISABLED"
        print(f"  {model}: {status}")
    
    print(f"\n🌐 Local AI: {'✅ ENABLED' if LOCAL_AI_ENABLED else '❌ DISABLED'}")
    print(f"☁️ Cloud AI: {'✅ ENABLED' if CLOUD_AI_ENABLED else '❌ DISABLED'}")
    
    # Validate configuration
    issues = validate_configuration()
    if issues:
        print("\n Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Configuration is valid")
    
    print("=" * 50)

# Initialize signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Print configuration summary on import
if __name__ == "__main__":
    print_configuration_summary()
    
    # Test configuration functions
    print("\n=== Configuration Tests ===")
    print(f"Enabled models: {get_enabled_models()}")
    print(f"Model execution order: {get_model_execution_order()}")
    print(f"Local AI config: {get_ollama_config()}")
    print(f"Cloud AI config: {get_cloud_ai_config()}")
    
    # Test individual model checks
    for model in ["deepseek_r1", "cloud_deepseek", "llama3", "mistral"]:
        print(f"Model {model}: {'ENABLED' if is_model_enabled(model) else 'DISABLED'}")
    
    print("✅ Configuration tests completed")