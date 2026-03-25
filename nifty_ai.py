import os
import glob
import datetime
from google import genai
from google.genai import types
import anthropic

from nifty_config import GEMINI_API_KEY, AI_LOGS_DIR, GEMINI_LOGS_DIR
from nifty_telegram import send_telegram_message

# Safely import ANTHROPIC_API_KEY if it exists, otherwise set to None
import nifty_config
ANTHROPIC_API_KEY = getattr(nifty_config, 'ANTHROPIC_API_KEY', None)


class NiftyAIAnalyzer:
    def __init__(self):
        # Initialize Gemini Client
        if not GEMINI_API_KEY or "YOUR_" in GEMINI_API_KEY:
            print("⚠️ Gemini config missing.")
            self.gemini_client = None
        else:
            self.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            
        # Initialize Anthropic (Claude) Client
        if not ANTHROPIC_API_KEY or "YOUR_" in ANTHROPIC_API_KEY:
            print("⚠️ Anthropic config missing. Claude fallback will be disabled.")
            self.claude_client = None
        else:
            self.claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        # ---------------------------------------------------------
        # AI SESSION MEMORY (Rolling Context Window)
        # ---------------------------------------------------------
        self.rolling_history = []
        self.max_snapshots = 6  # UPDATED: Now remembers the last 6 market snapshots

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
        """Waterfalls through Gemini Pro -> Claude -> Gemini Flash."""
        latest_file = self.get_latest_log_file()
        
        if not latest_file:
            return "❌ AI Analysis skipped: No data files available."
            
        print(f"🔄 Reading latest data from: {os.path.basename(latest_file)}")
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            return f"❌ Error reading file: {e}"

        system_instruction = "You are an expert Nifty options trading analyst. Review the data and provide a clear, actionable trading analysis. ALWAYS include a section titled exactly 'ANALYSIS NARRATIVE' or 'TRADING IMPLICATION'."
        
        ai_response = None
        used_model = "None"

        # -------------------------------------------------------------
        # 1st TRY: GEMINI PRO (Stateless Snapshot)
        # -------------------------------------------------------------
        if self.gemini_client:
            print("🧠 Requesting analysis from Google Gemini Pro...")
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-3.1-pro-preview", 
                    contents=[system_instruction, file_content]
                )
                ai_response = response.text
                used_model = "Gemini Pro"
                print("✅ Gemini Pro succeeded.")
            except Exception as e:
                print(f"⚠️ Gemini Pro failed: {e}")
        
        # -------------------------------------------------------------
        # 2nd TRY: CLAUDE OPUS (Fallback 1)
        # -------------------------------------------------------------
        if not ai_response:
            if self.claude_client:
                print("🧠 Switching to Anthropic Claude...")
                try:
                    message = self.claude_client.messages.create(
                        model="claude-3-opus-20240229",
                        max_tokens=1500,
                        system=system_instruction,
                        messages=[
                            {"role": "user", "content": file_content}
                        ]
                    )
                    ai_response = message.content[0].text
                    used_model = "Claude Opus"
                    print("✅ Claude succeeded.")
                except Exception as e:
                    print(f"⚠️ Claude failed: {e}")
            else:
                print("⏭️ Skipping Claude fallback: ANTHROPIC_API_KEY is not configured.")

        # -------------------------------------------------------------
        # 3rd TRY: GEMINI FLASH (Rolling Context Window)
        # -------------------------------------------------------------
        if not ai_response and self.gemini_client:
            print("🧠 Switching to Google Gemini Flash (Rolling Context Mode)...")
            try:
                # 1. Append the new market data as a "user" message
                self.rolling_history.append({
                    "role": "user", 
                    "parts": [{"text": file_content}]
                })

                # 2. Enforce the Rolling Window limit
                max_messages = self.max_snapshots * 2
                
                if len(self.rolling_history) > max_messages:
                    print(f"   [!] Trimming oldest context. Keeping last {self.max_snapshots} snapshots.")
                    self.rolling_history = self.rolling_history[-max_messages:]

                # 3. Configure the model settings
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2  
                )

                # 4. Send the explicitly managed history array
                response = self.gemini_client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview", 
                    contents=self.rolling_history,
                    config=config
                )
                
                ai_response = response.text
                used_model = "Gemini Flash"
                
                # 5. Save the AI's response to the history for the NEXT cycle
                self.rolling_history.append({
                    "role": "model", 
                    "parts": [{"text": ai_response}]
                })
                
                print("✅ Gemini Flash succeeded.")
                
            except Exception as e:
                print(f"⚠️ Gemini Flash failed: {e}")
                # Failsafe: If the API call fails, remove the last user message we just 
                # added so the history state doesn't get corrupted
                if self.rolling_history and self.rolling_history[-1]["role"] == "user":
                    self.rolling_history.pop()

        # -------------------------------------------------------------
        # FINAL CHECK & LOGGING
        # -------------------------------------------------------------
        if not ai_response:
            return "❌ AI analysis failed on all available engines (Pro, Claude, Flash)."

        # --- FILE SAVING LOGIC ---
        timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        output_filepath = os.path.join(GEMINI_LOGS_DIR, f"ai_analysis_{timestamp}.txt")
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(f"Source Data File: {os.path.basename(latest_file)}\n")
            f.write(f"Model Used: {used_model}\n")
            f.write("=" * 80 + "\n")
            f.write(f"AI ANALYSIS - Generated at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(ai_response)
            
        print(f"✅ Analysis saved successfully to:\n   {output_filepath}")
        
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
            snippet_lines = lines[start_idx:start_idx + 50]
            telegram_msg = f"🤖 {used_model} Strategy Update:\n\n" + "\n".join(snippet_lines)
            send_telegram_message(telegram_msg)
        else:
            print("⚠️ Keywords 'ANALYSIS NARRATIVE' or 'TRADING IMPLICATION' not found. Sending fallback response...")
            snippet_lines = lines[:50]
            telegram_msg = f"🤖 {used_model} Strategy Update:\n\n" + "\n".join(snippet_lines)
            send_telegram_message(telegram_msg)
            
        return f"\n🤖 {used_model.upper()} ANALYSIS:\n\n{ai_response}"
