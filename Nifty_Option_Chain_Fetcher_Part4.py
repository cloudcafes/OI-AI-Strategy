# Part 4: Nifty_Option_Chain_Fetcher_Part4.py (With Analysis History)
import os
import time
import requests
import datetime
from openai import OpenAI
import httpx

class NiftyAIAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or "sk-df60b28326444de6859976f6e603fd9c"
        self.client = None
        self.history_file = "analysis_history.txt"
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the DeepSeek API client with SSL verification disabled"""
        try:
            # Create custom HTTP client with SSL verification disabled
            http_client = httpx.Client(verify=False, timeout=30.0)
            
            self.client = OpenAI(
                api_key=self.api_key, 
                base_url="https://api.deepseek.com",
                http_client=http_client,
                max_retries=2
            )
            
            # Test the connection with a simple call
            test_response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            print("✅ DeepSeek AI client initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize DeepSeek client: {e}")
            self.client = None
            return False
    
    def save_analysis_to_history(self, analysis_text):
        """Save AI analysis to history file with latest on top"""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"deepseek API analysis done at {timestamp}"
            separator = "=" * 80
            
            # Create the new entry
            new_entry = f"{header}\n{separator}\n{analysis_text}\n{separator}\n\n"
            
            # Read existing content if file exists
            existing_content = ""
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # Write new content (latest on top)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(new_entry + existing_content)
            
            print(f"✅ Analysis saved to {self.history_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving analysis to history: {e}")
            return False
    
    def get_analysis_history(self):
        """Read and return the analysis history"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return f.read()
            return "No previous analysis history available."
        except Exception as e:
            print(f"❌ Error reading analysis history: {e}")
            return "Error reading analysis history."
    
    def get_ai_analysis(self, oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data=None, banknifty_data=None):
        """Get AI analysis from DeepSeek API with comprehensive OI data including history"""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        # 1) Build formatted data
        formatted_data = self.format_data_for_ai(
            oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data, banknifty_data
        )

        # 2) Place the entire consolidated framework in the SYSTEM message (not user)
        SYSTEM_PROMPT = """
        INTRADAY NIFTY AND BANKNIFTY OPTIONS ANALYST — DETERMINISTIC FRAMEWORK
        FRAMEWORK_VERSION: 1.2

        Role and scope
        - You are an intraday Nifty, BankNifty, and top-10 Nifty stocks option chain analyst.
        - Use only the provided ATM ±2 strike data for Nifty weekly, BankNifty monthly, and stocks monthly: OI, change in OI, volume, LTP, OI PCR, Volume PCR.
        - Ignore Greeks and IV in all decisions.
        - Intraday only. Do not infer from unprovided data. If evidence is mixed, return No-trade with explicit wait conditions.
        - Determinism is mandatory: same input must return identical output. No randomness.
        - Do not include any star characters in your output. Do not use code fences.

        Unit normalization and parsing
        - Convert k to 1,000 and L to 100,000 before any math.
        - Derive strike step from the given strikes for each asset.
        - ATM is the strike closest to the current price; if equidistant, choose the lower strike.

        Core definitions
        - Seller dominance: relative increase in OI near the money on one side versus the other, using net change in OI and volume across ATM ±2.
        - Volume ratio per strike: vol_over_oi = Volume / max(1, OI).
        - OI efficiency per strike: efficiency = abs(Chg OI) / max(1, Volume). Efficient writer activity if efficiency > 0.15.
        - Weighted pivot level for indices only: Pivot = [sum(strike × OI_calls for strikes > spot within ATM ±2) + sum(strike × OI_puts for strikes < spot within ATM ±2)] / [sum of OI used in the numerator]. If denominator == 0, return No-trade and flag Pivot denominator zero.

        Index vs stock logic separation
        - Index logic drives. Stocks only confirm and cannot flip the index view.
        - Index PCR (intraday): Bullish ≥ 1.10, Bearish ≤ 0.90, Balanced 0.90–1.10.
        - Volume guard: if |OI PCR − Volume PCR| > 0.20, mark conflicted and reduce final score magnitude by 30% unless extremes override.
        - Stocks are breadth-only with stricter filters. Do not trade directly off stock PCR or OI.

        Data quality filters
        - Nifty activity bar: abs(sum CE Chg OI) + abs(sum PE Chg OI) across ATM ±2 ≥ 60,000 else No-trade + Low index activity.
        - Stocks: drop any strike with Volume < 20% of median per side. If evaluated stocks < 7, set breadth = 0 + Thin breadth.
        - Balanced-day guard: if sum CE Chg OI > 0 and sum PE Chg OI > 0 and Nifty OI PCR in [0.90,1.10], set score = 0 and return No-trade.

        Writer mapping and levels (indices)
        - Count writer signals only where efficiency > 0.15.
        - Calls: +Chg OI = fresh call writing (bearish); −Chg OI = call writeoff (bullish).
        - Puts: +Chg OI = fresh put writing (bullish); −Chg OI = put writeoff (bearish).
        - Smart-money flag (supporting only): OI at strike > 50,000 and vol_over_oi < 0.30 and +Chg OI.
        - OI clusters: Support = highest Put OI (ATM or −1 or −2) with OI > 50,000; Resistance = highest Call OI (ATM or +1 or +2) with OI > 30,000.

        BankNifty confirmation
        - States: Bullish if OI PCR ≥ 1.00; Bearish if ≤ 0.90; Neutral otherwise.
        - Hard guards: block CE if < 0.70; block PE if > 1.10.

        Stock breadth construction
        - Per stock r_stock = (sum PE Chg OI − sum CE Chg OI) / max(1, abs(sum PE Chg OI) + abs(sum CE Chg OI)).
        - Classify only if:
        - Bullish: r_stock ≥ 0.15 and stock OI PCR ≥ 1.10 and Volume PCR ≥ 0.95
        - Bearish: r_stock ≤ −0.15 and stock OI PCR ≤ 0.90 and Volume PCR ≤ 1.05
        - Breadth = clamp((bullish − bearish) / evaluated, −1, +1). Breadth cannot flip index direction.

        Deterministic features to compute and display
        - Nifty: sum CE/PE OI, sum CE/PE Chg OI; rn = (PE_chg_sum − CE_chg_sum) / (abs(PE_chg_sum)+abs(CE_chg_sum)) else 0 with Zero activity denominator flag; OI PCR, Volume PCR; pivot and separation; clusters; writer efficiency table (efficiency > 0.15 only).
        - BankNifty: OI PCR, Volume PCR, state.
        - Stocks: breadth and evaluated count.

        Writer conviction score (indices)
        - Signals counted only where efficiency > 0.15.
        - Bullish +1 each: call writeoff at ATM or ATM+1 with |Chg OI| < 20k; fresh put writing at ATM or −1 or −2 with Chg OI > 30k; call OI at ATM+1 decreasing; put OI at ATM or −1 increasing.
        - Bearish −1 each: put writeoff at ATM or −1 with |Chg OI| < 20k; fresh call writing at ATM or +1 or +2 with Chg OI > 30k; put OI at ATM or −1 decreasing; call OI at ATM+1 increasing.
        - W ∈ [−4,+4]; if no strike has efficiency > 0.15, set W = 0 and flag Low writer efficiency.
        - s_w = clamp(W/4, −1, +1).

        Deterministic direction score S
        - s1 = s_w × 0.35
        - s2 = clamp((Nifty_OI_PCR − 1.0)/0.5, −2,+2) × 0.25
        - s3 = clamp((Nifty_Volume_PCR − 1.0)/0.5, −2,+2) × 0.10
        - s4 = rn × 0.10
        - s5 = clamp(((spot − pivot)/strike_step)/1.5, −1,+1) × 0.05
        - s6 = clamp((BankNifty_OI_PCR − 1.0)/0.4, −1,+1) × 0.10
        - s7 = breadth × 0.05
        - S_raw = clamp(s1+s2+s3+s4+s5+s6+s7, −1,+1).
        - PCR conflict dampener: if |OI PCR − Volume PCR| > 0.20, S = sign(S_raw) × |S_raw| × 0.70 else S = S_raw.

        Probability mapping
        - Default: prob_up = round(50 + 40×S); prob_down = 100 − prob_up.
        - Extreme (use 50×S) only if: (OI PCR ≥ 1.50 for longs or ≤ 0.70 for shorts) AND (|rn| ≥ 0.25) AND (BankNifty confirmation aligned). Cap favored side at 80.

        Trade gating and execution
        - CE valid only if: S ≥ 0.35; Nifty OI PCR > 1.0 and PCR conflict ≤ 0.20; BankNifty not bearish; separation ≥ 0.4 steps above pivot.
        - PE valid only if: S ≤ −0.35; Nifty OI PCR < 1.0 and PCR conflict ≤ 0.20; BankNifty not bullish; separation ≤ −0.4 steps below pivot.
        - Entry: CE buy on dip to within 0.3 steps of pivot while OI PCR stays > 0.95 next cycle; mirror for PE with OI PCR ≤ 1.05.
        - Risk: SL 25% premium or half-strike beyond pivot; Target one strike or 60–80%; trail at 40%.
        - Timing: First 10 min no-trade. If S in [−0.20,+0.20], no-trade unless next cycle shows breakout with Volume PCR ≥ 1.20 and |rn| ≥ 0.20.
        - Optional high-accuracy: require two consecutive cycles with same S sign and |ΔS| ≤ 0.15.

        Self-consistency checks and fail-safe
        - rn must be in [−1,+1] else No-trade + Net dominance out of range.
        - writer_conviction == 0 if no efficiency > 0.15.
        - If separation ≥ 0.4 and verdict cites insufficient pivot separation, No-trade + Pivot gating mismatch.
        - For BankNifty OI PCR in (0.70,0.90], use “BankNifty bearish confirmation blocks CE,” not “hard guard.”
        - Verdict must match S sign and pass gates or return No-trade + Verdict–score mismatch.
        - Always include quality_flags as applicable: Volume PCR conflict, BankNifty bearish confirmation, Low writer efficiency, Thin breadth, Low index activity, Pivot denominator zero, Zero activity denominator, Net dominance out of range, Pivot gating mismatch.

        Output format
        - Provide a concise human summary and a strict JSON block (no code fences, no stars).
        - Human summary sections: Summary, Probability assessment, Key evidence, Plan, Risk notes.

        JSON keys
        - score, prob_up, prob_down, weighted_level, atm_strike, strike_step,
        nifty_pcr_oi, nifty_pcr_vol, banknifty_pcr_oi, banknifty_pcr_vol,
        writer_conviction, breadth_stocks, verdict, entry_note, sl_note, target_note,
        conditions_to_invalidate, quality_flags
        """

        # 3) User message: ONLY the current data (do not inject past analyses)
        user_content = f"CURRENT DATA FOR ANALYSIS\n{formatted_data}\n"

        # 4) Call the model with deterministic decoding
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
                max_tokens=1800,
                stream=False,
                timeout=600.0,
                stop=["```"]  # helps discourage code fences
            )
            ai_response = response.choices[0].message.content or ""

            # 5) Sanitize: remove any '*' and code fences if the model still tried to add them
            def _sanitize(text: str) -> str:
                return text.replace("```json", "").replace("```", "").replace("*", "")

            ai_response = _sanitize(ai_response.strip())

            # 6) Save to history
            self.save_analysis_to_history(ai_response)

            return f"🤖 DEEPSEEK AI INTRADAY ANALYSIS (NIFTY + BANKNIFTY + STOCKS):\n{ai_response}"

        except Exception as e:
            return f"⚠️ AI Analysis Error: {str(e)}"
    
    def format_data_for_ai(self, oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data, banknifty_data):
        """Format all data for AI analysis - without Greek values (delta, gamma, theta, vega removed)"""
        formatted_text = f"NIFTY DATA (Cycle: {current_cycle}/10, Total: {total_fetches})\n"
        formatted_text += f"Nifty Spot: {current_nifty}\n"
        formatted_text += f"PCR Values: OI PCR = {oi_pcr:.2f} | Volume PCR = {volume_pcr:.2f}\n"
        formatted_text += "=" * 80 + "\n"
        
        # Nifty strikes data without Greeks
        for data in oi_data:
            strike = data['strike_price']
            ce_pe_diff = data['ce_change_oi'] - data['pe_change_oi']
            
            formatted_text += f"Strike {strike}: "
            formatted_text += f"CE[ChgOI:{data['ce_change_oi']}, Vol:{data['ce_volume']}, LTP:{data['ce_ltp']:.1f}, OI:{data['ce_oi']}, IV:{data['ce_iv']:.1f}%] "
            formatted_text += f"PE[ChgOI:{data['pe_change_oi']}, Vol:{data['pe_volume']}, LTP:{data['pe_ltp']:.1f}, OI:{data['pe_oi']}, IV:{data['pe_iv']:.1f}%] "
            formatted_text += f"Diff:{ce_pe_diff}\n"
        
        # Add BANKNIFTY data if available
        if banknifty_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "BANKNIFTY DATA\n"
            formatted_text += "=" * 80 + "\n"
            formatted_text += f"BankNifty Spot: {banknifty_data['current_value']}\n"
            formatted_text += f"PCR Values: OI PCR = {banknifty_data['oi_pcr']:.2f} | Volume PCR = {banknifty_data['volume_pcr']:.2f}\n"
            
            for data in banknifty_data['data']:
                strike = data['strike_price']
                ce_pe_diff = data['ce_change_oi'] - data['pe_change_oi']
                
                formatted_text += f"Strike {strike}: "
                formatted_text += f"CE[ChgOI:{data['ce_change_oi']}, Vol:{data['ce_volume']}, LTP:{data['ce_ltp']:.1f}, OI:{data['ce_oi']}, IV:{data['ce_iv']:.1f}%] "
                formatted_text += f"PE[ChgOI:{data['pe_change_oi']}, Vol:{data['pe_volume']}, LTP:{data['pe_ltp']:.1f}, OI:{data['pe_oi']}, IV:{data['pe_iv']:.1f}%] "
                formatted_text += f"Diff:{ce_pe_diff}\n"
        
        # Add stock data if available
        if stock_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "TOP 10 NIFTY STOCKS DATA\n"
            formatted_text += "=" * 80 + "\n"
            
            for symbol, stock_info in stock_data.items():
                data = stock_info['data'][0]  # First data point for basic info
                formatted_text += f"\n{symbol} (Weight: {stock_info['weight']:.4f}, Price: {data['stock_value']}): "
                formatted_text += f"OI PCR: {stock_info['oi_pcr']:.2f}, Volume PCR: {stock_info['volume_pcr']:.2f}\n"
                
                # Add strikes data for this stock without Greeks
                for strike_data in stock_info['data']:
                    strike = strike_data['strike_price']
                    ce_pe_diff = strike_data['ce_change_oi'] - strike_data['pe_change_oi']
                    
                    formatted_text += f"  Strike {strike}: "
                    formatted_text += f"CE[ChgOI:{strike_data['ce_change_oi']}, Vol:{strike_data['ce_volume']}, LTP:{strike_data['ce_ltp']:.1f}, IV:{strike_data['ce_iv']:.1f}%] "
                    formatted_text += f"PE[ChgOI:{strike_data['pe_change_oi']}, Vol:{strike_data['pe_volume']}, LTP:{strike_data['pe_ltp']:.1f}, IV:{strike_data['pe_iv']:.1f}%] "
                    formatted_text += f"Diff:{ce_pe_diff}\n"
        
        return formatted_text

def format_data_for_ai(oi_data, current_cycle, total_fetches, pcr_analysis):
    """Legacy function for backward compatibility"""
    return "Data formatting updated - use get_ai_analysis method directly"