import requests
import datetime
import urllib3
import json
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TelegramNiftyBot:
    def __init__(self):
        self.bot_token = "8053348951:AAE_cpgRXjWXO20XM4EasNUdSKvTYF5YzTA"
        self.chat_id = None
    
    def get_bot_info(self):
        """
        Get your bot's username - you need this to find it on Telegram
        """
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{self.bot_token}/getMe",
                verify=False,
                timeout=10
            )
            
            data = response.json()
            if data["ok"]:
                bot_info = data["result"]
                print(f"🔍 YOUR BOT USERNAME: @{bot_info['username']}")
                print(f"📛 Bot Name: {bot_info['first_name']}")
                print("\n📝 INSTRUCTIONS:")
                print(f"1. Open Telegram")
                print(f"2. Search for: @{bot_info['username']}")
                print(f"3. Click 'START' or send any message")
                print(f"4. Then run get_chat_id() again")
                return bot_info
            else:
                print("❌ Could not get bot info")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_chat_id(self, debug=False):
        """
        Get your Chat ID - run this AFTER sending a message to your bot
        """
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
                verify=False,
                timeout=10
            )
            
            data = response.json()
            
            if debug:
                print("🔍 DEBUG RESPONSE:")
                print(json.dumps(data, indent=2))
            
            if data["ok"]:
                if len(data["result"]) > 0:
                    # Get the latest message
                    latest_update = data["result"][-1]
                    if "message" in latest_update:
                        self.chat_id = latest_update["message"]["chat"]["id"]
                        user_name = latest_update["message"]["chat"].get("first_name", "Unknown")
                        print(f"✅ Chat ID found: {self.chat_id}")
                        print(f"👤 User: {user_name}")
                        return self.chat_id
                    else:
                        print("❌ No message found in update")
                        return None
                else:
                    print("❌ No messages found in getUpdates response")
                    print("💡 SOLUTION: Send a message to your bot first!")
                    print("   Run get_bot_info() to see your bot username")
                    return None
            else:
                print(f"❌ API Error: {data.get('description', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting chat ID: {e}")
            return None
    
    def send_test_message(self):
        """
        Send a test message once you have chat_id
        """
        if not self.chat_id:
            print("❌ No chat ID set. Run get_chat_id() first.")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': "🤖 Nifty Bot Test Message!\nYour bot is working correctly!",
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, verify=False, timeout=10)
            
            if response.status_code == 200:
                print("✅ Test message sent successfully!")
                return True
            else:
                print(f"❌ Failed to send test message: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending test message: {e}")
            return False

# COMPLETE SETUP PROCESS:
def setup_telegram_bot():
    """
    Complete setup process for Telegram bot
    """
    bot = TelegramNiftyBot()
    
    print("=" * 50)
    print("TELEGRAM BOT SETUP")
    print("=" * 50)
    
    # Step 1: Get bot info
    print("\n1. 🔍 Finding your bot username...")
    bot_info = bot.get_bot_info()
    
    if not bot_info:
        print("❌ Failed to get bot info. Check your bot token.")
        return None
    
    print(f"\n2. 📱 Go to Telegram and search for: @{bot_info['username']}")
    print("   Send any message like 'Hello' or click START")
    input("   Press Enter AFTER you've sent a message to your bot...")
    
    # Step 2: Get chat ID
    print("\n3. 🔑 Getting your chat ID...")
    chat_id = bot.get_chat_id(debug=True)  # Enable debug to see full response
    
    if chat_id:
        print(f"\n🎉 SUCCESS! Chat ID: {chat_id}")
        
        # Step 3: Send test message
        print("\n4. 📤 Sending test message...")
        bot.send_test_message()
        
        return bot
    else:
        print("\n❌ Failed to get chat ID.")
        print("   Make sure you sent a message to the bot.")
        return None

# Run the complete setup
if __name__ == "__main__":
    bot = setup_telegram_bot()
    if bot:
        print(f"\n✅ Setup complete! Your chat_id is: {bot.chat_id}")
        print("💡 Save this chat_id for your Nifty trading bot:")
        print(f"   CHAT_ID = {bot.chat_id}")