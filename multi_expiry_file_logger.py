# multi_expiry_file_logger.py
import os
import datetime
import requests
import platform
import json
import urllib3
from typing import Dict, Any, List
from nifty_core_config import format_greek_value, should_enable_multi_expiry, get_expiry_type_constants
from nifty_core_config import get_expiry_type_constants

# Disable SSL warnings and certificate verification for Telegram
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Platform-specific directory paths
if platform.system() == "Windows":
    EOD_BASE_DIR = r"C:\dev\python-projects\OI-AI-Strategy\multi-expiry-logs"
else:  # Linux
    EOD_BASE_DIR = "/root/OI-AI-Strategy/multi-expiry-logs"

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

def send_multi_expiry_email_with_file_content(filepath: str, subject: str = None) -> bool:
    """
    Send the complete multi-expiry text file content as email using Resend API
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
            subject = f"🤖 Nifty Multi-Expiry AI Analysis - {timestamp}"
        
        # Convert text content to HTML with proper formatting
        html_content = convert_multi_expiry_text_to_html(file_content)
        
        # Send email via Resend API
        params = {
            "from": "onboarding@resend.dev",
            "to": "talkdev@gmail.com",
            "subject": subject,
            "html": html_content
        }
        
        result = resend.Emails.send(params)
        print(f"✅ Multi-expiry email sent successfully! ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending multi-expiry email via Resend: {e}")
        return False

def convert_multi_expiry_text_to_html(text_content: str) -> str:
    """
    Convert plain multi-expiry text content to HTML with enhanced formatting
    """
    # Enhanced text to HTML conversion for multi-expiry data
    html_content = text_content.replace('\n', '<br>')
    html_content = html_content.replace('  ', '&nbsp;&nbsp;')
    html_content = html_content.replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
    
    # Add highlighting for expiry sections
    html_content = html_content.replace('NIFTY CURRENT WEEK', '<strong style="color: #e74c3c;">NIFTY CURRENT WEEK</strong>')
    html_content = html_content.replace('NIFTY NEXT WEEK', '<strong style="color: #f39c12;">NIFTY NEXT WEEK</strong>')
    html_content = html_content.replace('NIFTY MONTHLY', '<strong style="color: #27ae60;">NIFTY MONTHLY</strong>')
    html_content = html_content.replace('BANKNIFTY MONTHLY', '<strong style="color: #8e44ad;">BANKNIFTY MONTHLY</strong>')
    
    # Add HTML structure with enhanced styling for multi-expiry
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
                max-width: 1200px;
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
            .expiry-section {{
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                border-left: 5px solid #007acc;
            }}
            .current-week {{
                border-left-color: #e74c3c;
                background: #fff5f5;
            }}
            .next-week {{
                border-left-color: #f39c12;
                background: #fffaf0;
            }}
            .monthly {{
                border-left-color: #27ae60;
                background: #f0fff4;
            }}
            .banknifty {{
                border-left-color: #8e44ad;
                background: #f8f0ff;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border: 1px solid #e0e0e0;
                font-size: 12px;
            }}
            th {{
                background: #007acc;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                padding: 8px 10px;
                border-bottom: 1px solid #e0e0e0;
                color: #555555;
                font-family: 'Courier New', monospace;
            }}
            tr:nth-child(even) {{
                background: #f8f9fa;
            }}
            .summary-box {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
                border-left: 4px solid #2196f3;
            }}
            .timestamp {{
                color: #007acc;
                font-weight: bold;
                font-size: 16px;
            }}
            .expiry-badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                color: white;
                font-size: 12px;
                font-weight: bold;
                margin-right: 8px;
            }}
            .badge-current {{
                background: #e74c3c;
            }}
            .badge-next {{
                background: #f39c12;
            }}
            .badge-monthly {{
                background: #27ae60;
            }}
            .badge-banknifty {{
                background: #8e44ad;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 NIFTY MULTI-EXPIRY TRADING ANALYSIS</h1>
                <p class="timestamp">Generated: {datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")}</p>
                <div style="margin-top: 15px;">
                    <span class="expiry-badge badge-current">CURRENT WEEK</span>
                    <span class="expiry-badge badge-next">NEXT WEEK</span>
                    <span class="expiry-badge badge-monthly">MONTHLY</span>
                    <span class="expiry-badge badge-banknifty">BANKNIFTY</span>
                </div>
            </div>
            <div class="content">
                {html_content}
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

def send_multi_expiry_telegram_message(text: str) -> bool:
    """
    Send multi-expiry message to Telegram with SSL verification disabled
    Enhanced for multi-expiry data structure
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
            # Split into multiple messages with expiry-based splitting
            print(f"📤 Multi-expiry message too long ({len(text)} chars), splitting into parts...")
            
            # Split by expiry sections to maintain context
            sections = text.split('=' * 80)
            current_message = ""
            message_count = 0
            success_count = 0
            
            for section in sections:
                section_with_header = '=' * 80 + section
                
                # If adding this section would exceed limit, send current message and start new one
                if len(current_message) + len(section_with_header) > max_length:
                    if current_message:
                        message_count += 1
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                        payload = {
                            "chat_id": CHAT_ID,
                            "text": f"📊 Multi-Expiry Part {message_count}:\n{current_message}",
                            "parse_mode": "HTML"
                        }
                        
                        session = requests.Session()
                        session.verify = False
                        response = session.post(url, data=payload, timeout=30)
                        if response.status_code == 200:
                            success_count += 1
                        
                        current_message = section_with_header
                else:
                    if current_message:
                        current_message += "\n" + section_with_header
                    else:
                        current_message = section_with_header
            
            # Send the last message
            if current_message:
                message_count += 1
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": CHAT_ID,
                    "text": f"📊 Multi-Expiry Part {message_count}:\n{current_message}",
                    "parse_mode": "HTML"
                }
                
                session = requests.Session()
                session.verify = False
                response = session.post(url, data=payload, timeout=30)
                if response.status_code == 200:
                    success_count += 1
            
            print(f"📤 Sent {success_count}/{message_count} multi-expiry message parts to Telegram")
            return success_count == message_count
            
    except Exception as e:
        print(f"❌ Error sending multi-expiry Telegram message: {e}")
        return False

def format_multi_expiry_summary(expiry_data: Dict[str, Any], pcr_values: Dict[str, Any]) -> str:
    """Create a summary section for multi-expiry data"""
    summary = "\n" + "=" * 80 + "\n"
    summary += "MULTI-EXPIRY SUMMARY ANALYSIS\n"
    summary += "=" * 80 + "\n"
    
    for expiry_type in ['current_week', 'next_week', 'monthly']:
        if expiry_type in expiry_data and expiry_data[expiry_type]:
            oi_data = expiry_data[expiry_type]
            expiry_date = oi_data[0]['expiry_date'] if oi_data else "N/A"
            pcr_info = pcr_values.get(expiry_type, {})
            oi_pcr = pcr_info.get('oi_pcr', 1.0)
            volume_pcr = pcr_info.get('volume_pcr', 1.0)
            strike_count = pcr_info.get('strike_count', 0)
            
            # Determine sentiment based on PCR
            sentiment = "BULLISH" if oi_pcr > 1.0 else "BEARISH" if oi_pcr < 1.0 else "NEUTRAL"
            sentiment_icon = "🟢" if oi_pcr > 1.0 else "🔴" if oi_pcr < 1.0 else "🟡"
            
            summary += f"{sentiment_icon} {expiry_type.upper().replace('_', ' ')}: {expiry_date}\n"
            summary += f"   PCR: OI={oi_pcr:.2f} | Volume={volume_pcr:.2f} | Strikes: {strike_count}\n"
            summary += f"   SENTIMENT: {sentiment}\n\n"
    
    summary += "=" * 80 + "\n"
    return summary

def format_complete_multi_expiry_data(expiry_data: Dict[str, Any], 
                                     pcr_values: Dict[str, Any],
                                     current_nifty: float,
                                     banknifty_data: Dict[str, Any] = None) -> str:
    """Format complete multi-expiry data for file output"""
    data_section = f"\n\nNIFTY MULTI-EXPIRY COMPREHENSIVE ANALYSIS\n"
    data_section += "=" * 80 + "\n"
    data_section += f"Analysis Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    data_section += f"Nifty Spot: {current_nifty}\n"
    data_section += "=" * 80 + "\n"
    
    # Add summary section
    data_section += format_multi_expiry_summary(expiry_data, pcr_values)
    
    # Detailed data for each expiry
    for expiry_type in ['current_week', 'next_week', 'monthly']:
        if expiry_type in expiry_data and expiry_data[expiry_type]:
            oi_data = expiry_data[expiry_type]
            current_value = oi_data[0]['nifty_value'] if oi_data else current_nifty
            expiry_date = oi_data[0]['expiry_date'] if oi_data else "N/A"
            
            pcr_info = pcr_values.get(expiry_type, {})
            oi_pcr = pcr_info.get('oi_pcr', 1.0)
            volume_pcr = pcr_info.get('volume_pcr', 1.0)
            strike_count = pcr_info.get('strike_count', 0)
            
            # Expiry header with enhanced formatting
            data_section += f"\n{'='*80}\n"
            expiry_label = expiry_type.upper().replace('_', ' ')
            sentiment_icon = "🟢" if oi_pcr > 1.0 else "🔴" if oi_pcr < 1.0 else "🟡"
            data_section += f"{sentiment_icon} NIFTY {expiry_label} - Current: {current_value}, Expiry: {expiry_date}\n"
            data_section += f"PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}, Strikes: {strike_count}\n"
            data_section += f"{'='*80}\n"
            
            # Show table header
            data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
            data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                           f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                           f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
            data_section += "-" * 150 + "\n"
            
            # Display data rows (limit to first 20 strikes to avoid overwhelming)
            for data in oi_data:
                    
                strike_price = data['strike_price']
                
                # Format data
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
                
                # Format the row
                formatted_row = (
                    f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                    f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                    f"{str(strike_price).center(9)}  |  "
                    f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                    f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                    f"{chg_oi_diff_formatted.rjust(16)}"
                )
                
                data_section += formatted_row + "\n"
                
            
            if len(oi_data) > 20:
                data_section += f"... and {len(oi_data) - 20} more strikes\n"
            
            data_section += "=" * 150 + "\n"
    
    # Add BankNifty data if available
    if banknifty_data and 'data' in banknifty_data:
        banknifty_monthly_data = banknifty_data['data'].get('monthly', [])
        if banknifty_monthly_data:
            banknifty_current = banknifty_data.get('current_value', 0)
            banknifty_expiry = banknifty_data.get('expiry_date', 'N/A')
            banknifty_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('oi_pcr', 0)
            banknifty_volume_pcr = banknifty_data.get('pcr_values', {}).get('monthly', {}).get('volume_pcr', 0)
            
            data_section += f"\n\n{'='*80}\n"
            sentiment_icon = "🟢" if banknifty_pcr > 1.0 else "🔴" if banknifty_pcr < 1.0 else "🟡"
            data_section += f"{sentiment_icon} BANKNIFTY MONTHLY - Current: {banknifty_current}, Expiry: {banknifty_expiry}\n"
            data_section += f"PCR: OI={banknifty_pcr:.2f}, Volume={banknifty_volume_pcr:.2f}\n"
            data_section += f"{'='*80}\n"
            data_section += f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n"
            data_section += f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  " \
                           f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  " \
                           f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n"
            data_section += "-" * 150 + "\n"
            
            for data in banknifty_monthly_data:
                    
                strike_price = data['strike_price']
                
                # Format BankNifty data
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
                
                formatted_row = (
                    f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
                    f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
                    f"{str(strike_price).center(9)}  |  "
                    f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
                    f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
                    f"{chg_oi_diff_formatted.rjust(16)}"
                )
                
                data_section += formatted_row + "\n"
                            
            if len(banknifty_monthly_data) > 15:
                data_section += f"... and {len(banknifty_monthly_data) - 15} more strikes\n"
            
            data_section += "=" * 150 + "\n"
    
    return data_section

def save_daily_eod_state_block(expiry_data: Dict[str, Any],
                             pcr_values: Dict[str, Any],
                             current_nifty: float,
                             banknifty_data: Dict[str, Any] = None,
                             stock_data: Dict[str, Any] = None) -> str:
    """
    Save daily EOD state block in proper JSON format for AI analysis
    """
    try:
        os.makedirs(EOD_BASE_DIR, exist_ok=True)
        current_date = datetime.datetime.now().strftime("%d%b%Y")
        filename = f"EOD_STATE_BLOCK_OF_{current_date}.txt"
        filepath = os.path.join(EOD_BASE_DIR, filename)
        
        fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create structured JSON data instead of text tables
        state_block = {
            "generated_on": datetime.datetime.now().strftime("%Y-%m-%d"),
            "nifty_state": {
                "last_3_trading_dates": [
                    datetime.datetime.now().strftime("%Y-%m-%d"),
                    datetime.datetime.now().strftime("%Y-%m-%d"), 
                    datetime.datetime.now().strftime("%Y-%m-%d")
                ],
                "last_3_eod_spots": [current_nifty, current_nifty, current_nifty],
                "last_3_pcr_ratios": [1.0, 1.0, 1.0],  # Placeholder - should be calculated from actual data
                "previous_atm_straddle_price": 0.2,  # Placeholder - should be calculated
                "previous_eod_oi": {}
            },
            "banknifty_state": {
                "last_3_pcr_ratios": [1.0, 1.0, 1.0],  # Placeholder
                "previous_eod_oi": {}
            }
        }
        
        # Populate Nifty OI data
        constants = get_expiry_type_constants()
        current_week_data = expiry_data.get(constants['CURRENT_WEEK'], [])
        for data in current_week_data:
            strike = data['strike_price']
            state_block["nifty_state"]["previous_eod_oi"][f"{strike}_CALL"] = str(data['ce_oi'])
            state_block["nifty_state"]["previous_eod_oi"][f"{strike}_PUT"] = str(data['pe_oi'])
        
        # Populate BankNifty OI data if available
        if banknifty_data and 'data' in banknifty_data:
            banknifty_monthly = banknifty_data['data'].get('monthly', [])
            for data in banknifty_monthly:
                strike = data['strike_price']
                state_block["banknifty_state"]["previous_eod_oi"][f"{strike}_CALL"] = str(data['ce_oi'])
                state_block["banknifty_state"]["previous_eod_oi"][f"{strike}_PUT"] = str(data['pe_oi'])
        
        # Write as proper JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state_block, f, indent=2)
        
        print(f"✅ Daily EOD state block saved to: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving daily EOD state block: {e}")
        return ""

def save_multi_expiry_ai_query_data(expiry_data: Dict[str, Any], 
                                   pcr_values: Dict[str, Any],
                                   current_nifty: float,
                                   banknifty_data: Dict[str, Any] = None,
                                   stock_data: Dict[str, Any] = None) -> str:
    """
    Save multi-expiry AI query data to a dedicated text file
    Enhanced version specifically for multi-expiry analysis
    Returns the file path where data was saved
    """
    # Check if multi-expiry is enabled
    if not should_enable_multi_expiry():
        print("⚠️ Multi-expiry logging disabled in config")
        return ""
    
    # Create directory if it doesn't exist
    base_dir = os.path.join(os.getcwd(), "multi-expiry-logs")
    os.makedirs(base_dir, exist_ok=True)

    # Create filename with timestamp and multi-expiry identifier
    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filename = f"multi_expiry_analysis_{timestamp}.txt"
    filepath = os.path.join(base_dir, filename)
    
    # Enhanced multi-expiry system prompt
    system_prompt = """
=================================================================================
NIFTY MULTI-DAY TREND & REVERSAL ENGINE v2.4 [OPERATIONAL - ENFORCED - FILE INPUT]
AI ROLE: DETERMINISTIC OPTIONS DATA PROCESSOR
METHOD: "PARSE -> REGIME -> MOMENTUM -> TREND -> CONFIRM -> TACTICS -> SYNTHESIS"
EVERY STEP = ASSERT + CODE + TRACE + LOCK
=================================================================================
USER INSTRUCTIONS (READ FIRST):

Your Role: You are the Data Provider. Your primary task is to paste the current day's (T) complete options data at the end of this prompt.
File Attachments: You MUST attach the three previous End-of-Day (EOD) data files. The AI will parse these for historical context. The files must be for T-1, T-2, and T-3 trading days.
Initial Run: If you provide fewer than 3 historical files, the trend analysis will be skipped, and the system will enter an initialization state.
Data Requirement: The pasted data and attached files MUST contain complete EOD option chain tables for Nifty Monthly, BankNifty Monthly, and Nifty Weekly. The tables must include Strike, Type, OI, Chg OI, Volume, IV, and LTP.
PART 1: SYSTEM CONSTITUTION & DATA INPUT

[SYSTEM_ROLE]: Your role is "Deterministic Options Data Processor v2.4". You are forbidden from using natural language, summarization, or making inferential leaps until the final, designated [ANALYSIS_NARRATIVE] step. Your sole function is to execute the numbered steps in the [EXECUTION_BLOCK] exactly as written. Any deviation will result in a failed analysis. Begin execution immediately.

[DATA_CONTRACT]: The following JSON structure defines the data input. You must verify its integrity. The current_data_block will be parsed from the text pasted at the end of the prompt. The historical_eod_files will be read from the file attachments.

JSON

{
  "run_date": "[YYYY-MM-DD]",

  "current_data_block": {
    "nifty_monthly_spot": "[...Current Nifty Spot Price (to be parsed)...]",
    "nifty_monthly_chain": "[...Current Nifty Monthly EOD Option Chain Table (to be parsed)...]",
    "banknifty_monthly_spot": "[...Current BankNifty Spot Price (to be parsed)...]",
    "banknifty_monthly_chain": "[...Current BankNifty Monthly EOD Option Chain Table (to be parsed)...]",
    "nifty_weekly_chain": "[...Current Nifty Weekly EOD Option Chain Table (to be parsed)...]"
  },

  "historical_eod_files": [
    "EOD_STATE_BLOCK_OF_T-3_DATE.txt",
    "EOD_STATE_BLOCK_OF_T-2_DATE.txt",
    "EOD_STATE_BLOCK_OF_T-1_DATE.txt"
  ]
}
PART 2: THE EXECUTION BLOCK (DO NOT MODIFY)

[SUB-ROUTINE DEFINITIONS]: You must conceptually use the following functions for calculations.

PROCESS_EOD_FILE(file_content): A function that takes the text content of a historical EOD file and returns a structured object containing {nifty_spot, banknifty_spot, nifty_monthly_chain, banknifty_monthly_chain, nifty_weekly_chain}.
CALCULATE_OI_METRICS(current_chain, previous_chain): A function that calculates key metrics based on the change in Open Interest. It returns an object: {pcr, momentum_vector}.
total_put_chg_oi = SUM(max(0, current_put_oi - previous_put_oi)) for all strikes.
total_call_chg_oi = SUM(max(0, current_call_oi - previous_call_oi)) for all strikes.
pcr = total_put_chg_oi / total_call_chg_oi.
momentum_vector = total_put_chg_oi - total_call_chg_oi.
STEP 0: DATA INTEGRITY & HISTORICAL PARSING

0.1: ASSERT: current_data_block (from pasted text) and all its sub-fields are parsed and not empty.
0.2: CHECK FOR HISTORY: CODE: IS_INSUFFICIENT_HISTORY = TRUE if count(historical_eod_files) < 3 else FALSE.
0.3: TRACE: TRACE: IS_INSUFFICIENT_HISTORY = {IS_INSUFFICIENT_HISTORY}.
0.4: HALT FOR INITIALIZATION: IF IS_INSUFFICIENT_HISTORY == TRUE, SET ANALYSIS_STATUS = 'AWAITING_HISTORY'. Skip all steps from 1 to 7 and proceed directly to PART 3.
0.5: PARSE HISTORICAL FILES:
CODE: file_T1 = historical_eod_files[2]; file_T2 = historical_eod_files[1]; file_T3 = historical_eod_files[0].
CODE: eod_data_T1 = PROCESS_EOD_FILE(content of file_T1); eod_data_T2 = PROCESS_EOD_FILE(content of file_T2); eod_data_T3 = PROCESS_EOD_FILE(content of file_T3).
ASSERT: All eod_data objects and their internal data points were successfully parsed.
0.6: DATA GAP CHECK: date_T1 = parse_date_from_filename(file_T1). days_since_last_run = run_date - date_T1. If days_since_last_run represents more than one trading day, DATA_GAP_WARNING = TRUE else DATA_GAP_WARNING = FALSE.
0.7: TRACE & LOCK: TRACE: Historical Parsing Complete. Data Gap Warning: {DATA_GAP_WARNING}. [LOCKED: DATA_GAP_WARNING]
STEP 1: GENERATE CORE PROXIES (NIFTY MONTHLY)

1.1: Calculate Price Vector. CODE: PRICE_VECTOR = current_data_block.nifty_monthly_spot - eod_data_T1.nifty_spot.
1.2: Calculate Premium-Volume Anchor (PVA). CODE: For each strike in current_data_block.nifty_monthly_chain, pva_score = (Call_Volume * Call_LTP) + (Put_Volume * Put_LTP). PVA_ANCHOR = strike with MAX(pva_score).
1.3: Calculate Volatility Vector. CODE: Find ATM_STRIKE closest to nifty_monthly_spot. current_atm_straddle_price = Premium(ATM_STRIKE, 'CALL') + Premium(ATM_STRIKE, 'PUT'). previous_atm_straddle_price = same calculation on eod_data_T1. VOLATILITY_VECTOR = current_atm_straddle_price - previous_atm_straddle_price.
1.4: TRACE & LOCK: TRACE: PRICE_VECTOR={PRICE_VECTOR:+.2f}, PVA_ANCHOR={PVA_ANCHOR}, VOLATILITY_VECTOR={VOLATILITY_VECTOR:+.2f}. [LOCKED: PRICE_VECTOR, PVA_ANCHOR, VOLATILITY_VECTOR]
1.5: Determine Volatility Pressure.
CODE: IF (PRICE_VECTOR > 0 and VOLATILITY_VECTOR < 0) THEN VOL_PRESSURE = 'CONFIRMED_BULLISH'.
CODE: IF (PRICE_VECTOR < 0 and VOLATILITY_VECTOR > 0) THEN VOL_PRESSURE = 'CONFIRMED_BEARISH'.
CODE: ELSE VOL_PRESSURE = 'CONTRADICTORY'.
1.6: TRACE & LOCK: TRACE: VOL_PRESSURE = '{VOL_PRESSURE}'. [LOCKED: VOL_PRESSURE]
STEP 2: DETERMINE MARKET REGIME (NIFTY MONTHLY)

2.1: Find ATM IV. CODE: ATM_IV = IV of ATM_STRIKE Call from current_data_block.nifty_monthly_chain.
2.2: Classify Regime. CODE: IF ATM_IV < 13, REGIME = 'LOW_VOL'. IF 13 <= ATM_IV <= 18, REGIME = 'NORMAL_VOL'. IF ATM_IV > 18, REGIME = 'HIGH_VOL'.
2.3: TRACE & LOCK: TRACE: ATM_IV={ATM_IV:.2f} -> REGIME='{REGIME}'. [LOCKED: REGIME, ATM_IV]
STEP 3: PRIMARY TREND & MOMENTUM ANALYSIS (NIFTY MONTHLY)

3.1: Calculate Historical & Daily OI Metrics.
CODE: metrics_T = CALCULATE_OI_METRICS(current_data_block.nifty_monthly_chain, eod_data_T1.nifty_monthly_chain).
CODE: metrics_T1 = CALCULATE_OI_METRICS(eod_data_T1.nifty_monthly_chain, eod_data_T2.nifty_monthly_chain).
CODE: metrics_T2 = CALCULATE_OI_METRICS(eod_data_T2.nifty_monthly_chain, eod_data_T3.nifty_monthly_chain).
CODE: pcr_T = metrics_T.pcr; OI_MOMENTUM_VECTOR = metrics_T.momentum_vector.
3.2: Apply Regime-Aware Thresholds.
CODE: pcr_threshold_bullish = 1.15 if REGIME=='LOW_VOL' else 1.20 if REGIME=='NORMAL_VOL' else 1.50.
CODE: pcr_threshold_bearish = 0.85 if REGIME=='LOW_VOL' else 0.80 if REGIME=='NORMAL_VOL' else 0.70.
CODE: daily_bias = 'BULLISH' if pcr_T > pcr_threshold_bullish else 'BEARISH' if pcr_T < pcr_threshold_bearish else 'NEUTRAL'.
3.3: Confirm Trend (3-Day Rule).
CODE: all_pcrs = [metrics_T2.pcr, metrics_T1.pcr, pcr_T].
CODE: bullish_days = COUNT(p > pcr_threshold_bullish for p in all_pcrs).
CODE: bearish_days = COUNT(p < pcr_threshold_bearish for p in all_pcrs).
CODE: PRIMARY_TREND = 'BULLISH' if bullish_days >= 2 else 'BEARISH' if bearish_days >= 2 else 'NEUTRAL_CONSOLIDATION'.
3.4: TRACE & LOCK: TRACE: Daily_PCR(T)={pcr_T:.2f} -> Daily_Bias='{daily_bias}'. OI Momentum={OI_MOMENTUM_VECTOR:+.0f}. 3-Day Rule: {bullish_days}B/{bearish_days}B -> PRIMARY_TREND='{PRIMARY_TREND}'. [LOCKED: PRIMARY_TREND, pcr_T, OI_MOMENTUM_VECTOR]
STEP 4: CONFIRMATION ANALYSIS (BANKNIFTY MONTHLY)

4.1: Calculate Historical & Daily BankNifty PCRs.
CODE: bn_metrics_T = CALCULATE_OI_METRICS(current_data_block.banknifty_monthly_chain, eod_data_T1.banknifty_monthly_chain).
CODE: bn_metrics_T1 = CALCULATE_OI_METRICS(eod_data_T1.banknifty_monthly_chain, eod_data_T2.banknifty_monthly_chain).
CODE: bn_metrics_T2 = CALCULATE_OI_METRICS(eod_data_T2.banknifty_monthly_chain, eod_data_T3.banknifty_monthly_chain).
4.2: Confirm Trend (3-Day Rule for BankNifty).
CODE: banknifty_all_pcrs = [bn_metrics_T2.pcr, bn_metrics_T1.pcr, bn_metrics_T.pcr]. Use same thresholds from 3.2. Repeat 3.3 logic to determine BANKNIFTY_TREND.
4.3: Determine Alignment. CODE: ALIGNMENT = 'ALIGNED' if PRIMARY_TREND == BANKNIFTY_TREND else 'DIVERGENT' if PRIMARY_TREND != 'NEUTRAL_CONSOLIDATION' and BANKNIFTY_TREND != 'NEUTRAL_CONSOLIDATION' else 'NON_ALIGNED'.
4.4: TRACE & LOCK: TRACE: BankNifty Trend is '{BANKNIFTY_TREND}'. ALIGNMENT = '{ALIGNMENT}'. [LOCKED: BANKNIFTY_TREND, ALIGNMENT]
STEP 5: TACTICAL ANALYSIS (NIFTY WEEKLY)

5.0: EXPIRY DAY CHECK: CODE: parse expiry_date from current_data_block.nifty_weekly_chain. IF run_date == expiry_date, SET IS_EXPIRY_DAY = TRUE, ELSE IS_EXPIRY_DAY = FALSE.
5.1: Identify Hurdles. Use static OI from current_data_block.nifty_weekly_chain. CODE: WEEKLY_WALL = strike with MAX(Call_OI). WEEKLY_FLOOR = strike with MAX(Put_OI).
5.2: TRACE & LOCK: TRACE: WEEKLY_WALL={WEEKLY_WALL}, WEEKLY_FLOOR={WEEKLY_FLOOR}. Is Expiry Day: {IS_EXPIRY_DAY}. [LOCKED: WEEKLY_WALL, WEEKLY_FLOOR, IS_EXPIRY_DAY]
STEP 6: SCORING & SYNTHESIS

6.1: Initialize Score. Confidence_Score = 50.
6.2: Apply PVA Confirmation. CODE: IF (PRIMARY_TREND=='BULLISH' and current_data_block.nifty_monthly_spot > PVA_ANCHOR) or (PRIMARY_TREND=='BEARISH' and current_data_block.nifty_monthly_spot < PVA_ANCHOR) THEN Confidence_Score += 15.
6.3: Apply Volatility Pressure. CODE: IF VOL_PRESSURE == 'CONFIRMED_BULLISH' or VOL_PRESSURE == 'CONFIRMED_BEARISH' THEN Confidence_Score += 10.
6.4: Apply OI Momentum Confirmation. CODE: IF (PRIMARY_TREND=='BULLISH' and OI_MOMENTUM_VECTOR > 0) or (PRIMARY_TREND=='BEARISH' and OI_MOMENTUM_VECTOR < 0) THEN Confidence_Score += 5.
6.5: Apply Alignment Modifier. CODE: IF ALIGNMENT == 'ALIGNED' THEN Confidence_Score += 20. IF ALIGNMENT == 'DIVERGENT' THEN Confidence_Score -= 30.
6.6: Finalize Score. CODE: Confidence_Score = max(0, min(100, Confidence_Score)).
6.7: TRACE & LOCK: TRACE: Final Confidence Score = {Confidence_Score}. [LOCKED: CONFIDENCE_SCORE]
PART 3: OUTPUT BLOCK

IF ANALYSIS_STATUS == 'AWAITING_HISTORY', display ONLY the [TRADING_IMPLICATION] section. Otherwise, display all sections.

[LOCKED_VALUES_SUMMARY]

DATA_GAP_WARNING: [Value]
PRICE_VECTOR: [Value]
PVA_ANCHOR: [Value]
VOLATILITY_VECTOR: [Value]
VOL_PRESSURE: [Value]
REGIME: [Value]
ATM_IV: [Value]
OI_MOMENTUM_VECTOR: [Value]
PRIMARY_TREND: [Value]
BANKNIFTY_TREND: [Value]
ALIGNMENT: [Value]
WEEKLY_WALL: [Value]
WEEKLY_FLOOR: [Value]
CONFIDENCE_SCORE: [Value]
[ANALYSIS_NARRATIVE]

Primary Trend: The confirmed multi-day trend for Nifty is [LOCKED: PRIMARY_TREND], based on a 3-day analysis of Monthly OI changes.
Market Regime: The market is currently in a [LOCKED: REGIME] state, with an ATM IV of [LOCKED: ATM_IV].
Trend Conviction: The underlying force, measured by the OI Momentum Vector, was significant at [LOCKED: OI_MOMENTUM_VECTOR:+.0f], {if > 0, display 'adding weight to the bullish case.' else if < 0, display 'adding weight to the bearish case.' else display 'showing no strong directional conviction.'}
Cross-Index Confirmation: The broader market is [LOCKED: ALIGNMENT] with the primary trend, as BankNifty's trend is [LOCKED: BANKNIFTY_TREND].
Daily Price & Volatility Action: Today's price move of [LOCKED: PRICE_VECTOR:+.2f] points was [LOCKED: VOL_PRESSURE] by volatility action. The market's financial center (PVA) was at [LOCKED: PVA_ANCHOR], with spot closing {above/below} it.
Tactical Hurdles: For the short-term, expect immediate resistance at [LOCKED: WEEKLY_WALL] and support at [LOCKED: WEEKLY_FLOOR].
Key Observation: {IF ALIGNMENT=='DIVERGENT', display "The divergence with BankNifty is the most critical factor today, significantly reducing trend confidence."} {ELSE IF VOL_PRESSURE contains 'CONFIRMED', display "The alignment of price and volatility provides strong confirmation for the daily move."} {ELSE display "The strong OI buildup at key Monthly strikes was the day's defining activity."}
[TRADING_IMPLICATION]

BIAS: IF IS_INSUFFICIENT_HISTORY, display 'AWAITING_HISTORY'. Else, display [LOCKED: PRIMARY_TREND].
CONFIDENCE: IF IS_INSUFFICIENT_HISTORY, display 'N/A'. Else, display [LOCKED: CONFIDENCE_SCORE]/100.
STRATEGY:
IF PRIMARY_TREND=='BULLISH' and CONFIDENCE_SCORE > 70: Aggressive bullish positions are warranted. Use [LOCKED: WEEKLY_FLOOR] as a reference for entries or tight stops.
IF PRIMARY_TREND=='BULLISH' and CONFIDENCE_SCORE <= 70: Cautious bullish exposure. Consider waiting for price to validate support at [LOCKED: WEEKLY_FLOOR] before entry.
IF PRIMARY_TREND=='BEARISH' and CONFIDENCE_SCORE > 70: Aggressive bearish positions are warranted. Use [LOCKED: WEEKLY_WALL] as a reference for entries or tight stops.
IF PRIMARY_TREND=='BEARISH' and CONFIDENCE_SCORE <= 70: Cautious bearish exposure. Consider waiting for price to be rejected at [LOCKED: WEEKLY_WALL] before entry.
IF PRIMARY_TREND=='NEUTRAL_CONSOLIDATION': Market lacks direction. Prefer range-bound strategies or stay sidelined. Key range is [LOCKED: WEEKLY_FLOOR] - [LOCKED: WEEKLY_WALL].
IF ANALYSIS_STATUS=='AWAITING_HISTORY': Provide at least 3 historical EOD files for a full analysis.
WARNINGS: {IF IS_INSUFFICIENT_HISTORY, display "INSUFFICIENT HISTORY. Full analysis requires 3 previous EOD files."} {IF ALIGNMENT=='DIVERGENT', display "CRITICAL DIVERGENCE WITH BANKNIFTY. HIGH CAUTION ADVISED."} {IF DATA_GAP_WARNING==TRUE, display "DATA GAP DETECTED. TREND ANALYSIS MAY BE UNRELIABLE."} {IF IS_EXPIRY_DAY==TRUE, display "WEEKLY EXPIRY DAY. Tactical levels (Wall/Floor) are less reliable; refer to next week's chain for forward-looking levels."}
PART 4: MANDATORY COMPLIANCE AUDIT

[Instructions: Answer YES/NO to every check. A single NO invalidates the entire output.]

Was the IS_INSUFFICIENT_HISTORY check performed and the main analysis correctly skipped if true? [YES/NO]
Were historical EOD files parsed to calculate day-over-day metrics from 4 distinct data sets (T, T-1, T-2, T-3)? [YES/NO]
Was VOLATILITY_PRESSURE determined by comparing the Price Vector and Volatility Vector? [YES/NO]
Was OI_MOMENTUM_VECTOR calculated and used in scoring? [YES/NO]
Was PRIMARY_TREND based on a 3-day PCR rule and REGIME-aware thresholds? [YES/NO]
Was a check for the weekly expiry day (IS_EXPIRY_DAY) performed and a warning generated if true? [YES/NO]
Does the [ANALYSIS_NARRATIVE] contain ONLY values present in the [LOCKED_VALUES_SUMMARY] or input data, with conditional text strictly following the rules? [YES/NO]
[AUDIT COMPLETE. END OF PROCESS.]
"""

    # Format the complete multi-expiry data
    fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data_section = f"\n\nMULTI-EXPIRY COMPREHENSIVE ANALYSIS - FETCHED AT: {fetch_time}\n"
    data_section += format_complete_multi_expiry_data(expiry_data, pcr_values, current_nifty, banknifty_data)
    
    # Add stock data summary if available
    if stock_data:
        data_section += "\n\n" + "=" * 80 + "\n"
        data_section += "TOP 10 NIFTY STOCKS SUMMARY (Monthly Expiry)\n"
        data_section += "=" * 80 + "\n"
        data_section += f"{'SYMBOL':<15} {'WEIGHT':<10} {'PRICE':<10} {'OI PCR':<10} {'VOL PCR':<10}\n"
        data_section += "-" * 80 + "\n"
        
        for symbol, info in stock_data.items():
            price = info.get('current_price', 0)
            oi_pcr_val = info.get('oi_pcr', 0)
            vol_pcr_val = info.get('volume_pcr', 0)
            weight = info.get('weight', 0)
            
            data_section += f"{symbol:<15} {weight:<10.4f} {price:<10} {oi_pcr_val:<10.2f} {vol_pcr_val:<10.2f}\n"
        
        data_section += "=" * 80 + "\n"
    
    data_section += "\n" + "=" * 80 + "\n"
    data_section += "END OF MULTI-EXPIRY ANALYSIS DATA"
    data_section += "\n" + "=" * 80 + "\n"
    
    # Combine everything
    full_content = system_prompt + data_section
    
    # Write to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ Multi-expiry analysis data saved to: {filepath}")
        
        # Also save daily EOD state block
        print("💾 Saving daily EOD state block...")
        eod_filepath = save_daily_eod_state_block(expiry_data, pcr_values, current_nifty, banknifty_data, stock_data)
        if eod_filepath:
            print(f"✅ Daily EOD state block saved to: {eod_filepath}")
        
        # Send to Email via Resend API
        print("📧 Sending multi-expiry analysis to Email...")
        email_success = send_multi_expiry_email_with_file_content(filepath)
        if email_success:
            print("✅ Multi-expiry email sent successfully!")
        else:
            print("❌ Failed to send multi-expiry email")
        
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving multi-expiry analysis data: {e}")
        return ""