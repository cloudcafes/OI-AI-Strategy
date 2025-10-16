# stock-ai.py
# AI analysis using DeepSeek (SYSTEM_PROMPT unchanged)

import os
import json
import datetime
import httpx
from openai import OpenAI
from typing import Dict, Any, List, Optional

from stock_config import ENABLE_AI_ANALYSIS

class StockAIAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "sk-df60b28326444de6859976f6e603fd9c"
        self.client = None
        self.history_file = "ai_analysis_history.txt"
        self.initialize_client()

    def initialize_client(self) -> bool:
        """Initialize the DeepSeek API client"""
        if not ENABLE_AI_ANALYSIS:
            return False
            
        try:
            if not self.api_key:
                raise RuntimeError("DeepSeek API key not found.")

            verify_ssl_env = os.getenv("DEEPSEEK_VERIFY_SSL", "false").lower() in ("1", "true", "yes")
            http_client = httpx.Client(verify=verify_ssl_env, timeout=30.0)

            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
                http_client=http_client,
                max_retries=2
            )

            # Test connection
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

    def _sanitize_llm_text(self, text: str) -> str:
        """Remove code fences and star characters from LLM draft"""
        return text.replace("```json", "").replace("```", "").replace("*", "").strip()

    def _compose_dual_sections(self, py_text: str, ai_text: str) -> str:
        """Compose Python and AI analysis sections"""
        sep = "=" * 80
        header_py = f"{sep}\nPython Analysis:\n{sep}"
        header_ai = f"{sep}\nAI ANALYSIS (Model draft — not used for decisions):\n{sep}"
        ai_block = ai_text if ai_text.strip() else "No AI draft available."
        return f"{header_py}\n{py_text}\n\n{header_ai}\n{ai_block}"

    def save_analysis_to_history(self, analysis_text: str) -> bool:
        """Save analysis to history file with latest on top"""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"DeepSeek analysis done at {timestamp}"
            separator = "=" * 80
            new_entry = f"{header}\n{separator}\n{analysis_text}\n{separator}\n\n"

            existing_content = ""
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(new_entry + existing_content)

            return True

        except Exception as e:
            print(f"❌ Error saving analysis to history: {e}")
            return False

    def _build_stock_analysis_output(self, python_analysis: Dict[str, Any]) -> str:
        """Build comprehensive stock analysis output"""
        symbol = python_analysis.get('symbol', 'Unknown')
        current_price = python_analysis.get('current_price', 0)
        pcr_analysis = python_analysis.get('pcr_analysis', {})
        oi_analysis = python_analysis.get('oi_analysis', {})
        key_levels = python_analysis.get('key_levels', {})
        
        # Build human-readable analysis
        summary_lines = []
        summary_lines.append("Summary")
        
        # PCR-based sentiment
        sentiment = pcr_analysis.get('sentiment', 'NEUTRAL')
        oi_pcr = pcr_analysis.get('oi_pcr', 1.0)
        volume_pcr = pcr_analysis.get('volume_pcr', 1.0)
        
        summary_lines.append(
            f"Stock {symbol} at {current_price} shows {sentiment.lower()} bias with OI PCR {oi_pcr:.2f} "
            f"and Volume PCR {volume_pcr:.2f}. Net OI change indicates "
            f"{'put-side' if oi_analysis.get('net_oi_change', 0) > 0 else 'call-side'} dominance."
        )

        summary_lines.append("")
        summary_lines.append("Key Levels")
        
        # Support levels
        supports = key_levels.get('supports', [])
        if supports:
            support_info = ", ".join([f"{s['strike']}" for s in supports[:2]])
            summary_lines.append(f"Support: {support_info}")
        
        # Resistance levels  
        resistances = key_levels.get('resistances', [])
        if resistances:
            resistance_info = ", ".join([f"{r['strike']}" for r in resistances[:2]])
            summary_lines.append(f"Resistance: {resistance_info}")

        summary_lines.append("")
        summary_lines.append("OI Analysis")
        summary_lines.append(f"CE OI Change: {oi_analysis.get('total_ce_change_oi', 0):+,}")
        summary_lines.append(f"PE OI Change: {oi_analysis.get('total_pe_change_oi', 0):+,}")
        summary_lines.append(f"Max CE OI: {oi_analysis.get('max_ce_oi_value', 0):,} @ {oi_analysis.get('max_ce_oi_strike', 0)}")
        summary_lines.append(f"Max PE OI: {oi_analysis.get('max_pe_oi_value', 0):,} @ {oi_analysis.get('max_pe_oi_strike', 0)}")

        summary_lines.append("")
        summary_lines.append("Trading Plan")
        action = pcr_analysis.get('action', 'Wait for confirmation')
        summary_lines.append(f"Primary: {action}")
        
        # Risk assessment based on PCR values
        if oi_pcr > 1.2:
            summary_lines.append("Risk: Elevated put writing may indicate over-optimism")
        elif oi_pcr < 0.8:
            summary_lines.append("Risk: High call writing suggests bearish pressure")
        else:
            summary_lines.append("Risk: Balanced positioning, monitor for breakout")

        human_summary = "\n".join(summary_lines)

        # JSON output for structured data
        json_out = {
            "symbol": symbol,
            "current_price": current_price,
            "sentiment": sentiment,
            "oi_pcr": float(oi_pcr),
            "volume_pcr": float(volume_pcr),
            "net_oi_change": oi_analysis.get('net_oi_change', 0),
            "key_support_levels": [s['strike'] for s in supports[:2]],
            "key_resistance_levels": [r['strike'] for r in resistances[:2]],
            "max_ce_oi_strike": oi_analysis.get('max_ce_oi_strike', 0),
            "max_pe_oi_strike": oi_analysis.get('max_pe_oi_strike', 0),
            "trading_bias": "BULLISH" if oi_pcr > 1.1 else "BEARISH" if oi_pcr < 0.9 else "NEUTRAL",
            "confidence_level": pcr_analysis.get('confidence', 'Medium')
        }

        final_text = f"{human_summary}\n\n{json.dumps(json_out, ensure_ascii=False, indent=2)}"
        return final_text

    def get_ai_analysis(self, oi_data: List[Dict[str, Any]], python_analysis: Dict[str, Any]) -> str:
        """Get AI analysis for stock data"""
        if not ENABLE_AI_ANALYSIS:
            return "AI Analysis disabled in configuration"
            
        if not self.client:
            print("⚠️ AI client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        formatted_data = self.format_data_for_ai(oi_data, python_analysis)

        # SYSTEM_PROMPT unchanged as requested
        SYSTEM_PROMPT = """
        INTRADAY NIFTY AND BANKNIFTY OPTIONS ANALYST — DETERMINISTIC FRAMEWORK
        FRAMEWORK_VERSION: 1.3

        Role and scope
        - You are an intraday Nifty, BankNifty, and top-10 Nifty stocks option chain analyst.
        - Use only the provided ATM ±2 strike data for Nifty weekly, BankNifty monthly, and stocks monthly: OI, change in OI, volume, LTP, OI PCR, Volume PCR.
        - Ignore Greeks and IV in all decisions.
        - Intraday only. Do not infer from unprovided data. If evidence is mixed, return No-trade with explicit wait conditions.
        - Determinism is mandatory: same input must return identical output. No randomness.
        - Do not include any star characters in your output. Do not use code fences.

        Unit normalization and parsing
        - All OI and Volume values are provided as raw numbers. Use them directly without unit conversion.
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
        - For BankNifty OI PCR in (0.70,0.90], use "BankNifty bearish confirmation blocks CE," not "hard guard."
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

        user_content = f"CURRENT STOCK DATA FOR ANALYSIS\n{formatted_data}\n"

        # Call the model for AI analysis draft
        ai_text = ""
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
                stop=["```"]
            )
            raw_ai = response.choices[0].message.content or ""
            ai_text = self._sanitize_llm_text(raw_ai)
        except Exception as e:
            print(f"⚠️ AI call failed: {e}")
            ai_text = f"AI analysis failed: {e}"

        # Build Python analysis output (source of truth)
        py_text = self._build_stock_analysis_output(python_analysis)

        # Compose both sections
        combined_text = self._compose_dual_sections(py_text=py_text, ai_text=ai_text)

        # Save and return
        self.save_analysis_to_history(combined_text)
        return f"🤖 DEEPSEEK AI ANALYSIS FOR {python_analysis.get('symbol', 'STOCK')}:\n{combined_text}"

    def format_data_for_ai(self, oi_data: List[Dict[str, Any]], python_analysis: Dict[str, Any]) -> str:
        """Format all data for AI analysis"""
        if not oi_data:
            return "No data available for analysis"
            
        symbol = oi_data[0]['symbol']
        current_price = oi_data[0]['stock_value']
        pcr_analysis = python_analysis.get('pcr_analysis', {})
        
        formatted_text = f"STOCK DATA: {symbol}\n"
        formatted_text += f"Current Price: {current_price}\n"
        formatted_text += f"PCR Values: OI PCR = {pcr_analysis.get('oi_pcr', 0):.3f} | Volume PCR = {pcr_analysis.get('volume_pcr', 0):.3f}\n"
        formatted_text += "=" * 80 + "\n"
        formatted_text += "OPTION CHAIN DATA (ATM ±2 strikes):\n"

        for row in oi_data:
            strike = row['strike_price']
            ce_pe_diff = row.get('ce_change_oi', 0) - row.get('pe_change_oi', 0)
            formatted_text += (
                f"Strike {strike}: "
                f"CE[ChgOI:{row.get('ce_change_oi', 0)}, Vol:{row.get('ce_volume', 0)}, LTP:{row.get('ce_ltp', 0.0):.1f}, OI:{row.get('ce_oi', 0)}, IV:{row.get('ce_iv', 0.0):.1f}%] "
                f"PE[ChgOI:{row.get('pe_change_oi', 0)}, Vol:{row.get('pe_volume', 0)}, LTP:{row.get('pe_ltp', 0.0):.1f}, OI:{row.get('pe_oi', 0)}, IV:{row.get('pe_iv', 0.0):.1f}%] "
                f"Diff:{ce_pe_diff}\n"
            )

        # Add Python analysis summary
        formatted_text += "\n" + "=" * 80 + "\n"
        formatted_text += "PYTHON ANALYSIS SUMMARY:\n"
        formatted_text += f"Sentiment: {pcr_analysis.get('sentiment', 'Unknown')}\n"
        formatted_text += f"Confidence: {pcr_analysis.get('confidence', 'Unknown')}\n"
        formatted_text += f"Action: {pcr_analysis.get('action', 'Unknown')}\n"
        
        oi_analysis = python_analysis.get('oi_analysis', {})
        formatted_text += f"Net OI Change: {oi_analysis.get('net_oi_change', 0):+,}\n"
        formatted_text += f"Max CE OI Strike: {oi_analysis.get('max_ce_oi_strike', 0)}\n"
        formatted_text += f"Max PE OI Strike: {oi_analysis.get('max_pe_oi_strike', 0)}\n"

        return formatted_text


# Global instance
ai_analyzer = StockAIAnalyzer()