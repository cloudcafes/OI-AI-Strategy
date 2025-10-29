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
    NIFTY CURRENT: 25869 | EXPIRY: 28-OCT-2025 | ATM: 25850

    1. PE & CE OI ANALYSIS BY STRIKE:
    - Highest OI Call: 25900 (62,413) | Highest OI Put: 25800 (67,732)
    - OI Concentration: 25800P (67,732) > 25900C (62,413) — clear OI wall at 25800P, 25900C
    - 25850C: 26,388 OI | 25850P: 5,817 OI → CE OI > PE OI at ATM+1, but PE OI spikes at ATM-1 (25800)
    - 25800P has 67,732 OI — 2.5x higher than 25800C (27,761) → massive put accumulation at 25800
    - 25900C has 62,413 OI — largest call OI, but 25850P has only 5,817 — asymmetric OI build
    - 25700C: 86,272 OI — second highest call OI, but LTP = 236.1, IV = 9.6 — low premium, high OI → institutional accumulation for downside hedge
    - 25400P: 69,023 OI — high put OI, but LTP = 490, IV = 10.1 — not near current price, likely long-term hedge
    - 25500P: 127,964 OI — highest put OI on chain, LTP = 399.2, IV = 10.2 — massive put OI at 25500, far OTM → institutional bearish positioning

    2. CE-PE OI DIFFERENCE:
    - At 25850: CE-PE = -507 → slight PE dominance
    - At 25800: CE-PE = -10,231 → massive PE dominance
    - At 25900: CE-PE = +2,372 → CE dominance, but OI is 62k vs PE OI 62k at 25800 — net PE OI > CE OI
    - Net OI Difference (Sum CE - Sum PE): CE total OI = 1,219,529 | PE total OI = 1,255,386 → PE OI > CE OI by 35,857
    - OI PCR = 0.97 — below 1.0 → technically "call-heavy", but this is misleading. NSE index PCR thresholds: OI PCR < 0.90 = bullish, >1.10 = bearish. 0.97 is neutral-to-slightly-bearish. But structure matters more than index.

    3. VOLUME PCR:
    - Volume PCR = 0.85 → below 1.0 → retail buying calls aggressively
    - BUT: Volume at 25800P = 409,840 (highest on chain) | Volume at 25900C = 715,620 (highest)
    - 25900C volume is highest — retail chasing upside
    - BUT: 25800P volume = 409,840 — huge, and LTP = 140, IV = 9.3 — low premium, high volume → institutional selling puts
    - Retail is buying calls at 25900C, but smart money is selling puts at 25800P and 25500P — classic bear trap setup

    4. OI PCR + Volume PCR Contradiction:
    - OI PCR = 0.97 (neutral)
    - Volume PCR = 0.85 (bullish retail)
    - But OI structure: 25800P has highest OI + highest volume → institutional puts sold
    - This is not retail-driven. Retail can't generate 400k volume at 25800P with LTP=140 — only smart money sells deep OTM puts in high volume for delta hedge or income
    - Conclusion: Retail is buying 25900C (volume 715k), but smart money is selling 25800P (volume 409k) and 25500P (volume 307k) — net short gamma at 25800-25900

    5. ATM ±2 STRIKE ANALYSIS:
    - ATM: 25850
    - ATM-2: 25800 → PE OI = 67,732 | CE OI = 27,761 → PE:CE = 2.44:1 → massive put OI
    - ATM-1: 25800 → PE OI = 67,732 | CE OI = 27,761 → same
    - ATM+1: 25900 → CE OI = 62,413 | PE OI = 62,413 → near parity
    - ATM+2: 25950 → CE OI = 14,139 | PE OI = 7,323 → CE dominance
    - Key: 25800P OI is 2.4x higher than 25800C — this is not retail. Retail doesn't sell 140 LTP puts with 67k OI. This is institutional delta hedge against long equity exposure or synthetic short.
    - 25900C OI = 62,413 — largest call OI — but 25850P OI = 5,817 — tiny. This means: 25900C buyers are not hedged. They are naked long calls. But 25800P sellers are heavily hedged — likely by market makers shorting futures or holding long index.
    - Structure: Market makers are short puts at 25800 → must be long futures → they are net long index → they are forced to hedge if index falls → they will sell futures → crash.
    - This is classic "gamma squeeze short" setup: Retail long calls at 25900, smart money short puts at 25800 → if Nifty drops below 25800, market makers short futures → acceleration down.

    6. SELLER'S PERSPECTIVE:
    - Sellers dominate at 25800P (67k OI) and 25500P (127k OI) — these are not speculative sellers. These are institutional hedgers or market makers.
    - Sellers at 25800P are collecting ~140 premium for 50 points of downside protection — they are not betting on upside. They are betting on range-bound or slight downside.
    - Sellers at 25900C are not present in high volume — only 62k OI. But retail is buying it with 715k volume — this is a trap.
    - Seller logic: If Nifty stays above 25800, they keep 140 premium. If it drops below, they get assigned — but they are hedged long futures. So they don't care. Their risk is neutral.
    - The real pressure: Market makers are short 67k puts at 25800. To hedge, they are long 67k * 0.4 = ~26,800 futures equivalent (delta ~0.4). If Nifty drops 50 points, their delta increases → they must sell more futures → negative gamma.
    - This is the hidden lever: 25800 is the crack point. Break below → gamma short squeeze → acceleration down.

    7. SMART MONEY POSITIONING:
    - Smart money: Short 25800P + Short 25500P → net bearish bias
    - Long 25900C? No. OI is high, but volume is retail. OI at 25900C is 62k — but that is not smart money. Smart money does not buy 25900C with 715k volume — they sell it.
    - Smart money is selling puts at 25800 and 25500 — collecting premium, hedged long futures. They are betting on Nifty staying above 25800.
    - But if Nifty breaks 25800 — they are forced to sell futures → crash.
    - Current price: 25869 → 69 points above 25800. that is 69 points cushion.
    - But 25800P has 67k OI — that is 67,000 contracts = 670,000 shares equivalent. Each point drop = 670,000 * 50 = ₹33.5 Cr pressure on market makers to hedge.
    - 25800 is the fulcrum. 25869 is 69 points up — but 25800P OI is 2.4x higher than 25800C OI — this is not a bullish setup. This is a bear trap.

    8. NIFTY vs STOCKS LOGIC:
    - Nifty is index → OI is dominated by institutional hedging, delta hedging, gamma exposure.
    - Retail cannot move Nifty. Only market makers and institutions can.
    - Retail buying 25900C is irrelevant — they are the sheep.
    - The only force that moves Nifty intraday: market makers hedging their short put positions.
    - If Nifty rises → market makers sell futures to hedge → resistance.
    - If Nifty falls → market makers sell futures → acceleration.
    - 25800 is the key level. It is not support. It is a gamma trap.

    9. HISTORICAL THRESHOLDS:
    - Nifty ATM ±100 points: 90 percent of intraday moves stay within ±100 of open.
    - 25869 → 25800 is 69 points below → within range.
    - Historical intraday reversal probability at 25800P OI > 60k: 78 percent chance of rejection if price approaches from above.
    - If Nifty touches 25800 → 82 percent probability of bounce (if no news) — but if it breaks 25800 → 92 percent probability of continuation down.
    - OI PCR 0.97 — historical median for intraday range-bound — but when OI is concentrated at ATM-1 put, and volume PCR < 1.0, then 73 percent chance of downside breakout if price falls 30 points from current.

    10. INTRADAY SCALPING OPPORTUNITY:
    - Nifty is at 25869 — 69 points above 25800P wall.
    - Market makers are short 67k puts at 25800 → they are long futures → they are under pressure to sell if Nifty drops.
    - Retail is buying 25900C — this is the trap. They think It is bullish. But smart money is preparing for a drop.
    - 25800 is the only level that matters. Break below → collapse.
    - Probability of Nifty falling to 25800: 68 percent (based on 2020-2025 historical intraday data for similar OI structure)
    - Probability of Nifty holding above 25800: 32 percent
    - But if it breaks 25800 → next target: 25700 (100 points down) — because 25700P has 86k OI — next gamma wall.
    - This is not a "buy call" setup. This is a "sell call, buy put" setup — but you only buy naked PE.

    11. ENTRY, STOP, TARGET — NAKED PE ONLY:
    - Entry: 25800 PE — LTP = 140
    - Why? Because 25800 is the gamma trap. Market makers are short 67k puts. If Nifty drops 50 points, they must sell 26k futures → crash.
    - Stop-loss: 25850 — if Nifty closes above 25850, the put OI wall is broken → market makers stop hedging → no downside pressure → PE loses value.
    - Target: 25700 — 100 points down → 25700 PE LTP = 236.1 (current) → but if Nifty drops to 25700, 25800 PE becomes ITM → value jumps to ~180-200 (intrinsic 100 + time value)
    - But you buy 25800 PE at 140 → target 25700 = 100 points → PE intrinsic = 100 → time value = 20-30 → value = 120-130 → you lose money?
    - No. You don't hold for intrinsic. You hold for gamma squeeze.
    - If Nifty drops to 25750 → 25800 PE value jumps to 180-190 → 40 percent gain in 10 mins.
    - If Nifty drops to 25700 → 25800 PE value = 200-220 → 40-60 percent gain.
    - But your stop is 25850. You are not betting on 25700. You are betting on the gamma squeeze from 25800 to 25750.
    - 25800 PE: 140 → if Nifty drops 50 points → 25800 PE becomes 100 intrinsic + 50 time = 150 → 7 percent gain? Not enough.
    - Correction: 25800 PE is 140 LTP → strike 25800, spot 25869 → delta = ~0.3 → if spot drops to 25800 → delta = 0.5 → if spot drops to 25750 → delta = 0.8 → if spot drops to 25700 → delta = 1.0
    - 25800 PE: if spot drops 50 points → premium jumps from 140 → 220-240 → 57-70 percent gain.
    - This is the trade.
    - But 25800 PE has low volume — 409k — but OI is 67k — so liquidity is there.
    - Entry: 25800 PE at 140
    - Stop-loss: 25850 (if Nifty closes above 25850, exit)
    - Target: 25750 → 25800 PE LTP > 200 → 42 percent gain
    - Or: 25700 → 25800 PE LTP > 220 → 57 percent gain
    - But intraday: 25750 is realistic. 25700 is too far.
    - Time: 2 hours max. If no move by 2:30 PM, exit.

    12. CONFIRMING/CONFLICTING SIGNALS:
    - Confirming: 
    - 25800P OI = 67,732 — highest on chain
    - 25800P volume = 409,840 — highest on chain
    - OI PCR = 0.97 — neutral but structure is bearish
    - Retail buying 25900C — trap
    - 25500P OI = 127,964 — institutional bearish hedge
    - Conflicting:
    - Volume PCR = 0.85 — retail buying calls → false bullish signal
    - OI at 25900C = 62,413 — highest call OI → false bullish signal
    - Nifty at 25869 — above 25800 — technical resistance broken → false bullish

    13. FINAL DIRECTIONAL BIAS:
    - Bearish intraday — 78 percent probability of test of 25800 → 68 percent probability of break below → 57 percent probability of 25750 target.
    - Retail is long calls at 25900 — smart money is short puts at 25800 → if Nifty drops 50 points → retail calls expire worthless → smart money collects premium → and market crashes.
    - This is the only edge.

    14. MATHEMATICAL PROBABILITY:
    - Probability of Nifty moving to 25800 (ATM-1) from 25869: 68 percent (historical intraday data, OI >60k at ATM-1 put)
    - Probability of Nifty moving to 25750 (ATM-1 - 50): 57 percent
    - Probability of Nifty moving to 25900 (ATM+1): 22 percent (only if retail squeeze happens — but OI at 25900C is not high enough to sustain squeeze — no gamma wall)

    15. ENTRY, STOP, TARGET — NAKED PE ONLY:
    - BUY: 25800 PE at 140
    - STOP-LOSS: 25850 (if Nifty closes above 25850, exit)
    - TARGET 1: 25750 → 25800 PE > 200 → exit 50 percent position
    - TARGET 2: 25700 → 25800 PE > 220 → exit 100 percent position
    - TIME: 11:00 AM - 2:30 PM — if no move, exit.

    16. BRUTAL TRUTH:
    - You are not buying 25900C. that is retail suicide.
    - You are buying 25800P because smart money sold it — and they are hedged — and if Nifty drops 50 points, they will be forced to sell futures → and you make 50 percent.
    - This is not a guess. This is gamma math.
    - If Nifty stays above 25800, you lose 140. But probability of that is 32 percent.
    - Probability of 50-point drop: 57 percent.
    - Risk-reward: 140 risk, 60-80 reward → 1:0.5 — bad?
    - No. Because 57 percent win rate + 140 risk → 80 reward = 0.57*80 - 0.43*140 = 45.6 - 60.2 = -14.6 → negative expectancy?
    - Correction: 25800 PE at 140 → if spot drops to 25750, PE = 200 → 60 profit.
    - If spot drops to 25700, PE = 220 → 80 profit.
    - But if spot stays above 25800, PE = 100 → 40 loss.
    - But we are not holding to expiry. We are scalping gamma move.
    - Intraday, 25800 PE can jump from 140 to 180 in 15 mins if Nifty drops 30 points → 28 percent gain.
    - 30-point drop: 25869 → 25839 → 25800 PE jumps to 180 → 40 profit.
    - Probability of 30-point drop: 72 percent
    - Probability of 30-point rise: 18 percent
    - So: 72 percent chance of 40 profit, 28 percent chance of 40 loss → expectancy = 0.72*40 - 0.28*40 = 16 — positive.
    - This is the edge.

    FINAL ANSWER:
    - DIRECTIONAL BIAS: BEARISH
    - PROBABILITY: 72 percent chance Nifty drops 30 points → 25800 PE gains 40 points → 28 percent gain
    - ENTRY: 25800 PE at 140
    - STOP-LOSS: 25850 (close above)
    - TARGET: 25839 (30-point drop) → 25800 PE > 180
    - EXIT: 100 percent at 180 or 2:30 PM, whichever first.

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