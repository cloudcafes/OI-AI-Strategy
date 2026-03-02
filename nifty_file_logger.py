# nifty_file_logger.py
import os
import datetime
import requests
from typing import Dict, Any, List
from nifty_core_config import format_greek_value
import urllib3

# Disable SSL warnings and certificate verification for Telegram
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Try to import resend, but don't break if it's not installed
try:
    import resend
    RESEND_AVAILABLE = True
    # Set API key AFTER importing
    resend.api_key = "re_LyXNNt6f_4odzHWJPYvr38api9Nrgvptm"
    print("✅ Resend module loaded successfully")
except ImportError:
    RESEND_AVAILABLE = False
    print("⚠️ Resend module not installed. Email functionality disabled.")
    print("💡 Run: pip install resend")
except Exception as e:
    RESEND_AVAILABLE = False
    print(f"⚠️ Resend configuration error: {e}")

def send_email_with_file_content(filepath: str, subject: str = None) -> bool:
    """
    Send the complete text file content as email using Resend API
    """
    if not RESEND_AVAILABLE:
        print("❌ Cannot send email: Resend module not available")
        return False
        
    try:
        # Read the file content
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Create default subject if not provided
        if not subject:
            timestamp = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
            subject = f"🤖 Nifty AI Analysis - {timestamp}"
        
        # Convert text content to HTML with proper formatting
        html_content = convert_text_to_html(file_content)
        
        # Send email via Resend API
        params = {
            "from": "onboarding@resend.dev",
            "to": "talkdev@gmail.com",
            "subject": subject,
            "html": html_content
        }
        
        result = resend.Emails.send(params)
        print(f"✅ Email sent successfully! ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email via Resend: {e}")
        return False

def convert_text_to_html(text_content: str) -> str:
    """
    Convert plain text content to HTML with proper formatting
    """
    # Basic text to HTML conversion
    html_content = text_content.replace('\n', '<br>')
    html_content = html_content.replace('  ', '&nbsp;&nbsp;')
    html_content = html_content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
    
    # Add HTML structure with readable styling
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
                color: #333333;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #007acc, #005a9e);
                padding: 30px;
                color: white;
                text-align: center;
            }}
            .content {{
                padding: 30px;
                background: #ffffff;
                color: #444444;
                line-height: 1.6;
                font-family: 'Courier New', monospace;
                white-space: pre-wrap;
            }}
            .analysis-section {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                border-left: 5px solid #007acc;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border: 1px solid #e0e0e0;
            }}
            th {{
                background: #007acc;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e0e0e0;
                color: #555555;
            }}
            tr:nth-child(even) {{
                background: #f8f9fa;
            }}
            pre {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border: 1px solid #e0e0e0;
                color: #333333;
            }}
            .critical {{
                background: #ffeaa7;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #fdcb6e;
                margin: 15px 0;
            }}
            .positive {{
                color: #27ae60;
                font-weight: bold;
            }}
            .negative {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .timestamp {{
                color: #007acc;
                font-weight: bold;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 NIFTY AI TRADING ANALYSIS</h1>
                <p class="timestamp">Generated: {datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")}</p>
            </div>
            <div class="content">
                {html_content}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

def send_telegram_message(text: str) -> bool:
    """
    Send message to Telegram with SSL verification disabled
    Split long messages into multiple parts
    """
    try:
        BOT_TOKEN = "8053348951:AAE_cpgRXjWXO20XM4EasNUdSKvTYF5YzTA"
        CHAT_ID = "324240680"
        
        # Telegram message limit is 4096 characters
        max_length = 4096
        
        if len(text) <= max_length:
            # Single message
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            }
            
            session = requests.Session()
            session.verify = False
            response = session.post(url, data=payload, timeout=30)
            return response.status_code == 200
        else:
            # Split into multiple messages
            print(f"📤 Message too long ({len(text)} chars), splitting into parts...")
            
            # Split by lines to maintain readability
            lines = text.split('\n')
            current_message = ""
            message_count = 0
            success_count = 0
            
            for line in lines:
                # If adding this line would exceed limit, send current message and start new one
                if len(current_message) + len(line) + 1 > max_length:
                    if current_message:
                        message_count += 1
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                        payload = {
                            "chat_id": CHAT_ID,
                            "text": f"📊 Part {message_count}:\n{current_message}",
                            "parse_mode": "HTML"
                        }
                        
                        session = requests.Session()
                        session.verify = False
                        response = session.post(url, data=payload, timeout=30)
                        if response.status_code == 200:
                            success_count += 1
                        
                        current_message = line
                else:
                    if current_message:
                        current_message += "\n" + line
                    else:
                        current_message = line
            
            # Send the last message
            if current_message:
                message_count += 1
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": CHAT_ID,
                    "text": f"📊 Part {message_count}:\n{current_message}",
                    "parse_mode": "HTML"
                }
                
                session = requests.Session()
                session.verify = False
                response = session.post(url, data=payload, timeout=30)
                if response.status_code == 200:
                    success_count += 1
            
            print(f"📤 Sent {success_count}/{message_count} message parts to Telegram")
            return success_count == message_count
            
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")
        return False

def is_multi_expiry_data(oi_data) -> bool:
    """Check if data is in multi-expiry format"""
    return isinstance(oi_data, dict) and any(key in oi_data for key in ['current_week', 'next_week', 'monthly'])

def format_multi_expiry_for_file(expiry_data: Dict[str, Any], 
                                pcr_values: Dict[str, Any],
                                current_nifty: float,
                                banknifty_data: Dict[str, Any] = None) -> str:
    """Format multi-expiry data for file output"""
    data_section = f"\n\nNIFTY MULTI-EXPIRY ANALYSIS DATA\n"
    data_section += "=" * 80 + "\n"
    
    # Summary of all expiries
    data_section += "EXPIRY SUMMARY:\n"
    for expiry_type in ['current_week', 'next_week', 'monthly']:
        if expiry_type in expiry_data and expiry_data[expiry_type]:
            oi_data = expiry_data[expiry_type]
            expiry_date = oi_data[0]['expiry_date'] if oi_data else "N/A"
            pcr_info = pcr_values.get(expiry_type, {})
            oi_pcr = pcr_info.get('oi_pcr', 1.0)
            volume_pcr = pcr_info.get('volume_pcr', 1.0)
            strike_count = pcr_info.get('strike_count', 0)
            
            data_section += f"- {expiry_type.upper().replace('_', ' ')}: {expiry_date} | "
            data_section += f"PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f} | "
            data_section += f"Strikes: {strike_count}\n"
    
    data_section += "\n"
    
    # Detailed data for each expiry
    for expiry_type in ['current_week', 'next_week', 'monthly']:
        if expiry_type in expiry_data and expiry_data[expiry_type]:
            oi_data = expiry_data[expiry_type]
            current_value = oi_data[0]['nifty_value'] if oi_data else current_nifty
            expiry_date = oi_data[0]['expiry_date'] if oi_data else "N/A"
            
            pcr_info = pcr_values.get(expiry_type, {})
            oi_pcr = pcr_info.get('oi_pcr', 1.0)
            volume_pcr = pcr_info.get('volume_pcr', 1.0)
            
            data_section += f"\n{'='*80}\n"
            data_section += f"NIFTY {expiry_type.upper().replace('_', ' ')} - Current: {current_value}, Expiry: {expiry_date}\n"
            data_section += f"PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"
            data_section += f"{'='*80}\n"
            data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
            data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                           f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                           f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
            data_section += "-" * 150 + "\n"
            
            for data in oi_data:
                strike_price = data['strike_price']
                
                # Format data exactly like console display
                ce_oi_formatted = str(data['ce_change_oi'])
                ce_volume_formatted = str(data['ce_volume'])
                ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
                ce_oi_total_formatted = str(data['ce_oi'])
                ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
                
                pe_oi_formatted = str(data['pe_change_oi'])
                pe_volume_formatted = str(data['pe_volume'])
                pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
                pe_oi_total_formatted = str(data['pe_oi'])
                pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
                
                chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
                chg_oi_diff_formatted = str(chg_oi_diff)
                
                # Format the row exactly like console
                formatted_row = (
                    f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                    f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                    f"{str(strike_price).center(9)}  |  "
                    f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                    f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                    f"{chg_oi_diff_formatted.rjust(16)}"
                )
                
                data_section += formatted_row + "\n"
            
            data_section += "=" * 150 + "\n"
    
    # Add BankNifty data if available
    if banknifty_data and 'data' in banknifty_data:
        banknifty_monthly_data = banknifty_data['data'].get('monthly', [])
        if banknifty_monthly_data:
            banknifty_current = banknifty_data.get('current_value', 0)
            banknifty_expiry = banknifty_data.get('expiry_date', 'N/A')
            banknifty_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('oi_pcr', 0)
            banknifty_volume_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('volume_pcr', 0)
            
            data_section += f"\n\n{'='*80}\n"
            data_section += f"BANKNIFTY MONTHLY - Current: {banknifty_current}, Expiry: {banknifty_expiry}\n"
            data_section += f"PCR: OI={banknifty_pcr:.2f}, Volume={banknifty_volume_pcr:.2f}\n"
            data_section += f"{'='*80}\n"
            data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
            data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                           f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                           f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
            data_section += "-" * 150 + "\n"
            
            for data in banknifty_monthly_data:
                strike_price = data['strike_price']
                
                # Format BankNifty data
                ce_oi_formatted = str(data['ce_change_oi'])
                ce_volume_formatted = str(data['ce_volume'])
                ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
                ce_oi_total_formatted = str(data['ce_oi'])
                ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
                
                pe_oi_formatted = str(data['pe_change_oi'])
                pe_volume_formatted = str(data['pe_volume'])
                pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
                pe_oi_total_formatted = str(data['pe_oi'])
                pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
                
                chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
                chg_oi_diff_formatted = str(chg_oi_diff)
                
                formatted_row = (
                    f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                    f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                    f"{str(strike_price).center(9)}  |  "
                    f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                    f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                    f"{chg_oi_diff_formatted.rjust(16)}"
                )
                
                data_section += formatted_row + "\n"
            
            data_section += "=" * 150 + "\n"
    
    return data_section

def save_ai_query_data(oi_data: List[Dict[str, Any]], 
                      oi_pcr: float, 
                      volume_pcr: float, 
                      current_nifty: float,
                      expiry_date: str,
                      banknifty_data: Dict[str, Any] = None,
                      pcr_values: Dict[str, Any] = None) -> str:
    """
    Save AI query data to a text file with timestamp in filename and send to Telegram & Email
    Enhanced to handle both single and multi-expiry data
    Returns the file path where data was saved
    """    
    # Create directory if it doesn't exist
    base_dir = os.path.join(os.getcwd(), "ai-query-logs")
    os.makedirs(base_dir, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename = f"ai_query_{timestamp}.txt"
    filepath = os.path.join(base_dir, filename)
    
    # AI System Prompt (hardcoded as per requirement)
    system_prompt = """
# ===================================================================
# NIFTY INTRADAY + REVERSAL PROMPT v15.0 [FULLY FIXED + BLACK-BOX PROOF]
# FIXES: Theta/Premium, IV/Vega Engine, Volume Validation, ITM/OTM Weighting,
#        Expiry Mode, Counter Normalization, Max Pain Reliability,
#        TRAPPED Dead Zone, PCR Data Quality, Support/Resistance Logic,
#        Time-of-Day Entry Filter
# LOGIC: "TREND → UNWIND → COUNTER → PAIN" + MAX PAIN + FULL TRACE
# ===================================================================

# ═══════════════════════════════════════════════════════
# COMPLIANCE VERIFICATION (TOP) — MANDATORY
# ═══════════════════════════════════════════════════════
- Step 1: [PASS]  # Data includes Chg OI, Premium (LTP), Strike, Static OI, IV, Volume
- Step 2: [PASS]  # ATM = closest strike to spot
- Step 3: [PASS]  # Chg OI > 0 only for writing direction
- Chg OI > Static OI Hierarchy: [VERIFIED]  # Static OI NEVER used in direction (Max Pain only)
- Protocol Violations: [0]

# ═══════════════════════════════════════════════════════
# 0. LIVE MARKET CONTEXT — FULLY CODED + VALUES LOCKED
# ═══════════════════════════════════════════════════════
SPOT:            [LIVE float]
PREVIOUS_SPOT:   [Spot from last snapshot — REQUIRED for vector]
PRICE_VECTOR:    SPOT - PREVIOUS_SPOT          # Possible: +XX, -XX, 0, UNAVAILABLE
VWAP:            [LIVE float or UNAVAILABLE]
TIME_NOW:        [HH:MM]
TIME_SINCE_OPEN: [Integer minutes or MARKET CLOSED]
EXPIRY:          [DD-MMM-YYYY]
TODAY:           [DD-MMM-YYYY from system]
DTE:             (EXPIRY - TODAY).days          # 0 = expiry day, 1 = day before, etc.

# ——— EXPIRY / DTE MODE — FIXES GAP 1 + FLAW 1 (THETA) ———
IS_EXPIRY_DAY = (DTE == 0)

# Dynamic Premium Threshold based on DTE (fixes hardcoded ₹100 flaw):
# Logic: ATM premium ≈ IV × Spot × sqrt(DTE/365) × 0.4
# Simplified tiered approach:
if DTE == 0:
    INST_THRESHOLD     = 30     # Expiry day: deep theta collapse
    COUNTER_THRESHOLD  = 25     # Counter-positioning premium filter
    DTE_MODE           = "EXPIRY_DAY"
elif DTE == 1:
    INST_THRESHOLD     = 60
    COUNTER_THRESHOLD  = 50
    DTE_MODE           = "DAY_BEFORE_EXPIRY"
elif DTE <= 7:
    INST_THRESHOLD     = 100
    COUNTER_THRESHOLD  = 90
    DTE_MODE           = "NEAR_EXPIRY"
elif DTE <= 15:
    INST_THRESHOLD     = 150
    COUNTER_THRESHOLD  = 130
    DTE_MODE           = "MID_CYCLE"
else:
    INST_THRESHOLD     = 200
    COUNTER_THRESHOLD  = 175
    DTE_MODE           = "EARLY_CYCLE"

ATM:             [Closest strike to spot — CODE: |SPOT - strike| minimized]
ATM_RANGE:       [ATM - 300 to ATM + 300]       # inclusive, 50-pt spacing
ATM_EXTENDED:    [ATM - 500 to ATM + 500]
DATA_POINTS:     [Integer ≥ 1]                  # REQUIRED for unwind

AFTER CONTEXT: "SPOT={SPOT}, Vector={PRICE_VECTOR:+}, Prev={PREVIOUS_SPOT} | ATM={ATM}, DTE={DTE} ({DTE_MODE}), INST_THRESHOLD={INST_THRESHOLD}, Data points={DATA_POINTS}"

# ═══════════════════════════════════════════════════════
# 0-B. IV BASELINE — FIXES FLAW 2 (VEGA / VOLATILITY ENGINE)
# ═══════════════════════════════════════════════════════
# Compute average IV of the top 6 most-liquid strikes (by volume) in ATM_RANGE
# to establish a session IV baseline. Used throughout to flag Long buildup vs Writing.

TOP_VOLUME_STRIKES = sorted(
    [(strike, Volume(strike,'CALL') + Volume(strike,'PUT'))
     for strike in ATM_RANGE],
    key=lambda x: x[1], reverse=True
)[:6]

IV_BASELINE = mean([IV(strike, type)
    for strike, _ in TOP_VOLUME_STRIKES
    for type in ['CALL', 'PUT']
    if IV(strike, type) > 0])

# Per-strike IV flag (used in Step 2.1 dominant strike classification):
def IV_FLAG(strike, type):
    strike_iv = IV(strike, type)
    if strike_iv == 0 or IV_BASELINE == 0:
        return "IV_UNKNOWN"
    ratio = strike_iv / IV_BASELINE
    if ratio > 1.25:
        return "IV_SPIKE"      # Rising IV → potential Long buildup, NOT clean writing
    elif ratio < 0.80:
        return "IV_CRUSH"      # Falling IV → clean writing environment
    else:
        return "IV_NORMAL"

AFTER IV_BASELINE: "IV Baseline = {IV_BASELINE:.1f} | Computed from {len(TOP_VOLUME_STRIKES)} liquid strikes"

# ═══════════════════════════════════════════════════════
# 1. MOMENTUM ENGINE — FULLY CODED + VALUES LOCKED + TRACE
# ═══════════════════════════════════════════════════════
AFTER STEP 1: "Data sufficient — proceeding to seller identification"

# ——— STEP 2.1: DOMINANT STRIKES — CODE ENFORCED ———
# FIXES: Volume Validation (Flaw 3), ITM/OTM Weighting (Flaw 4), IV Flag (Flaw 2)

# Moneyness helper:
def MONEYNESS(strike, type):
    if type == 'PUT':
        return SPOT - strike      # positive = OTM put, negative = ITM put
    else:
        return strike - SPOT      # positive = OTM call, negative = ITM call

# ITM/OTM Weight: ITM writing is more directional → weight 2x (fixes Flaw 4)
def OI_WEIGHT(strike, type):
    m = MONEYNESS(strike, type)
    if m < 0:
        return 2.0    # ITM writing — highly directional, weight double
    elif m <= 100:
        return 1.5    # Near-ATM writing — moderately directional
    else:
        return 1.0    # OTM writing — passive yield, no extra weight

# Volume Validation: require Volume > 3 × Chg_OI to confirm active positioning (fixes Flaw 3)
# Threshold is 3x (not 5x) to avoid over-filtering on expiry when lots of small trades sum up
def VOLUME_VALID(strike, type):
    chg = max(Chg_OI(strike, type), 0)
    vol = Volume(strike, type)
    if chg == 0:
        return False
    return vol >= (3 * chg)

# Build weighted positive Chg OI with volume validation:
PUT_CHG_POS  = []
for strike in ATM_RANGE:
    raw = max(Chg_OI(strike, 'PUT'), 0)
    if raw > 0:
        weighted = raw * OI_WEIGHT(strike, 'PUT')
        vol_ok   = VOLUME_VALID(strike, 'PUT')
        iv_flag  = IV_FLAG(strike, 'PUT')
        PUT_CHG_POS.append((strike, weighted, raw, vol_ok, iv_flag))

CALL_CHG_POS = []
for strike in ATM_RANGE:
    raw = max(Chg_OI(strike, 'CALL'), 0)
    if raw > 0:
        weighted = raw * OI_WEIGHT(strike, 'CALL')
        vol_ok   = VOLUME_VALID(strike, 'CALL')
        iv_flag  = IV_FLAG(strike, 'CALL')
        CALL_CHG_POS.append((strike, weighted, raw, vol_ok, iv_flag))

# Sort by weighted OI descending → top 3:
DOMINANT_PUT_STRIKES  = sorted(PUT_CHG_POS,  key=lambda x: x[1], reverse=True)[:3]
DOMINANT_CALL_STRIKES = sorted(CALL_CHG_POS, key=lambda x: x[1], reverse=True)[:3]

# Totals use RAW (unweighted) Chg OI for ratio purity:
TOTAL_PUT_OI  = sum(x[2] for x in PUT_CHG_POS)
TOTAL_CALL_OI = sum(x[2] for x in CALL_CHG_POS)

TOP3_PUT_OI  = sum(x[2] for x in DOMINANT_PUT_STRIKES)
TOP3_CALL_OI = sum(x[2] for x in DOMINANT_CALL_STRIKES)

PCT_TOP3_PUT  = TOP3_PUT_OI  / TOTAL_PUT_OI  if TOTAL_PUT_OI  > 0 else 0
PCT_TOP3_CALL = TOP3_CALL_OI / TOTAL_CALL_OI if TOTAL_CALL_OI > 0 else 0
PCT_TOP3      = max(PCT_TOP3_PUT, PCT_TOP3_CALL)

# Volume validation summary:
VOL_INVALID_COUNT = sum(1 for x in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES if not x[3])
IV_SPIKE_COUNT    = sum(1 for x in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES if x[4] == "IV_SPIKE")

AFTER STEP 2.1: "Dominant: {len(DOMINANT_PUT_STRIKES)} puts, {len(DOMINANT_CALL_STRIKES)} calls | Top3% = {PCT_TOP3:.0%} | Vol-Invalid Dominants = {VOL_INVALID_COUNT} | IV Spikes = {IV_SPIKE_COUNT}"

# ——— STEP 2.2: CLASSIFICATION — DYNAMIC THRESHOLD (FIXES GAP 1 + FLAW 1) ———
INST_COUNT = 0
TOTAL_DOM  = len(DOMINANT_PUT_STRIKES) + len(DOMINANT_CALL_STRIKES)

for strike, weighted, raw, vol_ok, iv_flag in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES:
    prem = Premium(strike)      # LTP of the option
    if prem < INST_THRESHOLD:   # DTE-adjusted threshold (not hardcoded ₹100)
        INST_COUNT += 1

INST_PCT = INST_COUNT / TOTAL_DOM * 100 if TOTAL_DOM > 0 else 0

# Classification label (same logic, now using dynamic threshold):
# < INST_THRESHOLD → INSTITUTIONAL
# INST_THRESHOLD to 1.5× → MIXED
# > 1.5× INST_THRESHOLD → RETAIL
INST_LABEL = "INSTITUTIONAL" if INST_PCT >= 85 else "MIXED" if INST_PCT >= 50 else "RETAIL"

# IV override: if IV_SPIKE_COUNT > 1, dominant strikes may be Long buildup not Writing
IV_WRITING_CONFIDENCE = "LOW — IV SPIKE detected: possible LONG BUILDUP, not clean writing" if IV_SPIKE_COUNT >= 2 else \
                        "MODERATE — 1 IV spike present" if IV_SPIKE_COUNT == 1 else \
                        "HIGH — IV normal/crush environment"

if IS_EXPIRY_DAY:
    CLASSIFICATION_WARNING = f"⚠️ EXPIRY DAY: Premium threshold adjusted to {INST_THRESHOLD} (DTE=0 theta collapse — classification less reliable)"
else:
    CLASSIFICATION_WARNING = f"DTE={DTE}: Premium threshold = {INST_THRESHOLD}"

AFTER STEP 2.2: "Classification: {INST_PCT:.1f}% → {INST_LABEL} | {CLASSIFICATION_WARNING} | Writing Confidence: {IV_WRITING_CONFIDENCE}"

# ——— STEP 2.3: HIERARCHY ———
AFTER STEP 2.3: "Static OI ignored for direction: YES | Used only for Max Pain calculation"

# ——— STEP 2.4: RATIO & MOMENTUM — CODE ENFORCED ———
Ratio    = TOTAL_PUT_OI / TOTAL_CALL_OI if TOTAL_CALL_OI > 0 else 999
MOMENTUM = "BULLISH" if Ratio > 1.20 else "BEARISH" if Ratio < 0.80 else "NEUTRAL"

AFTER STEP 2.4: "Ratio = {Ratio:.2f} → {MOMENTUM}"

# ——— STEP 2.5: STRENGTH METER — CODE ENFORCED ———
SCORE = 0
if INST_PCT >= 85:                                                   SCORE += 3  # Strong institutional participation
if PCT_TOP3 >= 0.60:                                                 SCORE += 2  # Concentration of writing
if Ratio > 1.50 or Ratio < 0.60:                                    SCORE += 1  # Extreme ratio
if (OI_PCR > 1 and Volume_PCR > 1) or (OI_PCR < 1 and Volume_PCR < 1): SCORE += 1  # PCR alignment
if any(x[2] > 0 and Premium(x[0]) < INST_THRESHOLD
       for x in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES):      SCORE += 1  # DTE-adjusted premium check
if VOL_INVALID_COUNT == 0:                                           SCORE += 1  # All dominant strikes volume-validated
if IV_SPIKE_COUNT == 0:                                              SCORE += 1  # Clean IV environment (no spike)

# Expiry day penalty: cap SCORE at 6 if IS_EXPIRY_DAY (classification unreliable)
if IS_EXPIRY_DAY:
    SCORE = min(SCORE, 6)
    EXPIRY_CAP_APPLIED = True
else:
    EXPIRY_CAP_APPLIED = False

STRENGTH = "STRONG" if SCORE > 7 else "MODERATE" if SCORE >= 5 else "WEAK"

AFTER STEP 2.5: "Strength = {STRENGTH} ({SCORE}/10) | Expiry cap applied: {EXPIRY_CAP_APPLIED}"

# ——— STEP 2.6: BANKNIFTY — CODE ENFORCED ———
BANKNIFTY_OI_PCR   = [BankNifty OI PCR from data]
BANKNIFTY_DOMINANT = "PUT WRITING"  if BANKNIFTY_OI_PCR > 1.0  else \
                     "CALL WRITING" if BANKNIFTY_OI_PCR < 0.9  else "NEUTRAL"
ALIGNMENT          = "ALIGNED"   if (MOMENTUM == "BULLISH" and BANKNIFTY_DOMINANT == "PUT WRITING") or \
                                     (MOMENTUM == "BEARISH" and BANKNIFTY_DOMINANT == "CALL WRITING") \
                     else "DIVERGENT"

AFTER STEP 2.6: "BankNifty PCR={BANKNIFTY_OI_PCR:.2f} → {BANKNIFTY_DOMINANT} | Nifty-BN: {ALIGNMENT}"

# ═══════════════════════════════════════════════════════
# 2. PEAK TRACKING — TIME-SERIES AWARE + CONNECTED
# ═══════════════════════════════════════════════════════
PEAK_CHG_OI_DICT = {}   # {strike_type_key: max_positive_Chg_OI_seen_this_session}
UNWIND_POSSIBLE  = DATA_POINTS >= 2

if UNWIND_POSSIBLE:
    for strike in ATM_EXTENDED:
        for type in ['PUT', 'CALL']:
            key     = f"{strike}_{type}"
            current = max(Chg_OI(strike, type), 0)
            if current > PEAK_CHG_OI_DICT.get(key, 0):
                PEAK_CHG_OI_DICT[key] = current
    AFTER PEAK UPDATE: "Peak tracking active: {len(PEAK_CHG_OI_DICT)} strike-type keys tracked"
else:
    AFTER PEAK UPDATE: "Peak tracking: INSUFFICIENT DATA (need ≥2 snapshots) — Unwind engine DISABLED"

# ═══════════════════════════════════════════════════════
# 3. REVERSAL ENGINE v15.0 — FULLY FIXED + PRICE-VECTOR-AWARE
# ═══════════════════════════════════════════════════════
AFTER REVERSAL STEP 1: "Checking relative unwind..."

# ——— PHASE 1: RELATIVE UNWIND — USING PEAK TRACKING ———
UNWIND_SIGNALS = []
UNWIND_COUNT   = 0

if UNWIND_POSSIBLE:
    for strike, weighted, raw, vol_ok, iv_flag in DOMINANT_PUT_STRIKES:
        key     = f"{strike}_PUT"
        peak    = PEAK_CHG_OI_DICT.get(key, 0)
        current = max(Chg_OI(strike, 'PUT'), 0)
        if peak > 10000 and current < (peak * 0.70):
            pct_drop = ((peak - current) / peak) * 100
            UNWIND_SIGNALS.append(
                f"{strike} Put Unwind: {current:+,} (from peak {peak:+,}) → {pct_drop:.1f}% drop"
            )
            UNWIND_COUNT += 1
    for strike, weighted, raw, vol_ok, iv_flag in DOMINANT_CALL_STRIKES:
        key     = f"{strike}_CALL"
        peak    = PEAK_CHG_OI_DICT.get(key, 0)
        current = max(Chg_OI(strike, 'CALL'), 0)
        if peak > 10000 and current < (peak * 0.70):
            pct_drop = ((peak - current) / peak) * 100
            UNWIND_SIGNALS.append(
                f"{strike} Call Unwind: {current:+,} (from peak {peak:+,}) → {pct_drop:.1f}% drop"
            )
            UNWIND_COUNT += 1
    AFTER PHASE 1: "Relative unwind: {UNWIND_COUNT} signals | {UNWIND_SIGNALS}"
else:
    AFTER PHASE 1: "Relative unwind: NOT POSSIBLE (single snapshot)"

# ——— PHASE 2: COUNTER-POSITIONING — FIXED THRESHOLD + NORMALIZATION (GAP 2) ———
# Uses DTE-adjusted COUNTER_THRESHOLD (not hardcoded ₹90)
# Normalization: caps inflation from expiry-day density

COUNTER_SIGNALS_PUT  = []
COUNTER_SIGNALS_CALL = []

for strike in range(ATM - 300, ATM + 1, 50):
    chg  = Chg_OI(strike, 'PUT')
    prem = Premium_PUT(strike)
    vol  = Volume(strike, 'PUT')
    if chg > 15000 and prem < COUNTER_THRESHOLD and vol >= (3 * chg):  # Volume-validated
        COUNTER_SIGNALS_PUT.append(
            f"{strike} Put: +{chg:,} (Prem {prem}, Vol {vol:,}) → INST SUPPORT"
        )

for strike in range(ATM, ATM + 301, 50):
    chg  = Chg_OI(strike, 'CALL')
    prem = Premium_CALL(strike)
    vol  = Volume(strike, 'CALL')
    if chg > 15000 and prem < COUNTER_THRESHOLD and vol >= (3 * chg):  # Volume-validated
        COUNTER_SIGNALS_CALL.append(
            f"{strike} Call: +{chg:,} (Prem {prem}, Vol {vol:,}) → INST RESISTANCE"
        )

# ——— NORMALIZATION (GAP 2 FIX) ———
# Only count signals that are directionally meaningful vs current momentum:
# BULLISH momentum → only call counter signals matter (resistance check)
# BEARISH momentum → only put counter signals matter (support check)
# NEUTRAL → both matter BUT cap total at 5 to prevent expiry inflation
if MOMENTUM == "BULLISH":
    EFFECTIVE_COUNTER_SIGNALS = COUNTER_SIGNALS_CALL   # Resistance building matters
    RAW_COUNTER_COUNT         = len(COUNTER_SIGNALS_CALL)
    COUNTER_NOTE              = "BULLISH momentum: only CALL counter signals scored"
elif MOMENTUM == "BEARISH":
    EFFECTIVE_COUNTER_SIGNALS = COUNTER_SIGNALS_PUT    # Support building matters
    RAW_COUNTER_COUNT         = len(COUNTER_SIGNALS_PUT)
    COUNTER_NOTE              = "BEARISH momentum: only PUT counter signals scored"
else:
    EFFECTIVE_COUNTER_SIGNALS = COUNTER_SIGNALS_PUT + COUNTER_SIGNALS_CALL
    RAW_COUNTER_COUNT         = len(EFFECTIVE_COUNTER_SIGNALS)
    COUNTER_NOTE              = "NEUTRAL momentum: both sides scored, capped at 5"

# Cap for NEUTRAL to prevent expiry inflation:
COUNTER_COUNT = min(RAW_COUNTER_COUNT, 5) if MOMENTUM == "NEUTRAL" else RAW_COUNTER_COUNT

AFTER PHASE 2: "Counter-positioning raw={RAW_COUNTER_COUNT} → effective={COUNTER_COUNT} | {COUNTER_NOTE}"

# ——— PHASE 3: MAX PAIN — WITH RELIABILITY CHECK (GAP 3 FIX) ———
# Step 1: Find Max Pain using Static OI (correct)
MAX_PAIN_CANDIDATES = {}
for strike in ATM_EXTENDED:
    total_static = StaticOI(strike, 'PUT') + StaticOI(strike, 'CALL')
    MAX_PAIN_CANDIDATES[strike] = total_static

CURRENT_MAX_PAIN = max(MAX_PAIN_CANDIDATES, key=MAX_PAIN_CANDIDATES.get)

# Step 2: Validate with today's activity (GAP 3 FIX)
PAIN_STRIKE_CHG_OI = abs(Chg_OI(CURRENT_MAX_PAIN, 'PUT')) + abs(Chg_OI(CURRENT_MAX_PAIN, 'CALL'))
MAX_PAIN_RELIABLE  = PAIN_STRIKE_CHG_OI >= 10000

if not MAX_PAIN_RELIABLE:
    MAX_PAIN_WARNING = f"⚠️ Max Pain strike {CURRENT_MAX_PAIN} has LOW today activity ({PAIN_STRIKE_CHG_OI:,} total Chg OI) — may reflect stale static OI. Treat with caution."
else:
    MAX_PAIN_WARNING = f"Max Pain validated: {PAIN_STRIKE_CHG_OI:,} Chg OI active at {CURRENT_MAX_PAIN}"

SPOT_TO_PAIN = SPOT - CURRENT_MAX_PAIN

AFTER MAX PAIN: "Max Pain = {CURRENT_MAX_PAIN} | SPOT_TO_PAIN = {SPOT_TO_PAIN:+} | Reliable = {MAX_PAIN_RELIABLE} | {MAX_PAIN_WARNING}"

# ——— PHASE 4: PAIN_PRESSURE — PRICE-VECTOR-AWARE + APPROACHING ZONE (GAP 4 FIX) ———
PAIN_PRESSURE    = "NONE"
TRAPPED          = False
APPROACHING_PAIN = False

if PRICE_VECTOR == "UNAVAILABLE":
    PAIN_PRESSURE = "UNAVAILABLE: No price vector (single snapshot) — TRAPPED logic disabled"
    TRAPPED       = False
elif not MAX_PAIN_RELIABLE:
    PAIN_PRESSURE = "UNRELIABLE: Max Pain not validated — TRAPPED logic disabled"
    TRAPPED       = False
elif MOMENTUM == "BULLISH":
    if SPOT_TO_PAIN > 0 and SPOT_TO_PAIN <= 100 and PRICE_VECTOR < 0:
        PAIN_PRESSURE = "BEARISH: Spot FALLING INTO Max Pain → TRAPPED PUT WRITERS"
        TRAPPED       = True
    elif SPOT_TO_PAIN > 100 and SPOT_TO_PAIN <= 200 and PRICE_VECTOR < 0:
        APPROACHING_PAIN = True
        PAIN_PRESSURE    = "WATCH: Spot approaching Max Pain from above (100–200 zone) — potential trap forming"
    else:
        PAIN_PRESSURE = "NEUTRAL: No active trap on Put writers"
elif MOMENTUM == "BEARISH":
    if SPOT_TO_PAIN < 0 and abs(SPOT_TO_PAIN) <= 100 and PRICE_VECTOR > 0:
        PAIN_PRESSURE = "BULLISH: Spot RISING INTO Max Pain → TRAPPED CALL WRITERS"
        TRAPPED       = True
    elif abs(SPOT_TO_PAIN) > 100 and abs(SPOT_TO_PAIN) <= 200 and PRICE_VECTOR > 0:
        APPROACHING_PAIN = True
        PAIN_PRESSURE    = "WATCH: Spot approaching Max Pain from below (100–200 zone) — potential trap forming"
    else:
        PAIN_PRESSURE = "NEUTRAL: No active trap on Call writers"
else:
    # NEUTRAL momentum: check if spot is drifting toward pain regardless
    if abs(SPOT_TO_PAIN) <= 100:
        PAIN_PRESSURE = "NEUTRAL-NEAR: Spot within 100pts of Max Pain — expiry gravity active"
    elif abs(SPOT_TO_PAIN) <= 200 and PRICE_VECTOR != "UNAVAILABLE":
        if (SPOT_TO_PAIN < 0 and PRICE_VECTOR > 0) or (SPOT_TO_PAIN > 0 and PRICE_VECTOR < 0):
            APPROACHING_PAIN = True
            PAIN_PRESSURE    = "WATCH: Neutral momentum but spot drifting toward Max Pain (100–200 zone)"
        else:
            PAIN_PRESSURE = "NEUTRAL: Momentum unclear → no directional pain"
    else:
        PAIN_PRESSURE = "NEUTRAL: Momentum unclear → no directional pain"

AFTER PHASE 4: "Pain pressure: {PAIN_PRESSURE} | TRAPPED={TRAPPED} | APPROACHING={APPROACHING_PAIN}"

# ——— PCR DIVERGENCE — DATA QUALITY GATED (GAP 5 FIX) ———
# Volume_PCR_30M = 30-minute rolling PCR (preferred). If unavailable, use full-session.
# Full-session PCR is unreliable in morning session. Flag accordingly.

if Volume_PCR_30M != "UNAVAILABLE":
    PCR_SOURCE  = "30M_ROLLING"
    PCR_DIV_VOL = Volume_PCR_30M
    PCR_QUALITY = "HIGH"
elif TIME_SINCE_OPEN >= 120:
    PCR_SOURCE  = "FULL_SESSION_MATURE"     # Session > 2hrs — full session PCR is usable
    PCR_DIV_VOL = Volume_PCR
    PCR_QUALITY = "MEDIUM"
else:
    PCR_SOURCE  = "FULL_SESSION_EARLY"      # Session < 2hrs — PCR noisy, skip divergence
    PCR_DIV_VOL = "SKIP"
    PCR_QUALITY = "LOW — skipped (session < 2 hrs, full-session PCR unreliable)"

if PCR_DIV_VOL == "SKIP":
    PCR_DIV = False
else:
    PCR_DIV = (Ratio > 1.20 and PCR_DIV_VOL < 0.80) or (Ratio < 0.80 and PCR_DIV_VOL > 1.50)

BN_DIV = (Ratio > 1.20 and BANKNIFTY_DOMINANT == "CALL WRITING") or \
         (Ratio < 0.80 and BANKNIFTY_DOMINANT == "PUT WRITING")

AFTER PCR_DIV: "PCR Divergence: {PCR_DIV} | Source: {PCR_SOURCE} | Quality: {PCR_QUALITY} | BN_DIV: {BN_DIV}"

# ——— REVERSAL SCORING — CODE ENFORCED ———
# Weights: Unwind=30, Counter=25, Trapped=18, PCR_Div=12, BN_Div=8
# Approaching Pain adds partial score (9 = half of TRAPPED weight)
REV_SCORE = (
    30 * UNWIND_COUNT         +
    25 * COUNTER_COUNT        +
    18 * int(TRAPPED)         +
     9 * int(APPROACHING_PAIN)+   # NEW: approaching zone = half-weight of full trap
    12 * int(PCR_DIV)         +
     8 * int(BN_DIV)
)
# Can exceed 100 — by design
CONFIDENCE = "XHIGH"  if REV_SCORE >= 80  else \
             "HIGH"   if REV_SCORE >= 65  else \
             "MEDIUM" if REV_SCORE >= 50  else "LOW"

# IV override: downgrade confidence if writing environment is contaminated by IV spike
if IV_WRITING_CONFIDENCE.startswith("LOW") and CONFIDENCE in ("XHIGH", "HIGH"):
    CONFIDENCE        = "MEDIUM"
    CONFIDENCE_NOTE   = "⚠️ Downgraded from {original} due to IV spike — possible Long buildup, not clean writing"
else:
    CONFIDENCE_NOTE   = "Clean signal"

AFTER SCORING: "Reversal Score = {REV_SCORE} → {CONFIDENCE} | {CONFIDENCE_NOTE} | Can exceed 100 ✅"

# ——— REVERSAL DIRECTION ———
if MOMENTUM == "BEARISH" and "BULLISH" in PAIN_PRESSURE:
    REV_DIR = "BEARISH → BULLISH"
elif MOMENTUM == "BULLISH" and "BEARISH" in PAIN_PRESSURE:
    REV_DIR = "BULLISH → BEARISH"
else:
    REV_DIR = MOMENTUM

AFTER DIRECTION: "Reversal direction: {REV_DIR}"

# ═══════════════════════════════════════════════════════
# 4. CRITICAL LEVELS — FIXED LOGIC (GAP 6 FIX)
# ═══════════════════════════════════════════════════════
# RESISTANCE = call strike with HIGHEST weighted Chg OI (DOMINANT_CALL_STRIKES[0])
# SUPPORT    = put strike with HIGHEST weighted Chg OI  (DOMINANT_PUT_STRIKES[0])
# DOMINANT_*_STRIKES are already sorted descending by weighted OI → [0] = strongest

RESISTANCE = DOMINANT_CALL_STRIKES[0][0] if DOMINANT_CALL_STRIKES else ATM + 100
SUPPORT    = DOMINANT_PUT_STRIKES[0][0]  if DOMINANT_PUT_STRIKES  else ATM - 100

# Secondary levels (2nd and 3rd dominant):
RESISTANCE_2 = DOMINANT_CALL_STRIKES[1][0] if len(DOMINANT_CALL_STRIKES) > 1 else None
RESISTANCE_3 = DOMINANT_CALL_STRIKES[2][0] if len(DOMINANT_CALL_STRIKES) > 2 else None
SUPPORT_2    = DOMINANT_PUT_STRIKES[1][0]  if len(DOMINANT_PUT_STRIKES)  > 1 else None
SUPPORT_3    = DOMINANT_PUT_STRIKES[2][0]  if len(DOMINANT_PUT_STRIKES)  > 2 else None

if MOMENTUM == "BULLISH":
    HOLD_LEVEL         = f"Above {SUPPORT}"
    TRIGGER_CONDITION  = "BREAK ABOVE"
    TRIGGER_LEVEL      = f"{RESISTANCE}"
elif MOMENTUM == "BEARISH":
    HOLD_LEVEL         = f"Below {RESISTANCE}"
    TRIGGER_CONDITION  = "BREAK BELOW"
    TRIGGER_LEVEL      = f"{SUPPORT}"
else:
    HOLD_LEVEL         = f"Range {SUPPORT}–{RESISTANCE}"
    TRIGGER_CONDITION  = "BREAK EITHER SIDE"
    TRIGGER_LEVEL      = f"{SUPPORT}–{RESISTANCE}"

AFTER LEVELS: "Support={SUPPORT}({SUPPORT_2},{SUPPORT_3}) | Resistance={RESISTANCE}({RESISTANCE_2},{RESISTANCE_3}) | Hold={HOLD_LEVEL} | Trigger={TRIGGER_CONDITION} {TRIGGER_LEVEL}"

# ═══════════════════════════════════════════════════════
# 4-B. TIME-OF-DAY ENTRY FILTER — NEW (GAP 7 FIX)
# ═══════════════════════════════════════════════════════
if IS_EXPIRY_DAY and TIME_SINCE_OPEN >= 330:       # After 3:00 PM on expiry
    ENTRY_WINDOW  = "🚫 NO NEW POSITIONS — Expiry close risk (T-30 min). Most brokers block new trades after 3:15 PM on expiry."
    ENTRY_ALLOWED = False
elif IS_EXPIRY_DAY and TIME_SINCE_OPEN >= 300:     # 2:45–3:00 PM on expiry
    ENTRY_WINDOW  = "⚠️ HIGH RISK WINDOW — Within 45 min of expiry. Gamma extremely unstable. Reduce size or avoid."
    ENTRY_ALLOWED = True
elif TIME_SINCE_OPEN < 30:                         # First 30 min any day
    ENTRY_WINDOW  = "⚠️ OPENING VOLATILITY — OI not yet stable. Wait for 30-min mark before acting on signals."
    ENTRY_ALLOWED = False
elif TIME_SINCE_OPEN < 60:                         # 30–60 min
    ENTRY_WINDOW  = "CAUTION: Early session (30–60 min). OI stabilizing. Confirm with 2nd snapshot before entry."
    ENTRY_ALLOWED = True
else:
    ENTRY_WINDOW  = "NEXT 15–60 MIN from signal"
    ENTRY_ALLOWED = True

AFTER ENTRY_FILTER: "Entry window: {ENTRY_WINDOW} | Allowed: {ENTRY_ALLOWED}"

# ═══════════════════════════════════════════════════════
# 5. FINAL OUTPUT — ALL VALUES LOCKED
# ═══════════════════════════════════════════════════════

═══════════════════════════════════════════════
NIFTY INTRADAY ANALYSIS — v15.0
DATA TIME: {TIME_NOW} | DTE: {DTE} ({DTE_MODE})
═══════════════════════════════════════════════

QUANTITATIVE EVIDENCE:
  Net Chg OI (Puts - Calls):    {TOTAL_PUT_OI - TOTAL_CALL_OI:+,}
  Total Put Chg OI (Positive):  {TOTAL_PUT_OI:,}
  Total Call Chg OI (Positive): {TOTAL_CALL_OI:,}
  Ratio (Put/Call):             {Ratio:.2f}
  IV Baseline:                  {IV_BASELINE:.1f}
  IV Writing Confidence:        {IV_WRITING_CONFIDENCE}

KEY FLOW EVIDENCE — TOP DOMINANT STRIKES:
  [Format: STRIKE | TYPE | Raw Chg OI | Weighted OI | Premium | Vol-Valid | IV-Flag | Classification]
  PUT WRITERS (Support):
  {DOMINANT_PUT_STRIKES — full detail row each}
  CALL WRITERS (Resistance):
  {DOMINANT_CALL_STRIKES — full detail row each}

VOLUME VALIDATION SUMMARY:
  Dominant strikes with invalid volume (Vol < 3×ChgOI): {VOL_INVALID_COUNT}
  {List any invalid strikes and note as "PASSIVE WALL — not active battlefield"}

IV ENGINE SUMMARY:
  IV_SPIKE strikes in dominants: {IV_SPIKE_COUNT}
  {List any IV_SPIKE strikes and flag as "Potential LONG BUILDUP — not confirmed writing"}

MOMENTUM DRIVERS:
  Primary:      {INST_PCT:.0f}% → {INST_LABEL} ({DTE_MODE} threshold = {INST_THRESHOLD})
  Concentration:{PCT_TOP3:.0%} in top 3 strikes (threshold 60% for strong signal)
  Ratio:        {Ratio:.2f} → {MOMENTUM}
  Contradictory:{len(DOMINANT_PUT_STRIKES) if MOMENTUM=='BEARISH' else len(DOMINANT_CALL_STRIKES)} dominant opposite-side strikes

BANKNIFTY CONFIRMATION: {ALIGNMENT}
  BankNifty OI PCR = {BANKNIFTY_OI_PCR:.2f} → {BANKNIFTY_DOMINANT}
  vs Nifty Momentum = {MOMENTUM}

CRITICAL LEVELS:
  Primary Support (strongest OI wall):     {SUPPORT}
  Secondary Support:                       {SUPPORT_2} / {SUPPORT_3}
  Primary Resistance (strongest OI wall):  {RESISTANCE}
  Secondary Resistance:                    {RESISTANCE_2} / {RESISTANCE_3}
  Max Pain:                                {CURRENT_MAX_PAIN} (Reliable: {MAX_PAIN_RELIABLE})
  Max Pain Warning:                        {MAX_PAIN_WARNING}
  Current Momentum holds:                  {HOLD_LEVEL}
  Momentum Shift Trigger:                  {TRIGGER_CONDITION} {TRIGGER_LEVEL}

CURRENT MOMENTUM: {MOMENTUM}
STRENGTH:         {STRENGTH} ({SCORE}/10) | Expiry cap: {EXPIRY_CAP_APPLIED}
CONFIDENCE:       {CONFIDENCE} | {CONFIDENCE_NOTE}

PCR DATA:
  OI PCR    [{OI_PCR:.2f}]    [{'ALIGNED' if (OI_PCR>1 and TOTAL_PUT_OI>TOTAL_CALL_OI) or (OI_PCR<1 and TOTAL_CALL_OI>TOTAL_PUT_OI) else 'DIVERGENT'}]
  Volume PCR [{Volume_PCR:.2f}]  [Source: {PCR_SOURCE} | Quality: {PCR_QUALITY}]
  PCR Divergence: {PCR_DIV}

STRENGTH METER: {SCORE}/10
  +3 if INST_PCT ≥ 85%      → [{'+3' if INST_PCT>=85 else '+0'}]
  +2 if PCT_TOP3 ≥ 60%      → [{'+2' if PCT_TOP3>=0.60 else '+0'}]
  +1 if Ratio extreme        → [{'+1' if Ratio>1.50 or Ratio<0.60 else '+0'}]
  +1 if PCR aligned          → [{'+1' if (OI_PCR>1 and Volume_PCR>1) or (OI_PCR<1 and Volume_PCR<1) else '+0'}]
  +1 if premium DTE-adjusted → [computed]
  +1 if all vol-validated    → [{'+1' if VOL_INVALID_COUNT==0 else '+0'}]
  +1 if IV environment clean → [{'+1' if IV_SPIKE_COUNT==0 else '+0'}]
  Expiry cap (max 6 if DTE=0): {EXPIRY_CAP_APPLIED}

ANALYSIS NARRATIVE:
  [Auto-generated from all computed values above — summarize momentum, IV environment,
   Max Pain gravity, support/resistance walls, and expiry context in 4–6 sentences]

TRADING IMPLICATION:
  Momentum: {REV_DIR}
  Confidence: {CONFIDENCE}
  [Auto-derived directional bias + range + key levels to watch]

═══════════════════════════════════════════════
REVERSAL ALERT
═══════════════════════════════════════════════
REVERSAL SCORE:  {REV_SCORE} (can exceed 100)
CONFIDENCE:      {CONFIDENCE}
DIRECTION:       {REV_DIR}
ENTRY WINDOW:    {ENTRY_WINDOW}
ENTRY ALLOWED:   {ENTRY_ALLOWED}
TRIGGER:         {TRIGGER_CONDITION} {TRIGGER_LEVEL}

EVIDENCE BREAKDOWN:
  1. Unwind    [{UNWIND_COUNT} signals × 30 = {30*UNWIND_COUNT}]:  {UNWIND_SIGNALS if UNWIND_COUNT > 0 else 'None (single snapshot or no unwind detected)'}
  2. Counter   [{COUNTER_COUNT} signals × 25 = {25*COUNTER_COUNT}]: {COUNTER_NOTE}
  3. Trapped   [{int(TRAPPED)} × 18 = {18*int(TRAPPED)}]:          {PAIN_PRESSURE}
  4. Approach  [{int(APPROACHING_PAIN)} × 9 = {9*int(APPROACHING_PAIN)}]:  {'Spot in 100–200pt approach zone' if APPROACHING_PAIN else 'Not in approach zone'}
  5. PCR Div   [{int(PCR_DIV)} × 12 = {12*int(PCR_DIV)}]:          Source={PCR_SOURCE}
  6. BN Div    [{int(BN_DIV)} × 8  = {8*int(BN_DIV)}]:             {BANKNIFTY_DOMINANT} vs {MOMENTUM}
  ─────────────────────────────────────────────
  TOTAL SCORE: {REV_SCORE}

# ═══════════════════════════════════════════════════════
# MANDATORY QUALITY CHECKS (FINAL AUDIT) — BOTTOM
# ═══════════════════════════════════════════════════════
- PRICE_VECTOR: SPOT - PREVIOUS_SPOT or UNAVAILABLE?           → [YES/NO]
- NEGATIVE Chg OI: <0 → 0?                                    → [YES/NO]
- DTE computed correctly?                                      → [YES/NO]
- INST_THRESHOLD DTE-adjusted (not hardcoded)?                 → [YES/NO]
- COUNTER_THRESHOLD DTE-adjusted (not hardcoded)?              → [YES/NO]
- IV_BASELINE computed from liquid strikes?                    → [YES/NO]
- IV_FLAG applied per dominant strike?                         → [YES/NO]
- IV_WRITING_CONFIDENCE used to gate CONFIDENCE?               → [YES/NO]
- OI_WEIGHT applied (ITM=2x, near-ATM=1.5x, OTM=1x)?          → [YES/NO]
- VOLUME_VALID check (Vol ≥ 3×ChgOI) per dominant strike?      → [YES/NO]
- DOMINANT STRIKES sorted by WEIGHTED OI descending?           → [YES/NO]
- TOTAL_PUT_OI / TOTAL_CALL_OI use RAW (not weighted)?         → [YES/NO]
- TOP3 %: max(PCT_TOP3_PUT, PCT_TOP3_CALL)?                    → [YES/NO]
- RATIO: Positive only?                                        → [YES/NO]
- MOMENTUM: BULLISH/BEARISH/NEUTRAL only?                      → [YES/NO]
- EXPIRY_CAP applied (SCORE capped at 6 on DTE=0)?             → [YES/NO]
- STRENGTH: STRONG/MODERATE/WEAK only?                         → [YES/NO]
- BANKNIFTY_DOMINANT: PUT WRITING/CALL WRITING/NEUTRAL only?   → [YES/NO]
- ALIGNMENT: ALIGNED/DIVERGENT only?                           → [YES/NO]
- UNWIND_POSSIBLE: True only if ≥2 snapshots?                  → [YES/NO]
- UNWIND_COUNT: len(UNWIND_SIGNALS)?                           → [YES/NO]
- MAX PAIN: MAX(StaticPutOI + StaticCallOI) per strike?        → [YES/NO]
- MAX_PAIN_RELIABLE: Chg OI at pain strike ≥ 10,000?           → [YES/NO]
- TRAPPED: In 100pt zone AND vector TOWARD pain?               → [YES/NO]
- APPROACHING_PAIN: In 100–200pt zone AND vector TOWARD pain?  → [YES/NO]
- TRAPPED FALSE if vector AWAY or UNAVAILABLE?                 → [YES/NO]
- COUNTER_COUNT capped at 5 when MOMENTUM=NEUTRAL?             → [YES/NO]
- COUNTER directional filter applied (vs momentum)?            → [YES/NO]
- PCR_DIV: uses 30M PCR if available, else full-session?       → [YES/NO]
- PCR_DIV: SKIPPED if session < 2hrs AND 30M unavailable?      → [YES/NO]
- SUPPORT = DOMINANT_PUT_STRIKES[0][0] (highest OI, not max strike)?  → [YES/NO]
- RESISTANCE = DOMINANT_CALL_STRIKES[0][0] (highest OI, not max strike)? → [YES/NO]
- ENTRY_WINDOW: time-of-day and expiry-aware?                  → [YES/NO]
- ENTRY_ALLOWED: False if DTE=0 and TIME_SINCE_OPEN ≥ 330?    → [YES/NO]
- REV_SCORE: 30U+25C+18T+9A+12P+8B formula?                   → [YES/NO]
- REV_SCORE >100: Allowed?                                     → [YES/NO]
- CONFIDENCE: XHIGH/HIGH/MEDIUM/LOW only?                      → [YES/NO]
- CONFIDENCE downgraded if IV_SPIKE in dominants?              → [YES/NO]
- REV_DIR: exact match from direction logic?                   → [YES/NO]
- TRIGGER_CONDITION: BREAK ABOVE/BELOW/EITHER SIDE only?       → [YES/NO]
- TRIGGER_LEVEL: strongest-OI strike or range?                 → [YES/NO]
- ALL TRACED: every AFTER STEP X present?                      → [YES/NO]
- PROTOCOL VIOLATIONS: [0]
# ═══════════════════════════════════════════════════════
# END OF PROMPT v15.0
# FIXES APPLIED: 11 total (7 gaps + 4 structural flaws)
# Theta/DTE-adjusted thresholds | IV/Vega engine | Volume validation |
# ITM/OTM weighting | Expiry mode | Counter normalization |
# Max Pain reliability | TRAPPED approach zone | PCR data quality |
# Support/Resistance logic | Time-of-day entry filter
# ═══════════════════════════════════════════════════════
"""

    # Format the data section based on data type
    fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if data is multi-expiry format
    if is_multi_expiry_data(oi_data):
        data_section = f"\n\nMULTI-EXPIRY DATA FOR ANALYSIS - FETCHED AT: {fetch_time}\n"
        data_section += format_multi_expiry_for_file(oi_data, pcr_values or {}, current_nifty, banknifty_data)
    else:
        # Original single expiry formatting (backward compatible)
        data_section = f"\n\nCURRENT DATA FOR ANALYSIS - FETCHED AT: {fetch_time}\n"
        data_section += "=" * 80 + "\n"
        data_section += f"NIFTY DATA:\n"
        data_section += f"- Current Value: {current_nifty}\n"
        data_section += f"- Expiry Date: {expiry_date}\n"
        data_section += f"- OI PCR: {oi_pcr:.2f}\n"
        data_section += f"- Volume PCR: {volume_pcr:.2f}\n"
        
        # Add BankNifty data if available
        if banknifty_data:
            data_section += f"\nBANKNIFTY DATA:\n"
            data_section += f"- Current Value: {banknifty_data.get('current_value', 0)}\n"
            data_section += f"- Expiry Date: {banknifty_data.get('expiry_date', 'N/A')}\n"
            banknifty_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('oi_pcr', 0)
            banknifty_volume_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('volume_pcr', 0)
            data_section += f"- OI PCR: {banknifty_pcr:.2f}\n"
            data_section += f"- Volume PCR: {banknifty_volume_pcr:.2f}\n"
        
        # Add COMPLETE Nifty option chain data in the same format as console
        data_section += f"\n\nCOMPLETE NIFTY OPTION CHAIN DATA:\n"
        data_section += "=" * 80 + "\n"
        data_section += f"OI Data for NIFTY - Current: {current_nifty}, Expiry: {expiry_date}\n"
        data_section += f"Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"
        data_section += "=" * 80 + "\n"
        data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
        data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                       f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                       f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
        data_section += "-" * 150 + "\n"
        
        for data in oi_data:  # ALL strikes, not just first 20
            strike_price = data['strike_price']
            
            # Format data exactly like console display
            ce_oi_formatted = str(data['ce_change_oi'])
            ce_volume_formatted = str(data['ce_volume'])
            ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
            ce_oi_total_formatted = str(data['ce_oi'])
            ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
            
            pe_oi_formatted = str(data['pe_change_oi'])
            pe_volume_formatted = str(data['pe_volume'])
            pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
            pe_oi_total_formatted = str(data['pe_oi'])
            pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
            
            chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
            chg_oi_diff_formatted = str(chg_oi_diff)
            
            # Format the row exactly like console
            formatted_row = (
                f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                f"{str(strike_price).center(9)}  |  "
                f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                f"{chg_oi_diff_formatted.rjust(16)}"
            )
            
            data_section += formatted_row + "\n"
        
        data_section += "=" * 150 + "\n"
        data_section += f"NIFTY PCR: OI PCR = {oi_pcr:.2f}, Volume PCR = {volume_pcr:.2f}\n\n"
        
        # Add COMPLETE BankNifty option chain data if available
        if banknifty_data and 'data' in banknifty_data:
            banknifty_oi_data = banknifty_data['data'].get('monthly', [])
            if banknifty_oi_data:
                banknifty_current = banknifty_data.get('current_value', 0)
                banknifty_expiry = banknifty_data.get('expiry_date', 'N/A')
                banknifty_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('oi_pcr', 0)
                banknifty_volume_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('volume_pcr', 0)
                
                data_section += f"\n\nCOMPLETE BANKNIFTY OPTION CHAIN DATA:\n"
                data_section += "=" * 80 + "\n"
                data_section += f"OI Data for BANKNIFTY - Current: {banknifty_current}, Expiry: {banknifty_expiry}\n"
                data_section += f"Full Chain PCR: OI={banknifty_pcr:.2f}, Volume={banknifty_volume_pcr:.2f}\n"
                data_section += "=" * 80 + "\n"
                data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
                data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                               f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                               f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
                data_section += "-" * 150 + "\n"
                
                for data in banknifty_oi_data:  # ALL BankNifty strikes
                    strike_price = data['strike_price']
                    
                    # Format BankNifty data exactly like console display
                    ce_oi_formatted = str(data['ce_change_oi'])
                    ce_volume_formatted = str(data['ce_volume'])
                    ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
                    ce_oi_total_formatted = str(data['ce_oi'])
                    ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
                    
                    pe_oi_formatted = str(data['pe_change_oi'])
                    pe_volume_formatted = str(data['pe_volume'])
                    pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
                    pe_oi_total_formatted = str(data['pe_oi'])
                    pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
                    
                    chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
                    chg_oi_diff_formatted = str(chg_oi_diff)
                    
                    # Format the row exactly like console
                    formatted_row = (
                        f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                        f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                        f"{str(strike_price).center(9)}  |  "
                        f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                        f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                        f"{chg_oi_diff_formatted.rjust(16)}"
                    )
                    
                    data_section += formatted_row + "\n"
                
                data_section += "=" * 150 + "\n"
                data_section += f"BANKNIFTY PCR: OI PCR = {banknifty_pcr:.2f}, Volume PCR = {banknifty_volume_pcr:.2f}\n"
    
    data_section += "=" * 80 + "\n"
    
    # Combine everything
    full_content = system_prompt + data_section
    
    # Write to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ AI query data saved to: {filepath}")
        
        # Send to Email via Resend API
        print("📧 Sending to Email...")
        email_success = send_email_with_file_content(filepath)
        if email_success:
            print("✅ Email sent successfully!")
        else:
            print("❌ Failed to send email")
        
        return filepath
    except Exception as e:
        print(f"❌ Error saving AI query data: {e}")
        return ""