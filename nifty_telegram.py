import requests
import urllib3
from nifty_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Disable SSL warnings for the Telegram API call
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_telegram_message(text: str) -> bool:
    """
    Sends a formatted message to Telegram. 
    Automatically handles message splitting if it exceeds Telegram's size limits.
    """
    # 1. Credential Check
    if not TELEGRAM_BOT_TOKEN or "YOUR_" in TELEGRAM_BOT_TOKEN:
        print("⚠️ Telegram skipped: Bot token not configured in nifty_config.py")
        return False

    # 2. Markdown Cleanup (Prevents Telegram 400 Bad Request Parse Errors)
    clean_text = text.replace('**', '*').replace('##', '')
    
    # 3. Size Limit Handler
    max_length = 4000  # Safe buffer below Telegram's strict 4096 limit
    
    if len(clean_text) <= max_length:
        return _send_chunk(clean_text)
    else:
        print(f"📤 Message too long ({len(clean_text)} chars), splitting into parts...")
        lines = clean_text.split('\n')
        current_message = ""
        success = True
        part = 1
        
        for line in lines:
            # If adding the next line pushes it over the limit, send the chunk
            if len(current_message) + len(line) + 1 > max_length:
                if current_message:
                    if not _send_chunk(f"📊 Part {part}:\n\n{current_message}"):
                        success = False
                    part += 1
                    current_message = line
            else:
                current_message += "\n" + line if current_message else line
                
        # Send the final remaining chunk
        if current_message:
            if not _send_chunk(f"📊 Part {part}:\n\n{current_message}"):
                success = False
                
        return success

def _send_chunk(text: str) -> bool:
    """Internal helper to send a single validated payload to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
        # parse_mode removed to ensure guaranteed delivery of raw AI text and data tables
    }
    
    try:
        # verify=False is used to match your system's existing SSL bypass settings
        response = requests.post(url, json=payload, verify=False, timeout=15)
        if response.status_code == 200:
            print("📱 Successfully sent message to Telegram!")
            return True
        else:
            print(f"⚠️ Telegram API returned status code {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False