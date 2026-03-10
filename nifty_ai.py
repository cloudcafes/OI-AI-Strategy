import os
import glob
import datetime
from google import genai

from nifty_config import GEMINI_API_KEY, AI_LOGS_DIR, GEMINI_LOGS_DIR
from nifty_telegram import send_telegram_message

class NiftyAIAnalyzer:
    def __init__(self):
        # 1. Credential Check
        if not GEMINI_API_KEY or "YOUR_" in GEMINI_API_KEY:
            print("⚠️ Gemini skipped: API key not configured in nifty_config.py")
            self.client = None
            return
            
        # Initialize Gemini Client
        self.client = genai.Client(api_key=GEMINI_API_KEY)

    def get_latest_log_file(self) -> str:
        """Finds the most recently created text file in the input directory."""
        if not os.path.exists(AI_LOGS_DIR):
            print(f"⚠️ Input directory not found: {AI_LOGS_DIR}")
            return None
        
        list_of_files = glob.glob(os.path.join(AI_LOGS_DIR, '*.txt'))
        if not list_of_files:
            return None
            
        return max(list_of_files, key=os.path.getctime)

    def get_ai_analysis(self, **kwargs) -> str:
        """Reads data, gets Gemini analysis, saves file, and sends Telegram alert."""
        if not self.client:
            return "❌ AI Analysis skipped: Gemini client not initialized."

        latest_file = self.get_latest_log_file()
        
        if not latest_file:
            return "❌ AI Analysis skipped: No data files available."
            
        print(f"🔄 Reading latest data from: {os.path.basename(latest_file)}")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            return f"❌ Error reading file: {e}"

        print("🧠 Requesting analysis from Google Gemini...")
        try:
            response = self.client.models.generate_content(
                model="gemini-3.1-flash-lite-preview", 
                contents=[
                    "You are an expert Nifty options trading analyst. Review the data and provide a clear, actionable trading analysis. ALWAYS include a section titled exactly 'ANALYSIS NARRATIVE' or 'TRADING IMPLICATION'.",
                    file_content
                ]
            )
            
            ai_response = response.text
            
            # --- FILE SAVING LOGIC ---
            timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            output_filepath = os.path.join(GEMINI_LOGS_DIR, f"gemini_analysis_{timestamp}.txt")
            
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(f"Source Data File: {os.path.basename(latest_file)}\n")
                f.write("=" * 80 + "\n")
                f.write(f"GEMINI AI ANALYSIS - Generated at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(ai_response)
                
            print(f"✅ Gemini analysis saved successfully to:\n   {output_filepath}")
            
            # --- TELEGRAM PARSING LOGIC ---
            print("🔍 Parsing response for Telegram keywords...")
            lines = ai_response.split('\n')
            start_idx = -1
            
            for i, line in enumerate(lines):
                upper_line = line.upper()
                if "ANALYSIS NARRATIVE" in upper_line or "TRADING IMPLICATION" in upper_line:
                    start_idx = i
                    break
            
            if start_idx != -1:
                # Grab the matching line and the 49 lines after it
                snippet_lines = lines[start_idx:start_idx + 50]
                telegram_msg = "🤖 Gemini AI Strategy Update:\n\n" + "\n".join(snippet_lines)
                send_telegram_message(telegram_msg)
            else:
                print("⚠️ Keywords 'ANALYSIS NARRATIVE' or 'TRADING IMPLICATION' not found. Sending fallback response...")
                # Fallback: Just grab the first 50 lines of the analysis
                snippet_lines = lines[:50]
                telegram_msg = "🤖 Gemini AI Strategy Update:\n\n" + "\n".join(snippet_lines)
                send_telegram_message(telegram_msg)
                
            return f"\n🤖 GEMINI AI ANALYSIS:\n\n{ai_response}"
            
        except Exception as e:
            print(f"⚠️ Gemini API call failed: {e}")
            return f"❌ Gemini AI analysis failed: {str(e)}"