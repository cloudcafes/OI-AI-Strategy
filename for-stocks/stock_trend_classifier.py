# stock_trend_classifier.py
# Optimized trend classification for NSE F&O stock option chain data with confidence >=50% filter

def classify_stock_trend(data: dict) -> dict:
    """
    Classifies a stock's market trend based on a snapshot of options data.
    Returns result only if confidence >=50%, else returns empty dict.
    
    Parameters:
    -----------
    data: dict - A dictionary containing the following keys:
        'Total CE OI Change', 'Total CE OI Change%', 
        'Total PE OI Change', 'Total PE OI Change%',
        'OI PCR', 'Volume PCR'
    
    Returns:
    --------
    dict: Contains 'trend', 'confidence', 'scores', 'signals' if confidence >=50%, else {}
    """
    
    # Unpack data for clarity
    ce_oi_change_abs = data['Total CE OI Change']
    ce_oi_change_pct = data['Total CE OI Change%']
    pe_oi_change_abs = data['Total PE OI Change']
    pe_oi_change_pct = data['Total PE OI Change%']
    oi_pcr = data['OI PCR']
    volume_pcr = data['Volume PCR']

    # Initialize signal weights
    signals = []
    bullish_score = 0
    bearish_score = 0
    
    # --- CONDITION 1: OI PCR (Overall Positioning/Sentiment) - Flipped for stocks ---
    if oi_pcr < 0.7:
        bullish_score += 2.5
        signals.append("OI PCR < 0.7 (Strong Bullish Positioning/More Calls)")
    elif oi_pcr < 0.9:
        bullish_score += 1.5
        signals.append("OI PCR < 0.9 (Moderate Bullish Positioning)")
    elif oi_pcr > 1.3:
        bearish_score += 2.5
        signals.append("OI PCR > 1.3 (Strong Bearish Positioning/More Puts)")
    elif oi_pcr > 1.1:
        bearish_score += 1.5
        signals.append("OI PCR > 1.1 (Moderate Bearish Positioning)")
    else:
        signals.append("OI PCR is Neutral (0.9-1.1)")
        
    # Extreme PCR (contrarian exhaustion) - Flipped
    if oi_pcr > 2.0:
        signals.append("Extreme OI PCR > 2.0 (Bearish Exhaustion/Potential Bullish Reversal)")
        bullish_score += 0.5
    elif oi_pcr < 0.4:
        signals.append("Extreme OI PCR < 0.4 (Bullish Exhaustion/Potential Bearish Reversal)")
        bearish_score += 0.5
        
    # --- CONDITION 2: Volume PCR (Intraday Action/Aggression) - Increased weight for momentum ---
    if volume_pcr > 1.2:
        bearish_score += 2.0
        signals.append("Volume PCR > 1.2 (High Intraday Bearish Aggression - Confirm with OI)")
    elif volume_pcr < 0.8:
        bullish_score += 2.0
        signals.append("Volume PCR < 0.8 (High Intraday Bullish Aggression - Confirm with OI)")
        
    # --- CONDITION 3 & 4: OI Change (Flows & Conviction) - Loosened thresholds ---
    # Call Side
    if ce_oi_change_pct > 12:
        bearish_score += 2
        if ce_oi_change_abs > 2000:
            bearish_score += 0.5  # Lowered absolute boost
        signals.append("CE OI Change > 12% (Strong Call Writing/Resistance Building)")
    elif 5 < ce_oi_change_pct <= 12:
        bearish_score += 1
        signals.append("CE OI Change 5-12% (Moderate Call Writing)")
    elif ce_oi_change_pct < -8:
        bullish_score += 2
        if abs(ce_oi_change_abs) > 2000:
            bullish_score += 0.5
        signals.append("CE OI Change < -8% (Strong Call Unwinding/Short Covering)")
    elif -8 <= ce_oi_change_pct < -3:
        bullish_score += 1
        signals.append("CE OI Change -3 to -8% (Moderate Call Unwinding)")
    
    # Put Side
    if pe_oi_change_pct > 12:
        bullish_score += 2
        if pe_oi_change_abs > 2000:
            bullish_score += 0.5
        signals.append("PE OI Change > 12% (Strong Put Writing/Support Building)")
    elif 5 < pe_oi_change_pct <= 12:
        bullish_score += 1
        signals.append("PE OI Change 5-12% (Moderate Put Writing)")
    elif pe_oi_change_pct < -8:
        bearish_score += 2
        if abs(pe_oi_change_abs) > 2000:
            bearish_score += 0.5
        signals.append("PE OI Change < -8% (Strong Put Unwinding/Support Breaking)")
    elif -8 <= pe_oi_change_pct < -3:
        bearish_score += 1
        signals.append("PE OI Change -3 to -8% (Moderate Put Unwinding)")
    
    # Synergy: Opposite directional moves - Loosened
    if pe_oi_change_pct > 5 and ce_oi_change_pct < 0:
        bullish_score += 1
        signals.append("Synergy: PE Buildup + CE Decline (Bullish Conviction)")
    if ce_oi_change_pct > 5 and pe_oi_change_pct < 0:
        bearish_score += 1
        signals.append("Synergy: CE Buildup + PE Decline (Bearish Conviction)")
    
    # Momentum bias: Large OI change + aligned PCR
    if (pe_oi_change_pct > 15 or ce_oi_change_pct < -15) and oi_pcr < 0.9:
        bullish_score += 1
        signals.append("Momentum Bias: Large Bullish OI Shift + Supportive PCR")
    if (ce_oi_change_pct > 15 or pe_oi_change_pct < -15) and oi_pcr > 1.1:
        bearish_score += 1
        signals.append("Momentum Bias: Large Bearish OI Shift + Supportive PCR")
    
    # Both Down: Low conviction
    is_low_conviction = False
    if ce_oi_change_pct < -3 and pe_oi_change_pct < -3:
        signals.append("Both CE & PE OI Declining (Broad Unwinding - Low Conviction/Sideways)")
        is_low_conviction = True
    
    # --- CONDITION 5: Divergence & Confirmation (Reversal Signals) - Flipped ---
    is_reversal_signal = False
    is_bullish_reversal = False
    is_bearish_reversal = False
    
    # Bearish Reversal: Bullish positioning (low OI PCR) + Bearish action (high Vol PCR)
    if oi_pcr < 0.9 and volume_pcr > 1.2:
        signals.append("DIVERGENCE: Bullish Positioning (Low OI PCR) vs Bearish Action (High Vol PCR) -> Potential Bearish Reversal")
        bearish_score += 2
        is_bearish_reversal = True
        is_reversal_signal = True

    # Bullish Reversal: Bearish positioning (high OI PCR) + Bullish action (low Vol PCR)
    if oi_pcr > 1.1 and volume_pcr < 0.8:
        signals.append("DIVERGENCE: Bearish Positioning (High OI PCR) vs Bullish Action (Low Vol PCR) -> Potential Bullish Reversal")
        bullish_score += 2
        is_bullish_reversal = True
        is_reversal_signal = True

    # --- CONDITION 6: Volatility Signal (Synchronized Movement) ---
    is_volatility_signal = False
    if ce_oi_change_pct > 5 and pe_oi_change_pct > 5:
        signals.append("VOLATILITY ALERT: Both CE & PE OI Rising (Straddle/Strangle Buildup)")
        is_volatility_signal = True
        # Bias if difference >5%
        if pe_oi_change_pct - ce_oi_change_pct > 5:
            bullish_score += 0.5
        elif ce_oi_change_pct - pe_oi_change_pct > 5:
            bearish_score += 0.5

    # Apply low conviction reduction (exempt if large absolute changes for momentum)
    if is_low_conviction and max(abs(ce_oi_change_abs), abs(pe_oi_change_abs)) < 5000:
        bullish_score *= 0.8
        bearish_score *= 0.8

    # --- FINAL TREND CLASSIFICATION - Loosened for more sensitivity ---
    net_score = bullish_score - bearish_score
    confidence = min(abs(net_score) / 12 * 100, 100)  # Updated normalization

    # --- Confidence Filter: Return only if confidence >=50% ---
    if confidence < 50:
        return {}  # Empty dict for stocks with low confidence

    trend = "SIDEWAYS"  # Default
    if is_volatility_signal and abs(net_score) < 3:
        trend = "HIGH_VOLATILITY_EXPECTED"
    elif net_score >= 3.5:
        trend = "STRONG_BULLISH"
    elif net_score >= 1.5:
        trend = "BULLISH"
    elif net_score <= -3.5:
        trend = "STRONG_BEARISH"
    elif net_score <= -1.5:
        trend = "BEARISH"
    
    # Override with reversal signal
    if is_reversal_signal:
        if is_bullish_reversal:
            trend = "BULLISH_REVERSAL_CANDIDATE"
        if is_bearish_reversal:
            trend = "BEARISH_REVERSAL_CANDIDATE"

    return {
        'trend': trend,
        'confidence': round(confidence, 2),
        'scores': {
            'bullish': round(bullish_score, 2),
            'bearish': round(bearish_score, 2),
            'net': round(net_score, 2),
        },
        'signals': signals
    }


# Example usage for multiple stocks
if __name__ == "__main__":
    # Sample stock data (simulating 3 stocks from the 206 NSE F&O list)
    stock_data_list = [
        {
            'stock': 'RELIANCE',
            'Total CE OI Change': -10000, 'Total CE OI Change%': -13.0,
            'Total PE OI Change': 15000, 'Total PE OI Change%': 19.0,
            'OI PCR': 0.65, 'Volume PCR': 0.75
        },
        {
            'stock': 'HDFCBANK',
            'Total CE OI Change': -3000, 'Total CE OI Change%': -6.0,
            'Total PE OI Change': -4000, 'Total PE OI Change%': -7.0,
            'OI PCR': 1.0, 'Volume PCR': 0.95
        },
        {
            'stock': 'ASHOKLEY',
            'Total CE OI Change': 12000, 'Total CE OI Change%': 19.0,
            'Total PE OI Change': -8000, 'Total PE OI Change%': -13.0,
            'OI PCR': 1.35, 'Volume PCR': 1.3
        }
    ]

    # Process multiple stocks and filter for confidence >=50%
    print("Stocks with Confidence >=50%:")
    for data in stock_data_list:
        result = classify_stock_trend(data)
        if result:  # Only print non-empty results
            print(f"Stock: {data['stock']}")
            print(f"Result: {result['trend']} (Confidence: {result['confidence']}%)")
            print(f"Signals: {result['signals']}\n")