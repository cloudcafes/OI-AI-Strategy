# Part 4: Nifty_Option_Chain_Fetcher_Part4.py (Deterministic Analysis + Post-Validation + Dual Display)
import os
import time
import json
import math
import requests
import datetime
from statistics import median
from typing import Dict, Any, List, Tuple, Optional

from openai import OpenAI
import httpx


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


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

    def save_analysis_to_history(self, analysis_text: str) -> bool:
        """Save combined analysis to history file with latest on top."""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"deepseek validated analysis done at {timestamp}"
            separator = "=" * 80
            new_entry = f"{header}\n{separator}\n{analysis_text}\n{separator}\n\n"

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

    def _sanitize_llm_text(self, text: str) -> str:
        """Remove code fences and star characters from LLM draft."""
        return text.replace("```json", "").replace("```", "").replace("*", "").strip()

    def _compose_dual_sections(self, py_text: str, ai_text: str) -> str:
        sep = "=" * 80
        header_py = f"{sep}\nPython Analysis:\n{sep}"
        header_ai = f"{sep}\nAI ANALYSIS (Model draft — not used for decisions):\n{sep}"
        ai_block = ai_text if ai_text.strip() else "No AI draft available."
        return f"{header_py}\n{py_text}\n\n{header_ai}\n{ai_block}"

    def _nearest_atm(self, strikes: List[int], spot: float) -> int:
        strikes_sorted = sorted(strikes)
        atm = min(strikes_sorted, key=lambda s: (abs(s - spot), s))  # tie → lower strike
        return atm

    def _strike_step(self, strikes: List[int]) -> int:
        unique = sorted(set(strikes))
        if len(unique) < 2:
            return 50  # default
        steps = [j - i for i, j in zip(unique[:-1], unique[1:]) if (j - i) > 0]
        return min(steps) if steps else 50

    def _compute_writer_efficiency(self, chg_oi: float, vol: float) -> float:
        v = max(1.0, float(vol))
        return abs(float(chg_oi)) / v

    def _compute_pivot(self, nifty_rows: List[Dict[str, Any]], spot: float, step: int) -> Tuple[Optional[float], List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        Weighted pivot: calls above spot, puts below spot, within provided rows (expected ATM ±2).
        Returns (pivot or None if denom=0, calls_above_list, puts_below_list).
        """
        calls_above = []
        puts_below = []
        for row in nifty_rows:
            strike = int(row["strike_price"])
            ce_oi = float(row.get("ce_oi", 0))
            pe_oi = float(row.get("pe_oi", 0))
            if strike > spot:
                calls_above.append((strike, ce_oi))
            if strike < spot:
                puts_below.append((strike, pe_oi))

        num = 0.0
        den = 0.0
        for s, oi in calls_above:
            num += s * oi
            den += oi
        for s, oi in puts_below:
            num += s * oi
            den += oi

        if den <= 0:
            return (None, calls_above, puts_below)
        return (num / den, calls_above, puts_below)

    def _compute_breadth(self, stock_data: Optional[Dict[str, Any]]) -> Tuple[float, int, int, int, List[str]]:
        """
        Apply volume filter (per side) and classify stocks based on r_stock & PCR thresholds.
        Returns (breadth in [-1,+1], bullish_count, bearish_count, evaluated_count, flags).
        """
        flags = []
        if not stock_data:
            return (0.0, 0, 0, 0, flags)

        bullish = 0
        bearish = 0
        evaluated = 0

        for sym, info in stock_data.items():
            rows = info.get("data", [])
            if not rows:
                continue

            # Gather volumes per side
            ce_vols = [float(r.get("ce_volume", 0)) for r in rows]
            pe_vols = [float(r.get("pe_volume", 0)) for r in rows]
            if not ce_vols or not pe_vols:
                continue

            ce_med = median(ce_vols)
            pe_med = median(pe_vols)
            ce_threshold = 0.2 * ce_med
            pe_threshold = 0.2 * pe_med

            ce_chg_sum = 0.0
            pe_chg_sum = 0.0
            for r in rows:
                ce_v = float(r.get("ce_volume", 0))
                pe_v = float(r.get("pe_volume", 0))
                if ce_v >= ce_threshold:
                    ce_chg_sum += float(r.get("ce_change_oi", 0))
                if pe_v >= pe_threshold:
                    pe_chg_sum += float(r.get("pe_change_oi", 0))

            denom = abs(pe_chg_sum) + abs(ce_chg_sum)
            r_stock = (pe_chg_sum - ce_chg_sum) / denom if denom > 0 else 0.0

            stock_oi_pcr = float(info.get("oi_pcr", 0))
            stock_vol_pcr = float(info.get("volume_pcr", 0))

            # Strict classification
            cls = "Neutral"
            if r_stock >= 0.15 and stock_oi_pcr >= 1.10 and stock_vol_pcr >= 0.95:
                cls = "Bullish"
            elif r_stock <= -0.15 and stock_oi_pcr <= 0.90 and stock_vol_pcr <= 1.05:
                cls = "Bearish"

            # Only count classified names as evaluated (to avoid thin-signal bias)
            if cls != "Neutral":
                evaluated += 1
                if cls == "Bullish":
                    bullish += 1
                else:
                    bearish += 1

        if evaluated < 7:
            flags.append("Thin breadth")
            return (0.0, bullish, bearish, evaluated, flags)

        breadth = clamp((bullish - bearish) / max(1, evaluated), -1.0, 1.0)
        return (breadth, bullish, bearish, evaluated, flags)

    def _compute_writer_conviction(self, nifty_rows: List[Dict[str, Any]], atm: int, step: int) -> Tuple[int, bool]:
        """
        Returns (W in [-4,+4], has_any_efficiency_gt_0_15).
        Signals counted only where efficiency > 0.15.
        """
        by_strike = {int(r["strike_price"]): r for r in nifty_rows}
        strikes = sorted(by_strike.keys())

        def eff(side: str, s: int) -> float:
            row = by_strike.get(s, {})
            if side == "CE":
                return self._compute_writer_efficiency(row.get("ce_change_oi", 0), row.get("ce_volume", 0))
            else:
                return self._compute_writer_efficiency(row.get("pe_change_oi", 0), row.get("pe_volume", 0))

        def chg(side: str, s: int) -> float:
            row = by_strike.get(s, {})
            return float(row.get("ce_change_oi" if side == "CE" else "pe_change_oi", 0))

        has_eff = any(eff("CE", s) > 0.15 or eff("PE", s) > 0.15 for s in strikes)
        if not has_eff:
            return (0, False)

        W = 0
        # Bullish signals
        for s in [atm, atm + step]:
            if s in by_strike:
                if eff("CE", s) > 0.15 and chg("CE", s) < 0 and abs(chg("CE", s)) < 20000:
                    W += 1  # call writeoff at ATM/ATM+1

        for s in [atm, atm - step, atm - 2 * step]:
            if s in by_strike:
                if eff("PE", s) > 0.15 and chg("PE", s) > 30000:
                    W += 1  # fresh put writing ATM/ATM-1/ATM-2

        if (atm + step) in by_strike:
            if eff("CE", atm + step) > 0.15 and chg("CE", atm + step) < 0:
                W += 1  # call OI at ATM+1 decreasing

        for s in [atm, atm - step]:
            if s in by_strike:
                if eff("PE", s) > 0.15 and chg("PE", s) > 0:
                    W += 1  # put OI ATM/ATM-1 increasing

        # Bearish signals
        for s in [atm, atm - step]:
            if s in by_strike:
                if eff("PE", s) > 0.15 and chg("PE", s) < 0 and abs(chg("PE", s)) < 20000:
                    W -= 1  # put writeoff ATM/ATM-1

        for s in [atm, atm + step, atm + 2 * step]:
            if s in by_strike:
                if eff("CE", s) > 0.15 and chg("CE", s) > 30000:
                    W -= 1  # fresh call writing ATM/ATM+1/ATM+2

        for s in [atm, atm - step]:
            if s in by_strike:
                if eff("PE", s) > 0.15 and chg("PE", s) < 0:
                    W -= 1  # put OI ATM/ATM-1 decreasing

        if (atm + step) in by_strike:
            if eff("CE", atm + step) > 0.15 and chg("CE", atm + step) > 0:
                W -= 1  # call OI ATM+1 increasing

        W = int(clamp(W, -4, 4))
        return (W, True)

    def _compute_nifty_features(self, oi_data: List[Dict[str, Any]], spot: float) -> Dict[str, Any]:
        """Compute ATM, step, CE/PE sums, rn, activity, etc."""
        strikes = [int(r["strike_price"]) for r in oi_data]
        step = self._strike_step(strikes)
        atm = self._nearest_atm(strikes, spot)

        # Keep only ATM ±2 strikes if more were passed
        target_strikes = set([atm + i * step for i in (-2, -1, 0, 1, 2)])
        rows = [r for r in oi_data if int(r["strike_price"]) in target_strikes]
        if len(rows) == 0:
            rows = oi_data

        ce_chg_sum = sum(float(r.get("ce_change_oi", 0)) for r in rows)
        pe_chg_sum = sum(float(r.get("pe_change_oi", 0)) for r in rows)
        activity = abs(ce_chg_sum) + abs(pe_chg_sum)

        denom = abs(pe_chg_sum) + abs(ce_chg_sum)
        rn = (pe_chg_sum - ce_chg_sum) / denom if denom > 0 else 0.0
        rn = clamp(rn, -1.0, 1.0)

        return {
            "atm": atm,
            "step": step,
            "rows": rows,
            "ce_chg_sum": ce_chg_sum,
            "pe_chg_sum": pe_chg_sum,
            "activity": activity,
            "rn": rn
        }

    def _build_validated_output(self,
                                oi_data: List[Dict[str, Any]],
                                current_nifty: float,
                                oi_pcr: float,
                                volume_pcr: float,
                                banknifty_data: Optional[Dict[str, Any]],
                                stock_data: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """Compute deterministic result and build final human summary + JSON."""
        nf = self._compute_nifty_features(oi_data, current_nifty)
        atm = nf["atm"]
        step = nf["step"]
        rows = nf["rows"]
        rn = nf["rn"]
        activity = nf["activity"]

        # BankNifty PCRs
        bnf_oi_pcr = float(banknifty_data.get("oi_pcr", 0)) if banknifty_data else 1.0
        bnf_vol_pcr = float(banknifty_data.get("volume_pcr", 0)) if banknifty_data else 1.0

        # Pivot
        pivot, calls_above, puts_below = self._compute_pivot(rows, current_nifty, step)
        pivot_flag = []
        if pivot is None:
            pivot = float(atm)  # fallback
            pivot_flag.append("Pivot denominator zero")

        separation_steps = (current_nifty - pivot) / max(1, step)

        # Writer conviction
        W, has_eff = self._compute_writer_conviction(rows, atm, step)
        s_w = W / 4.0 if W is not None else 0.0

        # Breadth
        breadth, bull_cnt, bear_cnt, evaluated_cnt, breadth_flags = self._compute_breadth(stock_data)

        # Guards and s-components
        low_activity_flag = activity < 60000
        conflict = abs(oi_pcr - volume_pcr) > 0.20

        s1 = clamp(s_w, -1, 1) * 0.35
        s2 = clamp((oi_pcr - 1.0) / 0.5, -2, 2) * 0.25
        s3 = clamp((volume_pcr - 1.0) / 0.5, -2, 2) * 0.10
        s4 = rn * 0.10
        s5 = clamp((separation_steps) / 1.5, -1, 1) * 0.05
        s6 = clamp((bnf_oi_pcr - 1.0) / 0.4, -1, 1) * 0.10
        s7 = breadth * 0.05

        S_raw = clamp(s1 + s2 + s3 + s4 + s5 + s6 + s7, -1, 1)

        # Balanced-day guard
        balanced_flag = False
        if (nf["ce_chg_sum"] > 0) and (nf["pe_chg_sum"] > 0) and (0.90 <= oi_pcr <= 1.10):
            S = 0.0
            balanced_flag = True
        else:
            S = (math.copysign(abs(S_raw) * 0.70, S_raw) if conflict else S_raw)

        # Probability mapping (default 50 + 40×S), cap favored side at 80
        prob_up = int(round(50 + 40 * S))
        prob_up = max(0, min(80, prob_up))
        prob_down = 100 - prob_up

        # BankNifty confirmation state
        bnf_state = "bearish" if bnf_oi_pcr <= 0.90 else ("bullish" if bnf_oi_pcr >= 1.00 else "neutral")

        # Trade gating
        ce_valid = (S >= 0.35 and oi_pcr > 1.0 and not conflict and bnf_state != "bearish" and separation_steps >= 0.4)
        pe_valid = (S <= -0.35 and oi_pcr < 1.0 and not conflict and bnf_state != "bullish" and separation_steps <= -0.4)

        if ce_valid:
            verdict = "CE"
            entry_note = "Buy CE on pullback to within 0.3 steps of pivot if OI PCR stays > 0.95 next cycle."
        elif pe_valid:
            verdict = "PE"
            entry_note = "Buy PE on bounce to within 0.3 steps of pivot if OI PCR stays ≤ 1.05 next cycle."
        else:
            verdict = "No-trade"
            if bnf_state == "bearish":
                entry_note = "Bias bullish but wait: need BankNifty ≥ 0.90 and dip toward pivot, then consider CE."
            elif bnf_state == "bullish":
                entry_note = "Bias bearish but wait: need BankNifty ≤ 1.10 and bounce to pivot, then consider PE."
            else:
                entry_note = "Evidence mixed; wait for pivot retest with PCR alignment."

        sl_note = "25% premium or half-strike beyond pivot against the trade." if verdict != "No-trade" else "N/A - no trade"
        target_note = "One strike or 60–80% premium; trail at 40%." if verdict != "No-trade" else "N/A - no trade"
        conditions_to_invalidate = (
            "Invalidate long bias if Nifty OI PCR < 0.95 or sustained break below pivot without reclaim; "
            "CE remains blocked while BankNifty OI PCR ≤ 0.90."
        )

        # Quality flags
        qflags = []
        if conflict:
            qflags.append("Volume PCR conflict")
        if bnf_state == "bearish":
            qflags.append("BankNifty bearish confirmation")
        if not has_eff:
            qflags.append("Low writer efficiency")
        if low_activity_flag:
            qflags.append("Low index activity")
        if balanced_flag:
            qflags.append("Balanced-day")
        qflags.extend(pivot_flag)
        qflags.extend(breadth_flags)

        # Build human summary (deterministic)
        summary_lines = []
        summary_lines.append("Summary")
        bias_text = "bullish" if S > 0 else ("bearish" if S < 0 else "neutral")
        summary_lines.append(
            f"Nifty put-side dominance with OI PCR {oi_pcr:.2f} and rn {rn:.2f} tilts {bias_text}; "
            f"pivot {int(round(pivot))} sits {separation_steps:.2f} steps {'below' if separation_steps>0 else 'above'} spot. "
            f"BankNifty OI PCR {bnf_oi_pcr:.2f} is {bnf_state}; "
            f"{'PCR conflict active' if conflict else 'PCRs aligned'}."
        )

        summary_lines.append("")
        summary_lines.append("Probability assessment")
        summary_lines.append(f"Probability up: {prob_up}%, Probability down: {prob_down}%")

        summary_lines.append("")
        summary_lines.append("Key evidence")
        summary_lines.append(f"- Nifty: CE_chg_sum={nf['ce_chg_sum']:.0f}, PE_chg_sum={nf['pe_chg_sum']:.0f}, rn={rn:.2f}")
        summary_lines.append(f"- Pivot: {int(round(pivot))}, separation {separation_steps:.2f} steps; ATM {atm}, step {step}")
        summary_lines.append(f"- BankNifty PCR: OI {bnf_oi_pcr:.2f}, Vol {bnf_vol_pcr:.2f}; breadth {breadth:.2f} (bull {bull_cnt}, bear {bear_cnt}, eval {evaluated_cnt})")

        summary_lines.append("")
        summary_lines.append("Plan")
        if verdict == "CE":
            summary_lines.append("CE buy-on-dip near pivot if retest occurs within 0.3 steps and OI PCR holds > 0.95; avoid chasing.")
        elif verdict == "PE":
            summary_lines.append("PE buy-on-bounce to pivot if retest occurs within 0.3 steps and OI PCR ≤ 1.05; avoid chasing.")
        else:
            summary_lines.append(entry_note)

        summary_lines.append("")
        summary_lines.append("Risk notes")
        summary_lines.append(", ".join(qflags) if qflags else "No material quality flags.")

        human_summary = "\n".join(summary_lines)

        json_out = {
            "score": float(round(S, 6)),
            "prob_up": int(prob_up),
            "prob_down": int(prob_down),
            "weighted_level": int(round(pivot)),
            "atm_strike": int(atm),
            "strike_step": int(step),
            "nifty_pcr_oi": float(oi_pcr),
            "nifty_pcr_vol": float(volume_pcr),
            "banknifty_pcr_oi": float(bnf_oi_pcr),
            "banknifty_pcr_vol": float(bnf_vol_pcr),
            "writer_conviction": int(W),
            "breadth_stocks": float(round(breadth, 4)),
            "verdict": verdict,
            "entry_note": entry_note,
            "sl_note": sl_note,
            "target_note": target_note,
            "conditions_to_invalidate": conditions_to_invalidate,
            "quality_flags": qflags
        }

        final_text = f"{human_summary}\n\n{json.dumps(json_out, ensure_ascii=False, indent=2)}"
        return final_text, json_out

    def get_ai_analysis(self,
                        oi_data: List[Dict[str, Any]],
                        current_cycle: int,
                        total_fetches: int,
                        oi_pcr: float,
                        volume_pcr: float,
                        current_nifty: float,
                        stock_data: Optional[Dict[str, Any]] = None,
                        banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Request AI analysis draft (for display) and produce deterministic validated output (source of truth)."""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        formatted_data = self.format_data_for_ai(
            oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data, banknifty_data
        )

        SYSTEM_PROMPT = """
        You are an expert Nifty/BankNifty/top10 Nifty Stocks by weightage option chain analyst with deep knowledge of historical Nifty/BankNifty/top10 Nifty Stocks by weightage patterns and institutional trading behavior. You are not a dumb trader who only reads the data but you read in between the lines of provided data to decode the seller's & smart money perspective of the market which keeps you ahead from other traders when you provide any trade recommendation. You do mathemetical calculations as well as psychological analysis and interlink everything to understand the market. You never get in hurry to reply fast instead you focus on deep analysis and interlinked affect and take enough time to reply with your forecast.
        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Analyze the provided "OI data,greeks,CE-PE for the Nifty index ATM ±2 strikes of weekly expiry","OI data,greeks,CE-PE for the BANKNifty index ATM ±2 strikes of monthly expiry" and "OI data,greeks,CE-PE for the top10 Nifty Stocks by weightage ATM ±2 strikes of monthly expiry" to interpret the current only intraday trend which is provided to you live for this moment. Provide a short summary first, then a breakdown. Use historical proven patterns, data, and trends specific to the Nifty index ATM ±2 strikes,Banknifty index ATM ±2 strikes,Stocks ATM ±2 strikes for accurate analysis—reference.
        Key steps of analysis whose interlinked interpretation should be used for any forecasting and provide output catagerocially for each point: Analyze Nifty/BankNifty/top10 Nifty Stocks by weightage ATM ±2 strikes- OI changes,concentration, buildup, Evaluate OI PCR and Volume PCR, Ignore false signals, Analyze Greeks.
        You must provide output whether current nifty price will move to ATM+1 or ATM-1, and their probability based on scientific and mathemetical calculations and justification.
        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Remember, Nifty index ATM ±2 strikes of weekly expiry OI analysis differs from stock options: Nifty reflects broader market sentiment with more institutional writing, while stocks are prone to company-specific manipulation and lower liquidity. Always interpret Nifty option chain from the sellers' perspective. Focus solely on intraday implications, ignoring multi-day or expiry perspectives for trades.
        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        I only take naked Nifty put or call buys for intraday trades, squaring off same day. So you can suggest me CE buy if you find upside outlook and PE buy if downside outlook. Based on the intraday trend, recommend high-probability trades with highly positive outcome potential—estimate and accuracy based on historical intraday patterns. You also need to suggest like "currently the index is going down but will bounce from certain level so buy at that level" or "currently the index is going up but will from from certain level so buy at that level", this is to avoid entry at wrong level or price. Include entry/strike suggestions, stop-loss, target for quick exits, and why it suits this intra-day scenario. Hedge recommendations with uncertainty, e.g., 'Intra-day evidence leans toward bullish, but monitor for session-end breakouts.'.
        """

        user_content = f"CURRENT DATA FOR ANALYSIS\n{formatted_data}\n"

        # Call the model (deterministic settings) and capture its draft text
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
            print(f"⚠️ AI call failed, continuing with deterministic computation only: {e}")
            ai_text = f"AI call failed: {e}"

        # Deterministic, validated output from Python logic (source of truth)
        py_text, _json = self._build_validated_output(
            oi_data=oi_data,
            current_nifty=current_nifty,
            oi_pcr=float(oi_pcr),
            volume_pcr=float(volume_pcr),
            banknifty_data=banknifty_data,
            stock_data=stock_data
        )

        # Compose both sections
        combined_text = self._compose_dual_sections(py_text=py_text, ai_text=ai_text)

        # Save and return
        self.save_analysis_to_history(combined_text)
        return f"🤖 DEEPSEEK AI INTRADAY ANALYSIS (NIFTY + BANKNIFTY + STOCKS):\n{combined_text}"

    def format_data_for_ai(self,
                           oi_data: List[Dict[str, Any]],
                           current_cycle: int,
                           total_fetches: int,
                           oi_pcr: float,
                           volume_pcr: float,
                           current_nifty: float,
                           stock_data: Optional[Dict[str, Any]] = None,
                           banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Format all data for AI analysis - no Greeks in payload."""
        formatted_text = f"NIFTY DATA (Cycle: {current_cycle}/10, Total: {total_fetches})\n"
        formatted_text += f"Nifty Spot: {current_nifty}\n"
        formatted_text += f"PCR Values: OI PCR = {oi_pcr:.2f} | Volume PCR = {volume_pcr:.2f}\n"
        formatted_text += "=" * 80 + "\n"

        # Nifty strikes (assumed ATM ±2 or you pass the exact rows you want analyzed)
        for row in oi_data:
            strike = row['strike_price']
            ce_pe_diff = row.get('ce_change_oi', 0) - row.get('pe_change_oi', 0)
            formatted_text += (
                f"Strike {strike}: "
                f"CE[ChgOI:{row.get('ce_change_oi', 0)}, Vol:{row.get('ce_volume', 0)}, LTP:{row.get('ce_ltp', 0.0):.1f}, OI:{row.get('ce_oi', 0)}, IV:{row.get('ce_iv', 0.0):.1f}%] "
                f"PE[ChgOI:{row.get('pe_change_oi', 0)}, Vol:{row.get('pe_volume', 0)}, LTP:{row.get('pe_ltp', 0.0):.1f}, OI:{row.get('pe_oi', 0)}, IV:{row.get('pe_iv', 0.0):.1f}%] "
                f"Diff:{ce_pe_diff}\n"
            )

        if banknifty_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "BANKNIFTY DATA\n"
            formatted_text += "=" * 80 + "\n"
            formatted_text += f"BankNifty Spot: {banknifty_data.get('current_value')}\n"
            formatted_text += f"PCR Values: OI PCR = {banknifty_data.get('oi_pcr', 0.0):.2f} | Volume PCR = {banknifty_data.get('volume_pcr', 0.0):.2f}\n"
            for row in banknifty_data.get('data', []):
                strike = row['strike_price']
                ce_pe_diff = row.get('ce_change_oi', 0) - row.get('pe_change_oi', 0)
                formatted_text += (
                    f"Strike {strike}: "
                    f"CE[ChgOI:{row.get('ce_change_oi', 0)}, Vol:{row.get('ce_volume', 0)}, LTP:{row.get('ce_ltp', 0.0):.1f}, OI:{row.get('ce_oi', 0)}, IV:{row.get('ce_iv', 0.0):.1f}%] "
                    f"PE[ChgOI:{row.get('pe_change_oi', 0)}, Vol:{row.get('pe_volume', 0)}, LTP:{row.get('pe_ltp', 0.0):.1f}, OI:{row.get('pe_oi', 0)}, IV:{row.get('pe_iv', 0.0):.1f}%] "
                    f"Diff:{ce_pe_diff}\n"
                )

        if stock_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "TOP 10 NIFTY STOCKS DATA\n"
            formatted_text += "=" * 80 + "\n"
            for symbol, info in stock_data.items():
                rows = info.get('data', [])
                stock_px = rows[0].get('stock_value') if rows else None
                formatted_text += f"\n{symbol} (Weight: {info.get('weight', 0.0):.4f}, Price: {stock_px}): "
                formatted_text += f"OI PCR: {info.get('oi_pcr', 0.0):.2f}, Volume PCR: {info.get('volume_pcr', 0.0):.2f}\n"
                for r in rows:
                    strike = r['strike_price']
                    ce_pe_diff = r.get('ce_change_oi', 0) - r.get('pe_change_oi', 0)
                    formatted_text += (
                        f"  Strike {strike}: "
                        f"CE[ChgOI:{r.get('ce_change_oi', 0)}, Vol:{r.get('ce_volume', 0)}, LTP:{r.get('ce_ltp', 0.0):.1f}, IV:{r.get('ce_iv', 0.0):.1f}%] "
                        f"PE[ChgOI:{r.get('pe_change_oi', 0)}, Vol:{r.get('pe_volume', 0)}, LTP:{r.get('pe_ltp', 0.0):.1f}, IV:{r.get('pe_iv', 0.0):.1f}%] "
                        f"Diff:{ce_pe_diff}\n"
                    )
        return formatted_text


# Backward compatibility placeholder
def format_data_for_ai(oi_data, current_cycle, total_fetches, pcr_analysis):
    return "Data formatting updated - use get_ai_analysis method directly"