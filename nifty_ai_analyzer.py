import os
import glob
import datetime
import requests
import urllib3
from google import genai

# Disable SSL warnings for the Telegram API call
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NiftyAIAnalyzer:
    def __init__(self, api_key: str = None):
        # 1. API KEYS & CREDENTIALS
        self.api_key = api_key or "AIzaSyByKUPL90bV_8uvuWLPZKGqa8t6grC7SIc"
        self.telegram_bot_token = "8747682342:AAG5f--5bePDBGjTFQDw0B7rLNGZFNkzQU8"  # e.g., "123456789:ABCdefGhIJKlmNoPQRsT"
        self.telegram_chat_id = "8483179520"      # e.g., "-1001234567890" or "987654321"
        
        # Initialize Gemini Client
        self.client = genai.Client(api_key=self.api_key)
        
        # Set up absolute paths per your requirements
        self.input_dir = r"C:\Users\Administrator\Desktop\OI-AI-Strategy\ai-query-logs"
        self.output_dir = r"C:\Users\Administrator\Desktop\OI-AI-Strategy\gemini-logs"
        
        # Ensure the output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def get_latest_log_file(self) -> str:
        """Finds the most recently created text file in the input directory."""
        if not os.path.exists(self.input_dir):
            print(f"⚠️ Input directory not found: {self.input_dir}")
            return None
        
        list_of_files = glob.glob(os.path.join(self.input_dir, '*.txt'))
        if not list_of_files:
            return None
            
        return max(list_of_files, key=os.path.getctime)

    def send_telegram_alert(self, message_text: str):
        """Sends a formatted message to Telegram."""
        if self.telegram_bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            print("⚠️ Telegram skipped: Bot token not configured in nifty_ai_analyzer.py")
            return

        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message_text,
            "parse_mode": "Markdown"
        }
        
        try:
            # verify=False is used to match your system's existing SSL bypass settings
            response = requests.post(url, json=payload, verify=False, timeout=10)
            if response.status_code == 200:
                print("📱 Successfully sent parsed snippet to Telegram!")
            else:
                print(f"⚠️ Telegram API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")

    def get_ai_analysis(self, **kwargs) -> str:
        """Reads data, gets Gemini analysis, saves file, and sends Telegram alert."""
        latest_file = self.get_latest_log_file()
        
        if not latest_file:
            return "❌ AI Analysis skipped: No data files available."
            
        print(f"🔄 Reading latest data from: {os.path.basename(latest_file)}")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            return f"❌ Error reading file: {e}"

        # Note: If you stayed on the free tier, ensure the model below is "gemini-3.1-flash-lite-preview"
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
            output_filepath = os.path.join(self.output_dir, f"gemini_analysis_{timestamp}.txt")
            
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
                telegram_msg = "🤖 *Gemini AI Strategy Update:*\n\n" + "\n".join(snippet_lines)
                self.send_telegram_alert(telegram_msg)
            else:
                print("⚠️ Keywords 'ANALYSIS NARRATIVE' or 'TRADING IMPLICATION' not found. Telegram skipped.")
                
            return f"🤖 GEMINI AI ANALYSIS:\n\n{ai_response}"
            
        except Exception as e:
            print(f"⚠️ Gemini API call failed: {e}")
            return f"❌ Gemini AI analysis failed: {str(e)}"

# To maintain compatibility with nifty_main.py's import statement
def format_data_for_ai(*args, **kwargs):
    return "Data formatting handled internally by NiftyAIAnalyzer."