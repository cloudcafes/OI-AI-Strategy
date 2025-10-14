# Part 4: Nifty_Option_Chain_Fetcher_Part4.py (With Analysis History)
import os
import time
import requests
import datetime
from openai import OpenAI
import httpx

class NiftyAIAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or "sk-df60b28326444de6859976f6e603fd9c"
        self.client = None
        self.history_file = "analysis_history.txt"
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the DeepSeek API client with SSL verification disabled"""
        try:
            # Create custom HTTP client with SSL verification disabled
            http_client = httpx.Client(verify=False, timeout=30.0)
            
            self.client = OpenAI(
                api_key=self.api_key, 
                base_url="https://api.deepseek.com",
                http_client=http_client,
                max_retries=2
            )
            
            # Test the connection with a simple call
            test_response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            print("✅ DeepSeek AI client initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize DeepSeek client: {e}")
            self.client = None
            return False
    
    def save_analysis_to_history(self, analysis_text):
        """Save AI analysis to history file with latest on top"""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M on %d %B %Y")
            header = f"deepseek API analysis done at {timestamp}"
            separator = "=" * 80
            
            # Create the new entry
            new_entry = f"{header}\n{separator}\n{analysis_text}\n{separator}\n\n"
            
            # Read existing content if file exists
            existing_content = ""
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # Write new content (latest on top)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(new_entry + existing_content)
            
            print(f"✅ Analysis saved to {self.history_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving analysis to history: {e}")
            return False
    
    def get_analysis_history(self):
        """Read and return the analysis history"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return f.read()
            return "No previous analysis history available."
        except Exception as e:
            print(f"❌ Error reading analysis history: {e}")
            return "Error reading analysis history."
    
    def get_ai_analysis(self, oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data=None, banknifty_data=None):
        """Get AI analysis from DeepSeek API with comprehensive OI data including history"""
        if not self.client:
            print("⚠️ Client not initialized, attempting to reinitialize...")
            if not self.initialize_client():
                return "🤖 AI Analysis: Service temporarily unavailable - Check API connection"
        
        # Format data for AI analysis
        formatted_data = self.format_data_for_ai(oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data, banknifty_data)
        
        # Get previous analysis history
        analysis_history = self.get_analysis_history()
        
        prompt = f"""
            You are an expert Nifty/BankNifty/top10 Nifty Stocks by weightage option chain analyst with deep knowledge of historical Nifty/BankNifty/top10 Nifty Stocks by weightage patterns and institutional trading behavior. You are not a dumb trader who only reads the data but you read in between the lines of provided data to decode the seller's & smart money perspective of the market which keeps you ahead from other traders when you provide any trade recommendation. You do mathemetical calculations as well as psychological analysis and interlink everything to understand the market. You never get in hurry to reply fast instead you focus on deep analysis and interlinked affect and take enough time to reply with your forecast.

            Provide a short summary first, then a breakdown. Use historical proven patterns, data, and trends specific to the Nifty index ATM ±2 strikes,Banknifty index ATM ±2 strikes,Stocks ATM ±2 strikes for accurate analysis—reference.
            Remember, Nifty index ATM ±2 strikes of weekly expiry OI analysis differs from stock options: Nifty reflects broader market sentiment with more institutional writing, while stocks are prone to company-specific manipulation and lower liquidity. Always interpret Nifty option chain from the sellers' perspective. 
            Focus solely on intraday implications, ignoring multi-day or expiry perspectives for trades.
            Key steps of analysis whose interlinked interpretation should be used for any forecasting and provide output catagerocially for each point: Analyze Nifty/BankNifty/top10 Nifty Stocks by weightage ATM ±2 strikes- OI changes,concentration, buildup, Evaluate OI PCR and Volume PCR, Ignore false signals, Analyze Greeks.
            I only take naked Nifty put or call buys for intraday trades, squaring off same day.             

            TRADE RECOMMENDATION:
            If Confidence >70%:
            Direction: [Buy PE / Buy CE]
            Strike: {{recommended_strike}}
            Current LTP: Rs {{ltp}}
            Entry Zone: Ideal at Nifty {{ideal_level}}, Acceptable {{range_start}}-{{range_end}}
            Entry Trigger: {{Specific condition like "Enter when Nifty bounces from 25100" or "Enter on breakout above 25200 with 5-min close"}}
            Stop Loss: Nifty {{stop_level}}
            Target: Nifty {{target_level}} (Expected premium: Rs {{target_premium}})
            Risk:Reward: 1:{{ratio}}
            Time Horizon: Next {{hours}} hours
            Rationale: {{Specific OI evidence + Pattern reference + Greeks factor}}

            If Confidence <70%:
            Assessment: Range-bound between {{lower}}-{{upper}}
            Recommendation: AVOID trading. Wait for {{specific trigger}}. Re-evaluate for {{direction}} if {{event}} happens.

            CURRENT DATA FOR ANALYSIS:
            Analyze the below provided comprehensive "OI data,greeks,CE-PE for the Nifty index ATM ±2 strikes of weekly expiry","OI data,greeks,CE-PE for the BANKNifty index ATM ±2 strikes of monthly expiry" and "OI data,greeks,CE-PE for the top10 Nifty Stocks by weightage ATM ±2 strikes of monthly expiry" to interpret the current intraday only trend which is provided to you live for this moment. 
            {formatted_data}

            PREVIOUS ANALYSIS HISTORY (for context only to understand failed setups. - focus on current data):
            {analysis_history}
        """
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt == 0:
                    print(f"🔄 Requesting AI analysis from DeepSeek...")
                
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are an expert options analyst specializing in Nifty, BankNifty, and stock options analysis for intraday trading."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    temperature=1.0,
                    max_tokens=2000,
                    stream=False,
                    timeout=600.0
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Save this analysis to history
                self.save_analysis_to_history(ai_response)
                
                return f"🤖 DEEPSEEK AI INTRADAY ANALYSIS (NIFTY + BANKNIFTY + STOCKS):\n{ai_response}"
                
            except requests.exceptions.ConnectionError as e:
                error_msg = f"🔴 Connection Error (Attempt {attempt + 1}): Unable to reach DeepSeek API"
                print(error_msg)
                if attempt < max_retries - 1:
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return f"{error_msg}. Check internet connection."
                
            except requests.exceptions.Timeout:
                error_msg = f"⏰ Timeout Error (Attempt {attempt + 1}): Request timed out"
                print(error_msg)
                if attempt < max_retries - 1:
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    return f"{error_msg}. Try again next cycle."
                
            except Exception as e:
                error_msg = f"⚠️ AI Analysis Error: {str(e)}"
                print(error_msg)
                
                if any(keyword in str(e).lower() for keyword in ['auth', 'api key', 'key', 'invalid', 'quota']):
                    print("🔄 Attempting to reinitialize DeepSeek client...")
                    time.sleep(2)
                    if self.initialize_client():
                        if attempt < max_retries - 1:
                            continue
                    
                if attempt >= max_retries - 1:
                    return f"🤖 AI Analysis: Service temporarily unavailable - {str(e)}"
                
                time.sleep(retry_delay)
        
        return "🤖 AI Analysis: Maximum retries exceeded. Service temporarily unavailable."

    def format_data_for_ai(self, oi_data, current_cycle, total_fetches, oi_pcr, volume_pcr, current_nifty, stock_data, banknifty_data):
        """Format all data for AI analysis - just raw data, no analysis"""
        formatted_text = f"NIFTY DATA (Cycle: {current_cycle}/10, Total: {total_fetches})\n"
        formatted_text += f"Nifty Spot: {current_nifty}\n"
        formatted_text += f"PCR Values: OI PCR = {oi_pcr:.2f} | Volume PCR = {volume_pcr:.2f}\n"
        formatted_text += "=" * 80 + "\n"
        
        # Nifty strikes data
        for data in oi_data:
            strike = data['strike_price']
            ce_pe_diff = data['ce_change_oi'] - data['pe_change_oi']
            
            formatted_text += f"Strike {strike}: "
            formatted_text += f"CE[ChgOI:{data['ce_change_oi']}, Vol:{data['ce_volume']}, LTP:{data['ce_ltp']:.1f}, OI:{data['ce_oi']}, IV:{data['ce_iv']:.1f}%, Delta:{data['ce_delta']:.3f}] "
            formatted_text += f"PE[ChgOI:{data['pe_change_oi']}, Vol:{data['pe_volume']}, LTP:{data['pe_ltp']:.1f}, OI:{data['pe_oi']}, IV:{data['pe_iv']:.1f}%, Delta:{data['pe_delta']:.3f}] "
            formatted_text += f"Diff:{ce_pe_diff}\n"
        
        # Add BANKNIFTY data if available
        if banknifty_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "BANKNIFTY DATA\n"
            formatted_text += "=" * 80 + "\n"
            formatted_text += f"BankNifty Spot: {banknifty_data['current_value']}\n"
            formatted_text += f"PCR Values: OI PCR = {banknifty_data['oi_pcr']:.2f} | Volume PCR = {banknifty_data['volume_pcr']:.2f}\n"
            
            for data in banknifty_data['data']:
                strike = data['strike_price']
                ce_pe_diff = data['ce_change_oi'] - data['pe_change_oi']
                
                formatted_text += f"Strike {strike}: "
                formatted_text += f"CE[ChgOI:{data['ce_change_oi']}, Vol:{data['ce_volume']}, LTP:{data['ce_ltp']:.1f}, OI:{data['ce_oi']}, IV:{data['ce_iv']:.1f}%, Delta:{data['ce_delta']:.3f}] "
                formatted_text += f"PE[ChgOI:{data['pe_change_oi']}, Vol:{data['pe_volume']}, LTP:{data['pe_ltp']:.1f}, OI:{data['pe_oi']}, IV:{data['pe_iv']:.1f}%, Delta:{data['pe_delta']:.3f}] "
                formatted_text += f"Diff:{ce_pe_diff}\n"
        
        # Add stock data if available
        if stock_data:
            formatted_text += "\n" + "=" * 80 + "\n"
            formatted_text += "TOP 10 NIFTY STOCKS DATA\n"
            formatted_text += "=" * 80 + "\n"
            
            for symbol, stock_info in stock_data.items():
                data = stock_info['data'][0]  # First data point for basic info
                formatted_text += f"\n{symbol} (Weight: {stock_info['weight']:.4f}, Price: {data['stock_value']}): "
                formatted_text += f"OI PCR: {stock_info['oi_pcr']:.2f}, Volume PCR: {stock_info['volume_pcr']:.2f}\n"
                
                # Add strikes data for this stock
                for strike_data in stock_info['data']:
                    strike = strike_data['strike_price']
                    ce_pe_diff = strike_data['ce_change_oi'] - strike_data['pe_change_oi']
                    
                    formatted_text += f"  Strike {strike}: "
                    formatted_text += f"CE[ChgOI:{strike_data['ce_change_oi']}, Vol:{strike_data['ce_volume']}, LTP:{strike_data['ce_ltp']:.1f}] "
                    formatted_text += f"PE[ChgOI:{strike_data['pe_change_oi']}, Vol:{strike_data['pe_volume']}, LTP:{strike_data['pe_ltp']:.1f}] "
                    formatted_text += f"Diff:{ce_pe_diff}\n"
        
        return formatted_text

def format_data_for_ai(oi_data, current_cycle, total_fetches, pcr_analysis):
    """Legacy function for backward compatibility"""
    return "Data formatting updated - use get_ai_analysis method directly"