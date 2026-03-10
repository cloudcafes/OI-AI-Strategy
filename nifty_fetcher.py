import datetime
import time
import json

from nifty_config import (
    SYMBOL, HEADERS, STOCK_HEADERS, parse_numeric_value, parse_float_value,
    format_greek_value, TOP_NIFTY_STOCKS, ENABLE_STOCK_DISPLAY
)

# ---------------------------------------------------------
# PLAYWRIGHT SESSION MANAGEMENT
# ---------------------------------------------------------
_playwright_instance = None
_browser             = None
_browser_context     = None
_page                = None
_session_warmed      = False

_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-http2",          
    "--no-sandbox",
    "--disable-dev-shm-usage",
]

_NSE_HEADERS = {
    "Accept":            "application/json, text/plain, */*",
    "Referer":           "https://www.nseindia.com/option-chain",
    "X-Requested-With":  "XMLHttpRequest",
    "sec-fetch-dest":    "empty",
    "sec-fetch-mode":    "cors",
    "sec-fetch-site":    "same-origin",
}

def _start_playwright():
    """Start Playwright browser (called once per process)."""
    global _playwright_instance, _browser, _browser_context, _page
    if _page is not None:
        return

    try:
        from playwright.sync_api import sync_playwright
        _playwright_instance = sync_playwright().start()
        _browser = _playwright_instance.chromium.launch(headless=True, args=_CHROME_ARGS)
        _browser_context = _browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
        )
        _browser_context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined}); window.chrome={runtime:{}};"
        )
        _page = _browser_context.new_page()
        print("✅ Playwright browser started (Chromium)")
    except Exception as e:
        raise RuntimeError(f"Failed to start Playwright: {e}")

def _warm_session():
    """Warm NSE session cookies using lightweight page.request calls."""
    global _session_warmed
    if _session_warmed:
        return

    _start_playwright()
    print("🍪 Warming NSE session cookies...")

    warm_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
    }

    for url in ["https://www.nseindia.com", "https://www.nseindia.com/option-chain"]:
        try:
            _page.request.get(url, headers=warm_headers, timeout=20_000)
            time.sleep(2)
        except Exception:
            pass # Non-fatal

    _session_warmed = True
    print("✅ Session warm-up complete")

def _playwright_get(url: str, retries: int = 5, delay: int = 3) -> dict:
    """Fetch a JSON endpoint via the warmed Playwright page session."""
    _warm_session()

    for attempt in range(1, retries + 1):
        try:
            resp = _page.request.get(url, headers=_NSE_HEADERS, timeout=20_000)
            if not resp.ok:
                raise ValueError(f"HTTP {resp.status}")

            text = resp.text()
            if not text or text.strip() in ("{}", "[]", ""):
                time.sleep(delay)
                continue

            data = json.loads(text)
            if isinstance(data, dict) and "records" in data:
                if data["records"].get("underlyingValue", 0) == 0:
                    time.sleep(delay)
                    continue
            return data
        except Exception as e:
            if attempt < retries:
                time.sleep(delay)
    raise Exception(f"Failed to fetch {url} after {retries} attempts")

def stop_playwright():
    """Cleanly shut down the Playwright browser."""
    global _playwright_instance, _browser, _browser_context, _page, _session_warmed
    try:
        if _page: _page.close()
        if _browser_context: _browser_context.close()
        if _browser: _browser.close()
        if _playwright_instance: _playwright_instance.stop()
        print("🛑 Playwright browser closed")
    except Exception as e:
        print(f"⚠️ Error closing Playwright: {e}")
    finally:
        _playwright_instance = _browser = _browser_context = _page = None
        _session_warmed = False

# ---------------------------------------------------------
# DATA FETCHING & PARSING LOGIC
# ---------------------------------------------------------
def _get_expiry_dates(symbol: str) -> list:
    """Fetch available expiry dates from contract-info."""
    url = f"https://www.nseindia.com/api/option-chain-contract-info?symbol={symbol}"
    try:
        data = _playwright_get(url)
        return data.get("expiryDates", [])
    except Exception as e:
        print(f"⚠️ contract-info failed: {e}")
        return []

def _normalise_expiry(raw: str) -> str:
    """Convert any NSE date format to 'DD-Mon-YYYY'."""
    if not raw: return raw
    for fmt in ('%d-%b-%Y', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(raw, fmt).strftime('%d-%b-%Y')
        except ValueError:
            continue
    return raw

def fetch_option_chain():
    """Fetch ONLY the nearest NIFTY option chain (Optimized)."""
    print(f"   Getting expiry dates for {SYMBOL}...")
    expiry_dates = _get_expiry_dates(SYMBOL)
    if not expiry_dates:
        raise Exception("fetch_option_chain: could not retrieve expiry dates")

    nearest_expiry = expiry_dates[0]
    print(f"   Fetching nearest expiry: {nearest_expiry}")
    
    url = f"https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol={SYMBOL}&expiry={nearest_expiry}"
    data = _playwright_get(url)
    
    if not data or "records" not in data:
        raise Exception("fetch_option_chain: no valid data fetched")
        
    print(f"   ✅ Fetched {SYMBOL}: spot={data['records'].get('underlyingValue')}, strikes={len(data['records'].get('data', []))}")
    return data

def parse_option_chain(data):
    """Parse single option chain data."""
    if 'records' not in data:
        return []

    current_nifty = data['records']['underlyingValue']
    records = data['records']['data']
    expiry_date = data['records']['expiryDates'][0]

    filtered_records = []
    for record in records:
        # Normalize expiry field
        ce_exp = record.get('CE', {}).get('expiryDate', '')
        pe_exp = record.get('PE', {}).get('expiryDate', '')
        record_expiry = _normalise_expiry(record.get('expiryDate') or ce_exp or pe_exp or expiry_date)
        
        if record_expiry != expiry_date:
            continue

        ce_data = record.get('CE', {})
        pe_data = record.get('PE', {})
        strike = record.get('strikePrice') or ce_data.get('strikePrice') or pe_data.get('strikePrice') or 0

        filtered_records.append({
            'nifty_value':   round(current_nifty),
            'expiry_date':   expiry_date,
            'strike_price':  strike,
            'ce_change_oi':  parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
            'ce_volume':     parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
            'ce_ltp':        parse_float_value(ce_data.get('lastPrice', 0)),
            'ce_oi':         parse_numeric_value(ce_data.get('openInterest', 0)),
            'ce_iv':         parse_float_value(ce_data.get('impliedVolatility', 0)),
            'pe_change_oi':  parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
            'pe_volume':     parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
            'pe_ltp':        parse_float_value(pe_data.get('lastPrice', 0)),
            'pe_oi':         parse_numeric_value(pe_data.get('openInterest', 0)),
            'pe_iv':         parse_float_value(pe_data.get('impliedVolatility', 0)),
        })

    return filtered_records

def calculate_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for ALL strikes with zero safeguards."""
    total_ce_oi = sum(d['ce_oi'] for d in oi_data)
    total_pe_oi = sum(d['pe_oi'] for d in oi_data)
    total_ce_volume = sum(d['ce_volume'] for d in oi_data)
    total_pe_volume = sum(d['pe_volume'] for d in oi_data)

    oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
    volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 1.0

    return oi_pcr, volume_pcr

def fetch_banknifty_data():
    """Fetch BANKNIFTY option chain data without Greeks."""
    try:
        print("Fetching BANKNIFTY option chain...")
        expiry_dates = _get_expiry_dates("BANKNIFTY")
        if not expiry_dates: return None

        nearest_expiry = expiry_dates[0]
        url = f"https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol=BANKNIFTY&expiry={nearest_expiry}"
        data = _playwright_get(url)

        current_banknifty = data['records']['underlyingValue']
        records = data['records']['data']

        banknifty_data = []
        for record in records:
            ce_data = record.get('CE', {})
            pe_data = record.get('PE', {})
            banknifty_data.append({
                'symbol':           'BANKNIFTY',
                'underlying_value': round(current_banknifty, 2),
                'expiry_date':      nearest_expiry,
                'strike_price':     record['strikePrice'],
                'ce_change_oi':     parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                'ce_volume':        parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                'ce_ltp':           parse_float_value(ce_data.get('lastPrice', 0)),
                'ce_oi':            parse_numeric_value(ce_data.get('openInterest', 0)),
                'ce_iv':            parse_float_value(ce_data.get('impliedVolatility', 0)),
                'pe_change_oi':     parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                'pe_volume':        parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                'pe_ltp':           parse_float_value(pe_data.get('lastPrice', 0)),
                'pe_oi':            parse_numeric_value(pe_data.get('openInterest', 0)),
                'pe_iv':            parse_float_value(pe_data.get('impliedVolatility', 0)),
            })

        oi_pcr, volume_pcr = calculate_pcr_values(banknifty_data)

        return {
            'data': banknifty_data,
            'pcr_values': {'oi_pcr': oi_pcr, 'volume_pcr': volume_pcr},
            'current_value': current_banknifty,
            'expiry_date': nearest_expiry,
        }
    except Exception as e:
        print(f"Error fetching BANKNIFTY data: {e}")
        return None

def fetch_all_stock_data():
    """Fetch data for all top 10 Nifty stocks if enabled."""
    if not ENABLE_STOCK_DISPLAY:
        return {}

    print(f"\n{'='*80}\nFETCHING TOP 10 NIFTY STOCKS DATA...\n{'='*80}")
    stock_data = {}

    for symbol in TOP_NIFTY_STOCKS.keys():
        try:
            print(f"Fetching {symbol}...")
            expiry_dates = _get_expiry_dates(symbol)
            if not expiry_dates: continue
            
            nearest_expiry = expiry_dates[0]
            url = f"https://www.nseindia.com/api/option-chain-v3?type=Equities&symbol={symbol}&expiry={nearest_expiry}"
            
            try:
                data = _playwright_get(url)
            except Exception:
                # Fallback to legacy endpoint
                url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
                data = _playwright_get(url)

            current_stock_value = data['records']['underlyingValue']
            records = data['records']['data']

            oi_data = []
            for record in records:
                ce_data = record.get('CE', {})
                pe_data = record.get('PE', {})
                oi_data.append({
                    'symbol':        symbol,
                    'stock_value':   round(current_stock_value, 2),
                    'expiry_date':   nearest_expiry,
                    'strike_price':  record['strikePrice'],
                    'ce_change_oi':  parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume':     parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp':        parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi':         parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv':         parse_float_value(ce_data.get('impliedVolatility', 0)),
                    'pe_change_oi':  parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume':     parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp':        parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi':         parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv':         parse_float_value(pe_data.get('impliedVolatility', 0)),
                })

            oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
            stock_data[symbol] = {
                'data': oi_data,
                'oi_pcr': oi_pcr,
                'volume_pcr': volume_pcr,
                'weight': TOP_NIFTY_STOCKS[symbol]['weight'],
                'current_price': current_stock_value,
            }
            time.sleep(1) # Prevent rate-limiting
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    return stock_data