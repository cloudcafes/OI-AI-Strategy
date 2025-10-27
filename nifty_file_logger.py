# nifty_file_logger.py
import os
import datetime
import requests
from typing import Dict, Any, List
from nifty_core_config import format_greek_value
import urllib3
import resend

# Configure Resend API
resend.api_key = "re_LyXNNt6f_4odzHWJPYvr38api9Nrgvptm"

# Disable SSL warnings and certificate verification for Telegram
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_email_with_file_content(filepath: str, subject: str = None) -> bool:
    """
    Send the complete text file content as email using Resend API
    """
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
    # Replace line breaks and basic formatting
    html_content = text_content.replace('\n', '<br>')
    html_content = html_content.replace('=', '=')
    html_content = html_content.replace('-', '-')
    
    # Add basic HTML structure and styling
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                margin: 20px;
                background: #1e1e1e;
                color: #d4d4d4;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
            }}
            .header {{
                background: #2d2d2d;
                padding: 20px;
                border-radius: 5px;
                margin-bottom: 20px;
                border-left: 4px solid #007acc;
            }}
            .content {{
                background: #252525;
                padding: 20px;
                border-radius: 5px;
                white-space: pre-wrap;
                font-family: 'Courier New', monospace;
            }}
            .section {{
                margin: 15px 0;
                padding: 10px;
                background: #2a2a2a;
                border-radius: 3px;
            }}
            .timestamp {{
                color: #569cd6;
                font-weight: bold;
            }}
            .important {{
                color: #ff6b6b;
                font-weight: bold;
            }}
            .success {{
                color: #4ec9b0;
            }}
            .warning {{
                color: #ffd700;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 10px 0;
            }}
            th, td {{
                border: 1px solid #444;
                padding: 8px;
                text-align: left;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }}
            th {{
                background: #2d2d2d;
                color: #569cd6;
            }}
            pre {{
                background: #1e1e1e;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border: 1px solid #444;
            }}
            code {{
                background: #2d2d2d;
                padding: 2px 4px;
                border-radius: 3px;
                color: #ce9178;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🤖 NIFTY AI TRADING ANALYSIS</h2>
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
                            "text": f"📊 Part {message_count}:\n{current_message}",
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

# ... [Keep all the existing functions: resend_latest_ai_query, resend_specific_ai_query, list_ai_query_files] ...

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
# ... [Keep the entire system prompt as is] ...
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
        
        # Send to Telegram (optional - you can remove this if you only want email)
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