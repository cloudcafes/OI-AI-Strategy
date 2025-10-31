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
                            "text": f"📊 Part {message_count}:\n",
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

# ... [Keep all your existing resend_latest_ai_query, resend_specific_ai_query, list_ai_query_files functions] ...

def save_ai_query_data(oi_data: List[Dict[str, Any]], 
                      oi_pcr: float, 
                      volume_pcr: float, 
                      current_nifty: float,
                      expiry_date: str,
                      banknifty_data: Dict[str, Any] = None) -> str:
    """
    Save AI query data to a text file with timestamp in filename and send to Telegram & Email
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
# NIFTY INTRADAY + REVERSAL PROMPT v14.0 [FINAL + BLACK-BOX PROOF]
# EVERY STEP = CODE + AUDIT + TRACE + LOCKED VALUES | PRICE-VECTOR-AWARE
# LOGIC: "TREND → UNWIND → COUNTER → PAIN" + MAX PAIN + FULL TRACE
# ===================================================================

# ———————————————————————
# COMPLIANCE VERIFICATION (TOP) — MANDATORY
# ———————————————————————
- Step 1: [PASS]  # Data includes Chg OI, Premium, Strike, Static OI
- Step 2: [PASS]  # ATM = closest strike to spot
- Step 3: [PASS]  # Chg OI > 0 only for writing
- Chg OI > Static OI Hierarchy: [VERIFIED]  # Static OI NEVER used in direction
- Protocol Violations: [0]

# ———————————————————————
# 0. LIVE MARKET CONTEXT — FULLY CODED + VALUES LOCKED
# ———————————————————————
SPOT: [LIVE]  # Possible: Any float
PREVIOUS_SPOT: [Spot from last snapshot]  # REQUIRED for vector
PRICE_VECTOR: {SPOT - PREVIOUS_SPOT}  # Possible: +XX, -XX, 0
VWAP: [LIVE or UNAVAILABLE]  # Possible: Float or "UNAVAILABLE"
TIME_NOW: [HH:MM]  # Possible: 00:00–23:59
TIME_SINCE_OPEN: [MINUTES or MARKET CLOSED]  # Possible: Integer or "MARKET CLOSED"
EXPIRY: [TODAY]  # Possible: DD-MMM-YYYY
ATM: [Closest strike to spot]  # CODE: |SPOT - strike| minimized
ATM_RANGE: [ATM - 300 to ATM + 300]  # CODE: inclusive
ATM_EXTENDED: [ATM - 500 to ATM + 500]
DATA_POINTS: [1 or more]  # REQUIRED for unwind
AFTER CONTEXT: "SPOT={SPOT}, Vector={PRICE_VECTOR:+}, Prev={PREVIOUS_SPOT} | ATM={ATM}, Range={ATM_RANGE}, Data points={DATA_POINTS}"

# ———————————————————————
# 1. MOMENTUM ENGINE — FULLY CODED + VALUES LOCKED + TRACE
# ———————————————————————
AFTER STEP 1: "Data sufficient - proceeding to seller identification"

# ——— STEP 2.1: DOMINANT STRIKES — CODE ENFORCED ———
PUT_CHG_POS = [(strike, max(Chg_OI, 0)) for strike in ATM_RANGE if type=='PUT']
CALL_CHG_POS = [(strike, max(Chg_OI, 0)) for strike in ATM_RANGE if type=='CALL']

DOMINANT_PUT_STRIKES = sorted(PUT_CHG_POS, key=lambda x: x[1], reverse=True)[:3]
DOMINANT_CALL_STRIKES = sorted(CALL_CHG_POS, key=lambda x: x[1], reverse=True)[:3]

TOTAL_PUT_OI = sum(max(Chg_OI,0) for _, Chg_OI in PUT_CHG_POS)
TOTAL_CALL_OI = sum(max(Chg_OI,0) for _, Chg_OI in CALL_CHG_POS)
TOP3_PUT_OI = sum(Chg_OI for _, Chg_OI in DOMINANT_PUT_STRIKES)
TOP3_CALL_OI = sum(Chg_OI for _, Chg_OI in DOMINANT_CALL_STRIKES)

PCT_TOP3_PUT = TOP3_PUT_OI / TOTAL_PUT_OI if TOTAL_PUT_OI > 0 else 0
PCT_TOP3_CALL = TOP3_CALL_OI / TOTAL_CALL_OI if TOTAL_CALL_OI > 0 else 0
PCT_TOP3 = max(PCT_TOP3_PUT, PCT_TOP3_CALL)

AFTER STEP 2.1: "Dominant: {len(DOMINANT_PUT_STRIKES)} puts, {len(DOMINANT_CALL_STRIKES)} calls | Top3 % = {PCT_TOP3:.0%}"

# ——— STEP 2.2: CLASSIFICATION — CODE ENFORCED ———
INST_COUNT = 0
TOTAL_DOM = len(DOMINANT_PUT_STRIKES) + len(DOMINANT_CALL_STRIKES)
for strike, _ in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES:
   prem = Premium(strike)
   if prem < 100: INST_COUNT += 1
INST_PCT = INST_COUNT / TOTAL_DOM * 100 if TOTAL_DOM > 0 else 0

AFTER STEP 2.2: "Classification: {INST_PCT:.1f}% Institutional"

# ——— STEP 2.3: HIERARCHY ———
AFTER STEP 2.3: "Static OI ignored: YES"

# ——— STEP 2.4: RATIO & MOMENTUM — CODE ENFORCED ———
Ratio = TOTAL_PUT_OI / TOTAL_CALL_OI if TOTAL_CALL_OI > 0 else 999
MOMENTUM = "BULLISH" if Ratio > 1.20 else "BEARISH" if Ratio < 0.80 else "NEUTRAL"
AFTER STEP 2.4: "Ratio = {Ratio:.2f} → {MOMENTUM}"

# ——— STEP 2.5: STRENGTH METER — CODE ENFORCED ———
SCORE = 0
if INST_PCT >= 85: SCORE += 3
if PCT_TOP3 >= 0.60: SCORE += 2
if Ratio > 1.50 or Ratio < 0.60: SCORE += 1
if (OI_PCR > 1 and Volume_PCR > 1) or (OI_PCR < 1 and Volume_PCR < 1): SCORE += 1
if any(Premium(strike) < 80 for strike, _ in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES): SCORE += 1

STRENGTH = "STRONG" if SCORE > 7 else "MODERATE" if SCORE >= 5 else "WEAK"
AFTER STEP 2.5: "Strength = {STRENGTH} ({SCORE}/10)"

# ——— STEP 2.6: BANKNIFTY — CODE ENFORCED ———
BANKNIFTY_OI_PCR = BankNifty OI PCR
BANKNIFTY_DOMINANT = "PUT WRITING" if BANKNIFTY_OI_PCR > 1.0 else "CALL WRITING" if BANKNIFTY_OI_PCR < 0.9 else "NEUTRAL"
ALIGNMENT = "ALIGNED" if \
   (MOMENTUM == "BULLISH" and BANKNIFTY_DOMINANT == "PUT WRITING") or \
   (MOMENTUM == "BEARISH" and BANKNIFTY_DOMINANT == "CALL WRITING") \
   else "DIVERGENT"
AFTER STEP 2.6: "BankNifty: {BANKNIFTY_DOMINANT} → {ALIGNMENT}"

# ———————————————————————
# 2. PEAK TRACKING — TIME-SERIES AWARE + CONNECTED
# ———————————————————————
PEAK_CHG_OI_DICT = {}  # {strike: max_positive_Chg_OI_seen}
UNWIND_POSSIBLE = DATA_POINTS >= 2

if UNWIND_POSSIBLE:
   for strike in ATM_EXTENDED:
      current = max(current_Chg_OI(strike), 0)
      if current > PEAK_CHG_OI_DICT.get(strike, 0):
         PEAK_CHG_OI_DICT[strike] = current
   AFTER PEAK UPDATE: "Peak tracking active: {len(PEAK_CHG_OI_DICT)} strikes"
else:
   AFTER PEAK UPDATE: "Peak tracking: INSUFFICIENT DATA (need ≥2 snapshots)"

# ———————————————————————
# 3. REVERSAL ENGINE v14.0 — FULLY CONNECTED + PRICE-VECTOR-AWARE
# ———————————————————————
AFTER REVERSAL STEP 1: "Checking relative unwind..."

# ——— PHASE 1: RELATIVE UNWIND — USING PEAK TRACKING ———
UNWIND_SIGNALS = []
UNWIND_COUNT = 0

if UNWIND_POSSIBLE:
   for strike, _ in DOMINANT_PUT_STRIKES:
      peak = PEAK_CHG_OI_DICT.get(strike, 0)
      current = max(current_Chg_OI(strike), 0)
      if peak > 10000 and current < (peak * 0.70):
         UNWIND_SIGNALS.append(f"{strike} Put Unwind: {current:+,} (from {peak:+,}) → {((peak-current)/peak)*100:.1f}%")
         UNWIND_COUNT += 1
   for strike, _ in DOMINANT_CALL_STRIKES:
      peak = PEAK_CHG_OI_DICT.get(strike, 0)
      current = max(current_Chg_OI(strike), 0)
      if peak > 10000 and current < (peak * 0.70):
         UNWIND_SIGNALS.append(f"{strike} Call Unwind: {current:+,} (from {peak:+,}) → {((peak-current)/peak)*100:.1f}%")
         UNWIND_COUNT += 1
   AFTER PHASE 1: "Relative unwind: {UNWIND_COUNT} signals"
else:
   AFTER PHASE 1: "Relative unwind: NOT POSSIBLE (1 snapshot)"

# ——— PHASE 2: COUNTER-POSITIONING ———
COUNTER_SIGNALS = []
COUNTER_COUNT = 0
for strike in range(ATM-300, ATM+1, 50):
   if Chg_OI(strike, 'PUT') > 15000 and Premium(strike, 'PUT') < 90:
      COUNTER_SIGNALS.append(f"{strike} Put: +{Chg_OI(strike,'PUT'):,} (Prem {Premium(strike,'PUT')}) → INST SUPPORT")
      COUNTER_COUNT += 1
for strike in range(ATM, ATM+301, 50):
   if Chg_OI(strike, 'CALL') > 15000 and Premium(strike, 'CALL') < 90:
      COUNTER_SIGNALS.append(f"{strike} Call: +{Chg_OI(strike,'CALL'):,} (Prem {Premium(strike,'CALL')}) → INST RESISTANCE")
      COUNTER_COUNT += 1
AFTER PHASE 2: "Counter-positioning: {COUNTER_COUNT} signals"

# ——— PHASE 3: MAX PAIN — COMPUTED ———
CURRENT_MAX_PAIN = strike with MAX(Put_OI + Call_OI)
SPOT_TO_PAIN = SPOT - CURRENT_MAX_PAIN
AFTER MAX PAIN: "Max Pain = {CURRENT_MAX_PAIN}, Spot diff = {SPOT_TO_PAIN:+}"

# ——— PHASE 4: PAIN_PRESSURE — PRICE-VECTOR-AWARE ———
PAIN_PRESSURE = "NONE"
TRAPPED = False

if MOMENTUM == "BULLISH":
   if SPOT_TO_PAIN > 0 and SPOT_TO_PAIN <= 100 and PRICE_VECTOR < 0:
      PAIN_PRESSURE = "BEARISH: Spot FALLING INTO Max Pain → TRAPPED PUT WRITERS"
      TRAPPED = True
   else:
      PAIN_PRESSURE = "NEUTRAL: No active trap on Put writers"
elif MOMENTUM == "BEARISH":
   if SPOT_TO_PAIN < 0 and abs(SPOT_TO_PAIN) <= 100 and PRICE_VECTOR > 0:
      PAIN_PRESSURE = "BULLISH: Spot RISING INTO Max Pain → TRAPPED CALL WRITERS"
      TRAPPED = True
   else:
      PAIN_PRESSURE = "NEUTRAL: No active trap on Call writers"
else:
   PAIN_PRESSURE = "NEUTRAL: Momentum unclear → no directional pain"

AFTER PHASE 4: "Pain pressure: {PAIN_PRESSURE} → TRAPPED = {TRAPPED}"

# ——— PCR & BANKNIFTY DIVERGENCE ———
PCR_DIV = (Ratio > 1.20 and Volume_PCR_30M < 0.80) or (Ratio < 0.80 and Volume_PCR_30M > 1.50)
BN_DIV = (Ratio > 1.20 and BANKNIFTY_DOMINANT == "CALL WRITING") or (Ratio < 0.80 and BANKNIFTY_DOMINANT == "PUT WRITING")

# ——— REVERSAL SCORING — CODE ENFORCED ———
REV_SCORE = 30 * UNWIND_COUNT + 25 * COUNTER_COUNT + 18 * int(TRAPPED) + 12 * int(PCR_DIV) + 8 * int(BN_DIV)
# Can exceed 100
CONFIDENCE = "XHIGH" if REV_SCORE >= 80 else "HIGH" if REV_SCORE >= 65 else "MEDIUM" if REV_SCORE >= 50 else "LOW"

AFTER SCORING: "Reversal Score = {REV_SCORE}/100 → {CONFIDENCE} | Can exceed 100"

# ——— REVERSAL DIRECTION ———
if MOMENTUM == "BEARISH" and "BULLISH" in PAIN_PRESSURE:
   REV_DIR = "BEARISH → BULLISH"
elif MOMENTUM == "BULLISH" and "BEARISH" in PAIN_PRESSURE:
   REV_DIR = "BULLISH → BEARISH"
else:
   REV_DIR = MOMENTUM
AFTER DIRECTION: "Reversal direction: {REV_DIR}"

# ———————————————————————
# 4. CRITICAL LEVELS — CODE ENFORCED
# ———————————————————————
RESISTANCE = max((s for s, _ in DOMINANT_CALL_STRIKES), default=ATM + 100)
SUPPORT = max((s for s, _ in DOMINANT_PUT_STRIKES), default=ATM - 100)

if MOMENTUM == "BULLISH":
   HOLD_LEVEL = f"Above {SUPPORT}"
   TRIGGER_CONDITION = "BREAK ABOVE"
   TRIGGER_LEVEL = f"{RESISTANCE}"
elif MOMENTUM == "BEARISH":
   HOLD_LEVEL = f"Below {RESISTANCE}"
   TRIGGER_CONDITION = "BREAK BELOW"
   TRIGGER_LEVEL = f"{SUPPORT}"
else:
   HOLD_LEVEL = f"Range {SUPPORT}–{RESISTANCE}"
   TRIGGER_CONDITION = "BREAK EITHER SIDE"
   TRIGGER_LEVEL = f"{SUPPORT}–{RESISTANCE}"

AFTER LEVELS: "Hold = {HOLD_LEVEL} | Trigger = {TRIGGER_CONDITION} {TRIGGER_LEVEL}"

# ———————————————————————
# 5. FINAL OUTPUT — ALL VALUES LOCKED
# ———————————————————————
QUANTITATIVE EVIDENCE:
Net Chg OI (Puts - Calls): {TOTAL_PUT_OI - TOTAL_CALL_OI:+,}
Total Put Chg OI (Positive): {TOTAL_PUT_OI:,}
Total Call Chg OI (Positive): {TOTAL_CALL_OI:,}
Ratio: {Ratio:.2f}

KEY FLOW EVIDENCE:
[STRIKE]: [+/-XXXXX] - [Put/Call] Writing - [INSTITUTIONAL/RETAIL/MIXED]
...

MOMENTUM DRIVERS:
Primary: {INST_PCT:.0f}% Institutional {MOMENTUM.lower()} flow
Secondary: {PCT_TOP3:.0%} in top 3 strikes
Contradictory: {len(DOMINANT_PUT_STRIKES) if MOMENTUM=='BEARISH' else len(DOMINANT_CALL_STRIKES)} minor opposite

BANKNIFTY CONFIRMATION: {ALIGNMENT} [{BANKNIFTY_DOMINANT} vs {MOMENTUM}]

CRITICAL LEVELS:
Current Momentum holds: {HOLD_LEVEL}
Momentum Shift Trigger: {TRIGGER_CONDITION} {TRIGGER_LEVEL}

CURRENT MOMENTUM: {MOMENTUM}
STRENGTH: {STRENGTH}
CONFIDENCE: {CONFIDENCE}

PCR Data:
OI PCR [{OI_PCR:.2f}] [{'ALIGNED' if (OI_PCR>1 and TOTAL_PUT_OI>TOTAL_CALL_OI) or (OI_PCR<1 and TOTAL_CALL_OI>TOTAL_PUT_OI) else 'DIVERGENT'}]
Volume PCR [{Volume_PCR:.2f}] [{'ALIGNED' if not PCR_DIV else 'DIVERGENT'}]

STRENGTH METER: {SCORE}/10
[Justification via coded rules]

ANALYSIS NARRATIVE:
[Auto-generated from above]

TRADING IMPLICATION:
[Auto-derived from REV_DIR and CONFIDENCE]

# ———————————————————————
# REVERSAL ALERT
# ———————————————————————
REVERSAL SCORE: {REV_SCORE}/100
CONFIDENCE: {CONFIDENCE}
DIRECTION: {REV_DIR}
ENTRY WINDOW: NEXT 15–60 MIN
TRIGGER: {TRIGGER_CONDITION} {TRIGGER_LEVEL}
EVIDENCE SUMMARY:
1. Unwind: {UNWIND_COUNT} signals
2. Counter: {COUNTER_COUNT} signals
3. Pain: {PAIN_PRESSURE}
4. PCR Div: {PCR_DIV}
5. BN Div: {BN_DIV}

# ———————————————————————
# MANDATORY QUALITY CHECKS (FINAL AUDIT) — BOTTOM
# ———————————————————————
- PRICE_VECTOR: SPOT - PREVIOUS_SPOT? → [YES/NO]
- NEGATIVE Chg OI: <0 → 0? → [YES/NO]
- DOMINANT STRIKES: Top 3 positive Chg OI? → [YES/NO]
- TOP3 %: max(PCT_TOP3_PUT, PCT_TOP3_CALL)? → [YES/NO]
- INST %: <100=INST, 100-150=MIXED, >150=RETAIL? → [YES/NO]
- RATIO: Positive only? → [YES/NO]
- MOMENTUM: BULLISH/BEARISH/NEUTRAL only? → [YES/NO]
- STRENGTH: STRONG/MODERATE/WEAK only? → [YES/NO]
- BANKNIFTY_DOMINANT: PUT/CALL/NEUTRAL only? → [YES/NO]
- ALIGNMENT: ALIGNED/DIVERGENT only? → [YES/NO]
- UNWIND_POSSIBLE: True only if ≥2 points? → [YES/NO]
- UNWIND_COUNT: len(UNWIND_SIGNALS)? → [YES/NO]
- MAX PAIN: MAX(Put+Call OI)? → [YES/NO]
- TRAPPED: In zone AND vector TOWARDS pain? → [YES/NO]
- TRAPPED FALSE: If moving AWAY? → [YES/NO]
- REV_SCORE: 30*UNWIND + 25*COUNTER + 18*TRAPPED + ...? → [YES/NO]
- REV_SCORE >100: Allowed? → [YES/NO]
- CONFIDENCE: XHIGH/HIGH/MEDIUM/LOW only? → [YES/NO]
- REV_DIR: Exact match? → [YES/NO]
- TRIGGER_CONDITION: BREAK ABOVE/BELOW/EITHER SIDE only? → [YES/NO]
- TRIGGER_LEVEL: Strike or range? → [YES/NO]
- ALL TRACED: AFTER STEP X present? → [YES/NO]
- PROTOCOL VIOLATIONS: [0]
# ===================================================================
-----------------------------------------------------------------------------------------------    
"""

    # Format the data section
    fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
        data_section += f"- OI PCR: {banknifty_data.get('oi_pcr', 0):.2f}\n"
        data_section += f"- Volume PCR: {banknifty_data.get('volume_pcr', 0):.2f}\n"
    
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
        banknifty_oi_data = banknifty_data['data']
        banknifty_current = banknifty_data.get('current_value', 0)
        banknifty_expiry = banknifty_data.get('expiry_date', 'N/A')
        banknifty_oi_pcr = banknifty_data.get('oi_pcr', 0)
        banknifty_volume_pcr = banknifty_data.get('volume_pcr', 0)
        
        data_section += f"\n\nCOMPLETE BANKNIFTY OPTION CHAIN DATA:\n"
        data_section += "=" * 80 + "\n"
        data_section += f"OI Data for BANKNIFTY - Current: {banknifty_current}, Expiry: {banknifty_expiry}\n"
        data_section += f"Full Chain PCR: OI={banknifty_oi_pcr:.2f}, Volume={banknifty_volume_pcr:.2f}\n"
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
        data_section += f"BANKNIFTY PCR: OI PCR = {banknifty_oi_pcr:.2f}, Volume PCR = {banknifty_volume_pcr:.2f}\n"
    
    data_section += "=" * 80 + "\n"
    
    # Combine everything
    full_content = system_prompt + data_section
    
    # Write to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ AI query data saved to: {filepath}")
        
        # Send to Telegram
        #print("📤 Sending to Telegram...")
        #telegram_success = send_telegram_message(full_content)
        #if telegram_success:
            #print("✅ Message sent to Telegram successfully!")
        #else:
            #print("❌ Failed to send message to Telegram")
        
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