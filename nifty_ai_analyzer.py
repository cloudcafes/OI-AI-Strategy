# nifty_ai_analyzer.py
import os
import time
import json
import datetime
import requests
import httpx
from typing import Dict, Any, List, Optional
from openai import OpenAI

class NiftyAIAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        # Use env var or provided key; prefer env for security
        self.api_key = api_key or "sk-df60b28326444de6859976f6e603fd9c"
        self.client = None
        self.history_file = "analysis_history.txt"
        self.initialize_client()

    def initialize_client(self) -> bool:
        """Initialize the DeepSeek API client; SSL verify controlled by env DEEPSEEK_VERIFY_SSL."""
        try:
            if not self.api_key:
                raise RuntimeError("DeepSeek API key not found. Set DEEPSEEK_API_KEY env var or pass api_key to NiftyAIAnalyzer.")

            verify_ssl_env = os.getenv("DEEPSEEK_VERIFY_SSL", "false").lower() in ("1", "true", "yes")
            http_client = httpx.Client(verify=verify_ssl_env, timeout=30.0)

            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
                http_client=http_client,
                max_retries=2
            )

            # Smoke test
            _ = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0
            )
            print("✅ DeepSeek AI client initialized successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize DeepSeek client: {e}")
            self.client = None
            return False

    def save_analysis_to_history(self, raw_data: str, ai_response: str) -> bool:
        """Save both raw data and AI response to history file with latest on top."""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"deepseek analysis done at {timestamp}"
            separator = "=" * 80
            
            # Format the entry with both raw data and AI response
            new_entry = f"{header}\n{separator}\n"
            new_entry += "RAW DATA SENT TO AI:\n{separator}\n{raw_data}\n\n"
            new_entry += f"AI ANALYSIS RESPONSE:\n{separator}\n{ai_response}\n{separator}\n\n"

            existing_content = ""
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(new_entry + existing_content)

            print(f"✅ Analysis saved to {self.history_file}")
            return True

        except Exception as e:
            print(f"❌ Error saving analysis to history: {e}")
            return False

    def _clean_ai_response(self, text: str) -> str:
        """Clean and format AI response for better console display."""
        if not text:
            return "No response from AI"
        
        # Remove markdown code blocks
        cleaned = text.replace("```json", "").replace("```", "")
        
        # Remove excessive asterisks but keep some for emphasis
        cleaned = cleaned.replace("**", "").replace("*", "")
        
        # Clean up excessive line breaks
        lines = cleaned.split('\n')
        cleaned_lines = []
        prev_empty = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not prev_empty:
                    cleaned_lines.append('')
                    prev_empty = True
            else:
                cleaned_lines.append(stripped)
                prev_empty = False
        
        # Ensure proper spacing between sections
        result = '\n'.join(cleaned_lines)
        
        # Fix common formatting issues
        result = result.replace(' : ', ': ')
        result = result.replace(' , ', ', ')
        result = result.replace(' . ', '. ')
        
        return result

    def find_atm_strikes(self, oi_data: List[Dict[str, Any]], current_price: float, range_strikes: int = 10):
        """Find ATM strikes within specified range for detailed analysis"""
        if not oi_data:
            return []
        
        # Get all strike prices
        strike_prices = sorted(list(set(data['strike_price'] for data in oi_data)))
        
        # Find closest strike
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_price))
        closest_index = strike_prices.index(closest_strike)
        
        # Get strikes within range
        start_index = max(0, closest_index - range_strikes)
        end_index = min(len(strike_prices), closest_index + range_strikes + 1)
        selected_strikes = strike_prices[start_index:end_index]
        
        # Filter records for selected strikes
        atm_data = [data for data in oi_data if data['strike_price'] in selected_strikes]
        
        return atm_data

    def find_key_levels(self, oi_data: List[Dict[str, Any]]):
        """Find key resistance and support levels based on max OI"""
        if not oi_data:
            return {}, {}
        
        # Find max CE OI for resistance
        max_ce_oi = 0
        resistance_strike = None
        max_ce_oi_value = 0
        
        # Find max PE OI for support
        max_pe_oi = 0
        support_strike = None
        max_pe_oi_value = 0
        
        for data in oi_data:
            # Check for resistance (max CE OI)
            if data['ce_oi'] > max_ce_oi:
                max_ce_oi = data['ce_oi']
                resistance_strike = data['strike_price']
                max_ce_oi_value = data['ce_oi']
            
            # Check for support (max PE OI)
            if data['pe_oi'] > max_pe_oi:
                max_pe_oi = data['pe_oi']
                support_strike = data['strike_price']
                max_pe_oi_value = data['pe_oi']
        
        resistance_info = {
            'strike': resistance_strike,
            'ce_oi': max_ce_oi_value
        } if resistance_strike else {}
        
        support_info = {
            'strike': support_strike,
            'pe_oi': max_pe_oi_value
        } if support_strike else {}
        
        return resistance_info, support_info

    def format_data_for_ai(self,
                           oi_data: List[Dict[str, Any]],
                           oi_pcr: float,
                           volume_pcr: float,
                           current_nifty: float,
                           expiry_date: str,
                           stock_data: Optional[Dict[str, Any]] = None,
                           banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Format optimized data for AI analysis - full PCRs + ATM details + key levels"""
        formatted_text = f"NIFTY ANALYSIS DATA:\n"
        formatted_text += f"- Spot: {current_nifty} | Expiry: {expiry_date}\n"
        formatted_text += f"- Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"
        
        # Find ATM ±10 strikes for detailed analysis
        atm_data = self.find_atm_strikes(oi_data, current_nifty, 10)
        if atm_data:
            atm_oi_pcr, atm_volume_pcr = self.calculate_pcr_for_range(atm_data)
            formatted_text += f"- ATM Zone (±10): OI={atm_oi_pcr:.2f}, Volume={atm_volume_pcr:.2f}\n"
        
        # Find key levels
        resistance, support = self.find_key_levels(oi_data)
        formatted_text += "- Key Levels:\n"
        if resistance:
            formatted_text += f"  * Resistance: {resistance['strike']} (Max CE OI: {resistance['ce_oi']:,})\n"
        if support:
            formatted_text += f"  * Support: {support['strike']} (Max PE OI: {support['pe_oi']:,})\n"
        
        # Add high activity strikes
        high_volume_strikes = self.find_high_activity_strikes(oi_data)
        if high_volume_strikes:
            formatted_text += "  * High Activity Strikes:\n"
            for strike in high_volume_strikes[:3]:  # Top 3 only
                formatted_text += f"    {strike['strike']} (Volume: {strike['total_volume']:,})\n"
        
        # BankNifty alignment
        if banknifty_data:
            banknifty_pcr = banknifty_data.get('oi_pcr', 0)
            alignment = "Bullish" if banknifty_pcr > 1.0 else "Bearish" if banknifty_pcr < 1.0 else "Neutral"
            formatted_text += f"- BankNifty Alignment: {alignment} (PCR: {banknifty_pcr:.2f})\n"
        
        formatted_text += "\n" + "=" * 80 + "\n"
        formatted_text += "ATM ±10 STRIKES DETAILED DATA:\n"
        formatted_text += "=" * 80 + "\n"
        
        # Add detailed ATM strikes data
        for data in atm_data:
            strike = data['strike_price']
            formatted_text += (
                f"Strike {strike}: "
                f"CE[ChgOI:{data.get('ce_change_oi', 0):,}, Vol:{data.get('ce_volume', 0):,}, "
                f"LTP:{data.get('ce_ltp', 0.0):.1f}, OI:{data.get('ce_oi', 0):,}, IV:{data.get('ce_iv', 0.0):.1f}%] | "
                f"PE[ChgOI:{data.get('pe_change_oi', 0):,}, Vol:{data.get('pe_volume', 0):,}, "
                f"LTP:{data.get('pe_ltp', 0.0):.1f}, OI:{data.get('pe_oi', 0):,}, IV:{data.get('pe_iv', 0.0):.1f}%]\n"
            )
        
        # Stock data summary
        if stock_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "TOP 10 NIFTY STOCKS SUMMARY\n"
            formatted_text += "=" * 80 + "\n"
            formatted_text += f"{'SYMBOL':<15} {'WEIGHT':<10} {'PRICE':<10} {'OI PCR':<10} {'VOL PCR':<10}\n"
            formatted_text += "-" * 80 + "\n"
            
            for symbol, info in stock_data.items():
                price = info.get('current_price', 0)
                oi_pcr_val = info.get('oi_pcr', 0)
                vol_pcr_val = info.get('volume_pcr', 0)
                weight = info.get('weight', 0)
                
                formatted_text += f"{symbol:<15} {weight:<10.4f} {price:<10} {oi_pcr_val:<10.2f} {vol_pcr_val:<10.2f}\n"
            
            formatted_text += "=" * 80 + "\n"
        
        return formatted_text

    def calculate_pcr_for_range(self, oi_data: List[Dict[str, Any]]):
        """Calculate PCR for a specific range of strikes"""
        total_ce_oi = 0
        total_pe_oi = 0
        total_ce_volume = 0
        total_pe_volume = 0
        
        for data in oi_data:
            total_ce_oi += data['ce_oi']
            total_pe_oi += data['pe_oi']
            total_ce_volume += data['ce_volume']
            total_pe_volume += data['pe_volume']
        
        # Calculate PCR values with zero safeguards
        try:
            oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
        except ZeroDivisionError:
            oi_pcr = 1.0
        
        try:
            volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 1.0
        except ZeroDivisionError:
            volume_pcr = 1.0
        
        return oi_pcr, volume_pcr

    def find_high_activity_strikes(self, oi_data: List[Dict[str, Any]], top_n: int = 5):
        """Find strikes with highest trading activity"""
        if not oi_data:
            return []
        
        activity_data = []
        for data in oi_data:
            total_volume = data['ce_volume'] + data['pe_volume']
            if total_volume > 0:
                activity_data.append({
                    'strike': data['strike_price'],
                    'total_volume': total_volume,
                    'ce_volume': data['ce_volume'],
                    'pe_volume': data['pe_volume']
                })
        
        # Sort by total volume descending and return top N
        activity_data.sort(key=lambda x: x['total_volume'], reverse=True)
        return activity_data[:top_n]

    def get_ai_analysis(self,
                        oi_data: List[Dict[str, Any]],
                        oi_pcr: float,
                        volume_pcr: float,
                        current_nifty: float,
                        expiry_date: str,
                        stock_data: Optional[Dict[str, Any]] = None,
                        banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Request AI analysis with optimized data format"""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        # Format optimized data for AI
        formatted_data = self.format_data_for_ai(
            oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date, stock_data, banknifty_data
        )

        # Your existing prompt - preserved exactly as is
        SYSTEM_PROMPT = """
        You are an expert Nifty/BankNifty/top10 Nifty Stocks by weightage option chain analyst with deep knowledge of historical patterns and institutional trading behavior. You read between the lines to decode both smart money AND retail perspectives. You perform mathematical calculations, psychological analysis, and interlink all data points to understand market dynamics. You analyze the market from the seller's point of view because they only drive the market. Take your time for thorough analysis.

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Analyze the provided OI data for Nifty index (weekly expiry), BankNifty index (monthly expiry), and top 10 Nifty Stocks (monthly expiry) to interpret the intraday trend. 

        CRITICAL ANALYSIS FRAMEWORK - FOLLOW THIS ORDER:

        1. Analyze PE & CE OI for each strike.
        2. Analyze difference between PE & CE for each strike.
        3. Analyze OI PCR.
        4. Analyze Volume PCR.
        5. Analyze seprately once again for NIFTY ATM+-2 strike.
        6. Analyze the market from seller's perspective.
        7. Analyze smart money positions.
        8. Keep in mind, NSE nifty & bank nifty are index so their analysis logic is completely different from NSE stocks analysis logic.
        9. Always use historical proven threshold values for NIFTY and BANKNIFTY for making any calculation.
        10. You entire analysis should be focussed on providing intraday 20-40 points nifty scalping opportunity.
        11. I only take naked Nifty CE/PE buys for intraday.

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Provide output categorically:
        - Short summary with clear directional bias and justification behind your logic.
        - mathemetically and scientifically calculated probability of current nifty price moving to strike+1 or strike -1.
        - Breakdown of conflicting/confirming signals in short.
        - Specific entry levels, stop-loss, targets, do not provide hedge instead only buy CE/PE.

        Note: do not provide any value or calculation from thin air from your end. do not presume any thing hypothetically. do not include any information out of thin air.        

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        I don't want you to agree with me just to be polite or supportive. Drop the filter be brutally honest, straightforward, and logical. Challenge my assumptions, question my reasoning, and call out any flaws, contradictions, or unrealistic ideas you notice.

        Don't soften the truth or sugarcoat anything to protect my feelings I care more about growth and accuracy than comfort. Avoid empty praise, generic motivation, or vague advice. I want hard facts, clear reasoning, and actionable feedback.

        Think and respond like a no-nonsense coach or a brutally honest friend who's focused on making me better, not making me feel better. Push back whenever necessary, and never feed me bullshit. Stick to this approach for our entire conversation, regardless of the topic.

        And just give me answer no other worda or appreciation or any bullshit or judgements. Just plain n deep answer which is well researched.
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

        6. SELLER’S PERSPECTIVE:
        - Sellers dominate at 25800P (67k OI) and 25500P (127k OI) — these are not speculative sellers. These are institutional hedgers or market makers.
        - Sellers at 25800P are collecting ~140 premium for 50 points of downside protection — they are not betting on upside. They are betting on range-bound or slight downside.
        - Sellers at 25900C are not present in high volume — only 62k OI. But retail is buying it with 715k volume — this is a trap.
        - Seller logic: If Nifty stays above 25800, they keep 140 premium. If it drops below, they get assigned — but they are hedged long futures. So they don’t care. Their risk is neutral.
        - The real pressure: Market makers are short 67k puts at 25800. To hedge, they are long 67k * 0.4 = ~26,800 futures equivalent (delta ~0.4). If Nifty drops 50 points, their delta increases → they must sell more futures → negative gamma.
        - This is the hidden lever: 25800 is the crack point. Break below → gamma short squeeze → acceleration down.

        7. SMART MONEY POSITIONING:
        - Smart money: Short 25800P + Short 25500P → net bearish bias
        - Long 25900C? No. OI is high, but volume is retail. OI at 25900C is 62k — but that’s not smart money. Smart money doesn’t buy 25900C with 715k volume — they sell it.
        - Smart money is selling puts at 25800 and 25500 — collecting premium, hedged long futures. They are betting on Nifty staying above 25800.
        - But if Nifty breaks 25800 — they are forced to sell futures → crash.
        - Current price: 25869 → 69 points above 25800. That’s 69 points cushion.
        - But 25800P has 67k OI — that’s 67,000 contracts = 670,000 shares equivalent. Each point drop = 670,000 * 50 = ₹33.5 Cr pressure on market makers to hedge.
        - 25800 is the fulcrum. 25869 is 69 points up — but 25800P OI is 2.4x higher than 25800C OI — this is not a bullish setup. This is a bear trap.

        8. NIFTY vs STOCKS LOGIC:
        - Nifty is index → OI is dominated by institutional hedging, delta hedging, gamma exposure.
        - Retail cannot move Nifty. Only market makers and institutions can.
        - Retail buying 25900C is irrelevant — they are the sheep.
        - The only force that moves Nifty intraday: market makers hedging their short put positions.
        - If Nifty rises → market makers sell futures to hedge → resistance.
        - If Nifty falls → market makers sell futures → acceleration.
        - 25800 is the key level. It’s not support. It’s a gamma trap.

        9. HISTORICAL THRESHOLDS:
        - Nifty ATM ±100 points: 90% of intraday moves stay within ±100 of open.
        - 25869 → 25800 is 69 points below → within range.
        - Historical intraday reversal probability at 25800P OI > 60k: 78% chance of rejection if price approaches from above.
        - If Nifty touches 25800 → 82% probability of bounce (if no news) — but if it breaks 25800 → 92% probability of continuation down.
        - OI PCR 0.97 — historical median for intraday range-bound — but when OI is concentrated at ATM-1 put, and volume PCR < 1.0, then 73% chance of downside breakout if price falls 30 points from current.

        10. INTRADAY SCALPING OPPORTUNITY:
        - Nifty is at 25869 — 69 points above 25800P wall.
        - Market makers are short 67k puts at 25800 → they are long futures → they are under pressure to sell if Nifty drops.
        - Retail is buying 25900C — this is the trap. They think it’s bullish. But smart money is preparing for a drop.
        - 25800 is the only level that matters. Break below → collapse.
        - Probability of Nifty falling to 25800: 68% (based on 2020-2025 historical intraday data for similar OI structure)
        - Probability of Nifty holding above 25800: 32%
        - But if it breaks 25800 → next target: 25700 (100 points down) — because 25700P has 86k OI — next gamma wall.
        - This is not a "buy call" setup. This is a "sell call, buy put" setup — but you only buy naked PE.

        11. ENTRY, STOP, TARGET — NAKED PE ONLY:
        - Entry: 25800 PE — LTP = 140
        - Why? Because 25800 is the gamma trap. Market makers are short 67k puts. If Nifty drops 50 points, they must sell 26k futures → crash.
        - Stop-loss: 25850 — if Nifty closes above 25850, the put OI wall is broken → market makers stop hedging → no downside pressure → PE loses value.
        - Target: 25700 — 100 points down → 25700 PE LTP = 236.1 (current) → but if Nifty drops to 25700, 25800 PE becomes ITM → value jumps to ~180-200 (intrinsic 100 + time value)
        - But you buy 25800 PE at 140 → target 25700 = 100 points → PE intrinsic = 100 → time value = 20-30 → value = 120-130 → you lose money?
        - No. You don’t hold for intrinsic. You hold for gamma squeeze.
        - If Nifty drops to 25750 → 25800 PE value jumps to 180-190 → 40% gain in 10 mins.
        - If Nifty drops to 25700 → 25800 PE value = 200-220 → 40-60% gain.
        - But your stop is 25850. You are not betting on 25700. You are betting on the gamma squeeze from 25800 to 25750.
        - 25800 PE: 140 → if Nifty drops 50 points → 25800 PE becomes 100 intrinsic + 50 time = 150 → 7% gain? Not enough.
        - Correction: 25800 PE is 140 LTP → strike 25800, spot 25869 → delta = ~0.3 → if spot drops to 25800 → delta = 0.5 → if spot drops to 25750 → delta = 0.8 → if spot drops to 25700 → delta = 1.0
        - 25800 PE: if spot drops 50 points → premium jumps from 140 → 220-240 → 57-70% gain.
        - This is the trade.
        - But 25800 PE has low volume — 409k — but OI is 67k — so liquidity is there.
        - Entry: 25800 PE at 140
        - Stop-loss: 25850 (if Nifty closes above 25850, exit)
        - Target: 25750 → 25800 PE LTP > 200 → 42% gain
        - Or: 25700 → 25800 PE LTP > 220 → 57% gain
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
        - Bearish intraday — 78% probability of test of 25800 → 68% probability of break below → 57% probability of 25750 target.
        - Retail is long calls at 25900 — smart money is short puts at 25800 → if Nifty drops 50 points → retail calls expire worthless → smart money collects premium → and market crashes.
        - This is the only edge.

        14. MATHEMATICAL PROBABILITY:
        - Probability of Nifty moving to 25800 (ATM-1) from 25869: 68% (historical intraday data, OI >60k at ATM-1 put)
        - Probability of Nifty moving to 25750 (ATM-1 - 50): 57%
        - Probability of Nifty moving to 25900 (ATM+1): 22% (only if retail squeeze happens — but OI at 25900C is not high enough to sustain squeeze — no gamma wall)

        15. ENTRY, STOP, TARGET — NAKED PE ONLY:
        - BUY: 25800 PE at 140
        - STOP-LOSS: 25850 (if Nifty closes above 25850, exit)
        - TARGET 1: 25750 → 25800 PE > 200 → exit 50% position
        - TARGET 2: 25700 → 25800 PE > 220 → exit 100% position
        - TIME: 11:00 AM - 2:30 PM — if no move, exit.

        16. BRUTAL TRUTH:
        - You are not buying 25900C. That’s retail suicide.
        - You are buying 25800P because smart money sold it — and they are hedged — and if Nifty drops 50 points, they will be forced to sell futures → and you make 50%.
        - This is not a guess. This is gamma math.
        - If Nifty stays above 25800, you lose 140. But probability of that is 32%.
        - Probability of 50-point drop: 57%.
        - Risk-reward: 140 risk, 60-80 reward → 1:0.5 — bad?
        - No. Because 57% win rate + 140 risk → 80 reward = 0.57*80 - 0.43*140 = 45.6 - 60.2 = -14.6 → negative expectancy?
        - Correction: 25800 PE at 140 → if spot drops to 25750, PE = 200 → 60 profit.
        - If spot drops to 25700, PE = 220 → 80 profit.
        - But if spot stays above 25800, PE = 100 → 40 loss.
        - But we are not holding to expiry. We are scalping gamma move.
        - Intraday, 25800 PE can jump from 140 to 180 in 15 mins if Nifty drops 30 points → 28% gain.
        - 30-point drop: 25869 → 25839 → 25800 PE jumps to 180 → 40 profit.
        - Probability of 30-point drop: 72%
        - Probability of 30-point rise: 18%
        - So: 72% chance of 40 profit, 28% chance of 40 loss → expectancy = 0.72*40 - 0.28*40 = 16 — positive.
        - This is the edge.

        FINAL ANSWER:
        - DIRECTIONAL BIAS: BEARISH
        - PROBABILITY: 72% chance Nifty drops 30 points → 25800 PE gains 40 points → 28% gain
        - ENTRY: 25800 PE at 140
        - STOP-LOSS: 25850 (close above)
        - TARGET: 25839 (30-point drop) → 25800 PE > 180
        - EXIT: 100% at 180 or 2:30 PM, whichever first.

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        """
        user_content = f"CURRENT DATA FOR ANALYSIS:\n{formatted_data}\n"

        # Call the AI model
        ai_response = ""
        try:
            print("🔄 Requesting AI analysis from DeepSeek...")
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ],
                temperature=0,
                top_p=1.0,
                presence_penalty=0,
                frequency_penalty=0,
                max_tokens=1200,
                stream=False,
                timeout=300.0,
                stop=["```"]
            )
            raw_ai = response.choices[0].message.content or ""
            ai_response = self._clean_ai_response(raw_ai)
            
        except Exception as e:
            print(f"⚠️ AI call failed: {e}")
            ai_response = f"AI analysis failed: {e}"

        # Save both raw data and AI response to history
        self.save_analysis_to_history(formatted_data, ai_response)

        # Return formatted AI response
        return f"🤖 DEEPSEEK AI INTRADAY ANALYSIS (NIFTY + BANKNIFTY + STOCKS):\n\n{ai_response}"


# Backward compatibility placeholder
def format_data_for_ai(oi_data, current_cycle, total_fetches, pcr_analysis):
    return "Data formatting updated - use get_ai_analysis method directly"