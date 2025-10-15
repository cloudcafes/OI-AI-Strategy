# Part 2: Nifty_Option_Chain_Fetcher_Part2.py
import requests
import datetime
import time
import sqlite3
# Import from Part 1
from Nifty_Option_Chain_Fetcher_Part1 import (
    SYMBOL, MAX_RETRIES, INITIAL_RETRY_DELAY, HEADERS, 
    parse_numeric_value, parse_float_value, DB_FILE, get_next_cycle, format_greek_value
)

def fetch_option_chain(session):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={SYMBOL}"
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))
            else:
                raise Exception(f"Failed after {MAX_RETRIES} attempts: {str(e)}")

def parse_option_chain(data):
    try:
        current_nifty = data['records']['underlyingValue']
        records = data['records']['data']
        nearest_expiry = data['records']['expiryDates'][0]
        
        # Filter for nearest expiry only
        nearest_expiry_records = [record for record in records if record['expiryDate'] == nearest_expiry]
        strike_prices = sorted(list(set(record['strikePrice'] for record in nearest_expiry_records)))
        
        # Find closest strike and select ATM ±2 strikes only
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_nifty))
        closest_index = strike_prices.index(closest_strike)
        
        # Get ATM ±2 strikes (total 5 strikes)
        selected_strikes = strike_prices[max(0, closest_index - 2):min(len(strike_prices), closest_index + 3)]
        
        filtered_records = []
        
        for strike in selected_strikes:
            record = next((r for r in nearest_expiry_records if r['strikePrice'] == strike), None)
            if record:
                # Parse CE data without Greeks (delta, gamma, theta, vega removed)
                ce_data = record.get('CE', {})
                # Parse PE data without Greeks (delta, gamma, theta, vega removed)
                pe_data = record.get('PE', {})
                
                oi_data = {
                    'nifty_value': round(current_nifty),
                    'expiry_date': nearest_expiry,
                    'strike_price': strike,
                    # CE Data - only IV kept, other Greeks removed
                    'ce_change_oi': parse_numeric_value(ce_data.get('changeinOpenInterest', 0)),
                    'ce_volume': parse_numeric_value(ce_data.get('totalTradedVolume', 0)),
                    'ce_ltp': parse_float_value(ce_data.get('lastPrice', 0)),
                    'ce_oi': parse_numeric_value(ce_data.get('openInterest', 0)),
                    'ce_iv': parse_float_value(ce_data.get('impliedVolatility', 0)),
                    # PE Data - only IV kept, other Greeks removed
                    'pe_change_oi': parse_numeric_value(pe_data.get('changeinOpenInterest', 0)),
                    'pe_volume': parse_numeric_value(pe_data.get('totalTradedVolume', 0)),
                    'pe_ltp': parse_float_value(pe_data.get('lastPrice', 0)),
                    'pe_oi': parse_numeric_value(pe_data.get('openInterest', 0)),
                    'pe_iv': parse_float_value(pe_data.get('impliedVolatility', 0)),
                }
                filtered_records.append(oi_data)
        
        return filtered_records
    except Exception as e:
        raise Exception(f"Error parsing option chain: {str(e)}")

def calculate_pcr_values(oi_data):
    """Calculate OI PCR and Volume PCR for ATM ±2 strikes"""
    total_ce_oi = 0
    total_pe_oi = 0
    total_ce_volume = 0
    total_pe_volume = 0
    
    for data in oi_data:
        total_ce_oi += data['ce_oi']
        total_pe_oi += data['pe_oi']
        total_ce_volume += data['ce_volume']
        total_pe_volume += data['pe_volume']
    
    # Calculate PCR values
    oi_pcr = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 0
    volume_pcr = total_pe_volume / total_ce_volume if total_ce_volume > 0 else 0
    
    return oi_pcr, volume_pcr

def get_pcr_signals(oi_pcr, volume_pcr):
    """Generate signals based on PCR values using the new conditions"""
    
    # Condition 1: Extreme Bullish Sentiment
    if oi_pcr > 1.3 and volume_pcr > 1.5:
        return (
            "EXTREME BULLISH - Strong upside breakout likely",
            "Very High (70%+)",
            "Strong put writing across ATM ±2 strikes shows institutional confidence",
            "Look for breakout above VWAP or prior high for 0.6-1.0% upside move"
        )
    
    # Condition 2: Strong Bullish Sentiment
    elif 1.1 <= oi_pcr <= 1.3 and 1.1 <= volume_pcr <= 1.5:
        return (
            "STRONG BULLISH - Upside continuation expected",
            "High (63-68%)",
            "Steady put buildup shows smart money expecting upside",
            "Confirm with price breaking day high or VWAP"
        )
    
    # Condition 3: Weak Volume / Cautious Bullish
    elif 1.1 <= oi_pcr <= 1.2 and volume_pcr < 1.0:
        return (
            "CAUTIOUS BULLISH - Upside stalling",
            "Medium (40-45%)",
            "OI shows bullish positioning but low volume suggests disinterest",
            "Wait for strong breakout confirmation before bullish trades"
        )
    
    # Condition 4: Neutral or No Edge
    elif 0.9 <= oi_pcr <= 1.1 and 0.9 <= volume_pcr <= 1.1:
        return (
            "NEUTRAL - Sideways range-bound",
            "Moderate (45%)",
            "Balanced positioning between calls and puts",
            "Better for scalping or range trades, avoid direction bets"
        )
    
    # Condition 5: Bearish Set-Up
    elif oi_pcr < 0.9 and volume_pcr < 0.8:
        return (
            "BEARISH - Downside expected",
            "High (65-68%)",
            "Rising call OI or dropping put volume confirms bearish sentiment",
            "Look for breaks below VWAP or sell-on-rise setups"
        )
    
    # Condition 6: High Probability Breakdown
    elif oi_pcr < 0.75 and volume_pcr < 0.7:
        return (
            "EXTREME BEARISH - Panic selling/breakdown",
            "Very High (70-75%)",
            "Very low put activity shows no confidence in market stability",
            "High probability of continued fall below VWAP"
        )
    
    # Condition 7: Bear Trap or Short-Covering Possibility
    elif oi_pcr < 0.9 and volume_pcr > 1.2:
        return (
            "BEAR TRAP - Possible reversal upside",
            "Medium (55-60%)",
            "Bearish OI but high put volume shows panic put buying",
            "Watch for quick recovery candles or bullish divergences"
        )
    
    # Condition 8: Bull Trap or Sluggish Bull Phase
    elif oi_pcr > 1.1 and volume_pcr < 0.8:
        return (
            "BULL TRAP - Possible reversal downside",
            "Medium (53-60%)",
            "Bullish OI but low volume suggests weakening upside",
            "Likely pullback if price fails to clear day high"
        )
    
    # Default condition for unclassified scenarios
    else:
        return (
            "MIXED SIGNALS - Wait for confirmation",
            "Low",
            "Conflicting signals between OI and volume PCR",
            "Wait for clearer setup or price confirmation"
        )