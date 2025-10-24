# nifty_ai_analyzer.py
import os
import time
import json
import datetime
import requests
import httpx
from typing import Dict, Any, List, Optional
from openai import OpenAI
from nifty_core_config import (
    is_local_ai_enabled, 
    get_ollama_config, 
    get_cloud_ai_config,
    get_model_parameters
)

class NiftyAIAnalyzer:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "deepseek-r1:latest"):
        # Use env var or provided key; prefer env for security
        self.api_key = api_key or "sk-df60b28326444de6859976f6e603fd9c"
        self.client = None
        self.history_file = "analysis_history.txt"
        self.local_ai_enabled = is_local_ai_enabled()
        self.ollama_model = model_name
        self.initialize_client()

    def initialize_client(self) -> bool:
        """Initialize the appropriate AI client based on configuration"""
        if self.local_ai_enabled:
            return self.initialize_local_client()
        else:
            return self.initialize_cloud_client()

    def initialize_local_client(self) -> bool:
        """Initialize local Ollama client"""
        try:
            ollama_config = get_ollama_config()
            base_url = ollama_config["base_url"]
            
            # Test with a simple generate request instead of tags
            test_response = requests.post(
                f'{base_url}/api/generate',
                json={
                    'model': self.ollama_model,
                    'prompt': 'test',
                    'stream': False,
                    'options': {'num_predict': 5}
                },
                timeout=10
            )
            
            if test_response.status_code == 200:
                print(f"✅ Local Ollama client initialized successfully (Model: {self.ollama_model})")
                return True
            else:
                print(f"❌ Ollama test failed: {test_response.status_code} - {test_response.text}")
                return False
        except Exception as e:
            print(f"❌ Failed to initialize local Ollama client: {e}")
            return False

    def initialize_cloud_client(self) -> bool:
        """Initialize the DeepSeek cloud API client"""
        try:
            if not self.api_key:
                raise RuntimeError("DeepSeek API key not found. Set DEEPSEEK_API_KEY env var or pass api_key to NiftyAIAnalyzer.")

            verify_ssl_env = os.getenv("DEEPSEEK_VERIFY_SSL", "false").lower() in ("1", "true", "yes")
            http_client = httpx.Client(verify=verify_ssl_env, timeout=30.0)

            cloud_config = get_cloud_ai_config()
            
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=cloud_config["base_url"],
                http_client=http_client,
                max_retries=2
            )

            # Smoke test
            _ = self.client.chat.completions.create(
                model=cloud_config["model"],
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
                temperature=0
            )
            print("✅ DeepSeek Cloud AI client initialized successfully")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize DeepSeek cloud client: {e}")
            self.client = None
            return False

    def save_analysis_to_history(self, raw_data: str, ai_response: str, model_name: str = "unknown") -> bool:
        """Save both raw data and AI response to history file with latest on top."""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"AI analysis by {model_name} done at {timestamp}"
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

            print(f"✅ Analysis from {model_name} saved to {self.history_file}")
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

    def find_atm_strikes(self, oi_data: List[Dict[str, Any]], current_price: float, range_strikes: int = 10):
        """Find ATM strikes within specified range for detailed analysis"""
        if not oi_data:
            return []
        
        # Get all strike prices
        strike_prices = sorted(list(set(data['strike_price'] for data in oi_data)))
        
        # Find closest strike
        closest_strike = min(strike_prices, key=lambda x: abs(x - current_price))
        closest_index = strike_prices.index(closest_strike)
        
        # Get strikes within range
        start_index = max(0, closest_index - range_strikes)
        end_index = min(len(strike_prices), closest_index + range_strikes + 1)
        selected_strikes = strike_prices[start_index:end_index]
        
        # Filter records for selected strikes
        atm_data = [data for data in oi_data if data['strike_price'] in selected_strikes]
        
        return atm_data

    def find_key_levels(self, oi_data: List[Dict[str, Any]]):
        """Find key resistance and support levels based on max OI"""
        if not oi_data:
            return {}, {}
        
        # Find max CE OI for resistance
        max_ce_oi = 0
        resistance_strike = None
        max_ce_oi_value = 0
        
        # Find max PE OI for support
        max_pe_oi = 0
        support_strike = None
        max_pe_oi_value = 0
        
        for data in oi_data:
            # Check for resistance (max CE OI)
            if data['ce_oi'] > max_ce_oi:
                max_ce_oi = data['ce_oi']
                resistance_strike = data['strike_price']
                max_ce_oi_value = data['ce_oi']
            
            # Check for support (max PE OI)
            if data['pe_oi'] > max_pe_oi:
                max_pe_oi = data['pe_oi']
                support_strike = data['strike_price']
                max_pe_oi_value = data['pe_oi']
        
        resistance_info = {
            'strike': resistance_strike,
            'ce_oi': max_ce_oi_value
        } if resistance_strike else {}
        
        support_info = {
            'strike': support_strike,
            'pe_oi': max_pe_oi_value
        } if support_strike else {}
        
        return resistance_info, support_info

    def format_data_for_ai(self,
                           oi_data: List[Dict[str, Any]],
                           oi_pcr: float,
                           volume_pcr: float,
                           current_nifty: float,
                           expiry_date: str,
                           stock_data: Optional[Dict[str, Any]] = None,
                           banknifty_data: Optional[Dict[str, Any]] = None) -> str:
        """Format optimized data for AI analysis - full PCRs + ATM details + key levels"""
        formatted_text = f"NIFTY ANALYSIS DATA:\n"
        formatted_text += f"- Spot: {current_nifty} | Expiry: {expiry_date}\n"
        formatted_text += f"- Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"
        
        # Find ATM ±10 strikes for detailed analysis
        atm_data = self.find_atm_strikes(oi_data, current_nifty, 10)
        if atm_data:
            atm_oi_pcr, atm_volume_pcr = self.calculate_pcr_for_range(atm_data)
            formatted_text += f"- ATM Zone (±10): OI={atm_oi_pcr:.2f}, Volume={atm_volume_pcr:.2f}\n"
        
        # Find key levels
        resistance, support = self.find_key_levels(oi_data)
        formatted_text += "- Key Levels:\n"
        if resistance:
            formatted_text += f"  * Resistance: {resistance['strike']} (Max CE OI: {resistance['ce_oi']:,})\n"
        if support:
            formatted_text += f"  * Support: {support['strike']} (Max PE OI: {support['pe_oi']:,})\n"
        
        # Add high activity strikes
        high_volume_strikes = self.find_high_activity_strikes(oi_data)
        if high_volume_strikes:
            formatted_text += "  * High Activity Strikes:\n"
            for strike in high_volume_strikes[:3]:  # Top 3 only
                formatted_text += f"    {strike['strike']} (Volume: {strike['total_volume']:,})\n"
        
        # BankNifty alignment
        if banknifty_data:
            banknifty_pcr = banknifty_data.get('oi_pcr', 0)
            alignment = "Bullish" if banknifty_pcr > 1.0 else "Bearish" if banknifty_pcr < 1.0 else "Neutral"
            formatted_text += f"- BankNifty Alignment: {alignment} (PCR: {banknifty_pcr:.2f})\n"
        
        formatted_text += "\n" + "=" * 80 + "\n"
        formatted_text += "ATM ±10 STRIKES DETAILED DATA:\n"
        formatted_text += "=" * 80 + "\n"
        
        # Add detailed ATM strikes data
        for data in atm_data:
            strike = data['strike_price']
            formatted_text += (
                f"Strike {strike}: "
                f"CE[ChgOI:{data.get('ce_change_oi', 0):,}, Vol:{data.get('ce_volume', 0):,}, "
                f"LTP:{data.get('ce_ltp', 0.0):.1f}, OI:{data.get('ce_oi', 0):,}, IV:{data.get('ce_iv', 0.0):.1f}%] | "
                f"PE[ChgOI:{data.get('pe_change_oi', 0):,}, Vol:{data.get('pe_volume', 0):,}, "
                f"LTP:{data.get('pe_ltp', 0.0):.1f}, OI:{data.get('pe_oi', 0):,}, IV:{data.get('pe_iv', 0.0):.1f}%]\n"
            )
        
        # Stock data summary
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
        
        # Calculate PCR values with zero safeguards
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
        
        # Sort by total volume descending and return top N
        activity_data.sort(key=lambda x: x['total_volume'], reverse=True)
        return activity_data[:top_n]

    def get_local_ai_analysis(self, formatted_data: str, system_prompt: str, model_params: Dict[str, Any]) -> str:
        """Get analysis from local Ollama model"""
        try:
            ollama_config = get_ollama_config()
            base_url = ollama_config["base_url"]
            
            print(f"🔍 Sending request to Ollama: {base_url}/api/generate")
            print(f"🔍 Model: {self.ollama_model}")
            
            # Use the actual system prompt and formatted data
            full_prompt = f"{system_prompt}\n\n{formatted_data}"
            
            # Use the model parameters from configuration
            response = requests.post(
                f"{base_url}/api/generate",
                json={
                    'model': self.ollama_model,
                    'prompt': full_prompt,
                    'stream': False,
                    'options': {
                        'temperature': model_params.get('temperature', 0.1),
                        'top_p': model_params.get('top_p', 0.9),
                        'num_predict': model_params.get('max_tokens', 1200)  # Use proper token limit
                    }
                },
                timeout=model_params.get('timeout', 120)
            )
            
            print(f"🔍 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get('response', 'No response generated')
                print(f"✅ Success! Got response of {len(raw_response)} characters")
                return raw_response  # Return the full response
            else:
                print(f"❌ Error: {response.text}")
                response.raise_for_status()
                
        except Exception as e:
            error_msg = f"Local AI call failed: {str(e)}"
            print(f"⚠️ {error_msg}")
            return error_msg


    def get_cloud_ai_analysis(self, formatted_data: str, system_prompt: str, model_params: Dict[str, Any]) -> str:
        """Get analysis from cloud DeepSeek API"""
        if not self.client:
            print("⚠️ Cloud client not initialized, attempting to reinitialize...")
            if not self.initialize_cloud_client():
                return "🤖 Cloud AI Analysis: Service temporarily unavailable - Check API connection"

        try:
            cloud_config = get_cloud_ai_config()
            
            response = self.client.chat.completions.create(
                model=cloud_config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": formatted_data}
                ],
                temperature=model_params.get('temperature', 0),
                top_p=model_params.get('top_p', 1.0),
                presence_penalty=0,
                frequency_penalty=0,
                max_tokens=model_params.get('max_tokens', 1200),
                stream=False,
                timeout=model_params.get('timeout', 300.0),
                stop=["```"]
            )
            raw_ai = response.choices[0].message.content or ""
            return self._clean_ai_response(raw_ai)
            
        except Exception as e:
            print(f"⚠️ Cloud AI call failed: {e}")
            return f"Cloud AI analysis failed: {e}"

    def get_ai_analysis(self,
                        oi_data: List[Dict[str, Any]],
                        oi_pcr: float,
                        volume_pcr: float,
                        current_nifty: float,
                        expiry_date: str,
                        stock_data: Optional[Dict[str, Any]] = None,
                        banknifty_data: Optional[Dict[str, Any]] = None,
                        model_name: str = "unknown") -> str:
        """Request AI analysis with optimized data format"""
        if not self.client and not self.local_ai_enabled:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"

        # Format optimized data for AI
        formatted_data = self.format_data_for_ai(
            oi_data, oi_pcr, volume_pcr, current_nifty, expiry_date, stock_data, banknifty_data
        )

        # Your existing prompt - preserved exactly as is
        SYSTEM_PROMPT = """
        You are an expert Nifty/BankNifty/top10 Nifty Stocks by weightage option chain analyst with deep knowledge of historical patterns and institutional trading behavior. You read between the lines to decode both smart money AND retail perspectives. You perform mathematical calculations, psychological analysis, and interlink all data points to understand market dynamics. You analyze the market from the seller's point of view because they only drive the market. Take your time for thorough analysis.

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Analyze the provided OI data for Nifty index (weekly expiry), BankNifty index (monthly expiry), and top 10 Nifty Stocks (monthly expiry) to interpret the intraday trend. 

        CRITICAL ANALYSIS FRAMEWORK - FOLLOW THIS ORDER:

        1. Analyze PE & CE OI for each strike.
        2. Analyze difference between PE & CE for each strike.
        3. Analyze OI PCR.
        4. Analyze Volume PCR.
        5. Analyze seprately once again for NIFTY ATM+-2 strike.
        6. Analyze the market from seller's perspective.
        7. Analyze smart money positions.
        8. Keep in mind, NSE nifty & bank nifty are index so their analysis logic is completely different from NSE stocks analysis logic.
        9. Always use historical proven threshold values for NIFTY and BANKNIFTY for making any calculation.
        10. You entire analysis should be focussed on providing intraday 20-40 points nifty scalping opportunity.
        11. I only take naked Nifty CE/PE buys for intraday.

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        Provide output categorically:
        - Short summary with clear directional bias and justification behind your logic.
        - mathemetically and scientifically calculated probability of current nifty price moving to strike+1 or strike -1.
        - Breakdown of conflicting/confirming signals in short.
        - Specific entry levels, stop-loss, targets, do not provide hedge instead only buy CE/PE.

        Note: do not provide any value or calculation from thin air from your end. do not presume any thing hypothetically. do not include any information out of thin air.        

        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        I don't want you to agree with me just to be polite or supportive. Drop the filter be brutally honest, straightforward, and logical. Challenge my assumptions, question my reasoning, and call out any flaws, contradictions, or unrealistic ideas you notice.

        Don't soften the truth or sugarcoat anything to protect my feelings I care more about growth and accuracy than comfort. Avoid empty praise, generic motivation, or vague advice. I want hard facts, clear reasoning, and actionable feedback.

        Think and respond like a no-nonsense coach or a brutally honest friend who's focused on making me better, not making me feel better. Push back whenever necessary, and never feed me bullshit. Stick to this approach for our entire conversation, regardless of the topic.

        And just give me answer no other worda or appreciation or any bullshit or judgements. Just plain n deep answer which is well researched.
        ----------------------------------------------------------------------------------------------------------------------------------------------------------
        """

        ai_response = ""
        try:
            # Get model-specific parameters
            model_params = get_model_parameters(model_name)
            
            if self.local_ai_enabled:
                ai_response = self.get_local_ai_analysis(formatted_data, SYSTEM_PROMPT, model_params)
                source = "LOCAL"
            else:
                ai_response = self.get_cloud_ai_analysis(formatted_data, SYSTEM_PROMPT, model_params)
                source = "DEEPSEEK"
            
        except Exception as e:
            print(f"⚠️ AI call failed: {e}")
            ai_response = f"AI analysis failed: {e}"

        # Save both raw data and AI response to history
        self.save_analysis_to_history(formatted_data, ai_response, model_name)

        # Return formatted AI response
        return f"🤖 {source} AI INTRADAY ANALYSIS ({model_name.upper()}):\n\n{ai_response}\n\n{'='*80}"



# Backward compatibility placeholder
def format_data_for_ai(oi_data, current_cycle, total_fetches, pcr_analysis):
    return "Data formatting updated - use get_ai_analysis method directly"

# Test function
def test_ai_analyzer():
    """Test the AI analyzer with both local and cloud backends"""
    print("=== Testing AI Analyzer ===")
    
    # Test local analyzer
    print("Testing Local AI Analyzer...")
    local_analyzer = NiftyAIAnalyzer()
    local_analyzer.local_ai_enabled = True
    local_analyzer.ollama_model = "deepseek-r1:latest"
    
    if local_analyzer.initialize_local_client():
        print("✅ Local AI client initialized successfully")
    else:
        print("❌ Local AI client initialization failed")
    
    # Test cloud analyzer
    print("\nTesting Cloud AI Analyzer...")
    cloud_analyzer = NiftyAIAnalyzer()
    cloud_analyzer.local_ai_enabled = False
    
    if cloud_analyzer.initialize_cloud_client():
        print("✅ Cloud AI client initialized successfully")
    else:
        print("❌ Cloud AI client initialization failed")
    
    print("✅ AI analyzer tests completed")

if __name__ == "__main__":
    test_ai_analyzer()