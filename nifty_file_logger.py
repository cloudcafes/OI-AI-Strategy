# nifty_file_logger.py
import os
import datetime
import requests
from typing import Dict, Any, List
from nifty_core_config import format_greek_value
import urllib3

# Disable SSL warnings and certificate verification for Telegram
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def resend_latest_ai_query() -> bool:
    """
    Resend the latest AI query file to Telegram
    Returns True if successful, False otherwise
    """
    try:
        base_dir = os.path.join(os.getcwd(), "ai-query-logs")
        
        # Check if directory exists
        if not os.path.exists(base_dir):
            print(f"❌ Directory not found: {base_dir}")
            return False
        
        # Get all .txt files in the directory
        txt_files = [f for f in os.listdir(base_dir) if f.endswith('.txt') and f.startswith('ai_query_')]
        
        if not txt_files:
            print("❌ No AI query files found to resend")
            return False
        
        # Sort by creation time (newest first)
        txt_files.sort(key=lambda x: os.path.getctime(os.path.join(base_dir, x)), reverse=True)
        
        latest_file = txt_files[0]
        latest_filepath = os.path.join(base_dir, latest_file)
        
        print(f"📄 Found latest file: {latest_file}")
        
        # Read the file content
        with open(latest_filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Extract timestamp from filename for display
        timestamp_str = latest_file.replace('ai_query_', '').replace('.txt', '')
        try:
            # Parse the timestamp for better formatting
            dt = datetime.datetime.strptime(timestamp_str, "%d_%m_%Y_%H_%M_%S")
            formatted_time = dt.strftime("%d-%b-%Y %H:%M:%S")
        except:
            formatted_time = timestamp_str
        
        # Add resend header
        resend_content = f"🔄 RESEND - LATEST AI QUERY ANALYSIS\n"
        resend_content += f"📅 Originally created: {formatted_time}\n"
        resend_content += f"🕒 Resent at: {datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')}\n"
        resend_content += "=" * 60 + "\n\n"
        resend_content += file_content
        
        # Send to Telegram
        print("📤 Resending to Telegram...")
        telegram_success = send_telegram_message(resend_content)
        
        if telegram_success:
            print("✅ Latest AI query resent to Telegram successfully!")
            return True
        else:
            print("❌ Failed to resend message to Telegram")
            return False
            
    except Exception as e:
        print(f"❌ Error resending latest AI query: {e}")
        return False

def resend_specific_ai_query(filename: str) -> bool:
    """
    Resend a specific AI query file to Telegram
    Args:
        filename: The filename to resend (e.g., 'ai_query_27_10_2024_14_30_00.txt')
    Returns True if successful, False otherwise
    """
    try:
        base_dir = os.path.join(os.getcwd(), "ai-query-logs")
        
        # Check if directory exists
        if not os.path.exists(base_dir):
            print(f"❌ Directory not found: {base_dir}")
            return False
        
        filepath = os.path.join(base_dir, filename)
        
        # Check if file exists
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            
            # Show available files
            txt_files = [f for f in os.listdir(base_dir) if f.endswith('.txt') and f.startswith('ai_query_')]
            if txt_files:
                print("📁 Available AI query files:")
                for f in sorted(txt_files, reverse=True)[:10]:  # Show latest 10
                    print(f"  - {f}")
            return False
        
        print(f"📄 Resending specific file: {filename}")
        
        # Read the file content
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Extract timestamp from filename for display
        timestamp_str = filename.replace('ai_query_', '').replace('.txt', '')
        try:
            # Parse the timestamp for better formatting
            dt = datetime.datetime.strptime(timestamp_str, "%d_%m_%Y_%H_%M_%S")
            formatted_time = dt.strftime("%d-%b-%Y %H:%M:%S")
        except:
            formatted_time = timestamp_str
        
        # Add resend header
        resend_content = f"🔄 RESEND - SPECIFIC AI QUERY ANALYSIS\n"
        resend_content += f"📅 Originally created: {formatted_time}\n"
        resend_content += f"🕒 Resent at: {datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')}\n"
        resend_content += "=" * 60 + "\n\n"
        resend_content += file_content
        
        # Send to Telegram
        print("📤 Resending to Telegram...")
        telegram_success = send_telegram_message(resend_content)
        
        if telegram_success:
            print("✅ Specific AI query resent to Telegram successfully!")
            return True
        else:
            print("❌ Failed to resend message to Telegram")
            return False
            
    except Exception as e:
        print(f"❌ Error resending specific AI query: {e}")
        return False

def list_ai_query_files(limit: int = 10) -> List[str]:
    """
    List available AI query files
    Args:
        limit: Maximum number of files to list
    Returns list of filenames
    """
    try:
        base_dir = os.path.join(os.getcwd(), "ai-query-logs")
        
        if not os.path.exists(base_dir):
            print(f"❌ Directory not found: {base_dir}")
            return []
        
        txt_files = [f for f in os.listdir(base_dir) if f.endswith('.txt') and f.startswith('ai_query_')]
        
        if not txt_files:
            print("❌ No AI query files found")
            return []
        
        # Sort by creation time (newest first)
        txt_files.sort(key=lambda x: os.path.getctime(os.path.join(base_dir, x)), reverse=True)
        
        print(f"📁 Latest {min(limit, len(txt_files))} AI query files:")
        for i, filename in enumerate(txt_files[:limit]):
            filepath = os.path.join(base_dir, filename)
            created_time = datetime.datetime.fromtimestamp(os.path.getctime(filepath))
            formatted_time = created_time.strftime("%d-%b-%Y %H:%M:%S")
            print(f"  {i+1}. {filename} (Created: {formatted_time})")
        
        return txt_files[:limit]
        
    except Exception as e:
        print(f"❌ Error listing AI query files: {e}")
        return []

def save_ai_query_data(oi_data: List[Dict[str, Any]], 
                      oi_pcr: float, 
                      volume_pcr: float, 
                      current_nifty: float,
                      expiry_date: str,
                      banknifty_data: Dict[str, Any] = None) -> str:
    """
    Save AI query data to a text file with timestamp in filename and send to Telegram
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
You are an expert Nifty/BankNifty/top10 Nifty Stocks by weighage option chain analyst with deep knowledge of historical patterns and institutional trading behavior. You read between the lines to decode both smart money AND retail perspectives. You perform mathematical calculations, psychological analysis, and interlink all data points to understand market dynamics. You analyze the market from the seller's point of view because they only drive the market. Take your time for thorough analysis.
----------------------------------------------------------------------------------------------------------------------------------------------------------
Analyze the provided OI data for Nifty index (weekly expiry), BankNifty index (monthly expiry), and top 10 Nifty Stocks (monthly expiry) to interpret the intraday trend. 

CRITICAL ANALYSIS FRAMEWORK - FOLLOW THIS ORDER:

1. Analyze PE & CE OI for each strike.
2. Analyze difference between PE & CE for each strike.
3. Analyze OI PCR.
4. Analyze Volume PCR.
5. Analyze separately once again for NIFTY ATM+-2 strike.
6. Analyze the market from seller's perspective.
7. Analyze smart money positions.
8. Keep in mind, NSE nifty & bank nifty are index so their analysis logic is completely different from NSE stocks analysis logic.
9. Always use historical proven threshold values for NIFTY and BANKNIFTY for making any calculation.
10. You entire analysis should be focussed on providing intraday 20-40 points nifty scalping opportunity.
11. I only take naked Nifty CE/PE buys for intraday.
12. Tips must consider for correct calculations: "Price action overrides OI data" & "Verify gamma direction (MM short puts = long futures)" & "Calculate probabilities using distance-to-strike formula" & "Institutional selling ≠ directional betting & Validate risk-reward with expectancy calculation" & "PCR + rising price = bullish, not bearish & High call volume + uptrend = momentum confirmation" & "Maximum probability cap at 70percentage without statistical proof" & "Theta decay > gamma for <24hr expiry" & "Daily range boundaries override OI walls"

----------------------------------------------------------------------------------------------------------------------------------------------------------
Provide output categorically:
- Short summary with clear directional bias and justification behind your logic.
- mathematically and scientifically calculated probability of current nifty price moving to strike+1 or strike -1.
- Breakdown of conflicting/confirming signals in short.
- Specific entry levels, stop-loss, targets, do not provide hedge instead only buy CE/PE.

Note: do not provide any value or calculation from thin air from your end. do not presume any thing hypothetically. do not include any information out of thin air.        

----------------------------------------------------------------------------------------------------------------------------------------------------------
I don't want you to agree with me just to be polite or supportive. Drop the filter be brutally honest, straightforward, and logical. Challenge my assumptions, question my reasoning, and call out any flaws, contradictions, or unrealistic ideas you notice.
Don't soften the truth or sugarcoat anything to protect my feelings I care more about growth and accuracy than comfort. Avoid empty praise, generic motivation, or vague advice. I want hard facts, clear reasoning, and actionable feedback.
Think and respond like a no-nonsense coach or a brutally honest friend who's focused on making me better, not making me feel better. Push back whenever necessary, and never feed me bullshit. Stick to this approach for our entire conversation, regardless of the topic.
And just give me answer no other words or appreciation or any bullshit or judgement. Just plain n deep answer which is well researched.

----------------------------------------------------------------------------------------------------------------------------------------------------------
Sample output and calculation format:
NIFTY INTRADAY SCALPING ANALYSIS
27-OCT-2025 | 09:51:11 | CURRENT: 25931 | EXPIRY: 28-OCT-2025 (WEEKLY)

---
CRITICAL VERDICT: SETUP IS DEAD. DO NOT TRADE.
Price has moved +55 points in 29 minutes (25876 → 25931) on massive call buying volume. This is a retail capitulation rally, not a tradeable scalp setup.
---
1. PE & CE OI ANALYSIS - LIVE DETERIORATION
| Strike | 09:22 CE OI | 09:51 CE OI | Δ Change | 09:22 PE OI | 09:51 PE OI | Δ Change | Signal |
|--------|---|---|---|---|---|---|---|
| 25700 | 33,114 | 26,901 | -8,158 | 146,615 | 173,800 | +39,778 | Call sellers winning |
| 25750 | 37,552 | 28,116 | -11,282 | 82,911 | 102,956 | +33,823 | Call sellers winning |
| 25800 | 120,713 | 82,418 | -33,528 | 144,703 | 221,892 | +124,457 | Massive call unwinding |
| 25850 | 198,356 | 62,408 | -17,691 | 88,171 | 178,442 | +142,884 | Call short squeeze |
| 25900 | 98,310 | 142,980 | -4,727 | 98,310 | 268,522 | +218,331 | Retail panic bought puts |
| 25950 | 28,584 | 108,753 | +30,436 | 28,584 | 102,067 | +83,936 | Gamma explosion |
---
2. BRUTAL REALITY: OI PCR WENT FROM 0.70 → 1.00 (EXTREME SHIFT)
At 09:22: OI PCR = 0.70 (call-heavy, bearish setup signal)
At 09:51: OI PCR = 1.00 (PERFECT PARITY, neutralized completely)
What this means:
- Call OI COLLAPSED from 1.2M → estimated 1.1M (calls being closed)
- Put OI EXPANDED from 1.3M → estimated 1.1M+ (puts being added)
- The put accumulation was NOT hedging—it was LIQUIDATION OF LOSING SHORTS
Timeline of events:
1. 09:22: Retail shorts puts at 25800 (collected premium, got crushed as price rose)
2. 09:31: Panic buying puts at 25800-25850-25900 (forced shorts covering)
3. 09:41: Put OI spike reached extreme (181k at 25800P)
4. 09:51: Put OI now at 221k at 25800P (MAXIMUM accumulation)
   - But THIS IS NOT DIRECTIONAL
   - This is forced liquidation of short positions + retail panic buying
---
3. PRICE ACTION OVERRIDES OI DATA (Critical Rule)
Key observation: Price UP +55 points despite massive put accumulation
This violates the bearish thesis because:
- If puts were accumulating as protection (bullish setup), price would have already reversed
- But price keeps rising = Puts are being accumulated by FORCED SHORT SELLERS
- Market makers shorting puts at 25800 are now UNDERWATER
- They're buying puts back to limit losses, not to hedge long positions
The puts at 25800P with 221k OI now represent:
- Original shorts (144k) trying to cover
- New shorts adding (77k) to collect more income on dip
- NET: Underwater shorts trying to manage damage
This is NOT a bullish put wall. This is a SHORT SQUEEZE of put sellers.
---
4. GAMMA DIRECTION VERIFICATION
At 25876 (09:22):
- Market makers SHORT 144k puts at 25800
- Delta ~0.35
- Hedge: Long ~50,646 Nifty
- Gamma: NEGATIVE (if price drops, they lose MORE)
At 25931 (09:51):
- Market makers SHORT 221k puts at 25800 (added 77k while price rose)
- Delta ~0.25 (decreased, should help them)
- BUT OI increased to 221k (HURT them due to larger notional)
- Hedge requirement: Long ~55,472 Nifty (INCREASED despite delta fall)
- Gamma: STILL NEGATIVE (OI growth > delta improvement)
Critical insight: As price RISES, market makers are FORCED to ADD shorts (25800P OI +77k). This means they are doubling down on a losing position. This is capitulation selling, not strategic positioning.
When do they stop? At first sign of reversal below 25900, they will panic-cover and trigger acceleration down. But UNTIL THEN, they keep selling puts, supporting the rally.
---
5. VOLUME PCR ANALYSIS - CONFIRMATION OF DEATH
Previous (09:41): 0.82
Current (09:51): 0.77 (deterioration)
But this understates the real situation:
| Strike | 09:41 Volume | 09:51 Volume | percentage Change | Signal |
|--------|---|---|---|---|
| 25800C | 467,919 | 555,377 | +18percentage | Calls still flowing OUT |
| 25800P | 681,295 | 873,250 | +28percentage | Puts flowing IN (forced) |
| 25850C | 577,435 | 695,327 | +20 percentage | Call distribution continues |
| 25850P | 648,930 | 829,442 | +27 percentage | Put forced buying continues |
| 25900C | 772,803 | 1,543,228 | +100 percentage | RETAIL EUPHORIA (highest volume EVER on chain) |
| 25900P | 459,200 | 1,121,408 | +144 percentage | PANIC PUT BUYING (extreme) |
What this tells us:
- 25900C volume at 1.5M is the HIGHEST SINGLE STRIKE ON ENTIRE CHAIN
- This is NOT smart money accumulation
- This is RETAIL BUYING AT THE TOP
- 25900P volume 1.1M also shows panic on the sell-off (puts being bought for protection)
Combined signal: Market is in MAXIMUM EUPHORIA + PANIC mode. This is a reversal candle forming.
---
6. ATM SHIFT - CRITICAL
At 09:22: ATM was 25850 (current price 25876 = ATM+26)
At 09:51: ATM is now 25900 (current price 25931 = ATM+31)
But look at 25900 OI structure:
- 25900C OI: 142,980 (new ATM call)
- 25900P OI: 268,522 (new ATM put)
- PE:CE ratio = 1.88:1 (EXTREME PE dominance at new ATM)
This is telling us:
- Retail bought calls expecting 26000+
- But at 25900 resistance, put buyers came in MASSIVELY
- The new ATM is DEFENDED by puts (1.88x ratio)
- This is a REJECTION, not a breakout
---
7. SELLER'S PERSPECTIVE - INSTITUTIONAL PANIC
Original shorts (09:22):
- Short 144k puts at 25800 (collected premium)
- Hedged with 50,646 long Nifty
- Expected market to hold above 25800
Current situation (09:51):
- Original shorts now UNDERWATER (price 25931 vs 25800 strike)
- Added 77k more shorts (trying to average down)
- Hedge now requires 55,472 long Nifty (INCREASED)
- Losing money on both: 1) Increased notional exposure, 2) Negative gamma
What happens next:
- If price stays above 25900, put sellers are DESTROYED
- They will be forced to buy futures to cover
- But volume at 25900 shows RESISTANCE (puts accumulating)
- Most likely: Reversal from 25900-25950, sharp drop to 25850-25800
---
8. SMART MONEY POSITIONING - DECODED
At 09:22: Bearish (short puts, collecting premium)
At 09:51: DEFENSIVE + LIQUIDATING
Evidence:
1. 25700P OI only increased +39,778 (vs +124,457 at 25800P)
   - If smart money was bullish, they'd accumulate more 25700P
   - They're NOT. This shows they're CONFUSED or EXITING
2. 25800P OI explosive growth +124,457
   - These are not new directional positions
   - These are FORCED COVERS by market makers
   - Smart money is SELLING into this panic (distributing puts)
3. 25900C volume 1.5M (retail)
   - Smart money NOT participating
   - This is pure retail euphoria
   - Smart money is watching, not trading
Net smart money stance: NEUTRAL + Awaiting reversal signal
---
9. HISTORICAL PROBABILITY - RECALCULATED FOR CURRENT STATE
Given: 
- Price +55 points from open
- Volume PCR 0.77 (put buying < call volume still)
- 25900 at parity (1.88 PE:CE)
- Retail volume EXTREME at 25900C
Historical pattern matches (2020-2025):
- Sample: 12 days with similar profile (retail euphoria at ATM+50, put accumulation at new ATM)
- Next 15-minute outcome:
  - Reversal down 20-40 points: 68 percentage (high probability)
  - Continue up 10-20 points: 18 percentage (retail squeeze attempt)
  - Sideways: 14 percentage (consolidation)
Why reversal is likely:
1. Theta acceleration: <24 hours to expiry (theta > gamma effect)
2. Put accumulation at 25900: Signals defensive positioning
3. Retail euphoria: Always precedes sharp reversal
4. OI PCR 1.00: Neutral = no institutional conviction for either direction
Maximum probability cap: 68 percentage (per your rule: no assumption >70 percentage)
---
10. DISTANCE-TO-STRIKE PROBABILITY CALCULATION
Current price: 25931
Distance to key strikes:
- 25900: -31 points (ATM, already approached)
- 25850: -81 points (resistance level)
- 25800: -131 points (original bear thesis, now unlikely)
Probability matrix:
- Nifty touches 25900 (0 more points needed): Already at it = 100 percentage
- Nifty holds above 25900: 65 percentage (based on put:call parity)
- Nifty drops to 25880-25890: 58 percentage (first reversal target)
- Nifty drops to 25850: 42 percentage (second reversal target)
- Nifty drops to 25800: 18 percentage (original bear thesis, now low prob)
---
11. RISK-REWARD EXPECTANCY - FINAL CALCULATION
Old setup (09:22): Buy 25800 PE at 140, risk 50 points up, target 50 points down
- Expected value: POSITIVE (72 percentage win prob -> 40 reward - 28 percentage loss prob -> 50 loss)
Current setup (09:51): Buy 25800 PE at market (estimated 220)
- Entry: 25800 PE at ~220 (theta-crushed from 140)
- Stop-loss: 25950 (80 points up = total risk now 200+)
- Target: 25850 (80 points down = gain only 100-120)
- Probability: 42 percentage (low, reversal pending)
- Expected value: NEGATIVE (42 percentage -> 100 - 58 percentage -> 200 = 42 - 116 = -74)
Verdict: DO NOT TRADE. Expectancy is negative.
---
12. CONFLICTING vs CONFIRMING SIGNALS
CONFIRMING SIGNALS (Bearish - Now WEAK):
1. ✗ 25800P OI 221k (was highest, now weak because underwater shorts)
2. ✗ Put accumulation (now revealed as forced, not directional)
3. ✗ 25700P accumulation (did NOT increase as expected = bearish thesis FAILING)
CONFLICTING SIGNALS (Bullish - Now STRONG):
1. ✓ Price +55 points (clear uptrend)
2. ✓ 25900C volume 1.5M (retail buying climax)
3. ✓ Call OI declining (not being held, but calls are winning intraday)
4. ✓ OI PCR 1.00 (neutralized, no institutional conviction for downside)
Score:
- Bearish signals: 3 (All WEAKENED or INVALIDATED)
- Bullish signals: 4 (All STRENGTHENED)
- Net: BEARISH THESIS 30percentage confidence, BULLISH SETUP 70percentage confidence
The reversal is PENDING, not completed. Do NOT short puts. Do NOT buy puts.
---
13. WHAT TO DO NOW
WAIT for price to hit 25950-26000 (terminal exhaustion zone)
Then, DO THIS:
IF price BREAKS ABOVE 26000:
- Entry: 26000 CE at market (estimated 60-80)
- Stop-Loss: 25950 (close below)
- Target: 26050 → 26000 CE ~100-120 = 40-50percentage gain
- Probability: 15percentage (NOT recommended, too risky)
IF price REVERSES FROM 25950 (most likely):
- Entry: 25900 PE at market (estimated 50.5)
- Stop-Loss: 25980 (above current resistance)
- Target: 25850 → 25900 PE ~100-120 = 100-140percentage gain
- Probability: 68percentage (REAL setup, wait for confirmation)
- Time frame: 30-60 minutes
CURRENT LEVEL (25931): NO EDGE. Do NOT trade.
---
14. THETA DECAY WARNING
Time to expiry: ~18 hours
At current IV levels:
- 25800 PE theta: ~2.5 per hour (accelerating)
- 25900 PE theta: ~1.8 per hour
- 25900 CE theta: ~1.2 per hour
By 2:30 PM:
- All options lose 30-40percentage of time value
- Gamma effects DIMINISH relative to theta
- Reversions to intrinsic value accelerate
Implication: Any position held past 2:00 PM is fighting theta decay. Current time is 09:51 AM. You have ~4 hours of viable gamma window left. After that, theta kills everything.
---
15. FINAL VERDICT
STATUS: WAIT FOR REVERSAL CONFIRMATION AT 25950+
Current Bias: NEUTRAL-BULLISH (but exhaustion forming)
Probability of 80-point down move (to 25850): 42percentage (NOT >70percentage, too low)
DO NOT ENTER TRADES AT:
- Current price 25931 (too late, chasing)
- 25800 PE (wrong strike, wrong timing)
- Any bearish position (thesis broken)
WAIT FOR:
- Price to tag 25950-26000 (exhaustion confirmation)
- Then reversal candle (close below 25950 on 5-min)
- Volume confirmation on drop
- THEN enter 25900 PE for downside scalp
Expected scalp window: 10:00 AM - 2:00 PM (if reversal confirms)
---
16. BANKNIFTY STATUS
Current: 57959.55 | OI PCR: 0.97 | Volume PCR: 0.79
- OI PCR 0.97 (near parity, like Nifty)
- 58000C OI 65,056 (highest call, but retail driven)
- 58000P OI 46,634 (lower than calls = call dominance)
- BankNifty structure LESS bearish than Nifty
BankNifty will lag Nifty downside on reversal. Focus on Nifty first.
---
SUMMARY TABLE
| Metric | 09:22 | 09:51 | Interpretation |
|--------|-------|-------|---|
| Price | 25876 | 25931 | +55 pts (rally, not down) |
| OI PCR | 0.70 | 1.00 | Bearish thesis DEAD |
| Volume PCR | 0.84 | 0.77 | Put panic buying |
| 25800P OI | 144k | 221k | Forced short covers |
| 25900C Vol | 446k | 1.54M | Retail climax |
| 25800P PE:CE | 2.44:1 | 2.69:1 | Still bearish but WEAK |
| Probability (Down 50 pts) | 68percentage | 18percentage | THESIS BROKEN |
| Best Setup | Bearish | Bullish Reversal | Wait for confirmation |
---
17. BRUTAL HONESTY
Your original 09:22 analysis was CORRECT at that time.
But markets move. The setup INVALIDATED in 29 minutes due to:
1. Retail capitulation buying (euphoria)
2. Forced short covering (not strategic selling)
3. Gamma relief (put OI growth = underwater shorts trying to survive)
4. OI PCR parity (no institutional conviction)
The only tradeable setup NOW is the REVERSAL, not the breakdown.
Waiting for price to hit 25950-26000 and then fade is the ONLY edge left. The bearish edge you identified is DEAD. Do not chase it.
Price action overrides OI data. You were taught this. Apply it.

----------------------------------------------------------------------------------------------------------------------------------------------------------
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
        print("📤 Sending to Telegram...")
        telegram_success = send_telegram_message(full_content)
        if telegram_success:
            print("✅ Message sent to Telegram successfully!")
        else:
            print("❌ Failed to send message to Telegram")
        
        return filepath
    except Exception as e:
        print(f"❌ Error saving AI query data: {e}")
        return ""