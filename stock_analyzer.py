# stock-analyzer.py
# Python analysis with PCR calculations and technical patterns
from statistics import median
from typing import Dict, List, Any, Tuple

# ----------------------------
# Helpers (non-breaking additions)
# ----------------------------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def _strike_step(strikes: List[int]) -> int:
    strikes = sorted(set(int(s) for s in strikes if s is not None))
    if len(strikes) < 2:
        return 1
    diffs = [j - i for i, j in zip(strikes[:-1], strikes[1:]) if (j - i) > 0]
    return min(diffs) if diffs else 1

def _atm(strikes: List[int], spot: float) -> int:
    strikes = sorted(set(int(s) for s in strikes if s is not None))
    if not strikes:
        return int(round(spot))
    # tie -> lower
    return min(strikes, key=lambda s: (abs(s - spot), s))

def _filter_atm_pm2(rows: List[Dict[str, Any]], atm: int, step: int) -> List[Dict[str, Any]]:
    if step <= 0:
        return rows
    wanted = {atm + i * step for i in (-2, -1, 0, 1, 2)}
    f = [r for r in rows if int(r.get('strike_price', -10**9)) in wanted]
    return f if f else rows

def _volume_thresholds(rows5: List[Dict[str, Any]]) -> Tuple[float, float]:
    ce_vols = [_safe_float(r.get('ce_volume', 0)) for r in rows5]
    pe_vols = [_safe_float(r.get('pe_volume', 0)) for r in rows5]
    ce_med = median(ce_vols) if ce_vols else 0.0
    pe_med = median(pe_vols) if pe_vols else 0.0
    return 0.2 * ce_med, 0.2 * pe_med  # 20% of median per side

def _dominance_and_activity(rows5: List[Dict[str, Any]], ce_thr: float, pe_thr: float) -> Tuple[float, float, float]:
    ce_chg_sum = sum(_safe_float(r.get('ce_change_oi', 0)) for r in rows5 if _safe_float(r.get('ce_volume', 0)) >= ce_thr)
    pe_chg_sum = sum(_safe_float(r.get('pe_change_oi', 0)) for r in rows5 if _safe_float(r.get('pe_volume', 0)) >= pe_thr)
    denom = abs(pe_chg_sum) + abs(ce_chg_sum)
    r_stock = (pe_chg_sum - ce_chg_sum) / denom if denom > 0 else 0.0
    activity = abs(ce_chg_sum) + abs(pe_chg_sum)
    return r_stock, activity, denom

def _writer_efficiency(change_oi: float, volume: float) -> float:
    v = max(1.0, _safe_float(volume))
    return abs(_safe_float(change_oi)) / v

def _writer_triggers(rows_by_strike: Dict[int, Dict[str, float]], atm: int, step: int) -> Tuple[bool, bool, List[Dict[str, Any]]]:
    """
    Returns (writer_bull_trigger, writer_bear_trigger, efficient_strikes[])
    Triggers require efficiency > 0.15 at the referenced strike.
    Bull: CE writeoff at ATM/ATM+1 or fresh PE writing at ATM/ATM-1
    Bear: PE writeoff at ATM/ATM-1 or fresh CE writing at ATM/ATM+1
    """
    efficient_strikes = []
    writer_bull = False
    writer_bear = False

    # Efficient strikes collection
    for s, d in rows_by_strike.items():
        ce_eff = _writer_efficiency(d.get('ce_change_oi', 0.0), d.get('ce_volume', 0.0))
        pe_eff = _writer_efficiency(d.get('pe_change_oi', 0.0), d.get('pe_volume', 0.0))
        if ce_eff > 0.15 or pe_eff > 0.15:
            efficient_strikes.append({
                'strike': s,
                'ce_efficiency': round(ce_eff, 3),
                'pe_efficiency': round(pe_eff, 3),
                'ce_change_oi': int(_safe_float(d.get('ce_change_oi', 0.0))),
                'pe_change_oi': int(_safe_float(d.get('pe_change_oi', 0.0)))
            })

    def eff_ce(s: int) -> float:
        d = rows_by_strike.get(s, {})
        return _writer_efficiency(d.get('ce_change_oi', 0.0), d.get('ce_volume', 0.0))
    def eff_pe(s: int) -> float:
        d = rows_by_strike.get(s, {})
        return _writer_efficiency(d.get('pe_change_oi', 0.0), d.get('pe_volume', 0.0))

    def chg_ce(s: int) -> float:
        return _safe_float(rows_by_strike.get(s, {}).get('ce_change_oi', 0.0))
    def chg_pe(s: int) -> float:
        return _safe_float(rows_by_strike.get(s, {}).get('pe_change_oi', 0.0))

    # Bull triggers
    for s in [atm, atm + step]:
        if eff_ce(s) > 0.15 and chg_ce(s) < 0 and abs(chg_ce(s)) < 20000:
            writer_bull = True
    for s in [atm, atm - step]:
        if eff_pe(s) > 0.15 and chg_pe(s) > 30000:
            writer_bull = True

    # Bear triggers
    for s in [atm, atm - step]:
        if eff_pe(s) > 0.15 and chg_pe(s) < 0 and abs(chg_pe(s)) < 20000:
            writer_bear = True
    for s in [atm, atm + step]:
        if eff_ce(s) > 0.15 and chg_ce(s) > 30000:
            writer_bear = True

    return writer_bull, writer_bear, efficient_strikes

def _pivot_and_separation(rows5: List[Dict[str, Any]], spot: float, step: int) -> Tuple[int, float]:
    """
    Weighted pivot (stocks): calls above spot + puts below spot within ATM ±2.
    Returns (pivot_int, separation_steps), where separation_steps = (spot - pivot)/step.
    """
    calls_above = [(int(r['strike_price']), _safe_float(r.get('ce_oi', 0.0))) for r in rows5 if int(r['strike_price']) > spot]
    puts_below = [(int(r['strike_price']), _safe_float(r.get('pe_oi', 0.0))) for r in rows5 if int(r['strike_price']) < spot]
    num = sum(s * oi for s, oi in calls_above) + sum(s * oi for s, oi in puts_below)
    den = sum(oi for _, oi in calls_above) + sum(oi for _, oi in puts_below)
    pivot = (num / den) if den > 0 else spot
    sep_steps = (spot - pivot) / max(1, step)
    return int(round(pivot)), float(sep_steps)

def _delta_proxy(rows_by_strike: Dict[int, Dict[str, float]], step: int, atm: int) -> Tuple[float, float]:
    """
    Delta proxies without Greeks:
    deltaC ≈ (C(K) - C(K+step)) / step clipped to [0,1]
    deltaP ≈ (P(K-step) - P(K)) / step clipped to [0,1]
    """
    cK = _safe_float(rows_by_strike.get(atm, {}).get('ce_ltp', 0.0))
    cKp = _safe_float(rows_by_strike.get(atm + step, {}).get('ce_ltp', 0.0))
    pKm = _safe_float(rows_by_strike.get(atm - step, {}).get('pe_ltp', 0.0))
    pK = _safe_float(rows_by_strike.get(atm, {}).get('pe_ltp', 0.0))
    dC = clamp((cK - cKp) / float(step), 0.0, 1.0) if step > 0 else 0.0
    dP = clamp((pKm - pK) / float(step), 0.0, 1.0) if step > 0 else 0.0
    return dC, dP

# ----------------------------
# Existing functions (kept for compatibility)
# ----------------------------

def calculate_pcr_values(oi_data: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Calculate OI PCR and Volume PCR for stock option chain data"""
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_volume = 0
    total_pe_volume = 0
    
    for data in oi_data:
        total_ce_oi += data.get('ce_oi', 0)
        total_pe_oi += data.get('pe_oi', 0)
        total_ce_volume += data.get('ce_volume', 0)
        total_pe_volume += data.get('pe_volume', 0)
    
    # Calculate PCR values with safety checks
    oi_pcr = (total_pe_oi / total_ce_oi) if total_ce_oi > 0 else 0.0
    volume_pcr = (total_pe_volume / total_ce_volume) if total_ce_volume > 0 else 0.0
    
    return round(oi_pcr, 3), round(volume_pcr, 3)

def get_pcr_sentiment(oi_pcr: float, volume_pcr: float) -> Dict[str, Any]:
    """Generate sentiment analysis based on PCR values (kept to avoid breaking dependencies)"""
    # Extreme Bullish Sentiment
    if oi_pcr > 1.3 and volume_pcr > 1.5:
        return {
            "sentiment": "EXTREME BULLISH",
            "confidence": "Very High (70%+)",
            "reason": "Strong put writing across strikes shows institutional confidence",
            "action": "Look for breakout above key levels for upside move"
        }
    # Strong Bullish Sentiment
    elif 1.1 <= oi_pcr <= 1.3 and 1.1 <= volume_pcr <= 1.5:
        return {
            "sentiment": "STRONG BULLISH", 
            "confidence": "High (63-68%)",
            "reason": "Steady put buildup indicates smart money expecting upside",
            "action": "Confirm with price breaking resistance levels"
        }
    # Weak Volume / Cautious Bullish
    elif 1.1 <= oi_pcr <= 1.2 and volume_pcr < 1.0:
        return {
            "sentiment": "CAUTIOUS BULLISH",
            "confidence": "Medium (40-45%)",
            "reason": "OI shows bullish positioning but low volume suggests disinterest",
            "action": "Wait for strong breakout confirmation before bullish trades"
        }
    # Neutral or No Edge
    elif 0.9 <= oi_pcr <= 1.1 and 0.9 <= volume_pcr <= 1.1:
        return {
            "sentiment": "NEUTRAL",
            "confidence": "Moderate (45%)",
            "reason": "Balanced positioning between calls and puts",
            "action": "Better for scalping or range trades, avoid direction bets"
        }
    # Bearish Set-Up
    elif oi_pcr < 0.9 and volume_pcr < 0.8:
        return {
            "sentiment": "BEARISH",
            "confidence": "High (65-68%)",
            "reason": "Rising call OI or dropping put volume confirms bearish sentiment",
            "action": "Look for breaks below support or sell-on-rise setups"
        }
    # High Probability Breakdown
    elif oi_pcr < 0.75 and volume_pcr < 0.7:
        return {
            "sentiment": "EXTREME BEARISH",
            "confidence": "Very High (70-75%)",
            "reason": "Very low put activity shows no confidence in stability",
            "action": "High probability of continued decline below key levels"
        }
    # Bear Trap or Short-Covering Possibility
    elif oi_pcr < 0.9 and volume_pcr > 1.2:
        return {
            "sentiment": "BEAR TRAP",
            "confidence": "Medium (55-60%)",
            "reason": "Bearish OI but high put volume shows panic put buying",
            "action": "Watch for quick recovery candles or bullish divergences"
        }
    # Bull Trap or Sluggish Bull Phase
    elif oi_pcr > 1.1 and volume_pcr < 0.8:
        return {
            "sentiment": "BULL TRAP",
            "confidence": "Medium (53-60%)",
            "reason": "Bullish OI but low volume suggests weakening upside",
            "action": "Likely pullback if price fails to clear resistance"
        }
    # Default condition for unclassified scenarios
    else:
        return {
            "sentiment": "MIXED SIGNALS",
            "confidence": "Low",
            "reason": "Conflicting signals between OI and volume PCR",
            "action": "Wait for clearer setup or price confirmation"
        }

def calculate_oi_analysis(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive OI analysis"""
    if not oi_data:
        return {}
    
    # Calculate net OI changes
    total_ce_change_oi = sum(data.get('ce_change_oi', 0) for data in oi_data)
    total_pe_change_oi = sum(data.get('pe_change_oi', 0) for data in oi_data)
    net_oi_change = total_pe_change_oi - total_ce_change_oi
    
    # Calculate total volumes
    total_ce_volume = sum(data.get('ce_volume', 0) for data in oi_data)
    total_pe_volume = sum(data.get('pe_volume', 0) for data in oi_data)
    
    # Find max OI strikes
    max_ce_oi_strike = max(oi_data, key=lambda x: x.get('ce_oi', 0))
    max_pe_oi_strike = max(oi_data, key=lambda x: x.get('pe_oi', 0))
    
    # Calculate average IV (using median to reduce outlier impact)
    ce_iv_values = [data.get('ce_iv', 0) for data in oi_data if _safe_float(data.get('ce_iv', 0)) > 0]
    pe_iv_values = [data.get('pe_iv', 0) for data in oi_data if _safe_float(data.get('pe_iv', 0)) > 0]
    avg_ce_iv = round(median(ce_iv_values), 2) if ce_iv_values else 0
    avg_pe_iv = round(median(pe_iv_values), 2) if pe_iv_values else 0
    
    return {
        'total_ce_change_oi': int(total_ce_change_oi),
        'total_pe_change_oi': int(total_pe_change_oi),
        'net_oi_change': int(net_oi_change),
        'total_ce_volume': int(total_ce_volume),
        'total_pe_volume': int(total_pe_volume),
        'max_ce_oi_strike': max_ce_oi_strike.get('strike_price'),
        'max_ce_oi_value': int(max_ce_oi_strike.get('ce_oi', 0)),
        'max_pe_oi_strike': max_pe_oi_strike.get('strike_price'),
        'max_pe_oi_value': int(max_pe_oi_strike.get('pe_oi', 0)),
        'avg_ce_iv': avg_ce_iv,
        'avg_pe_iv': avg_pe_iv,
        'iv_skew': round((avg_pe_iv - avg_ce_iv), 2) if avg_ce_iv and avg_pe_iv else 0
    }

def identify_key_levels(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Identify key support and resistance levels based on OI"""
    if not oi_data:
        return {}
    
    current_price = _safe_float(oi_data[0].get('stock_value', 0.0))
    
    # Find support levels (high PE OI below current price)
    support_levels = []
    for data in oi_data:
        if _safe_float(data.get('strike_price', 0.0)) < current_price and _safe_float(data.get('pe_oi', 0.0)) > 1000:
            support_levels.append({
                'strike': data.get('strike_price'),
                'pe_oi': int(data.get('pe_oi', 0)),
                'distance_pct': round(((current_price - _safe_float(data.get('strike_price', 0.0))) / max(1e-6, current_price)) * 100, 2)
            })
    
    # Find resistance levels (high CE OI above current price)
    resistance_levels = []
    for data in oi_data:
        if _safe_float(data.get('strike_price', 0.0)) > current_price and _safe_float(data.get('ce_oi', 0.0)) > 1000:
            resistance_levels.append({
                'strike': data.get('strike_price'),
                'ce_oi': int(data.get('ce_oi', 0)),
                'distance_pct': round(((_safe_float(data.get('strike_price', 0.0)) - current_price) / max(1e-6, current_price)) * 100, 2)
            })
    
    # Sort and get top levels
    support_levels.sort(key=lambda x: x['pe_oi'], reverse=True)
    resistance_levels.sort(key=lambda x: x['ce_oi'], reverse=True)
    
    return {
        'supports': support_levels[:3],  # Top 3 support levels
        'resistances': resistance_levels[:3]  # Top 3 resistance levels
    }

def analyze_writer_activity(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze writer activity and efficiency (kept; efficiency threshold aligned with intraday logic)"""
    if not oi_data:
        return {}
    
    writer_signals = {
        'call_writing': 0,
        'put_writing': 0,
        'call_unwinding': 0,
        'put_unwinding': 0,
        'efficient_strikes': []
    }
    
    for data in oi_data:
        strike = data.get('strike_price')
        ce_efficiency = _writer_efficiency(data.get('ce_change_oi', 0), data.get('ce_volume', 0))
        pe_efficiency = _writer_efficiency(data.get('pe_change_oi', 0), data.get('pe_volume', 0))
        
        # Identify efficient strikes
        if ce_efficiency > 0.15 or pe_efficiency > 0.15:
            writer_signals['efficient_strikes'].append({
                'strike': strike,
                'ce_efficiency': round(ce_efficiency, 3),
                'pe_efficiency': round(pe_efficiency, 3),
                'ce_change_oi': int(_safe_float(data.get('ce_change_oi', 0))),
                'pe_change_oi': int(_safe_float(data.get('pe_change_oi', 0)))
            })
        
        # Identify writing/unwinding patterns (simple counts)
        if _safe_float(data.get('ce_change_oi', 0)) > 10000:
            writer_signals['call_writing'] += 1
        elif _safe_float(data.get('ce_change_oi', 0)) < -10000:
            writer_signals['call_unwinding'] += 1
            
        if _safe_float(data.get('pe_change_oi', 0)) > 10000:
            writer_signals['put_writing'] += 1
        elif _safe_float(data.get('pe_change_oi', 0)) < -10000:
            writer_signals['put_unwinding'] += 1
    
    return writer_signals

# ----------------------------
# New intraday stock features (added, not breaking)
# ----------------------------

def compute_intraday_stock_features(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Stock-specific intraday analysis on ATM ±2 with strict filtering.
    Returns a dict with fields used later for high-probability filters (50-point premium, etc.).
    """
    if not oi_data:
        return {'error': 'No data'}

    symbol = oi_data[0].get('symbol', '')
    spot = _safe_float(oi_data[0].get('stock_value', 0.0))
    strikes = [int(r.get('strike_price', 0)) for r in oi_data]
    step = _strike_step(strikes)
    atm = _atm(strikes, spot)
    rows5 = _filter_atm_pm2(oi_data, atm, step)

    # PCRs (across all rows, consistent with calculate_pcr_values)
    oi_pcr, vol_pcr = calculate_pcr_values(oi_data)
    pcr_conflict = abs(oi_pcr - vol_pcr) > 0.20

    # 20% median side-volume filters for dominance
    ce_thr, pe_thr = _volume_thresholds(rows5)
    r_stock, activity, denom = _dominance_and_activity(rows5, ce_thr, pe_thr)

    # Build rows_by_strike for trigger/delta
    rows_by_strike = {
        int(r.get('strike_price', 0)): {
            'ce_ltp': _safe_float(r.get('ce_ltp', 0.0)),
            'pe_ltp': _safe_float(r.get('pe_ltp', 0.0)),
            'ce_change_oi': _safe_float(r.get('ce_change_oi', 0.0)),
            'pe_change_oi': _safe_float(r.get('pe_change_oi', 0.0)),
            'ce_volume': _safe_float(r.get('ce_volume', 0.0)),
            'pe_volume': _safe_float(r.get('pe_volume', 0.0)),
            'ce_oi': _safe_float(r.get('ce_oi', 0.0)),
            'pe_oi': _safe_float(r.get('pe_oi', 0.0)),
        } for r in rows5
    }

    # Writer triggers and efficient strikes on ATM ±2
    writer_bull, writer_bear, efficient_strikes = _writer_triggers(rows_by_strike, atm, step)

    # Pivot & separation
    pivot, sep_steps = _pivot_and_separation(rows5, spot, step)

    # Delta proxies and 50-point feasibility (for later filters)
    dC, dP = _delta_proxy(rows_by_strike, step, atm)
    target_premium = 50.0
    req_steps_C = (target_premium / max(0.05, dC) / step) if (dC > 0 and step > 0) else float('inf')
    req_steps_P = (target_premium / max(0.05, dP) / step) if (dP > 0 and step > 0) else float('inf')
    feasible_ce_50 = (req_steps_C <= 2.0)
    feasible_pe_50 = (req_steps_P <= 2.0)

    # Stock PCR bands (for later gating; do not replace your get_pcr_sentiment)
    pcr_band = "balanced"
    if oi_pcr >= 1.10:
        pcr_band = "bullish"
    elif oi_pcr <= 0.90:
        pcr_band = "bearish"

    # Direction hint (for later filtering): requires dominance + PCR + location (not a trade signal yet)
    direction_hint = "Neutral"
    if (r_stock >= 0.15) and (pcr_band == "bullish") and (sep_steps >= 0.4):
        direction_hint = "CE"
    elif (r_stock <= -0.15) and (pcr_band == "bearish") and (sep_steps <= -0.4):
        direction_hint = "PE"

    # Simple pre-filter score for later ranking (stock-only)
    # Focus on dominance, PCR alignment, triggers, activity, feasibility
    pcr_align = clamp((oi_pcr - 1.0) / 0.3, -1, 1) if direction_hint == "CE" else clamp((1.0 - oi_pcr) / 0.3, -1, 1) if direction_hint == "PE" else 0.0
    eff_flag = 1.0 if (writer_bull and direction_hint == "CE") or (writer_bear and direction_hint == "PE") else 0.0
    activity_norm = clamp(activity / 40000.0, 0.0, 1.0)
    feas = clamp((2.0 - (req_steps_C if direction_hint == "CE" else req_steps_P if direction_hint == "PE" else 2.0)) / 2.0, 0.0, 1.0)
    pre_filter_score = round(0.35 * abs(r_stock) + 0.25 * pcr_align + 0.20 * eff_flag + 0.10 * activity_norm + 0.10 * feas, 3)

    return {
        'symbol': symbol,
        'spot': spot,
        'atm': atm,
        'strike_step': step,
        'strikes_used': len(rows5),
        'oi_pcr': oi_pcr,
        'volume_pcr': vol_pcr,
        'pcr_conflict': pcr_conflict,
        'r_stock': round(r_stock, 3),
        'activity': int(activity),
        'pivot': pivot,
        'separation_steps': round(sep_steps, 2),
        'writer_bull_trigger': writer_bull,
        'writer_bear_trigger': writer_bear,
        'efficient_strikes': efficient_strikes,  # list of dicts
        'delta_proxy_ce': round(dC, 3),
        'delta_proxy_pe': round(dP, 3),
        'req_steps_ce_50': round(req_steps_C, 2) if req_steps_C != float('inf') else float('inf'),
        'req_steps_pe_50': round(req_steps_P, 2) if req_steps_P != float('inf') else float('inf'),
        'feasible_ce_50': feasible_ce_50,
        'feasible_pe_50': feasible_pe_50,
        'pcr_band': pcr_band,
        'direction_hint': direction_hint,      # CE / PE / Neutral
        'pre_filter_score': pre_filter_score   # for later ranking
    }

# ----------------------------
# Main analysis API (kept signature)
# ----------------------------

def perform_python_analysis(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Main function to perform complete Python analysis (non-breaking but richer)"""
    if not oi_data:
        return {'error': 'No data available for analysis'}
    
    symbol = oi_data[0].get('symbol', '')
    current_price = _safe_float(oi_data[0].get('stock_value', 0.0))
    
    # Perform all analyses
    oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
    pcr_sentiment = get_pcr_sentiment(oi_pcr, volume_pcr)
    oi_analysis = calculate_oi_analysis(oi_data)
    key_levels = identify_key_levels(oi_data)
    writer_activity = analyze_writer_activity(oi_data)
    intraday_feats = compute_intraday_stock_features(oi_data)  # New, stock-specific
    
    # Compile comprehensive analysis (kept keys + added 'intraday_features')
    analysis_result = {
        'symbol': symbol,
        'current_price': current_price,
        'expiry_date': oi_data[0].get('expiry_date'),
        'pcr_analysis': {
            'oi_pcr': oi_pcr,
            'volume_pcr': volume_pcr,
            'sentiment': pcr_sentiment['sentiment'],
            'confidence': pcr_sentiment['confidence'],
            'reason': pcr_sentiment['reason'],
            'action': pcr_sentiment['action']
        },
        'oi_analysis': oi_analysis,
        'key_levels': key_levels,
        'writer_activity': writer_activity,
        'intraday_features': intraday_feats,   # New block for later filtering logic
        'strikes_analyzed': len(oi_data),
        'analysis_timestamp': None  # Will be set by main program
    }
    
    return analysis_result

# ----------------------------
# Display (kept, with a new section appended)
# ----------------------------

def format_analysis_for_display(analysis: Dict[str, Any]) -> str:
    """Format analysis results for console display"""
    if 'error' in analysis:
        return f"Error: {analysis['error']}"
    
    output = []
    output.append(f"\n{'='*80}")
    output.append(f"PYTHON ANALYSIS: {analysis['symbol']}")
    output.append(f"{'='*80}")
    output.append(f"Current Price: {analysis['current_price']} | Expiry: {analysis['expiry_date']}")
    output.append(f"Strikes Analyzed: {analysis['strikes_analyzed']} (full chain fed); Intraday uses ATM ±2")
    
    # PCR Analysis
    pcr = analysis['pcr_analysis']
    output.append(f"\n📊 PCR ANALYSIS:")
    output.append(f"  OI PCR: {pcr['oi_pcr']:.3f} | Volume PCR: {pcr['volume_pcr']:.3f}")
    output.append(f"  Sentiment: {pcr['sentiment']} | Confidence: {pcr['confidence']}")
    output.append(f"  Reason: {pcr['reason']}")
    output.append(f"  Action: {pcr['action']}")
    
    # OI Analysis
    oi = analysis['oi_analysis']
    output.append(f"\n📈 OI ANALYSIS:")
    output.append(f"  Net OI Change: {oi['net_oi_change']:+,} (PE-CE)")
    output.append(f"  CE Change: {oi['total_ce_change_oi']:+,} | PE Change: {oi['total_pe_change_oi']:+,}")
    output.append(f"  Max CE OI: {oi['max_ce_oi_value']:,} @ {oi['max_ce_oi_strike']}")
    output.append(f"  Max PE OI: {oi['max_pe_oi_value']:,} @ {oi['max_pe_oi_strike']}")
    output.append(f"  IV Skew: {oi['iv_skew']}% (PE-CE)")
    
    # Key Levels
    levels = analysis['key_levels']
    if levels.get('supports'):
        output.append(f"\n🛡️ SUPPORT LEVELS:")
        for support in levels['supports']:
            output.append(f"  {support['strike']} (OI: {support['pe_oi']:,}, {support['distance_pct']}% below)")
    
    if levels.get('resistances'):
        output.append(f"\n🎯 RESISTANCE LEVELS:")
        for resistance in levels['resistances']:
            output.append(f"  {resistance['strike']} (OI: {resistance['ce_oi']:,}, {resistance['distance_pct']}% above)")
    
    # Writer Activity (broad)
    writer = analysis['writer_activity']
    if writer.get('efficient_strikes'):
        output.append(f"\n⚡ EFFICIENT WRITER ACTIVITY (full chain):")
        for strike_info in writer['efficient_strikes'][:3]:  # Show top 3
            output.append(f"  Strike {strike_info['strike']}: CE Eff {strike_info['ce_efficiency']}, PE Eff {strike_info['pe_efficiency']}")
    
    # Intraday stock features (ATM ±2, strict; new section)
    feats = analysis.get('intraday_features', {})
    if feats and 'error' not in feats:
        output.append(f"\n🧭 INTRADAY STOCK FEATURES (ATM ±2):")
        output.append(f"  ATM: {feats['atm']} | Step: {feats['strike_step']} | Used Strikes: {feats['strikes_used']}")
        output.append(f"  Activity: {feats['activity']:,} | r_stock: {feats['r_stock']:+.2f} | PCR band: {feats['pcr_band']} | PCR conflict: {feats['pcr_conflict']}")
        output.append(f"  Pivot: {feats['pivot']} | Separation: {feats['separation_steps']:+.2f} steps")
        output.append(f"  Writer triggers: bull {feats['writer_bull_trigger']} | bear {feats['writer_bear_trigger']}")
        if feats.get('efficient_strikes'):
            top_eff = feats['efficient_strikes'][:3]
            output.append("  Top efficient strikes:")
            for e in top_eff:
                output.append(f"    {e['strike']}: CE Eff {e['ce_efficiency']} | PE Eff {e['pe_efficiency']} | dCE {e['ce_change_oi']} | dPE {e['pe_change_oi']}")
        output.append(f"  Delta proxies: CE {feats['delta_proxy_ce']:.3f} | PE {feats['delta_proxy_pe']:.3f}")
        output.append(f"  Req steps for 50 premium: CE {feats['req_steps_ce_50']} | PE {feats['req_steps_pe_50']}")
        output.append(f"  Feasible 50-pt: CE {feats['feasible_ce_50']} | PE {feats['feasible_pe_50']}")
        output.append(f"  Direction hint: {feats['direction_hint']} | Pre-filter score: {feats['pre_filter_score']}")
    
    output.append(f"{'='*80}")
    
    return "\n".join(output)