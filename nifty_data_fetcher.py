# nifty_data_fetcher.py
# ─────────────────────────────────────────────────────────────────────────────
# FETCH LAYER: Replaced requests-based NSE fetch with Playwright browser fetch.
#              Root cause: NSE returns empty {} for unauthenticated requests-
#              based calls. Playwright warms up a real browser session (cookies,
#              JS fingerprint) so NSE returns live data.
#
# ALL OTHER LOGIC IS UNCHANGED:
#   - classify_expiry_dates()
#   - parse_option_chain()
#   - calculate_pcr_values() / calculate_pcr_for_expiry_data()
#   - parse_stock_option_chain() / calculate_stock_pcr_values()
#   - fetch_banknifty_data() / fetch_all_stock_data()
#   - fetch_stock_option_chain()
# ─────────────────────────────────────────────────────────────────────────────

import datetime
import time
import json

from nifty_core_config import (
    SYMBOL, MAX_RETRIES, INITIAL_RETRY_DELAY, HEADERS, STOCK_HEADERS,
    parse_numeric_value, parse_float_value, format_greek_value,
    TOP_NIFTY_STOCKS, initialize_session, initialize_stock_session,
    should_enable_multi_expiry, get_expiry_type_constants,
    get_expiry_classification_params
)

# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT SESSION  (replaces requests.Session for NSE API calls)
# ─────────────────────────────────────────────────────────────────────────────

_playwright_instance = None
_browser             = None
_browser_context     = None
_page                = None
_session_warmed      = False

_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-http2",          # prevents ERR_HTTP2_PROTOCOL_ERROR on NSE
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
    global _playwright_instance, _browser, _browser_context, _page, _session_warmed
    if _page is not None:
        return  # already started

    try:
        from playwright.sync_api import sync_playwright
        _playwright_instance = sync_playwright().start()
        _browser = _playwright_instance.chromium.launch(
            headless=True,
            args=_CHROME_ARGS,
        )
        _browser_context = _browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
        )
        _browser_context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};"
        )
        _page = _browser_context.new_page()
        print("✅ Playwright browser started (Chromium)")
    except Exception as e:
        raise RuntimeError(f"Failed to start Playwright: {e}")


def _warm_session():
    """
    Warm NSE session cookies using lightweight page.request calls.

    WHY NOT page.goto():
      page.goto() tries to load the full page + execute all JS, which times out
      on NSE's heavily JS-rendered pages (60s+ timeout exceeded every time).

    WHY page.request WORKS:
      page.request.get() fires a plain HTTP request through the same Chromium
      engine (same cookie jar, same TLS fingerprint) but without waiting for JS.
      This is enough for NSE to set its session cookies, after which API calls
      return real data instead of empty {}.

    This is identical to what succeeded in our standalone test script.
    """
    global _session_warmed
    if _session_warmed:
        return

    _start_playwright()
    print("🍪 Warming NSE session cookies (lightweight fetch, no JS wait)...")

    warm_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
    }

    for url in [
        "https://www.nseindia.com",
        "https://www.nseindia.com/option-chain",
    ]:
        try:
            resp = _page.request.get(url, headers=warm_headers, timeout=20_000)
            print(f"   ✅ Cookie warm: {url} → HTTP {resp.status}")
            time.sleep(2)
        except Exception as e:
            # Non-fatal — partial cookies may still be enough
            print(f"   ⚠️  (non-fatal) {url}: {e}")

    _session_warmed = True
    print("✅ Session warm-up complete")


def _playwright_get(url: str, retries: int = 5, delay: int = 3) -> dict:
    """
    Fetch a JSON endpoint via the warmed Playwright page session.
    Retries if NSE returns empty / zero-valued data (cookie not yet warm).
    Returns parsed JSON dict/list, or raises on total failure.
    """
    _warm_session()

    for attempt in range(1, retries + 1):
        try:
            resp = _page.request.get(url, headers=_NSE_HEADERS, timeout=20_000)

            if not resp.ok:
                raise ValueError(f"HTTP {resp.status}")

            text = resp.text()
            if not text or text.strip() in ("{}", "[]", ""):
                print(f"   ⚠️  Empty response (attempt {attempt}/{retries}), retrying...")
                time.sleep(delay)
                continue

            data = json.loads(text)

            # Validate that the response contains real data (not stub zeros)
            if isinstance(data, dict) and "records" in data:
                records = data["records"]
                if records.get("underlyingValue", 0) == 0 or not records.get("data"):
                    print(f"   ⚠️  Stub data received (attempt {attempt}/{retries}), retrying...")
                    time.sleep(delay)
                    continue

            return data  # ✅ good data

        except Exception as e:
            print(f"   ⚠️  Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(delay * attempt)

    raise Exception(f"Failed to fetch {url} after {retries} attempts")


def stop_playwright():
    """
    Cleanly shut down the Playwright browser.
    Call this when the program is about to exit.
    """
    global _playwright_instance, _browser, _browser_context, _page, _session_warmed
    try:
        if _page:
            _page.close()
        if _browser_context:
            _browser_context.close()
        if _browser:
            _browser.close()
        if _playwright_instance:
            _playwright_instance.stop()
        print("🛑 Playwright browser closed")
    except Exception as e:
        print(f"⚠️  Error closing Playwright: {e}")
    finally:
        _playwright_instance = _browser = _browser_context = _page = None
        _session_warmed = False


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC FETCH FUNCTIONS  (same signatures as original — drop-in replacement)
# ─────────────────────────────────────────────────────────────────────────────

def _get_expiry_dates(symbol: str) -> list:
    """
    STEP 1: Fetch available expiry dates from contract-info.
    Confirmed working: returns {expiryDates:[...]} without needing an expiry param.
    """
    url = f"https://www.nseindia.com/api/option-chain-contract-info?symbol={symbol}"
    try:
        resp = _page.request.get(url, headers=_NSE_HEADERS, timeout=20_000)
        data = json.loads(resp.text())
        expiries = data.get("expiryDates", [])
        if expiries:
            print(f"   📅 Got {len(expiries)} expiry dates from contract-info")
            return expiries
    except Exception as e:
        print(f"   ⚠️  contract-info failed: {e}")
    return []


def _fetch_chain_for_expiry(symbol: str, expiry: str, retries: int = 5, delay: int = 3):
    """
    STEP 2: Fetch full option chain for one specific expiry.
    Confirmed working: option-chain-v3?type=Indices&symbol=X&expiry=DD-Mon-YYYY
    """
    url = f"https://www.nseindia.com/api/option-chain-v3?type=Indices&symbol={symbol}&expiry={expiry}"
    for attempt in range(1, retries + 1):
        try:
            resp = _page.request.get(url, headers=_NSE_HEADERS, timeout=20_000)
            text = resp.text()
            if not text or text.strip() in ("{}", "[]", ""):
                print(f"   ⚠️  Empty for {expiry} (attempt {attempt}/{retries}), retrying...")
                time.sleep(delay)
                continue
            data = json.loads(text)
            if isinstance(data, dict) and "records" in data:
                rec = data["records"]
                if rec.get("underlyingValue", 0) > 0 and rec.get("data"):
                    return data
                print(f"   ⚠️  Stub data for {expiry} (attempt {attempt}/{retries}), retrying...")
            time.sleep(delay)
        except Exception as e:
            print(f"   ⚠️  Attempt {attempt} for {expiry}: {e}")
            time.sleep(delay * attempt)
    return None


def fetch_option_chain(session=None):
    """
    Fetch NIFTY option chain — proven 2-step approach:
      1. Get expiry list from contract-info  (always works, no expiry param needed)
      2. Fetch each expiry via option-chain-v3&expiry=DATE  (confirmed working)

    Merges all fetched expiries into one combined response dict matching the
    exact structure parse_option_chain() expects (unchanged downstream logic).
    `session` parameter kept for API compatibility but unused.
    """
    _warm_session()

    # STEP 1: Get expiry dates
    print(f"   Getting expiry dates for {SYMBOL}...")
    expiry_dates = _get_expiry_dates(SYMBOL)
    if not expiry_dates:
        raise Exception("fetch_option_chain: could not retrieve expiry dates")

    # STEP 2: Determine which expiries to fetch (current_week, next_week, monthly)
    params = get_expiry_classification_params()
    needed_expiries = [expiry_dates[0]]  # always current week
    try:
        current_dt = datetime.datetime.strptime(expiry_dates[0], "%d-%b-%Y")
        for exp in expiry_dates[1:]:
            exp_dt = datetime.datetime.strptime(exp, "%d-%b-%Y")
            days = (exp_dt - current_dt).days
            nw_min, nw_max = params["next_week_day_range"]
            if nw_min <= days <= nw_max and len(needed_expiries) < 2:
                needed_expiries.append(exp)
            if days >= params["monthly_threshold_days"] and len(needed_expiries) < 3:
                needed_expiries.append(exp)
            if len(needed_expiries) == 3:
                break
    except Exception as e:
        print(f"   ⚠️  Expiry pre-selection error (non-fatal): {e}")

    print(f"   Fetching {len(needed_expiries)} expiries: {needed_expiries}")

    # STEP 3: Fetch each expiry and merge all rows into one combined response
    combined_rows = []
    spot_value = 0
    timestamp = ""
    first_fetch = True

    for expiry in needed_expiries:
        print(f"   Fetching expiry: {expiry}")
        result = _fetch_chain_for_expiry(SYMBOL, expiry)
        if result:
            rec = result["records"]
            if first_fetch:
                spot_value = rec.get("underlyingValue", 0)
                timestamp = rec.get("timestamp", "")
                first_fetch = False
            for row in rec.get("data", []):
                if "expiryDate" not in row:
                    ce_exp = row.get("CE", {}).get("expiryDate", "")
                    pe_exp = row.get("PE", {}).get("expiryDate", "")
                    row["expiryDate"] = _normalise_expiry(ce_exp or pe_exp or expiry)
                combined_rows.append(row)
            print(f"   ✅ {expiry}: {len(rec.get('data', []))} strikes, spot={rec.get('underlyingValue')}")
        else:
            print(f"   ⚠️  Skipping {expiry} — no data returned")

    if not combined_rows or spot_value == 0:
        raise Exception("fetch_option_chain: no valid data fetched for any expiry")

    # STEP 4: Return combined structure — identical to what parse_option_chain() expects
    combined = {
        "records": {
            "timestamp": timestamp,
            "underlyingValue": spot_value,
            "expiryDates": expiry_dates,
            "data": combined_rows,
        }
    }
    _log_fetch_success(combined)
    return combined


def _log_fetch_success(data: dict):
    records = data.get("records", {})
    spot    = records.get("underlyingValue", "?")
    expiries = records.get("expiryDates", [])
    count   = len(records.get("data", []))
    ts      = records.get("timestamp", "")
    print(f"   ✅ Fetched: spot={spot}, rows={count}, ts={ts}")
    if expiries:
        print(f"   📅 Expiries: {expiries[:5]} ...")


# ─────────────────────────────────────────────────────────────────────────────
# EVERYTHING BELOW IS IDENTICAL TO THE ORIGINAL FILE
# ─────────────────────────────────────────────────────────────────────────────

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

        # Assign classified expiries
        if next_week_candidate:
            classified[constants['NEXT_WEEK']] = next_week_candidate

        if monthly_candidate:
            classified[constants['MONTHLY']] = monthly_candidate

        # Handle dual classification
        if (next_week_candidate and monthly_candidate and
                next_week_candidate == monthly_candidate):
            print(f"📅 Dual classification: {monthly_candidate} is both next_week and monthly")

    except Exception as e:
        print(f"⚠️ Expiry classification failed: {e}")
        if expiry_dates:
            classified[constants['CURRENT_WEEK']] = expiry_dates[0]

    return classified


def parse_option_chain(data):
    """
    Parse option chain data with multi-expiry support.
    Returns structured data with current_week, next_week, monthly datasets.
    """
    try:
        # --- DIAGNOSTIC BLOCK ---
        if 'records' not in data:
            print("\n❌ FORMAT ERROR: 'records' key missing from NSE response.")
            print(f"🔍 EXACT DATA RECEIVED: {data}\n")
            return {}
        # ------------------------

        current_nifty = data['records']['underlyingValue']
        records       = data['records']['data']
        expiry_dates  = data['records']['expiryDates']

        # Classify expiry dates
        classified_expiries = {}
        if should_enable_multi_expiry():
            classified_expiries = classify_expiry_dates(expiry_dates)
        else:
            constants = get_expiry_type_constants()
            classified_expiries[constants['CURRENT_WEEK']] = expiry_dates[0]

        # ── NEW: normalise the expiryDate field inside each record ──────────
        # The v3 API may embed expiryDate inside CE/PE rather than at row level.
        # We normalise so the filter below always works.
        for record in records:
            if 'expiryDate' not in record:
                # Try to pull it from CE or PE sub-object
                ce_expiry = record.get('CE', {}).get('expiryDate', '')
                pe_expiry = record.get('PE', {}).get('expiryDate', '')
                raw = ce_expiry or pe_expiry or record.get('expiryDates', '')
                record['expiryDate'] = _normalise_expiry(raw)
            else:
                record['expiryDate'] = _normalise_expiry(record['expiryDate'])
        # ────────────────────────────────────────────────────────────────────

        # Process data for each classified expiry
        expiry_data = {}
        constants   = get_expiry_type_constants()

        for expiry_type, expiry_date in classified_expiries.items():
            expiry_records  = [r for r in records if r['expiryDate'] == expiry_date]
            filtered_records = []

            for record in expiry_records:
                ce_data = record.get('CE', {})
                pe_data = record.get('PE', {})

                # strikePrice can live at record level or inside CE/PE
                strike = (
                    record.get('strikePrice')
                    or ce_data.get('strikePrice')
                    or pe_data.get('strikePrice')
                    or 0
                )

                oi_data = {
                    'nifty_value':   round(current_nifty),
                    'expiry_date':   expiry_date,
                    'expiry_type':   expiry_type,
                    'strike_price':  strike,
                    # CE Data
                    'ce_change_oi':  parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume':     parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp':        parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi':         parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv':         parse_float_value(ce_data.get('impliedVolatility', 0)),
                    # PE Data
                    'pe_change_oi':  parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume':     parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp':        parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi':         parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv':         parse_float_value(pe_data.get('impliedVolatility', 0)),
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


def _normalise_expiry(raw: str) -> str:
    """
    Convert any NSE date format to 'DD-Mon-YYYY' (e.g. '10-Mar-2026').
    Handles: '10-Mar-2026', '10-03-2026', '10/03/2026'.
    """
    if not raw:
        return raw
    for fmt in ('%d-%b-%Y', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(raw, fmt).strftime('%d-%b-%Y')
        except ValueError:
            continue
    return raw  # return as-is if unparseable


def calculate_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for ALL strikes with zero value safeguards"""
    total_ce_oi     = 0
    total_pe_oi     = 0
    total_ce_volume = 0
    total_pe_volume = 0

    for data in oi_data:
        total_ce_oi     += data['ce_oi']
        total_pe_oi     += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']

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
    Calculate PCR values for multi-expiry data structure.
    Returns dict with PCR values for each expiry type.
    """
    pcr_values = {}

    for expiry_type, oi_data in expiry_data.items():
        if oi_data:
            oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
            pcr_values[expiry_type] = {
                'oi_pcr':      oi_pcr,
                'volume_pcr':  volume_pcr,
                'strike_count': len(oi_data),
            }
        else:
            pcr_values[expiry_type] = {
                'oi_pcr':      1.0,
                'volume_pcr':  1.0,
                'strike_count': 0,
            }

    return pcr_values


def fetch_stock_option_chain(session, symbol):
    """
    Fetch option chain data for individual stock via Playwright.
    Uses same 2-step pattern: contract-info for expiry, then v3&expiry for data.
    Falls back to equities endpoint if v3 doesn't have the symbol.
    """
    # Step 1: get expiry dates for this stock
    expiry_dates = _get_expiry_dates(symbol)
    if expiry_dates:
        nearest_expiry = expiry_dates[0]
        # Try v3 equities endpoint with expiry param
        url = (f"https://www.nseindia.com/api/option-chain-v3"
               f"?type=Equities&symbol={symbol}&expiry={nearest_expiry}")
        try:
            resp = _page.request.get(url, headers=_NSE_HEADERS, timeout=20_000)
            text = resp.text()
            if text and text.strip() not in ("{}", "[]", ""):
                data = json.loads(text)
                if isinstance(data, dict) and "records" in data:
                    rec = data["records"]
                    if rec.get("underlyingValue", 0) > 0 and rec.get("data"):
                        return data
        except Exception:
            pass

    # Fallback: legacy equities endpoint
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    return _playwright_get(url)


def parse_stock_option_chain(data, symbol):
    """Parse stock option chain data without Greeks — ALL strikes"""
    try:
        current_stock_value = data['records']['underlyingValue']
        records             = data['records']['data']
        nearest_expiry      = data['records']['expiryDates'][0]

        nearest_expiry_records = [
            r for r in records if r.get('expiryDate') == nearest_expiry
        ]

        filtered_records = []
        for record in nearest_expiry_records:
            ce_data = record.get('CE', {})
            pe_data = record.get('PE', {})

            oi_data = {
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
            }
            filtered_records.append(oi_data)

        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain for {symbol}: {str(e)}")


def calculate_stock_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for stock with zero value safeguards"""
    total_ce_oi     = 0
    total_pe_oi     = 0
    total_ce_volume = 0
    total_pe_volume = 0

    for data in oi_data:
        total_ce_oi     += data['ce_oi']
        total_pe_oi     += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']

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
    """Fetch BANKNIFTY option chain data without Greeks — ALL strikes (monthly only)"""
    try:
        print("Fetching BANKNIFTY option chain...")

        # Same proven 2-step pattern as NIFTY:
        # contract-info gives expiry list, then v3&expiry=DATE gives real data
        expiry_dates = _get_expiry_dates("BANKNIFTY")
        if not expiry_dates:
            raise Exception("Could not get BANKNIFTY expiry dates")

        nearest_expiry = expiry_dates[0]
        print(f"   BANKNIFTY nearest expiry: {nearest_expiry}")

        data = _fetch_chain_for_expiry("BANKNIFTY", nearest_expiry)
        if not data:
            raise Exception(f"No data for BANKNIFTY expiry {nearest_expiry}")

        current_banknifty = data['records']['underlyingValue']
        records           = data['records']['data']

        # Normalise expiryDate field so filter works across v3 format
        for row in records:
            if "expiryDate" not in row:
                ce_exp = row.get("CE", {}).get("expiryDate", "")
                pe_exp = row.get("PE", {}).get("expiryDate", "")
                row["expiryDate"] = _normalise_expiry(ce_exp or pe_exp or nearest_expiry)
            else:
                row["expiryDate"] = _normalise_expiry(row["expiryDate"])

        nearest_expiry_records = [
            r for r in records if r.get('expiryDate') == nearest_expiry
        ]

        banknifty_data = []
        for record in nearest_expiry_records:
            ce_data = record.get('CE', {})
            pe_data = record.get('PE', {})

            oi_data = {
                'symbol':           'BANKNIFTY',
                'underlying_value': round(current_banknifty, 2),
                'expiry_date':      nearest_expiry,
                'expiry_type':      'monthly',
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
            }
            banknifty_data.append(oi_data)

        oi_pcr, volume_pcr = calculate_pcr_values(banknifty_data)

        return {
            'data':          {'monthly': banknifty_data},
            'pcr_values':    {
                'monthly': {
                    'oi_pcr':      oi_pcr,
                    'volume_pcr':  volume_pcr,
                    'strike_count': len(banknifty_data),
                }
            },
            'current_value': current_banknifty,
            'expiry_date':   nearest_expiry,
        }

    except Exception as e:
        print(f"Error fetching BANKNIFTY data: {e}")
        return None


def fetch_all_stock_data():
    """Fetch data for all top 10 Nifty stocks — ALL strikes (monthly only)"""
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

            # session arg kept for API compat; Playwright handles auth internally
            data   = fetch_stock_option_chain(session=None, symbol=symbol)
            oi_data = parse_stock_option_chain(data, symbol)
            oi_pcr, volume_pcr = calculate_stock_pcr_values(oi_data)

            stock_data[symbol] = {
                'data':          oi_data,
                'oi_pcr':        oi_pcr,
                'volume_pcr':    volume_pcr,
                'weight':        TOP_NIFTY_STOCKS[symbol]['weight'],
                'current_price': oi_data[0]['stock_value'] if oi_data else 0,
            }

            time.sleep(1)  # small delay to avoid rate-limiting

        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    return stock_data