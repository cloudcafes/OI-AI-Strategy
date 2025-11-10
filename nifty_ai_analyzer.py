import os
import time
import json
import datetime
import requests
import httpx
import glob
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from openai import OpenAI

class NiftyAIAnalyzer:
    def __init__(self, api_key: Optional[str] = None):
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

    def save_analysis_to_history(self, raw_data: str, ai_response: str, query_type: str = "single") -> bool:
        """Save both raw data and AI response to history file with latest on top."""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"deepseek {query_type.upper()} analysis done at {timestamp}"
            separator = "=" * 80
            
            new_entry = f"{header}\n{separator}\n"
            new_entry += f"QUERY TYPE: {query_type.upper()}\n"
            new_entry += f"RAW DATA SENT TO AI:\n{separator}\n{raw_data}\n\n"
            new_entry += f"AI ANALYSIS RESPONSE:\n{separator}\n{ai_response}\n{separator}\n\n"

            existing_content = ""
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()

            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(new_entry + existing_content)
                
            print(f"✅ {query_type.upper()} analysis saved to {self.history_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving analysis to history: {e}")
            return False

    def _clean_ai_response(self, text: str) -> str:
        """Clean and format AI response for better console display."""
        if not text:
            return "No response from AI"

        cleaned = text.replace("```json", "").replace("```", "")
        cleaned = cleaned.replace("**", "").replace("*", "")
        
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

        result = '\n'.join(cleaned_lines)
        result = result.replace(' : ', ': ')
        result = result.replace(' , ', ', ')
        result = result.replace(' . ', '. ')
        
        return result

    def find_latest_multi_expiry_file(self) -> Optional[str]:
        """Find the most recent multi-expiry analysis file."""
        try:
            from nifty_core_config import get_multi_expiry_logs_directory
            logs_dir = get_multi_expiry_logs_directory()
            
            if not os.path.exists(logs_dir):
                print(f"⚠️ Multi-expiry logs directory not found: {logs_dir}")
                return None

            pattern = os.path.join(logs_dir, "multi_expiry_analysis_*.txt")
            files = glob.glob(pattern)
            
            if not files:
                print("⚠️ No multi-expiry analysis files found")
                return None

            # Sort by creation time and get the latest
            latest_file = max(files, key=os.path.getctime)
            print(f"✅ Found latest multi-expiry file: {os.path.basename(latest_file)}")
            return latest_file
            
        except Exception as e:
            print(f"❌ Error finding multi-expiry file: {e}")
            return None

    def find_latest_eod_files(self, count: int = 3) -> List[str]:
        """Find the latest EOD state block files (T, T-1, T-2)."""
        try:
            from nifty_core_config import get_eod_base_directory
            eod_dir = get_eod_base_directory()
            
            if not os.path.exists(eod_dir):
                print(f"⚠️ EOD directory not found: {eod_dir}")
                return []

            pattern = os.path.join(eod_dir, "EOD_STATE_BLOCK_OF_*.txt")
            files = glob.glob(pattern)
            
            if not files:
                print("⚠️ No EOD state block files found")
                return []

            # Sort by creation time (newest first) and take the requested count
            sorted_files = sorted(files, key=os.path.getctime, reverse=True)
            latest_files = sorted_files[:count]
            
            print(f"✅ Found {len(latest_files)} EOD files:")
            for i, file in enumerate(latest_files):
                print(f"   T-{i}: {os.path.basename(file)}")
                
            return latest_files
            
        except Exception as e:
            print(f"❌ Error finding EOD files: {e}")
            return []

    def read_file_content(self, filepath: str) -> str:
        """Read content from a file with proper error handling."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error reading file {filepath}: {str(e)}"

    def format_multi_ai_query(self) -> Tuple[str, str]:
        """Format multi AI query with file attachments."""
        try:
            # Find required files
            multi_expiry_file = self.find_latest_multi_expiry_file()
            eod_files = self.find_latest_eod_files(3)
            
            if not multi_expiry_file:
                return "", "No multi-expiry analysis file found"
                
            if len(eod_files) < 3:
                return "", f"Insufficient EOD files found: {len(eod_files)}/3 required"

            # Read file contents
            multi_expiry_content = self.read_file_content(multi_expiry_file)
            eod_contents = [self.read_file_content(f) for f in eod_files]
            
            # Construct the query with file attachments
            query_content = f"MULTI-EXPIRY AI ANALYSIS REQUEST\n"
            query_content += "=" * 80 + "\n\n"
            
            query_content += f"MAIN DATA FILE: {os.path.basename(multi_expiry_file)}\n"
            query_content += "CONTENT:\n" + "=" * 80 + "\n"
            query_content += multi_expiry_content + "\n\n"
            
            query_content += "HISTORICAL EOD FILES ATTACHED:\n"
            query_content += "=" * 80 + "\n"
            for i, (file_path, content) in enumerate(zip(eod_files, eod_contents)):
                query_content += f"EOD_FILE_T-{i}: {os.path.basename(file_path)}\n"
                query_content += f"CONTENT:\n{'-'*40}\n{content}\n{'-'*40}\n\n"
            
            return query_content, "Multi-query formatted successfully"
            
        except Exception as e:
            return "", f"Error formatting multi query: {str(e)}"

    def detect_ai_query_mode(self) -> str:
        """Detect which AI query mode to use based on configuration."""
        try:
            from nifty_core_config import (
                should_enable_single_ai_query, 
                should_enable_multi_ai_query,
                get_ai_query_mode
            )
            
            config_mode = get_ai_query_mode()
            
            if config_mode == "both" and should_enable_single_ai_query() and should_enable_multi_ai_query():
                return "both"
            elif config_mode == "multi" and should_enable_multi_ai_query():
                return "multi"
            elif config_mode == "single" and should_enable_single_ai_query():
                return "single"
            elif should_enable_multi_ai_query():
                return "multi"
            elif should_enable_single_ai_query():
                return "single"
            else:
                return "none"
                
        except Exception as e:
            print(f"⚠️ Error detecting AI query mode: {e}")
            return "single"  # Fallback to single mode

    def find_atm_strikes(self, oi_data: List[Dict[str, Any]], current_price: float, range_strikes: int = 10):
        """Find ATM strikes within specified range for detailed analysis"""
        if not oi_data:
            return []

        strike_prices = sorted(list(set(data['strike_price'] for data in oi_data)))
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_price))
        closest_index = strike_prices.index(closest_strike)
        
        start_index = max(0, closest_index - range_strikes)
        end_index = min(len(strike_prices), closest_index + range_strikes + 1)
        selected_strikes = strike_prices[start_index:end_index]
        
        atm_data = [data for data in oi_data if data['strike_price'] in selected_strikes]
        return atm_data

    def find_key_levels(self, oi_data: List[Dict[str, Any]]):
        """Find key resistance and support levels based on max OI"""
        if not oi_data:
            return {}, {}

        max_ce_oi = 0
        resistance_strike = None
        max_ce_oi_value = 0
        
        max_pe_oi = 0
        support_strike = None
        max_pe_oi_value = 0

        for data in oi_data:
            if data['ce_oi'] > max_ce_oi:
                max_ce_oi = data['ce_oi']
                resistance_strike = data['strike_price']
                max_ce_oi_value = data['ce_oi']
                
            if data['pe_oi'] > max_pe_oi:
                max_pe_oi = data['pe_oi']
                support_strike = data['strike_price']
                max_pe_oi_value = data['pe_oi']

        resistance_info = {'strike': resistance_strike, 'ce_oi': max_ce_oi_value} if resistance_strike else {}
        support_info = {'strike': support_strike, 'pe_oi': max_pe_oi_value} if support_strike else {}
        
        return resistance_info, support_info

    def is_multi_expiry_data(self, oi_data) -> bool:
        """Check if data is multi-expiry format"""
        return isinstance(oi_data, dict) and any(key in oi_data for key in ['current_week', 'next_week', 'monthly'])

    def format_multi_expiry_data_for_ai(self,
                                      expiry_data: Dict[str, Any],
                                      oi_pcr: float,
                                      volume_pcr: float,
                                      current_nifty: float,
                                      expiry_date: str,
                                      stock_data: Optional[Dict[str, Any]] = None,
                                      banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Format multi-expiry data for AI analysis"""
        formatted_text = f"NIFTY MULTI-EXPIRY ANALYSIS DATA:\n"
        formatted_text += f"- Spot: {current_nifty}\n"
        formatted_text += f"- Current Week PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"

        for expiry_type in ['current_week', 'next_week', 'monthly']:
            if expiry_type in expiry_data and expiry_data[expiry_type]:
                oi_data = expiry_data[expiry_type]
                expiry_date = oi_data[0]['expiry_date'] if oi_data else expiry_date
                expiry_oi_pcr, expiry_volume_pcr = self.calculate_pcr_for_range(oi_data)
                resistance, support = self.find_key_levels(oi_data)
                
                formatted_text += f"\n{expiry_type.upper().replace('_', ' ')} ANALYSIS:\n"
                formatted_text += f"- Expiry: {expiry_date}\n"
                formatted_text += f"- PCR: OI={expiry_oi_pcr:.2f}, Volume={expiry_volume_pcr:.2f}\n"
                
                if resistance:
                    formatted_text += f"- Resistance: {resistance['strike']} (Max CE OI: {resistance['ce_oi']:,})\n"
                if support:
                    formatted_text += f"- Support: {support['strike']} (Max PE OI: {support['pe_oi']:,})\n"
                    
                if expiry_type == 'current_week':
                    atm_data = self.find_atm_strikes(oi_data, current_nifty, 5)
                    if atm_data:
                        atm_oi_pcr, atm_volume_pcr = self.calculate_pcr_for_range(atm_data)
                        formatted_text += f"- ATM Zone (±5): OI={atm_oi_pcr:.2f}, Volume={atm_volume_pcr:.2f}\n"

        if banknifty_data:
            banknifty_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('oi_pcr', 0)
            alignment = "Bullish" if banknifty_pcr > 1.0 else "Bearish" if banknifty_pcr < 1.0 else "Neutral"
            formatted_text += f"\n- BankNifty Alignment: {alignment} (PCR: {banknifty_pcr:.2f})\n"

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

    def format_data_for_ai(self,
                          oi_data: List[Dict[str, Any]],
                          oi_pcr: float,
                          volume_pcr: float,
                          current_nifty: float,
                          expiry_date: str,
                          stock_data: Optional[Dict[str, Any]] = None,
                          banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Format optimized data for AI analysis - handles both single and multi-expiry"""
        if self.is_multi_expiry_data(oi_data):
            return self.format_multi_expiry_data_for_ai(oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date, stock_data, banknifty_data)

        formatted_text = f"NIFTY ANALYSIS DATA:\n"
        formatted_text += f"- Spot: {current_nifty} | Expiry: {expiry_date}\n"
        formatted_text += f"- Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"

        atm_data = self.find_atm_strikes(oi_data, current_nifty, 10)
        if atm_data:
            atm_oi_pcr, atm_volume_pcr = self.calculate_pcr_for_range(atm_data)
            formatted_text += f"- ATM Zone (±10): OI={atm_oi_pcr:.2f}, Volume={atm_volume_pcr:.2f}\n"

        resistance, support = self.find_key_levels(oi_data)
        formatted_text += "- Key Levels:\n"
        if resistance:
            formatted_text += f" * Resistance: {resistance['strike']} (Max CE OI: {resistance['ce_oi']:,})\n"
        if support:
            formatted_text += f" * Support: {support['strike']} (Max PE OI: {support['pe_oi']:,})\n"

        high_volume_strikes = self.find_high_activity_strikes(oi_data)
        if high_volume_strikes:
            formatted_text += " * High Activity Strikes:\n"
            for strike in high_volume_strikes[:3]:
                formatted_text += f" {strike['strike']} (Volume: {strike['total_volume']:,})\n"

        if banknifty_data:
            banknifty_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('oi_pcr', 0)
            alignment = "Bullish" if banknifty_pcr > 1.0 else "Bearish" if banknifty_pcr < 1.0 else "Neutral"
            formatted_text += f"- BankNifty Alignment: {alignment} (PCR: {banknifty_pcr:.2f})\n"

        formatted_text += "\n" + "=" * 80 + "\n"
        formatted_text += "ATM ±10 STRIKES DETAILED DATA:\n"
        formatted_text += "=" * 80 + "\n"

        for data in atm_data:
            strike = data['strike_price']
            formatted_text += (f"Strike {strike}: "
                            f"CE[ChgOI:{data.get('ce_change_oi', 0):,}, Vol:{data.get('ce_volume', 0):,}, "
                            f"LTP:{data.get('ce_ltp', 0.0):.1f}, OI:{data.get('ce_oi', 0):,}, IV:{data.get('ce_iv', 0.0):.1f}%] | "
                            f"PE[ChgOI:{data.get('pe_change_oi', 0):,}, Vol:{data.get('pe_volume', 0):,}, "
                            f"LTP:{data.get('pe_ltp', 0.0):.1f}, OI:{data.get('pe_oi', 0):,}, IV:{data.get('pe_iv', 0.0):.1f}%]\n")

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

        activity_data.sort(key=lambda x: x['total_volume'], reverse=True)
        return activity_data[:top_n]

    def get_single_ai_analysis(self,
                             oi_data: List[Dict[str, Any]],
                             oi_pcr: float,
                             volume_pcr: float,
                             current_nifty: float,
                             expiry_date: str,
                             stock_data: Optional[Dict[str, Any]] = None,
                             banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Perform single AI analysis with formatted data"""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        formatted_data = self.format_data_for_ai(oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date, stock_data, banknifty_data)
        
        SYSTEM_PROMPT = """
[Your existing single analysis system prompt here]
"""

        user_content = f"CURRENT DATA FOR SINGLE ANALYSIS:\n{formatted_data}\n"
        ai_response = ""
        
        try:
            print("🔄 Requesting SINGLE AI analysis from DeepSeek...")
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
            print(f"⚠️ Single AI call failed: {e}")
            ai_response = f"Single AI analysis failed: {e}"

        self.save_analysis_to_history(formatted_data, ai_response, "single")
        return f"🤖 DEEPSEEK AI SINGLE ANALYSIS:\n\n{ai_response}"

    def get_multi_ai_analysis(self) -> str:
        """Perform multi AI analysis with file attachments"""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 Multi AI Analysis: Service temporarily unavailable - Check API connection"

        query_content, status_message = self.format_multi_ai_query()
        
        if not query_content:
            return f"❌ Multi AI analysis failed: {status_message}"

        SYSTEM_PROMPT = """
[Your existing multi-analysis system prompt with file input instructions here]
"""

        user_content = f"MULTI-EXPIRY FILE-BASED ANALYSIS REQUEST:\n{query_content}\n"
        ai_response = ""
        
        try:
            print("🔄 Requesting MULTI AI analysis from DeepSeek...")
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
                max_tokens=1500,  # Slightly higher for multi-analysis
                stream=False,
                timeout=300.0,
                stop=["```"]
            )
            raw_ai = response.choices[0].message.content or ""
            ai_response = self._clean_ai_response(raw_ai)
            
        except Exception as e:
            print(f"⚠️ Multi AI call failed: {e}")
            ai_response = f"Multi AI analysis failed: {e}"

        self.save_analysis_to_history(query_content, ai_response, "multi")
        return f"🤖 DEEPSEEK AI MULTI-EXPIRY ANALYSIS:\n\n{ai_response}"

    def get_ai_analysis(self,
                       oi_data: List[Dict[str, Any]] = None,
                       oi_pcr: float = None,
                       volume_pcr: float = None,
                       current_nifty: float = None,
                       expiry_date: str = None,
                       stock_data: Optional[Dict[str, Any]] = None,
                       banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Main AI analysis method that handles both single and multi queries based on configuration"""
        
        query_mode = self.detect_ai_query_mode()
        
        if query_mode == "none":
            return "🤖 AI Analysis: Both single and multi queries are disabled in configuration"
        
        results = []
        
        # Perform single analysis if requested
        if query_mode in ["single", "both"]:
            if all(param is not None for param in [oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date]):
                single_result = self.get_single_ai_analysis(oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date, stock_data, banknifty_data)
                results.append(single_result)
            else:
                results.append("❌ Single AI analysis skipped: Missing required parameters")
        
        # Perform multi analysis if requested
        if query_mode in ["multi", "both"]:
            multi_result = self.get_multi_ai_analysis()
            results.append(multi_result)
        
        # Combine results
        if len(results) == 1:
            return results[0]
        else:
            separator = "\n" + "="*100 + "\n"
            return separator.join(results)


def format_data_for_ai(oi_data, current_cycle, total_fetches, pcr_analysis):
    return "Data formatting updated - use get_ai_analysis method directly"