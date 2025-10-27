# nifty_file_logger.py
import os
import datetime
import requests
from typing import Dict, Any, List
from nifty_core_config import format_greek_value
import urllib3

# Disable SSL warnings and certificate verification for Telegram
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Try to import resend, but don't break if it's not installed
try:
    import resend
    RESEND_AVAILABLE = True
    # Set API key AFTER importing
    resend.api_key = "re_LyXNNt6f_4odzHWJPYvr38api9Nrgvptm"
    print("✅ Resend module loaded successfully")
except ImportError:
    RESEND_AVAILABLE = False
    print("⚠️ Resend module not installed. Email functionality disabled.")
    print("💡 Run: pip install resend")
except Exception as e:
    RESEND_AVAILABLE = False
    print(f"⚠️ Resend configuration error: {e}")

def send_email_with_file_content(filepath: str, subject: str = None) -> bool:
    """
    Send the complete text file content as email using Resend API
    """
    if not RESEND_AVAILABLE:
        print("❌ Cannot send email: Resend module not available")
        return False
        
    try:
        # Read the file content
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        # Create default subject if not provided
        if not subject:
            timestamp = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
            subject = f"🤖 Nifty AI Analysis - {timestamp}"
        
        # Convert text content to HTML with proper formatting
        html_content = convert_text_to_html(file_content)
        
        # Send email via Resend API
        params = {
            "from": "onboarding@resend.dev",
            "to": "talkdev@gmail.com",
            "subject": subject,
            "html": html_content
        }
        
        result = resend.Emails.send(params)
        print(f"✅ Email sent successfully! ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email via Resend: {e}")
        return False

def convert_text_to_html(text_content: str) -> str:
    """
    Convert plain text content to HTML with proper formatting
    """
    # Basic text to HTML conversion
    html_content = text_content.replace('\n', '<br>')
    html_content = html_content.replace('  ', '&nbsp;&nbsp;')
    html_content = html_content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
    
    # Add HTML structure with readable styling
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
                color: #333333;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #007acc, #005a9e);
                padding: 30px;
                color: white;
                text-align: center;
            }}
            .content {{
                padding: 30px;
                background: #ffffff;
                color: #444444;
                line-height: 1.6;
                font-family: 'Courier New', monospace;
                white-space: pre-wrap;
            }}
            .analysis-section {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                border-left: 5px solid #007acc;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border: 1px solid #e0e0e0;
            }}
            th {{
                background: #007acc;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #e0e0e0;
                color: #555555;
            }}
            tr:nth-child(even) {{
                background: #f8f9fa;
            }}
            pre {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border: 1px solid #e0e0e0;
                color: #333333;
            }}
            .critical {{
                background: #ffeaa7;
                padding: 15px;
                border-radius: 5px;
                border-left: 4px solid #fdcb6e;
                margin: 15px 0;
            }}
            .positive {{
                color: #27ae60;
                font-weight: bold;
            }}
            .negative {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .timestamp {{
                color: #007acc;
                font-weight: bold;
                font-size: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 NIFTY AI TRADING ANALYSIS</h1>
                <p class="timestamp">Generated: {datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")}</p>
            </div>
            <div class="content">
                {html_content}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

def send_telegram_message(text: str) -> bool:
    """
    Send message to Telegram with SSL verification disabled
    Split long messages into multiple parts
    """
    try:
        BOT_TOKEN = "8053348951:AAE_cpgRXjWXO20XM4EasNUdSKvTYF5YzTA"
        CHAT_ID = "324240680"
        
        # Telegram message limit is 4096 characters
        max_length = 4096
        
        if len(text) <= max_length:
            # Single message
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML"
            }
            
            session = requests.Session()
            session.verify = False
            response = session.post(url, data=payload, timeout=30)
            return response.status_code == 200
        else:
            # Split into multiple messages
            print(f"📤 Message too long ({len(text)} chars), splitting into parts...")
            
            # Split by lines to maintain readability
            lines = text.split('\n')
            current_message = ""
            message_count = 0
            success_count = 0
            
            for line in lines:
                # If adding this line would exceed limit, send current message and start new one
                if len(current_message) + len(line) + 1 > max_length:
                    if current_message:
                        message_count += 1
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                        payload = {
                            "chat_id": CHAT_ID,
                            "text": f"📊 Part {message_count}:\n",
                            "parse_mode": "HTML"
                        }
                        
                        session = requests.Session()
                        session.verify = False
                        response = session.post(url, data=payload, timeout=30)
                        if response.status_code == 200:
                            success_count += 1
                        
                        current_message = line
                else:
                    if current_message:
                        current_message += "\n" + line
                    else:
                        current_message = line
            
            # Send the last message
            if current_message:
                message_count += 1
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": CHAT_ID,
                    "text": f"📊 Part {message_count}:\n{current_message}",
                    "parse_mode": "HTML"
                }
                
                session = requests.Session()
                session.verify = False
                response = session.post(url, data=payload, timeout=30)
                if response.status_code == 200:
                    success_count += 1
            
            print(f"📤 Sent {success_count}/{message_count} message parts to Telegram")
            return success_count == message_count
            
    except Exception as e:
        print(f"❌ Error sending Telegram message: {e}")
        return False

# ... [Keep all your existing resend_latest_ai_query, resend_specific_ai_query, list_ai_query_files functions] ...

def save_ai_query_data(oi_data: List[Dict[str, Any]], 
                      oi_pcr: float, 
                      volume_pcr: float, 
                      current_nifty: float,
                      expiry_date: str,
                      banknifty_data: Dict[str, Any] = None) -> str:
    """
    Save AI query data to a text file with timestamp in filename and send to Telegram & Email
    Returns the file path where data was saved
    """    
    # Create directory if it doesn't exist
    base_dir = os.path.join(os.getcwd(), "ai-query-logs")
    os.makedirs(base_dir, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename = f"ai_query_{timestamp}.txt"
    filepath = os.path.join(base_dir, filename)
    
    # AI System Prompt (hardcoded as per requirement)
    system_prompt = """
You are an expert Nifty/BankNifty/top10 Nifty Stocks by weighage option chain analyst with deep knowledge of historical patterns and institutional trading behavior. You read between the lines to decode both smart money AND retail perspectives. You perform mathematical calculations, psychological analysis, and interlink all data points to understand market dynamics. You analyze the market from the seller's point of view because they only drive the market. Take your time for thorough analysis.
----------------------------------------------------------------------------------------------------------------------------------------------------------
Analyze the provided OI data for Nifty index (weekly expiry), BankNifty index (monthly expiry), and top 10 Nifty Stocks (monthly expiry) to interpret the intraday trend. 

CRITICAL ANALYSIS FRAMEWORK - FOLLOW THIS ORDER:

1. Analyze PE & CE OI for each strike.
2. Analyze difference between PE & CE for each strike.
3. Analyze OI PCR.
4. Analyze Volume PCR.
5. Analyze separately once again for NIFTY ATM+-2 strike.
6. Analyze the market from seller's perspective.
7. Analyze smart money positions.
8. Keep in mind, NSE nifty & bank nifty are index so their analysis logic is completely different from NSE stocks analysis logic.
9. Always use historical proven threshold values for NIFTY and BANKNIFTY for making any calculation.
10. You entire analysis should be focussed on providing intraday 20-40 points nifty scalping opportunity.
11. I only take naked Nifty CE/PE buys for intraday.
12. Tips must consider for correct calculations: "Price action overrides OI data" & "Verify gamma direction (MM short puts = long futures)" & "Calculate probabilities using distance-to-strike formula" & "Institutional selling ≠ directional betting & Validate risk-reward with expectancy calculation" & "PCR + rising price = bullish, not bearish & High call volume + uptrend = momentum confirmation" & "Maximum probability cap at 70percentage without statistical proof" & "Theta decay > gamma for <24hr expiry" & "Daily range boundaries override OI walls"

----------------------------------------------------------------------------------------------------------------------------------------------------------
Provide output categorically:
- Short summary with clear directional bias and justification behind your logic.
- mathematically and scientifically calculated probability of current nifty price moving to strike+1 or strike -1.
- Breakdown of conflicting/confirming signals in short.
- Specific entry levels, stop-loss, targets, do not provide hedge instead only buy CE/PE.

Note: do not provide any value or calculation from thin air from your end. do not presume any thing hypothetically. do not include any information out of thin air.        

----------------------------------------------------------------------------------------------------------------------------------------------------------
I don't want you to agree with me just to be polite or supportive. Drop the filter be brutally honest, straightforward, and logical. Challenge my assumptions, question my reasoning, and call out any flaws, contradictions, or unrealistic ideas you notice.
Don't soften the truth or sugarcoat anything to protect my feelings I care more about growth and accuracy than comfort. Avoid empty praise, generic motivation, or vague advice. I want hard facts, clear reasoning, and actionable feedback.
Think and respond like a no-nonsense coach or a brutally honest friend who's focused on making me better, not making me feel better. Push back whenever necessary, and never feed me bullshit. Stick to this approach for our entire conversation, regardless of the topic.
And just give me answer no other words or appreciation or any bullshit or judgement. Just plain n deep answer which is well researched.

----------------------------------------------------------------------------------------------------------------------------------------------------------
# ... [Keep the rest of your system prompt as is] ...
    """

    # Format the data section
    fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data_section = f"\n\nCURRENT DATA FOR ANALYSIS - FETCHED AT: {fetch_time}\n"
    data_section += "=" * 80 + "\n"
    data_section += f"NIFTY DATA:\n"
    data_section += f"- Current Value: {current_nifty}\n"
    data_section += f"- Expiry Date: {expiry_date}\n"
    data_section += f"- OI PCR: {oi_pcr:.2f}\n"
    data_section += f"- Volume PCR: {volume_pcr:.2f}\n"
    
    # Add BankNifty data if available
    if banknifty_data:
        data_section += f"\nBANKNIFTY DATA:\n"
        data_section += f"- Current Value: {banknifty_data.get('current_value', 0)}\n"
        data_section += f"- Expiry Date: {banknifty_data.get('expiry_date', 'N/A')}\n"
        data_section += f"- OI PCR: {banknifty_data.get('oi_pcr', 0):.2f}\n"
        data_section += f"- Volume PCR: {banknifty_data.get('volume_pcr', 0):.2f}\n"
    
    # Add COMPLETE Nifty option chain data in the same format as console
    data_section += f"\n\nCOMPLETE NIFTY OPTION CHAIN DATA:\n"
    data_section += "=" * 80 + "\n"
    data_section += f"OI Data for NIFTY - Current: {current_nifty}, Expiry: {expiry_date}\n"
    data_section += f"Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}\n"
    data_section += "=" * 80 + "\n"
    data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
    data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                   f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                   f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
    data_section += "-" * 150 + "\n"
    
    for data in oi_data:  # ALL strikes, not just first 20
        strike_price = data['strike_price']
        
        # Format data exactly like console display
        ce_oi_formatted = str(data['ce_change_oi'])
        ce_volume_formatted = str(data['ce_volume'])
        ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
        ce_oi_total_formatted = str(data['ce_oi'])
        ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
        
        pe_oi_formatted = str(data['pe_change_oi'])
        pe_volume_formatted = str(data['pe_volume'])
        pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
        pe_oi_total_formatted = str(data['pe_oi'])
        pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
        
        chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
        chg_oi_diff_formatted = str(chg_oi_diff)
        
        # Format the row exactly like console
        formatted_row = (
            f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
            f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
            f"{str(strike_price).center(9)}  |  "
            f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
            f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
            f"{chg_oi_diff_formatted.rjust(16)}"
        )
        
        data_section += formatted_row + "\n"
    
    data_section += "=" * 150 + "\n"
    data_section += f"NIFTY PCR: OI PCR = {oi_pcr:.2f}, Volume PCR = {volume_pcr:.2f}\n\n"
    
    # Add COMPLETE BankNifty option chain data if available
    if banknifty_data and 'data' in banknifty_data:
        banknifty_oi_data = banknifty_data['data']
        banknifty_current = banknifty_data.get('current_value', 0)
        banknifty_expiry = banknifty_data.get('expiry_date', 'N/A')
        banknifty_oi_pcr = banknifty_data.get('oi_pcr', 0)
        banknifty_volume_pcr = banknifty_data.get('volume_pcr', 0)
        
        data_section += f"\n\nCOMPLETE BANKNIFTY OPTION CHAIN DATA:\n"
        data_section += "=" * 80 + "\n"
        data_section += f"OI Data for BANKNIFTY - Current: {banknifty_current}, Expiry: {banknifty_expiry}\n"
        data_section += f"Full Chain PCR: OI={banknifty_oi_pcr:.2f}, Volume={banknifty_volume_pcr:.2f}\n"
        data_section += "=" * 80 + "\n"
        data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
        data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                       f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                       f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
        data_section += "-" * 150 + "\n"
        
        for data in banknifty_oi_data:  # ALL BankNifty strikes
            strike_price = data['strike_price']
            
            # Format BankNifty data exactly like console display
            ce_oi_formatted = str(data['ce_change_oi'])
            ce_volume_formatted = str(data['ce_volume'])
            ce_ltp_formatted = f"{data['ce_ltp']:.1f}" if data['ce_ltp'] else "0"
            ce_oi_total_formatted = str(data['ce_oi'])
            ce_iv_formatted = format_greek_value(data['ce_iv'], 1)
            
            pe_oi_formatted = str(data['pe_change_oi'])
            pe_volume_formatted = str(data['pe_volume'])
            pe_ltp_formatted = f"{data['pe_ltp']:.1f}" if data['pe_ltp'] else "0"
            pe_oi_total_formatted = str(data['pe_oi'])
            pe_iv_formatted = format_greek_value(data['pe_iv'], 1)
            
            chg_oi_diff = data['ce_change_oi'] - data['pe_change_oi']
            chg_oi_diff_formatted = str(chg_oi_diff)
            
            # Format the row exactly like console
            formatted_row = (
                f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                f"{str(strike_price).center(9)}  |  "
                f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                f"{chg_oi_diff_formatted.rjust(16)}"
            )
            
            data_section += formatted_row + "\n"
        
        data_section += "=" * 150 + "\n"
        data_section += f"BANKNIFTY PCR: OI PCR = {banknifty_oi_pcr:.2f}, Volume PCR = {banknifty_volume_pcr:.2f}\n"
    
    data_section += "=" * 80 + "\n"
    
    # Combine everything
    full_content = system_prompt + data_section
    
    # Write to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ AI query data saved to: {filepath}")
        
        # Send to Telegram
        print("📤 Sending to Telegram...")
        telegram_success = send_telegram_message(full_content)
        if telegram_success:
            print("✅ Message sent to Telegram successfully!")
        else:
            print("❌ Failed to send message to Telegram")
        
        # Send to Email via Resend API
        print("📧 Sending to Email...")
        email_success = send_email_with_file_content(filepath)
        if email_success:
            print("✅ Email sent successfully!")
        else:
            print("❌ Failed to send email")
        
        return filepath
    except Exception as e:
        print(f"❌ Error saving AI query data: {e}")
        return ""