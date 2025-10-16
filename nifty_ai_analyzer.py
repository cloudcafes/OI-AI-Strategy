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

    def format_data_for_ai(self,
                           oi_data: List[Dict[str, Any]],
                           current_cycle: int,
                           total_fetches: int,
                           oi_pcr: float,
                           volume_pcr: float,
                           current_nifty: float,
                           stock_data: Optional[Dict[str, Any]] = None,
                           banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Format all data as raw data sections for AI analysis - no preprocessing."""
        formatted_text = f"NIFTY DATA (Cycle: {current_cycle}/10, Total: {total_fetches})\n"
        formatted_text += f"Nifty Spot: {current_nifty}\n"
        formatted_text += "PCR VALUES:\n"
        formatted_text += f"OI PCR = {oi_pcr:.2f}\n"
        formatted_text += f"Volume PCR = {volume_pcr:.2f}\n"
        formatted_text += "=" * 80 + "\n"
        formatted_text += "OI DATA (ATM ±2 strikes):\n"

        # Raw Nifty OI data
        for row in oi_data:
            strike = row['strike_price']
            formatted_text += (
                f"Strike {strike}: "
                f"CE[ChgOI:{row.get('ce_change_oi', 0)}, Vol:{row.get('ce_volume', 0)}, "
                f"LTP:{row.get('ce_ltp', 0.0):.1f}, OI:{row.get('ce_oi', 0)}, IV:{row.get('ce_iv', 0.0):.1f}%] | "
                f"PE[ChgOI:{row.get('pe_change_oi', 0)}, Vol:{row.get('pe_volume', 0)}, "
                f"LTP:{row.get('pe_ltp', 0.0):.1f}, OI:{row.get('pe_oi', 0)}, IV:{row.get('pe_iv', 0.0):.1f}%]\n"
            )

        # BankNifty data if available
        if banknifty_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "BANKNIFTY DATA\n"
            formatted_text += "=" * 80 + "\n"
            formatted_text += f"BankNifty Spot: {banknifty_data.get('current_value')}\n"
            formatted_text += "PCR VALUES:\n"
            formatted_text += f"OI PCR = {banknifty_data.get('oi_pcr', 0.0):.2f}\n"
            formatted_text += f"Volume PCR = {banknifty_data.get('volume_pcr', 0.0):.2f}\n"
            formatted_text += "OI DATA (ATM ±2 strikes):\n"
            
            for row in banknifty_data.get('data', []):
                strike = row['strike_price']
                formatted_text += (
                    f"Strike {strike}: "
                    f"CE[ChgOI:{row.get('ce_change_oi', 0)}, Vol:{row.get('ce_volume', 0)}, "
                    f"LTP:{row.get('ce_ltp', 0.0):.1f}, OI:{row.get('ce_oi', 0)}, IV:{row.get('ce_iv', 0.0):.1f}%] | "
                    f"PE[ChgOI:{row.get('pe_change_oi', 0)}, Vol:{row.get('pe_volume', 0)}, "
                    f"LTP:{row.get('pe_ltp', 0.0):.1f}, OI:{row.get('pe_oi', 0)}, IV:{row.get('pe_iv', 0.0):.1f}%]\n"
                )

        # Stock data if available
        if stock_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "TOP 10 NIFTY STOCKS DATA\n"
            formatted_text += "=" * 80 + "\n"
            
            for symbol, info in stock_data.items():
                rows = info.get('data', [])
                if not rows:
                    continue
                    
                stock_px = rows[0].get('stock_value') if rows else None
                formatted_text += f"\n{symbol} (Weight: {info.get('weight', 0.0):.4f}, Price: {stock_px}):\n"
                formatted_text += "PCR VALUES:\n"
                formatted_text += f"OI PCR: {info.get('oi_pcr', 0.0):.2f}, Volume PCR: {info.get('volume_pcr', 0.0):.2f}\n"
                formatted_text += "OI DATA (ATM ±2 strikes):\n"
                
                for r in rows:
                    strike = r['strike_price']
                    formatted_text += (
                        f"  Strike {strike}: "
                        f"CE[ChgOI:{r.get('ce_change_oi', 0)}, Vol:{r.get('ce_volume', 0)}, "
                        f"LTP:{r.get('ce_ltp', 0.0):.1f}, IV:{r.get('ce_iv', 0.0):.1f}%] | "
                        f"PE[ChgOI:{r.get('pe_change_oi', 0)}, Vol:{r.get('pe_volume', 0)}, "
                        f"LTP:{r.get('pe_ltp', 0.0):.1f}, IV:{r.get('pe_iv', 0.0):.1f}%]\n"
                    )
        
        return formatted_text

    def get_ai_analysis(self,
                        oi_data: List[Dict[str, Any]],
                        current_cycle: int,
                        total_fetches: int,
                        oi_pcr: float,
                        volume_pcr: float,
                        current_nifty: float,
                        stock_data: Optional[Dict[str, Any]] = None,
                        banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Request AI analysis with raw data passing only."""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        # Format raw data for AI
        formatted_data = self.format_data_for_ai(
            oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data, banknifty_data
        )

        # Your existing prompt - preserved exactly as is
        SYSTEM_PROMPT = """
        You are an expert Nifty/BankNifty/top10 Nifty Stocks by weightage option chain analyst with deep knowledge of historical patterns and institutional trading behavior. You read between the lines to decode both smart money AND retail perspectives. You perform mathematical calculations, psychological analysis, and interlink all data points to understand market dynamics. Take your time for thorough analysis.

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Analyze the provided OI data for Nifty index (weekly expiry), BankNifty index (monthly expiry), and top 10 Nifty Stocks (monthly expiry) to interpret the intraday trend. 

        CRITICAL ANALYSIS FRAMEWORK - FOLLOW THIS ORDER:

        1. PCR CONFLICT RESOLUTION: When OI PCR and Volume PCR contradict:
        - Volume PCR takes priority for intraday momentum
        - OI PCR indicates institutional positioning
        - Major divergence (>0.3 difference) suggests false signals

        2. SECTOR CONFIRMATION: 
        - BankNifty must confirm Nifty direction
        - Majority of top 10 stocks should align with index signals
        - Contradictory sector signals reduce probability

        3. OI CHANGE INTERPRETATION:
        - Put writing can be HEDGING (bearish) or BULLISH positioning
        - Call writing can be BEARISH or PROFIT-TAKING
        - Analyze CE-PE differences and volume context

        4. FALSE SIGNAL DETECTION:
        - Identify when institutional activity contradicts price action
        - Spot hedging vs directional positioning
        - Recognize manipulation in stock options

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Provide output categorically:
        - Short summary with clear directional bias
        - Breakdown of conflicting/confirming signals
        - ATM+1 vs ATM-1 probability with mathematical justification
        - Specific entry levels, stop-loss, targets
        - Risk assessment and contradictory evidence

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        I only take naked Nifty CE/PE buys for intraday. Recommend "buy on dip" or "sell on rise" levels to avoid wrong entries. Include:
        - Exact strike and entry price range
        - Stop-loss based on premium and spot levels
        - Realistic targets (40-60% for intraday)
        - Conditions that would invalidate the trade
        - Hedge recommendations for uncertainty

        Focus on intraday implications only. Identify when data suggests "NO TRADE" due to conflicting evidence.
        """
        user_content = f"CURRENT DATA FOR ANALYSIS\n{formatted_data}\n"

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