# stock-analyzer.py
# Python analysis with aggregate metrics for complete option chain

from statistics import median
from typing import Dict, List, Any, Tuple

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def calculate_pcr_values(oi_data: List[Dict[str, Any]]) -> Tuple[float, float]:
    """Calculate OI PCR and Volume PCR for complete stock option chain data"""
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

def calculate_aggregate_metrics(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate the 6 aggregate metrics for complete option chain"""
    if not oi_data:
        return {}
    
    # Calculate totals for entire chain
    total_ce_oi_change = sum(data.get('ce_change_oi', 0) for data in oi_data)
    total_pe_oi_change = sum(data.get('pe_change_oi', 0) for data in oi_data)
    total_ce_oi = sum(data.get('ce_oi', 0) for data in oi_data)
    total_pe_oi = sum(data.get('pe_oi', 0) for data in oi_data)
    
    # Calculate OI Change percentages for entire chain
    ce_oi_change_pct = (total_ce_oi_change / total_ce_oi * 100) if total_ce_oi > 0 else 0.0
    pe_oi_change_pct = (total_pe_oi_change / total_pe_oi * 100) if total_pe_oi > 0 else 0.0
    
    # Calculate PCR values
    oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
    
    return {
        'Total CE OI Change': int(total_ce_oi_change),
        'Total CE OI Change%': round(ce_oi_change_pct, 2),
        'Total PE OI Change': int(total_pe_oi_change),
        'Total PE OI Change%': round(pe_oi_change_pct, 2),
        'OI PCR': oi_pcr,
        'Volume PCR': volume_pcr
    }

def get_pcr_sentiment(oi_pcr: float, volume_pcr: float) -> Dict[str, Any]:
    """Generate sentiment analysis based on PCR values"""
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

def perform_python_analysis(oi_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Main function to perform complete Python analysis with aggregate metrics"""
    if not oi_data:
        return {'error': 'No data available for analysis'}
    
    symbol = oi_data[0].get('symbol', '')
    current_price = _safe_float(oi_data[0].get('stock_value', 0.0))
    
    # Calculate aggregate metrics for trend classification
    aggregate_metrics = calculate_aggregate_metrics(oi_data)
    
    # Calculate PCR sentiment
    oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
    pcr_sentiment = get_pcr_sentiment(oi_pcr, volume_pcr)
    
    # Identify key levels
    key_levels = identify_key_levels(oi_data)
    
    # Compile comprehensive analysis
    analysis_result = {
        'symbol': symbol,
        'current_price': current_price,
        'expiry_date': oi_data[0].get('expiry_date'),
        'aggregate_metrics': aggregate_metrics,  # The 6 key metrics for trend classification
        'pcr_analysis': {
            'oi_pcr': oi_pcr,
            'volume_pcr': volume_pcr,
            'sentiment': pcr_sentiment['sentiment'],
            'confidence': pcr_sentiment['confidence'],
            'reason': pcr_sentiment['reason'],
            'action': pcr_sentiment['action']
        },
        'key_levels': key_levels,
        'strikes_analyzed': len(oi_data),
        'analysis_timestamp': None  # Will be set by main program
    }
    
    return analysis_result

def format_analysis_for_display(analysis: Dict[str, Any]) -> str:
    """Format analysis results for console display"""
    if 'error' in analysis:
        return f"Error: {analysis['error']}"
    
    output = []
    output.append(f"\n{'='*80}")
    output.append(f"PYTHON ANALYSIS: {analysis['symbol']}")
    output.append(f"{'='*80}")
    output.append(f"Current Price: {analysis['current_price']} | Expiry: {analysis['expiry_date']}")
    output.append(f"Strikes Analyzed: {analysis['strikes_analyzed']} (Complete Chain)")
    
    # Aggregate Metrics
    metrics = analysis['aggregate_metrics']
    output.append(f"\n📊 AGGREGATE METRICS (Complete Chain):")
    output.append(f"  Total CE OI Change: {metrics['Total CE OI Change']:+,} ({metrics['Total CE OI Change%']}%)")
    output.append(f"  Total PE OI Change: {metrics['Total PE OI Change']:+,} ({metrics['Total PE OI Change%']}%)")
    output.append(f"  OI PCR: {metrics['OI PCR']:.3f} | Volume PCR: {metrics['Volume PCR']:.3f}")
    
    # PCR Analysis
    pcr = analysis['pcr_analysis']
    output.append(f"\n🎯 PCR SENTIMENT:")
    output.append(f"  Sentiment: {pcr['sentiment']} | Confidence: {pcr['confidence']}")
    output.append(f"  Reason: {pcr['reason']}")
    output.append(f"  Action: {pcr['action']}")
    
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
    
    output.append(f"{'='*80}")
    
    return "\n".join(output)