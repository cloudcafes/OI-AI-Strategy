import os
import datetime
from typing import Dict, Any, List
import urllib3

from nifty_config import format_greek_value, AI_LOGS_DIR, RESEND_API_KEY, EMAIL_TO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------
# EMAIL (RESEND) INITIALIZATION
# ---------------------------------------------------------
try:
    import resend
    RESEND_AVAILABLE = True
    resend.api_key = RESEND_API_KEY
    print("✅ Resend module loaded successfully")
except ImportError:
    RESEND_AVAILABLE = False
    print("⚠️ Resend module not installed. Email functionality disabled.")
except Exception as e:
    RESEND_AVAILABLE = False
    print(f"⚠️ Resend configuration error: {e}")

# ---------------------------------------------------------
# HELPER: CSV FORMATTER (Optimized for LLM Tokens)
# ---------------------------------------------------------
def format_csv_row(data: dict) -> str:
    """Formats a single options chain row as a highly token-efficient CSV string."""
    ce_iv = format_greek_value(data['ce_iv'], 1)
    pe_iv = format_greek_value(data['pe_iv'], 1)
    chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
    
    # Handle missing/empty LTP values cleanly
    ce_ltp = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0.0"
    pe_ltp = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0.0"
    
    # Format: CE_ChgOI, CE_Vol, CE_LTP, CE_OI, CE_IV, STRIKE, PE_ChgOI, PE_Vol, PE_LTP, PE_OI, PE_IV, CE_PE_DIFF
    return f"{data['ce_change_oi']},{data['ce_volume']},{ce_ltp},{data['ce_oi']},{ce_iv},{data['strike_price']},{data['pe_change_oi']},{data['pe_volume']},{pe_ltp},{data['pe_oi']},{pe_iv},{chg_oi_diff}\n"

# ---------------------------------------------------------
# EMAIL SENDING LOGIC
# ---------------------------------------------------------
def send_email_with_file_content(filepath: str, subject: str = None) -> bool:
    """Sends the complete text file content as an email using Resend API."""
    if not RESEND_AVAILABLE or not RESEND_API_KEY or "YOUR_" in RESEND_API_KEY:
        print("❌ Cannot send email: Resend module not available or key not configured")
        return False
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        if not subject:
            timestamp = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
            subject = f"🤖 Nifty AI Analysis - {timestamp}"
        
        # Basic text to HTML conversion
        html_content = file_content.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        
        # Add simple HTML envelope for better reading
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: 'Courier New', monospace; font-size: 14px; background: #f5f5f5; color: #333; padding: 20px;">
            <div style="max-width: 1100px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px;">
                <h2 style="color: #007acc;">🤖 NIFTY AI TRADING ANALYSIS</h2>
                <p><strong>Generated:</strong> {datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")}</p>
                <hr>
                <div>{html_content}</div>
            </div>
        </body>
        </html>
        """
        
        params = {
            "from": "onboarding@resend.dev",
            "to": EMAIL_TO,
            "subject": subject,
            "html": html_template
        }
        
        result = resend.Emails.send(params)
        print(f"✅ Email sent successfully! ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email via Resend: {e}")
        return False

# ---------------------------------------------------------
# FILE SAVING LOGIC
# ---------------------------------------------------------
def save_ai_query_data(oi_data: List[Dict[str, Any]], 
                      oi_pcr: float, 
                      volume_pcr: float, 
                      current_nifty: float,
                      expiry_date: str,
                      banknifty_data: Dict[str, Any] = None) -> str:
    """Saves formatted option chain data to a text file and triggers email."""    
    
    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filepath = os.path.join(AI_LOGS_DIR, f"ai_query_{timestamp}.txt")
    
    # Using a list to build the string (Massive performance optimization)
    lines = []
    fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Add AI Prompt Header
    system_prompt = """
🤖 NIFTY AI TRADING ANALYSIS
# ===================================================================
This report is run from the server having UST time Zone so calculate time in IST accordingly.
Data is not pre market but in IST market hours but due to UST time show early.
# ===================================================================

# ═══════════════════════════════════════════════════════
# PRE-EXECUTION INSTRUCTION (MANDATORY)
# ═══════════════════════════════════════════════════════
# 1. You must act as a deterministic computational engine.
# 2. Before the final output, you MUST provide a "STRIKE SCRATCHPAD"
# showing the math for the Top 3 CE and Top 3 PE strikes.
# 3. Use the v15.1 weights: ITM (2.0x), Near-ATM (1.5x), OTM (1.0x).
# 4. If volume validation fails (Vol < 3x Chg OI), flag it explicitly.
# ═══════════════════════════════════════════════════════

# ACTION: Provide SCRATCHPAD workings first.

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
IV_WRITING_CONFIDENCE = "LOW — IV SPIKE detected: possible LONG BUILDUP, not clean writing" if IV_SPIKE_COUNT >= 2 else                         "MODERATE — 1 IV spike present" if IV_SPIKE_COUNT == 1 else                         "HIGH — IV normal/crush environment"

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
BANKNIFTY_DOMINANT = "PUT WRITING"  if BANKNIFTY_OI_PCR > 1.0  else                      "CALL WRITING" if BANKNIFTY_OI_PCR < 0.9  else "NEUTRAL"
ALIGNMENT          = "ALIGNED"   if (MOMENTUM == "BULLISH" and BANKNIFTY_DOMINANT == "PUT WRITING") or                                      (MOMENTUM == "BEARISH" and BANKNIFTY_DOMINANT == "CALL WRITING")                      else "DIVERGENT"

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
# 3. REVERSAL ENGINE v15.1 — FULLY FIXED + PRICE-VECTOR-AWARE
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

BN_DIV = (Ratio > 1.20 and BANKNIFTY_DOMINANT == "CALL WRITING") or          (Ratio < 0.80 and BANKNIFTY_DOMINANT == "PUT WRITING")

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
CONFIDENCE = "XHIGH"  if REV_SCORE >= 80  else              "HIGH"   if REV_SCORE >= 65  else              "MEDIUM" if REV_SCORE >= 50  else "LOW"

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
# 4-C. QUANTITATIVE PROBABILITY & TARGET ENGINE — NEW
# ═══════════════════════════════════════════════════════
# 1. Expected Intraday Range (EIR) using IV Baseline
# Formula: Spot * (IV / 100) / sqrt(252 trading days)
if IV_BASELINE > 0:
    EIR = (SPOT * (IV_BASELINE / 100)) / 15.87  # 15.87 is approx sqrt(252)
else:
    EIR = SPOT * 0.0075  # Fallback to 0.75% default range if IV unknown

# 2. Probability / Surety Score Calculation (%)
# Base: 50% | Strength Meter: Up to +20% | Reversal Score: Up to +20% | BN Alignment: +10% or -10%
PROBABILITY_BASE = 50.0
PROB_STRENGTH    = (SCORE / 10.0) * 20.0
PROB_REVERSAL    = min(REV_SCORE, 50) / 50.0 * 20.0
PROB_ALIGNMENT   = 10.0 if ALIGNMENT == "ALIGNED" else -10.0

WIN_PROBABILITY  = PROBABILITY_BASE + PROB_STRENGTH + PROB_REVERSAL + PROB_ALIGNMENT
WIN_PROBABILITY  = max(10.0, min(WIN_PROBABILITY, 95.0))  # Cap between 10% and 95%

# 3. Mathematical Targets (using 50% of EIR for highly probable intraday swings)
INTRADAY_SWING = EIR * 0.50

if REV_DIR == "BULLISH" or (MOMENTUM == "BULLISH" and REV_DIR == "NEUTRAL"):
    MATH_ENTRY  = SPOT
    MATH_T1     = SPOT + INTRADAY_SWING
    MATH_T2     = RESISTANCE
    MATH_SL     = SUPPORT
    TRADE_TYPE  = "CE BUY / PE SHORT"
elif REV_DIR == "BEARISH" or (MOMENTUM == "BEARISH" and REV_DIR == "NEUTRAL"):
    MATH_ENTRY  = SPOT
    MATH_T1     = SPOT - INTRADAY_SWING
    MATH_T2     = SUPPORT
    MATH_SL     = RESISTANCE
    TRADE_TYPE  = "PE BUY / CE SHORT"
else:
    MATH_ENTRY  = "WAIT FOR RANGE BREAK"
    MATH_T1     = RESISTANCE
    MATH_T2     = SUPPORT
    MATH_SL     = "N/A - NEUTRAL"
    TRADE_TYPE  = "MEAN REVERSION / IRON CONDOR"

AFTER MATH ENGINE: "EIR={EIR:.1f} | Win Prob={WIN_PROBABILITY:.1f}% | T1={MATH_T1:.1f}"

# ═══════════════════════════════════════════════════════
# 5. FINAL OUTPUT — ALL VALUES LOCKED
# ═══════════════════════════════════════════════════════

═══════════════════════════════════════════════
NIFTY INTRADAY ANALYSIS — v15.1
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

TRADE RECOMMENDATION & TARGETS:  
  Action:        {TRADE_TYPE}
  Entry Zone:    {MATH_ENTRY}
  Target 1 (T1): {MATH_T1:.1f} (Mathematical Intraday Swing based on IV)
  Target 2 (T2): {MATH_T2} (Dominant OI Level)
  Stop Loss:     {MATH_SL} (Requires 15-min candle close beyond this level)
  
TRADING IMPLICATION:
  Momentum Bias:     {REV_DIR}
  Setup Confidence:  {CONFIDENCE}
  Statistical Setup Surety: {WIN_PROBABILITY:.1f}% probability of successful execution.
  Volatility Context: The market is pricing in a max daily range of {EIR:.1f} points based on {IV_BASELINE:.1f} IV.

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
- EIR computed via Spot * (IV/100) / 15.87?                    → [YES/NO]
- WIN_PROBABILITY capped correctly between 10% and 95%?        → [YES/NO]
- PROTOCOL VIOLATIONS: [0]
# ═══════════════════════════════════════════════════════
# ACTION: Provide SCRATCHPAD workings first.
# ═══════════════════════════════════════════════════════
"""
    lines.append(system_prompt)
    
    # 2. Add Nifty Summary
    lines.append(f"\nCURRENT DATA FOR ANALYSIS - FETCHED AT: {fetch_time}\n")
    lines.append("=" * 80 + "\n")
    lines.append(f"NIFTY DATA:\n- Current Value: {current_nifty}\n- Expiry Date: {expiry_date}\n- OI PCR: {oi_pcr:.2f}\n- Volume PCR: {volume_pcr:.2f}\n")
    
    # 3. Add BankNifty Summary (If available)
    if banknifty_data and 'data' in banknifty_data:
        bn_curr = banknifty_data.get('current_value', 0)
        bn_exp = banknifty_data.get('expiry_date', 'N/A')
        bn_pcr = banknifty_data.get('pcr_values', {}).get('oi_pcr', 0)
        bn_vol_pcr = banknifty_data.get('pcr_values', {}).get('volume_pcr', 0)
        lines.append(f"\nBANKNIFTY DATA:\n- Current Value: {bn_curr}\n- Expiry Date: {bn_exp}\n- OI PCR: {bn_pcr:.2f}\n- Volume PCR: {bn_vol_pcr:.2f}\n")

    # 4. Add Nifty Data Table (Optimized CSV format)
    lines.append(f"\n\nCOMPLETE NIFTY OPTION CHAIN DATA (CSV FORMAT):\n")
    lines.append("CE_ChgOI,CE_Vol,CE_LTP,CE_OI,CE_IV,STRIKE,PE_ChgOI,PE_Vol,PE_LTP,PE_OI,PE_IV,CE-PE_DIFF\n")
    
    # Filter to only include strikes within ATM +/- 600 points
    atm_strike = round(current_nifty / 50) * 50
    filtered_data = [d for d in oi_data if abs(d['strike_price'] - atm_strike) <= 600]
    
    for data in filtered_data:
        lines.append(format_csv_row(data))
        
    lines.append("\n")

    # Final string compilation
    full_content = "".join(lines)
    
    # Write to File
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ AI query data saved to: {os.path.basename(filepath)}")
        
        print("📧 Sending to Email...")
        if send_email_with_file_content(filepath):
            print("✅ Email dispatched successfully!")
            
        return filepath
    except Exception as e:
        print(f"❌ Error saving AI query data: {e}")
        return ""
