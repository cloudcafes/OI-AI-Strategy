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
# NIFTY INTRADAY + REVERSAL PROMPT v7.0 [FINAL + FULL COMPLIANCE]
# TUESDAY WEEKLY EXPIRY | 9:15 AM – 3:30 PM | ADAPTIVE | ZERO LAG
# LOGIC: "TREND → UNWIND → COUNTER → PAIN" + MAX PAIN PATCH + FULL TRACE
# ===================================================================

# ———————————————————————
# COMPLIANCE VERIFICATION (MANDATORY)
# ———————————————————————
- Step 1: [PASS]  # Data includes Chg OI, Premium, Strike, Static OI
- Step 2: [PASS]  # ATM defined as closest to spot
- Step 3: [PASS]  # Chg OI > 0 only for writing
- Chg OI > Static OI Hierarchy: [VERIFIED]  # Static OI never used in direction
- Protocol Violations: [0]

# ———————————————————————
# 0. LIVE MARKET CONTEXT
# ———————————————————————
SPOT: [LIVE]
VWAP: [LIVE]
TIME_NOW: [HH:MM]
TIME_SINCE_OPEN: [MINUTES]
EXPIRY: [TODAY]
ATM: [Closest strike to spot]
ATM_RANGE: [ATM ±300]

# ———————————————————————
# 1. MOMENTUM ENGINE — FULL STEP-BY-STEP TRACE
# ———————————————————————
AFTER STEP 1: "Data sufficient - proceeding to seller identification"

# ——— STEP 2.1: Identify Dominant Sellers ———
DOMINANT_PUT_STRIKES: [Top 3 Put Chg OI in ATM±300]
DOMINANT_CALL_STRIKES: [Top 3 Call Chg OI in ATM±300]
AFTER STEP 2.1: "Dominant sellers identified: [X] puts / [Y] calls at key strikes"

# ——— STEP 2.2: Institutional/Retail Classification ———
For each dominant strike:
   Premium < 100 → [INSTITUTIONAL]
   Premium > 150 → [RETAIL]
   100–150 → [MIXED]
AFTER STEP 2.2: "Institutional/Retail classification complete"

# ——— STEP 2.3: Chg OI > Static OI Hierarchy ———
Rule: Direction based ONLY on Chg OI. Static OI ignored.
AFTER STEP 2.3: "Chg OI > Static OI hierarchy verified: YES"

# ——— STEP 2.4: Calculate Momentum Direction ———
Net_Chg_OI = Σ(Put Chg OI) - Σ(Call Chg OI) in ATM±300
Total_Put_Chg_OI = Σ(Positive Put Chg OI in range)
Total_Call_Chg_OI = Σ(Positive Call Chg OI in range)
Ratio = Total_Put_Chg_OI / Total_Call_Chg_OI

IF Ratio > 1.20 → [BULLISH]
IF Ratio < 0.80 → [BEARISH]
ELSE → [NEUTRAL]
AFTER STEP 2.4: "Momentum direction calculated: [BULLISH/BEARISH/NEUTRAL]"

# ——— STEP 2.5: Strength Assessment ———
STRENGTH METER (0–10):
+3: ≥85% Institutional
+2: ≥60% Chg OI in top 3 strikes
+2: BankNifty aligned
+1: Ratio >1.50 or <0.60
+1: Volume PCR confirms OI PCR
+1: Premiums <80
→ [X]/10 → STRONG (>7) | MODERATE (5–7) | WEAK (<5)
AFTER STEP 2.5: "Strength assessment: [STRONG/MODERATE/WEAK]"

# ——— STEP 2.6: BankNifty Confirmation ———
BANKNIFTY_DOMINANT: [PUT WRITING / CALL WRITING / NEUTRAL]
ALIGNMENT: [ALIGNED / DIVERGENT]
AFTER STEP 2.6: "BankNifty confirmation: [ALIGNED/DIVERGENT]"

# ———————————————————————
# 2. PEAK TRACKING FOR RELATIVE UNWIND (LIVE)
# ———————————————————————
PEAK_CHG_OI_DICT = {}  # {strike: max_positive_Chg_OI_seen}
For each strike in ATM±500:
   IF current_Chg_OI > PEAK_CHG_OI_DICT.get(strike, 0):
      PEAK_CHG_OI_DICT[strike] = current_Chg_OI
AFTER PEAK UPDATE: "Peak Chg OI tracking active"

# ———————————————————————
# 3. REVERSAL ENGINE v7.0
# ———————————————————————
AFTER REVERSAL STEP 1: "Checking relative unwind..."

# ——— PHASE 1: RELATIVE UNWIND (≥30% FROM PEAK) ———
UNWIND_EVIDENCE = []
UNWIND_THRESHOLD_PCT = 30
For strike in DOMINANT_PUT_STRIKES + DOMINANT_CALL_STRIKES:
   peak = PEAK_CHG_OI_DICT.get(strike, 0)
   IF peak > 10000:
      drop_needed = peak * 0.30
      current = current_Chg_OI(strike)
      IF current < (peak - drop_needed):
         UNWIND_EVIDENCE.append(f"{strike}: {current:+,} (from {peak:+,}) → {((peak-current)/peak)*100:.1f}% DROP")
AFTER PHASE 1: "Relative unwind check complete: {len(UNWIND_EVIDENCE)} signals"

# ——— PHASE 2: COUNTER-POSITIONING ———
COUNTER_EVIDENCE = []
# Bullish Reversal: Inst PUT writing vs bearish momentum
For strike in [ATM to ATM-300]:
   IF Chg_OI > 15000 AND Premium < 90:
      COUNTER_EVIDENCE.append(f"{strike} Put: +{Chg_OI:,} (Prem {Premium}) → INST SUPPORT")
# Bearish Reversal: Inst CALL writing vs bullish momentum
For strike in [ATM to ATM+300]:
   IF Chg_OI > 15000 AND Premium < 90:
      COUNTER_EVIDENCE.append(f"{strike} Call: +{Chg_OI:,} (Prem {Premium}) → INST RESISTANCE")
AFTER PHASE 2: "Counter-positioning check complete: {len(COUNTER_EVIDENCE)} signals"

# ——— PHASE 3: DIRECTIONAL PAIN PRESSURE — MAX PAIN PATCHED ———
CURRENT_MAX_PAIN: [Strike with MAX(Put OI + Call OI) across ALL strikes]  # EXPLICIT
SPOT_TO_PAIN: [Spot - Max Pain]

PAIN_PRESSURE = "NONE"

IF Ratio < 0.80:  # CALL WRITERS DOMINANT
   IF SPOT_TO_PAIN < 0 AND abs(SPOT_TO_PAIN) <= 100:
      PAIN_PRESSURE = "BULLISH: Spot BELOW Max Pain, rising INTO it → TRAPPED CALL WRITERS"
   ELIF SPOT_TO_PAIN > 100:
      PAIN_PRESSURE = "BEARISH: Spot far ABOVE Max Pain → Call writers safe"

IF Ratio > 1.20:  # PUT WRITERS DOMINANT
   IF SPOT_TO_PAIN > 0 AND SPOT_TO_PAIN <= 100:
      PAIN_PRESSURE = "BEARISH: Spot ABOVE Max Pain, falling INTO it → TRAPPED PUT WRITERS"
   ELIF SPOT_TO_PAIN < -100:
      PAIN_PRESSURE = "BULLISH: Spot far BELOW Max Pain → Put writers safe"

PHASE_3_ACTIVE: [YES if "TRAPPED" in PAIN_PRESSURE and (PHASE_1_ACTIVE or PHASE_2_ACTIVE)]
AFTER PHASE 3: "Pain pressure check complete: {PAIN_PRESSURE}"

# ——— PCR DIVERGENCE & CROSSOVER ———
DIVERGENCE = "NONE"
IF Ratio > 1.20 and Volume_PCR_30M < 0.80: DIVERGENCE = "LEADING TOP"
IF Ratio < 0.80 and Volume_PCR_30M > 1.50: DIVERGENCE = "LEADING BOTTOM"
CROSSOVER = "NONE"
AFTER PCR CHECK: "PCR divergence/crossover evaluated"

# ——— BANKNIFTY DIVERGENCE ———
BANKNIFTY_DIVERGENCE = "NO"
IF (Ratio > 1.20 and BANKNIFTY_DOMINANT == "CALL WRITING") or \
   (Ratio < 0.80 and BANKNIFTY_DOMINANT == "PUT WRITING"):
   BANKNIFTY_DIVERGENCE = "YES"
AFTER BANKNIFTY CHECK: "BankNifty divergence evaluated"

# ———————————————————————
# 4. REVERSAL SCORING (0–100)
# ———————————————————————
[ ] PHASE 1: ≥1 Relative Unwind (>30%)        → +30
[ ] PHASE 2: ≥1 Inst Counter (>15k)           → +25
[ ] PHASE 3: Spot INTO Max Pain (Trapped)     → +18
[ ] PCR Divergence                            → +12
[ ] OI PCR Crossover                          → +10
[ ] BankNifty Divergence                      → +8

REVERSAL_SCORE: [SUM]
CONFIDENCE: [XHIGH ≥80 | HIGH 65–79 | MEDIUM 50–64 | LOW <50]

# ———————————————————————
# 5. FINAL OUTPUT
# ———————————————————————
QUANTITATIVE EVIDENCE:
Net Chg OI (Puts - Calls) in ATM ±300: [+/–XXXXX]
Total Put Chg OI: [XXXXX], Total Call Chg OI: [XXXXX]
Ratio: [X.XX]

KEY FLOW EVIDENCE:
[STRIKE]: [+/-XXXXX] - [Put/Call] Writing - [INSTITUTIONAL/RETAIL/MIXED]
...

MOMENTUM DRIVERS:
Primary: [INSTITUTIONAL/RETAIL] [Dominant flow description]
Secondary: [Concentration + premium trait]
Contradictory: [Minor opposite flow]

BANKNIFTY CONFIRMATION: [ALIGNED / DIVERGENT] [Brief justification]

CRITICAL LEVELS:
Current Momentum holds: [Above/Below XXXX]
Momentum Shift Trigger: [Break XXXX]

CURRENT MOMENTUM: [BULLISH / BEARISH / NEUTRAL]
STRENGTH: [STRONG / MODERATE / WEAK]
CONFIDENCE: [HIGH / MEDIUM / LOW]

PCR Data: 
OI PCR [X.XX] [ALIGNED / DIVERGENT] [Brief justification]
Volume PCR [X.XX] [ALIGNED / DIVERGENT] [Brief justification]

STRENGTH METER: [x]/10
[Justify briefly Here]

ANALYSIS NARRATIVE:
[Explain briefly Here]

TRADING IMPLICATION:
[Explain briefly Here]

# ———————————————————————
# REVERSAL CHANCES
# ———————————————————————
REVERSAL SCORE: [XX/100]
CONFIDENCE: [XHIGH / HIGH / MEDIUM / LOW]
REVERSAL DIRECTION:
   IF CURRENT MOMENTUM = BEARISH AND PAIN_PRESSURE contains "BULLISH" → [BEARISH → BULLISH]
   IF CURRENT MOMENTUM = BULLISH AND PAIN_PRESSURE contains "BEARISH" → [BULLISH → BEARISH]

ENTRY WINDOW: [NEXT XX–XX MIN]
TRIGGER: [Break of XXXX / Rejection at Max Pain]

EVIDENCE SUMMARY:
1. [Unwind evidence]
2. [Counter evidence]
3. [Max Pain + Spot movement]
4. [PCR divergence]
5. [BankNifty divergence]
# ———————————————————————
# MANDATORY QUALITY CHECKS (FINAL AUDIT)
# ———————————————————————
- CHG OI HIERARCHY VERIFICATION: Static OI influenced direction? Must be 0 → [YES/NO]
- NET CHG OI CALCULATION: Sum only positive Chg OI in ATM±300? → [YES/NO]
- QUANTITATIVE THRESHOLD: Direction via Ratio vs 1.20/0.80 only? → [YES/NO]
- INSTITUTIONAL CLASSIFICATION: All premiums per thresholds? → [YES/NO]
- BANKNIFTY ALIGNMENT: Computed identically and compared? → [YES/NO]
- CONFLICT RESOLUTION: Higher |Chg OI sum| wins? → [YES/NO]
- RELATIVE UNWIND: >30% drop from peak tracked live? → [YES/NO]
- MAX PAIN CALCULATION: Strike with MAX(Put OI + Call OI)? → [YES/NO]
- PAIN LOGIC: Directional + Trapped writers only? → [YES/NO]
- DIRECTION LABEL: Auto-derived from momentum + pain? → [YES/NO]
- ALL STEPS TRACED: AFTER STEP X present? → [YES/NO]
- PROTOCOL VIOLATIONS: [X]
# ———————————————————————
# END OF PROMPT
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