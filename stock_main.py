# stock-main.py
# Main executor with error handling & rate limiting

import time
import datetime
from typing import List, Dict, Any, Optional

from stock_config import STOCK_LIST, ENABLE_AI_ANALYSIS, RATE_LIMIT_DELAY, SHOW_DETAILED_OUTPUT
from stock_fetcher import get_stock_data, initialize_session
from stock_analyzer import perform_python_analysis, format_analysis_for_display
from stock_ai import ai_analyzer

# Optional config overrides (safe defaults if not present)
try:
    import stock_config as CFG
except Exception:
    CFG = None

def _get_cfg(name: str, default):
    return getattr(CFG, name, default) if CFG else default

# Filtering and display parameters (strict defaults)
TOP_K_STOCKS         = _get_cfg('TOP_K_STOCKS', 15)          # how many selected candidates to show
SHOW_ONLY_FILTERED   = _get_cfg('SHOW_ONLY_FILTERED', True)  # when True, hide non-selected stocks
MIN_STOCK_ACTIVITY   = _get_cfg('MIN_STOCK_ACTIVITY', 15000) # min activity across ATM ±2
REQ_STEPS_LIMIT      = _get_cfg('REQ_STEPS_LIMIT', 2.0)      # max underlying steps for 50-pt premium feasibility
REQ_SEP_STEPS        = _get_cfg('REQ_SEP_STEPS', 0.4)        # min pivot separation steps in direction
RUN_AI_ON_FILTERED   = _get_cfg('RUN_AI_ON_FILTERED', True)  # run AI only on filtered candidates
VERBOSE_FILTER       = _get_cfg('VERBOSE_FILTER', False)     # print rejection reasons
KEEP_REJECT_SAMPLES  = _get_cfg('KEEP_REJECT_SAMPLES', 10)   # how many rejections to display if verbose
MIN_ATM_OPTION_LTP   = _get_cfg('MIN_ATM_OPTION_LTP', 0)     # optional liquidity floor on ATM option LTP (0 disables)

# Relaxed fallback (only used if no strict matches)
RELAX_IF_ZERO          = _get_cfg('RELAX_IF_ZERO', True)
RELAX_MIN_ACTIVITY     = _get_cfg('RELAX_MIN_STOCK_ACTIVITY', 8000)
RELAX_REQ_STEPS_LIMIT  = _get_cfg('RELAX_REQ_STEPS_LIMIT', 2.5)
RELAX_REQ_SEP_STEPS    = _get_cfg('RELAX_REQ_SEP_STEPS', 0.30)
RELAX_PCR_CONFLICT_MAX = _get_cfg('RELAX_PCR_CONFLICT_MAX', 0.25)
RELAX_R_STOCK_ABS      = _get_cfg('RELAX_R_STOCK_ABS', 0.20)
RELAX_OI_PCR_BULL      = _get_cfg('RELAX_OI_PCR_BULL', 1.05)
RELAX_OI_PCR_BEAR      = _get_cfg('RELAX_OI_PCR_BEAR', 0.95)
EXTREME_R_STOCK_ABS    = _get_cfg('EXTREME_R_STOCK_ABS', 0.40)
EXTREME_OI_PCR_BULL    = _get_cfg('EXTREME_OI_PCR_BULL', 1.25)
EXTREME_OI_PCR_BEAR    = _get_cfg('EXTREME_OI_PCR_BEAR', 0.80)

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

class StockAnalysisExecutor:
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        self.session = None
        self.results: List[Dict[str, Any]] = []     # store per-stock python_analysis
        self.data_cache: Dict[str, Any] = {}        # symbol -> {'oi_data': ..., 'analysis': ...}

    def initialize(self):
        """Initialize the analysis executor"""
        self.start_time = datetime.datetime.now()
        print(f"\n🎯 STOCK F&O ANALYSIS STARTED")
        print(f"📊 Total Stocks: {len(STOCK_LIST)}")
        print(f"🤖 AI Analysis: {'ENABLED' if ENABLE_AI_ANALYSIS else 'DISABLED'}")
        print(f"⏰ Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        try:
            self.session = initialize_session()
            print("✅ Session initialized successfully")
        except Exception as e:
            print(f"❌ Session initialization failed: {e}")
            return False
        return True
    
    def process_single_stock(self, symbol: str) -> bool:
        """Fetch, analyze, and optionally display per-stock results."""
        try:
            if not SHOW_ONLY_FILTERED:
                print(f"\n🔄 Processing {symbol}...")
            
            oi_data = get_stock_data(symbol, self.session)
            if not oi_data:
                if not SHOW_ONLY_FILTERED:
                    print(f"❌ No data retrieved for {symbol}")
                self.error_count += 1
                return False
            
            analysis_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            python_analysis = perform_python_analysis(oi_data)
            python_analysis['analysis_timestamp'] = analysis_timestamp

            # Cache for post-filter AI analysis
            self.data_cache[symbol] = {'oi_data': oi_data, 'analysis': python_analysis}
            self.results.append(python_analysis)
            
            # Per-stock printing only when not filtering-only mode
            if not SHOW_ONLY_FILTERED:
                if SHOW_DETAILED_OUTPUT:
                    print(format_analysis_for_display(python_analysis))
                else:
                    pcr = python_analysis['pcr_analysis']
                    print(f"✅ {symbol}: {pcr['sentiment']} | OI PCR: {pcr['oi_pcr']:.3f} | Vol PCR: {pcr['volume_pcr']:.3f}")
                
                # AI analysis for each stock only when not filtering-only
                if ENABLE_AI_ANALYSIS:
                    try:
                        ai_output = ai_analyzer.get_ai_analysis(oi_data, python_analysis)
                        print(ai_output)
                    except Exception as ai_error:
                        print(f"⚠️ AI analysis failed for {symbol}: {ai_error}")
            
            self.processed_count += 1
            return True
            
        except Exception as e:
            if not SHOW_ONLY_FILTERED:
                print(f"❌ Error processing {symbol}: {e}")
            self.error_count += 1
            return False

    def _atm_ltp(self, symbol: str, analysis: Dict[str, Any]) -> Dict[str, float]:
        """
        Optional ATM LTP pull (for liquidity filter) using cached oi_data.
        Returns {'ce': ce_ltp, 'pe': pe_ltp} or zeros if not found or disabled.
        """
        if MIN_ATM_OPTION_LTP <= 0:
            return {'ce': 0.0, 'pe': 0.0}
        try:
            cache = self.data_cache.get(symbol, {})
            oi_data = cache.get('oi_data', [])
            feats = analysis.get('intraday_features', {}) or {}
            atm = feats.get('atm', None)
            if not oi_data or atm is None:
                return {'ce': 0.0, 'pe': 0.0}
            atm_row = next((r for r in oi_data if int(r.get('strike_price', -1)) == int(atm)), None)
            if not atm_row:
                return {'ce': 0.0, 'pe': 0.0}
            return {
                'ce': float(atm_row.get('ce_ltp', 0.0)),
                'pe': float(atm_row.get('pe_ltp', 0.0))
            }
        except Exception:
            return {'ce': 0.0, 'pe': 0.0}

    def _score_candidate_mode(self,
                              analysis: Dict[str, Any],
                              mode: str = "strict") -> Optional[Dict[str, Any]]:
        """
        Convert a python_analysis into a trade candidate based on 'strict' or 'relaxed' gates.
        Returns a dict for candidates, or a rejection dict if VERBOSE_FILTER=True (with '_rejected').
        """
        try:
            feats = analysis.get('intraday_features', {}) or {}
            pcr = analysis.get('pcr_analysis', {}) or {}
            reasons = []
            if not feats or 'error' in feats:
                if VERBOSE_FILTER:
                    return {"_rejected": True, "symbol": analysis.get('symbol',''), "reasons": ["missing intraday_features"], "mode": mode}
                return None

            symbol = analysis.get('symbol', '')
            oi_pcr = float(pcr.get('oi_pcr', 0.0))
            vol_pcr = float(pcr.get('volume_pcr', 0.0))
            r_stock = float(feats.get('r_stock', 0.0))
            activity = int(feats.get('activity', 0))
            pcr_conflict = bool(feats.get('pcr_conflict', False))
            sep_steps = float(feats.get('separation_steps', 0.0))
            req_steps_ce = feats.get('req_steps_ce_50', float('inf'))
            req_steps_pe = feats.get('req_steps_pe_50', float('inf'))
            feasible_ce = bool(feats.get('feasible_ce_50', False))
            feasible_pe = bool(feats.get('feasible_pe_50', False))
            writer_bull = bool(feats.get('writer_bull_trigger', False))
            writer_bear = bool(feats.get('writer_bear_trigger', False))
            direction_hint = feats.get('direction_hint', 'Neutral')
            pivot = feats.get('pivot', None)
            atm = feats.get('atm', None)
            step = feats.get('strike_step', None)

            # Optional ATM LTP floor
            atm_ltp = self._atm_ltp(symbol, analysis)
            if MIN_ATM_OPTION_LTP > 0:
                if direction_hint == "CE" and atm_ltp['ce'] < MIN_ATM_OPTION_LTP:
                    reasons.append(f"ATM CE LTP {atm_ltp['ce']:.1f} < {MIN_ATM_OPTION_LTP}")
                if direction_hint == "PE" and atm_ltp['pe'] < MIN_ATM_OPTION_LTP:
                    reasons.append(f"ATM PE LTP {atm_ltp['pe']:.1f} < {MIN_ATM_OPTION_LTP}")

            # Mode parameters
            if mode == "strict":
                min_activity = MIN_STOCK_ACTIVITY
                steps_limit = REQ_STEPS_LIMIT
                sep_req = REQ_SEP_STEPS
                pcr_conflict_max = 0.20
                r_thr = 0.25
                oi_pcr_bull = 1.10
                oi_pcr_bear = 0.90
                writer_needed = True
            else:
                min_activity = RELAX_MIN_ACTIVITY
                steps_limit = RELAX_REQ_STEPS_LIMIT
                sep_req = RELAX_REQ_SEP_STEPS
                pcr_conflict_max = RELAX_PCR_CONFLICT_MAX
                r_thr = RELAX_R_STOCK_ABS
                oi_pcr_bull = RELAX_OI_PCR_BULL
                oi_pcr_bear = RELAX_OI_PCR_BEAR
                writer_needed = False  # allow alternatives below

            # Common gating
            if activity < min_activity:
                reasons.append(f"activity {activity} < {min_activity}")
            if abs(oi_pcr - vol_pcr) > pcr_conflict_max:
                reasons.append(f"PCR conflict |OI-Vol|={abs(oi_pcr-vol_pcr):.2f} > {pcr_conflict_max}")
            if step is None or step <= 0:
                reasons.append("invalid strike step")

            # Direction gates (dominance + PCR + location)
            ce_gate = (r_stock >= r_thr and oi_pcr >= oi_pcr_bull and sep_steps >= sep_req)
            pe_gate = (r_stock <= -r_thr and oi_pcr <= oi_pcr_bear and sep_steps <= -sep_req)

            # 50-point feasibility
            if not feasible_ce:
                reasons.append(f"CE not feasible: req_steps_ce={req_steps_ce}")
            if not feasible_pe:
                reasons.append(f"PE not feasible: req_steps_pe={req_steps_pe}")

            # Writer triggers or approved alternatives
            writer_ok_ce = writer_bull
            writer_ok_pe = writer_bear
            if not writer_needed and mode == "relaxed":
                # Allow extreme alternatives if no writer trigger
                extreme_alt_ce = (abs(r_stock) >= EXTREME_R_STOCK_ABS) or (oi_pcr >= EXTREME_OI_PCR_BULL)
                extreme_alt_pe = (abs(r_stock) >= EXTREME_R_STOCK_ABS) or (oi_pcr <= EXTREME_OI_PCR_BEAR)
                writer_ok_ce = writer_bull or extreme_alt_ce
                writer_ok_pe = writer_bear or extreme_alt_pe
                if not writer_bull and extreme_alt_ce:
                    reasons.append("CE allowed by extreme dominance/PCR")
                if not writer_bear and extreme_alt_pe:
                    reasons.append("PE allowed by extreme dominance/PCR")

            # Location vs hint (avoid mid-range)
            if direction_hint == "CE" and sep_steps < sep_req:
                reasons.append(f"CE separation {sep_steps:.2f} < {sep_req}")
            if direction_hint == "PE" and sep_steps > -sep_req:
                reasons.append(f"PE separation {sep_steps:.2f} > {-sep_req}")

            # Build final OK flags using hint as soft override
            ce_ok = ((direction_hint == "CE") or ce_gate) and feasible_ce and (float(req_steps_ce) <= steps_limit) and writer_ok_ce
            pe_ok = ((direction_hint == "PE") or pe_gate) and feasible_pe and (float(req_steps_pe) <= steps_limit) and writer_ok_pe

            if not ce_ok and not pe_ok:
                if VERBOSE_FILTER:
                    return {"_rejected": True, "symbol": symbol, "reasons": reasons[:10], "mode": mode, "snap": {
                        "oi_pcr": round(oi_pcr,2), "vol_pcr": round(vol_pcr,2), "r_stock": round(r_stock,3),
                        "activity": activity, "sep_steps": round(sep_steps,2), "req_ce": req_steps_ce, "req_pe": req_steps_pe
                    }}
                return None

            # Score survivors
            if ce_ok:
                pcr_align = clamp((oi_pcr - 1.0) / 0.3, -1, 1)  # bullish alignment
                feas_norm = clamp((2.0 - float(req_steps_ce)) / 2.0, 0.0, 1.0)
                direction = "CE"
            else:
                pcr_align = clamp((1.0 - oi_pcr) / 0.3, -1, 1)  # bearish alignment
                feas_norm = clamp((2.0 - float(req_steps_pe)) / 2.0, 0.0, 1.0)
                direction = "PE"

            eff_flag = 1.0 if (writer_bull and direction == "CE") or (writer_bear and direction == "PE") else 0.0
            activity_norm = clamp(activity / 40000.0, 0.0, 1.0)
            score = round(0.35 * abs(r_stock) + 0.25 * pcr_align + 0.20 * eff_flag + 0.10 * activity_norm + 0.10 * feas_norm, 3)
            req = req_steps_ce if direction == "CE" else req_steps_pe

            return {
                "symbol": symbol,
                "direction": direction,
                "score": score,
                "oi_pcr": round(oi_pcr, 2),
                "vol_pcr": round(vol_pcr, 2),
                "r_stock": round(r_stock, 3),
                "activity": activity,
                "sep_steps": round(sep_steps, 2),
                "req_steps": req,
                "pivot": pivot,
                "atm": atm,
                "step": step,
                "timestamp": analysis.get('analysis_timestamp'),
                "mode": mode
            }
        except Exception as e:
            if VERBOSE_FILTER:
                return {"_rejected": True, "symbol": analysis.get('symbol',''), "reasons": [f"exception {e}"], "mode": mode}
            return None

    def _filter_and_rank(self, analyses: List[Dict[str, Any]], top_k: int, mode: str = "strict") -> List[Dict[str, Any]]:
        """Create candidates from analyses, filter by mode gates, and rank by score."""
        candidates: List[Dict[str, Any]] = []
        rejects: List[Dict[str, Any]] = []
        for a in analyses:
            c = self._score_candidate_mode(a, mode=mode)
            if not c:
                continue
            if c.get("_rejected"):
                rejects.append(c)
            else:
                candidates.append(c)
        candidates.sort(key=lambda d: d["score"], reverse=True)
        if VERBOSE_FILTER and rejects:
            self._print_rejects(rejects[:KEEP_REJECT_SAMPLES], mode)
        return candidates[:max(1, top_k)] if candidates else []

    def _print_rejects(self, rejects: List[Dict[str, Any]], mode: str):
        print(f"\n{'-'*80}")
        print(f"🧪 REJECTION SAMPLES ({mode}): why stocks did not pass gates")
        for r in rejects:
            sym = r.get("symbol","")
            print(f"  {sym}: " + "; ".join(r.get("reasons", [])))
            snap = r.get("snap", {})
            if snap:
                print(f"     snap: PCR {snap.get('oi_pcr')}/{snap.get('vol_pcr')}, r_stock {snap.get('r_stock')}, act {snap.get('activity')}, sep {snap.get('sep_steps')}, req_ce {snap.get('req_ce')}, req_pe {snap.get('req_pe')}")
        print(f"{'-'*80}")

    def execute_analysis(self):
        """Main execution: first pass collects all; then filter and show only selected."""
        if not self.initialize():
            return
        
        print(f"\n🚀 Starting analysis of {len(STOCK_LIST)} stocks...")
        
        # First pass: collect analyses (silent if SHOW_ONLY_FILTERED=True)
        for index, symbol in enumerate(STOCK_LIST, 1):
            self.process_single_stock(symbol)
            # Progress update
            if index % 10 == 0:
                progress = (index / len(STOCK_LIST)) * 100
                print(f"\n📈 Progress: {index}/{len(STOCK_LIST)} ({progress:.1f}%)")
            # Rate limit between fetches
            if index < len(STOCK_LIST):
                time.sleep(RATE_LIMIT_DELAY)

        # Strict filter and rank: show only selected candidates
        top_candidates = self._filter_and_rank(self.results, TOP_K_STOCKS, mode="strict")

        # Relaxed fallback if none
        relaxed_used = False
        if not top_candidates and RELAX_IF_ZERO:
            top_candidates = self._filter_and_rank(self.results, TOP_K_STOCKS, mode="relaxed")
            relaxed_used = bool(top_candidates)

        self._print_top_candidates(top_candidates, relaxed_used)

        # Optional second-pass AI only on selected candidates
        if ENABLE_AI_ANALYSIS and RUN_AI_ON_FILTERED and top_candidates:
            print(f"\n{'='*80}")
            print("🤖 AI ANALYSIS FOR SELECTED CANDIDATES")
            print(f"{'='*80}")
            for i, c in enumerate(top_candidates, 1):
                sym = c['symbol']
                cache = self.data_cache.get(sym, {})
                oi_data = cache.get('oi_data')
                analysis = cache.get('analysis')
                if not oi_data or not analysis:
                    continue
                try:
                    print(f"\n[{i}/{len(top_candidates)}] {sym} ({c['direction']}) [{c['mode']}]")
                    ai_output = ai_analyzer.get_ai_analysis(oi_data, analysis)
                    print(ai_output)
                except Exception as e:
                    print(f"⚠️ AI analysis failed for {sym}: {e}")
                if i < len(top_candidates):
                    time.sleep(RATE_LIMIT_DELAY)

        self._print_summary()
    
    def _print_top_candidates(self, top: List[Dict[str, Any]], relaxed_used: bool):
        print(f"\n{'='*80}")
        title = "SELECTED CANDIDATES (50-pt premium feasibility)"
        if relaxed_used:
            title += " — RELAXED GATES"
        print(f"🏆 {title}")
        print(f"{'='*80}")

        if not top:
            print("No stocks met the gates. Consider relaxing thresholds in stock_config.py:")
            print("  MIN_STOCK_ACTIVITY, REQ_STEPS_LIMIT, REQ_SEP_STEPS, TOP_K_STOCKS, or enable RELAX_IF_ZERO.")
            return

        # Tabular display of selected only
        print(f"{'Symbol':<12}{'Dir':<6}{'Mode':<9}{'Score':<8}{'OI PCR':<8}{'Vol PCR':<8}{'r_stock':<9}{'Act':<10}{'Sep':<7}{'ReqSteps':<10}{'ATM':<8}{'Step':<6}{'Pivot':<8}{'Time'}")
        for c in top:
            print(f"{c['symbol']:<12}{c['direction']:<6}{c['mode']:<9}{c['score']:<8.3f}{c['oi_pcr']:<8.2f}{c['vol_pcr']:<8.2f}"
                  f"{c['r_stock']:<9.3f}{c['activity']:<10d}{c['sep_steps']:<7.2f}{c['req_steps']:<10.2f}"
                  f"{c['atm']:<8}{c['step']:<6}{c['pivot']:<8}{c.get('timestamp','')}")

        print(f"{'-'*80}")
        print("Legend: Mode=strict/relaxed, Dir=CE/PE, Score, r_stock dominance, Act=activity (abs dOI sum), Sep=pivot separation steps, ReqSteps=underlying steps implied for 50-pt premium")

    def _print_summary(self):
        """Print execution summary"""
        end_time = datetime.datetime.now()
        duration = end_time - self.start_time
        
        print(f"\n{'='*80}")
        print("📊 EXECUTION SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Successfully processed: {self.processed_count} stocks")
        print(f"❌ Errors encountered: {self.error_count} stocks")
        print(f"⏰ Total duration: {duration}")
        print(f"🏁 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.processed_count > 0:
            avg_time_per_stock = duration.total_seconds() / self.processed_count
            print(f"📈 Average time per stock: {avg_time_per_stock:.2f} seconds")
        
        if self.processed_count > 0:
            success_rate = (self.processed_count / len(STOCK_LIST)) * 100
            print(f"🎯 Success rate: {success_rate:.1f}%")
        
        print(f"{'='*80}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            self.session.close()
            print("✅ Session closed")

def main():
    """Main entry point"""
    executor = StockAnalysisExecutor()
    
    try:
        executor.execute_analysis()
    except KeyboardInterrupt:
        print(f"\n⏹️ Analysis interrupted by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
    finally:
        executor.cleanup()

if __name__ == "__main__":
    main()