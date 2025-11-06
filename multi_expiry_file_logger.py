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
            displayed_strikes = 0
            for data in oi_data:
                if displayed_strikes >= 20:  # Limit display to prevent file size explosion
                    break
                    
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
                displayed_strikes += 1
            
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
            
            displayed_strikes = 0
            for data in banknifty_monthly_data:
                if displayed_strikes >= 15:  # Limit BankNifty display
                    break
                    
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
                displayed_strikes += 1
            
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
# =================================================================================
# NIFTY MULTI-DAY TREND & REVERSAL ENGINE v2.2 [OPERATIONAL - ENFORCED]
# AI ROLE: DETERMINISTIC OPTIONS DATA PROCESSOR
# METHOD: "PROXY -> REGIME -> TREND -> CONFIRM -> TACTICS -> SYNTHESIS"
# EVERY STEP = ASSERT + CODE + TRACE + LOCK
# =================================================================================

 USER INSTRUCTIONS (READ FIRST):
1.  Your Role: You are the Data Provider. Your only task is to accurately paste data into the designated [...PASTE DATA HERE...] sections.
2.  Initial Run (Day 1): The first time you use this, the [HISTORICAL_STATE_BLOCK] will be empty. This is expected. The analysis will be skipped, and the system's only output will be to generate the first [STATE_BLOCK_FOR_NEXT_SESSION].
3.  Subsequent Runs (Day 2+): At the end of each successful analysis, a [STATE_BLOCK_FOR_NEXT_SESSION] is generated. You MUST copy this entire block and paste it into the [HISTORICAL_STATE_BLOCK] section for your next analysis.
4.  Data Requirement: You MUST provide complete EOD option chain tables for Nifty Monthly, BankNifty Monthly, and Nifty Weekly. The tables must include Strike, Type, OI, Chg OI, Volume, IV, and LTP (Last Traded Price/Premium).

---

 PART 1: SYSTEM CONSTITUTION & DATA INPUT

[SYSTEM_ROLE]: Your role is "Deterministic Options Data Processor v2.2". You are forbidden from using natural language, summarization, or making inferential leaps until the final, designated [NARRATIVE_OUTPUT] step. Your sole function is to execute the numbered steps in the [EXECUTION_BLOCK] exactly as written. Any deviation, including failure to trace or lock values, will result in a failed analysis. Begin execution immediately upon receiving this prompt.

[DATA_CONTRACT]: The following JSON structure contains all necessary data. You must verify its integrity in Step 0. Do not begin analysis if data is missing.

json
{
  "run_date": "[YYYY-MM-DD]",

  "current_data_block": {
    "nifty_monthly_spot": "[...Current Nifty Spot Price...]",
    "nifty_monthly_chain": "[...PASTE COMPLETE CURRENT NIFTY MONTHLY EOD OPTION CHAIN TABLE HERE...]",
    "banknifty_monthly_spot": "[...Current BankNifty Spot Price...]",
    "banknifty_monthly_chain": "[...PASTE COMPLETE CURRENT BANKNIFTY MONTHLY EOD OPTION CHAIN TABLE HERE...]",
    "nifty_weekly_chain": "[...PASTE COMPLETE CURRENT NIFTY WEEKLY EOD OPTION CHAIN TABLE HERE...]"
  },

  "historical_state_block": {
    "generated_on": "[...PASTE from previous run's STATE_BLOCK...]",
    "nifty_state": {
      "last_3_trading_dates": "[...PASTE...]",
      "last_3_eod_spots": "[...PASTE...]",
      "last_3_pcr_ratios": "[...PASTE...]",
      "previous_atm_straddle_price": "[...PASTE...]",
      "previous_eod_oi": {
        "[STRIKE]_[TYPE]": "[OI_VALUE]",
        "...": "..."
      }
    },
    "banknifty_state": {
      "last_3_pcr_ratios": "[...PASTE...]",
      "previous_eod_oi": {
        "[STRIKE]_[TYPE]": "[OI_VALUE]",
        "...": "..."
      }
    }
  }
}


---

 PART 2: THE EXECUTION BLOCK (DO NOT MODIFY)

STEP 0: DATA INTEGRITY & INITIALIZATION
- 0.1: ASSERT: current_data_block and all its sub-fields are present and not empty.
- 0.2: CHECK FOR INITIAL RUN: CODE: IF historical_state_block.generated_on is empty THEN IS_INITIAL_RUN = TRUE ELSE IS_INITIAL_RUN = FALSE.
- 0.3: TRACE: TRACE: IS_INITIAL_RUN = {IS_INITIAL_RUN}.
- 0.4: HALT FOR INITIALIZATION (IF APPLICABLE): IF IS_INITIAL_RUN == TRUE, SET ANALYSIS_STATUS = 'INITIALIZING'. Skip all steps from 1 to 6 and proceed directly to PART 3.
- 0.5: DATA GAP CHECK: days_since_last_run = run_date - historical_state_block.generated_on. If days_since_last_run > 4 (to account for weekends), set DATA_GAP_WARNING = TRUE else DATA_GAP_WARNING = FALSE.
- 0.6: TRACE & LOCK: TRACE: Data Integrity Checks Passed. Data Gap Warning: {DATA_GAP_WARNING}. [LOCKED: DATA_GAP_WARNING]

STEP 1: GENERATE CORE PROXIES (NIFTY MONTHLY)
- 1.1: Calculate Price Vector.
    - CODE: previous_spot = historical_state_block.nifty_state.last_3_eod_spots[-1].
    - CODE: PRICE_VECTOR = current_data_block.nifty_monthly_spot - previous_spot.
- 1.2: Calculate Premium-Volume Anchor (PVA).
    - CODE: For each strike in nifty_monthly_chain, pva_score = (Call_Volume * Call_LTP) + (Put_Volume * Put_LTP).
    - CODE: PVA_ANCHOR = strike with MAX(pva_score).
- 1.3: Calculate Volatility Vector.
    - CODE: Find ATM_STRIKE closest to nifty_monthly_spot.
    - CODE: current_atm_straddle_price = Premium(ATM_STRIKE, 'CALL') + Premium(ATM_STRIKE, 'PUT').
    - CODE: VOLATILITY_VECTOR = current_atm_straddle_price - historical_state_block.nifty_state.previous_atm_straddle_price.
- 1.4: TRACE & LOCK: TRACE: PRICE_VECTOR={PRICE_VECTOR:+.2f}, PVA_ANCHOR={PVA_ANCHOR}, VOLATILITY_VECTOR={VOLATILITY_VECTOR:+.2f}. [LOCKED: PRICE_VECTOR, PVA_ANCHOR, VOLATILITY_VECTOR, current_atm_straddle_price]

STEP 2: DETERMINE MARKET REGIME (NIFTY MONTHLY)
- 2.1: Find ATM IV. CODE: ATM_IV = IV of ATM_STRIKE Call.
- 2.2: Classify Regime.
    - CODE: IF ATM_IV < 13, REGIME = 'LOW_VOL'.
    - CODE: IF 13 <= ATM_IV <= 18, REGIME = 'NORMAL_VOL'.
    - CODE: IF ATM_IV > 18, REGIME = 'HIGH_VOL'.
- 2.3: TRACE & LOCK: TRACE: ATM_IV={ATM_IV:.2f} -> REGIME='{REGIME}'. [LOCKED: REGIME, ATM_IV]

STEP 3: PRIMARY TREND ANALYSIS (NIFTY MONTHLY)
- 3.1: Calculate Daily Change in OI.
    - CODE: For each strike, Chg_OI = current_OI - historical_state_block.nifty_state.previous_eod_oi.get(strike, 0).
    - CODE: total_put_chg_oi = SUM(max(0, Chg_OI) for all Puts).
    - CODE: total_call_chg_oi = SUM(max(0, Chg_OI) for all Calls).
- 3.2: Calculate Daily PCR. CODE: daily_pcr = total_put_chg_oi / total_call_chg_oi if total_call_chg_oi > 0 else 999.
- 3.3: Apply Regime-Aware Thresholds.
    - CODE: pcr_threshold_bullish = 1.15 if REGIME=='LOW_VOL' else 1.20 if REGIME=='NORMAL_VOL' else 1.50.
    - CODE: pcr_threshold_bearish = 0.85 if REGIME=='LOW_VOL' else 0.80 if REGIME=='NORMAL_VOL' else 0.70.
    - CODE: daily_bias = 'BULLISH' if daily_pcr > pcr_threshold_bullish else 'BEARISH' if daily_pcr < pcr_threshold_bearish else 'NEUTRAL'.
- 3.4: Confirm Trend (3-Day Rule).
    - CODE: all_pcrs = historical_state_block.nifty_state.last_3_pcr_ratios[1:] + [daily_pcr].
    - CODE: bullish_days = COUNT(p > pcr_threshold_bullish for p in all_pcrs).
    - CODE: bearish_days = COUNT(p < pcr_threshold_bearish for p in all_pcrs).
    - CODE: PRIMARY_TREND = 'BULLISH' if bullish_days >= 2 else 'BEARISH' if bearish_days >= 2 else 'NEUTRAL_CONSOLIDATION'.
- 3.5: TRACE & LOCK: TRACE: Daily_PCR={daily_pcr:.2f} -> Daily_Bias='{daily_bias}'. 3-Day Rule: {bullish_days} bullish, {bearish_days} bearish -> PRIMARY_TREND='{PRIMARY_TREND}'. [LOCKED: PRIMARY_TREND, daily_pcr, all_pcrs]

STEP 4: CONFIRMATION ANALYSIS (BANKNIFTY MONTHLY)
- 4.1: Repeat Step 3.1-3.3 for BankNifty data. CODE: Calculate banknifty_daily_pcr and banknifty_daily_bias.
- 4.2: Confirm Trend (3-Day Rule). CODE: banknifty_all_pcrs = historical_state_block.banknifty_state.last_3_pcr_ratios[1:] + [banknifty_daily_pcr]. Repeat 3.4 logic to determine BANKNIFTY_TREND.
- 4.3: Determine Alignment. CODE: ALIGNMENT = 'ALIGNED' if PRIMARY_TREND == BANKNIFTY_TREND else 'DIVERGENT' if PRIMARY_TREND != 'NEUTRAL_CONSOLIDATION' and BANKNIFTY_TREND != 'NEUTRAL_CONSOLIDATION' else 'NON_ALIGNED'.
- 4.4: TRACE & LOCK: TRACE: BankNifty Trend is '{BANKNIFTY_TREND}'. ALIGNMENT = '{ALIGNMENT}'. [LOCKED: BANKNIFTY_TREND, ALIGNMENT, banknifty_all_pcrs]

STEP 5: TACTICAL ANALYSIS (NIFTY WEEKLY)
- 5.1: Identify Hurdles. Use static OI from the nifty_weekly_chain.
    - CODE: WEEKLY_WALL = strike with MAX(Call_OI).
    - CODE: WEEKLY_FLOOR = strike with MAX(Put_OI).
- 5.2: TRACE & LOCK: TRACE: WEEKLY_WALL={WEEKLY_WALL}, WEEKLY_FLOOR={WEEKLY_FLOOR}. [LOCKED: WEEKLY_WALL, WEEKLY_FLOOR]

STEP 6: SCORING & SYNTHESIS
- 6.1: Initialize Score. Confidence_Score = 50.
- 6.2: Apply PVA Confirmation.
    - CODE: IF (PRIMARY_TREND=='BULLISH' and nifty_monthly_spot > PVA_ANCHOR) or (PRIMARY_TREND=='BEARISH' and nifty_monthly_spot < PVA_ANCHOR) THEN Confidence_Score += 15.
- 6.3: Apply Volatility Vector Context.
    - CODE: IF (PRICE_VECTOR > 0 and VOLATILITY_VECTOR < 0) or (PRICE_VECTOR < 0 and VOLATILITY_VECTOR > 0) THEN Confidence_Score += 10.
- 6.4: Apply Alignment Modifier.
    - CODE: IF ALIGNMENT == 'ALIGNED' THEN Confidence_Score += 20.
    - CODE: IF ALIGNMENT == 'DIVERGENT' THEN Confidence_Score -= 30.
- 6.5: Finalize Score. CODE: Confidence_Score = max(0, min(100, Confidence_Score)).
- 6.6: TRACE & LOCK: TRACE: Final Confidence Score = {Confidence_Score}. [LOCKED: CONFIDENCE_SCORE]

---

 PART 3: OUTPUT BLOCK

IF ANALYSIS_STATUS == 'INITIALIZING', display ONLY the [TRADING_IMPLICATION] and [STATE_BLOCK_FOR_NEXT_SESSION] sections. Otherwise, display all sections.

[LOCKED_VALUES_SUMMARY]
- DATA_GAP_WARNING: [Value]
- PRICE_VECTOR: [Value]
- PVA_ANCHOR: [Value]
- VOLATILITY_VECTOR: [Value]
- REGIME: [Value]
- ATM_IV: [Value]
- PRIMARY_TREND: [Value]
- BANKNIFTY_TREND: [Value]
- ALIGNMENT: [Value]
- WEEKLY_WALL: [Value]
- WEEKLY_FLOOR: [Value]
- CONFIDENCE_SCORE: [Value]

[ANALYSIS_NARRATIVE]
- Primary Trend: The confirmed multi-day trend for Nifty is [LOCKED: PRIMARY_TREND], based on a 3-day analysis of Monthly OI.
- Market Regime: The market is currently in a [LOCKED: REGIME] state, with an ATM IV of [LOCKED: ATM_IV].
- Cross-Index Confirmation: The broader market is [LOCKED: ALIGNMENT] with the primary trend, as BankNifty's trend is [LOCKED: BANKNIFTY_TREND].
- Daily Price Action: Today's price move was [LOCKED: PRICE_VECTOR:+.2f] points. The market's financial center of gravity (PVA) was the [LOCKED: PVA_ANCHOR] strike, with the spot closing {above/below} it.
- Volatility Context: The Volatility Vector was [LOCKED: VOLATILITY_VECTOR:+.2f], indicating {rising/falling} fear relative to the price move.
- Tactical Hurdles: For the short-term, expect immediate resistance at the [LOCKED: WEEKLY_WALL] and support at the [LOCKED: WEEKLY_FLOOR].

[TRADING_IMPLICATION]
- BIAS: IF IS_INITIAL_RUN, display 'AWAITING_DATA'. Else, display [LOCKED: PRIMARY_TREND].
- CONFIDENCE: IF IS_INITIAL_RUN, display 'N/A'. Else, display [LOCKED: CONFIDENCE_SCORE]/100.
- STRATEGY:
    - If BULLISH: Look for long opportunities, using the [LOCKED: WEEKLY_FLOOR] as a potential entry zone or stop-loss reference.
    - If BEARISH: Look for short opportunities, using the [LOCKED: WEEKLY_WALL] as a potential entry zone or stop-loss reference.
    - If NEUTRAL: Expect range-bound activity between [LOCKED: WEEKLY_FLOOR] and [LOCKED: WEEKLY_WALL]. Wait for a clear trend to re-emerge.
- WARNINGS: {IF IS_INITIAL_RUN, display "INITIALIZATION RUN COMPLETE. Please use the generated State Block for your next session."} {IF ALIGNMENT=='DIVERGENT', display "CRITICAL DIVERGENCE WITH BANKNIFTY. HIGH CAUTION ADVISED."} {IF DATA_GAP_WARNING==TRUE, display "DATA GAP DETECTED. OI CHANGES REFLECT MULTIPLE DAYS; MAGNITUDE MAY BE INFLATED."}

[STATE_BLOCK_FOR_NEXT_SESSION] (COPY THIS ENTIRE BLOCK FOR YOUR NEXT RUN)
json
{
  "generated_on": "[Value of 'run_date' from input]",
  "nifty_state": {
    "last_3_trading_dates": "[CODE: IF IS_INITIAL_RUN, create list with 3 copies of 'run_date'. Else, create list using historical_state_block.nifty_state.last_3_trading_dates[1:] + [run_date]]",
    "last_3_eod_spots": "[CODE: IF IS_INITIAL_RUN, create list with 3 copies of 'nifty_monthly_spot'. Else, create list using historical_state_block.nifty_state.last_3_eod_spots[1:] + [nifty_monthly_spot]]",
    "last_3_pcr_ratios": "[CODE: IF IS_INITIAL_RUN, create list [1.0, 1.0, 1.0]. Else, use value of [LOCKED: all_pcrs]]",
    "previous_atm_straddle_price": "[CODE: IF IS_INITIAL_RUN, calculate current_atm_straddle_price. Else, use value of [LOCKED: current_atm_straddle_price]]",
    "previous_eod_oi": {
      "...": "..." // Generate a new key-value map of 'strike_type': 'current_oi' from the nifty_monthly_chain
    }
  },
  "banknifty_state": {
    "last_3_pcr_ratios": "[CODE: IF IS_INITIAL_RUN, create list [1.0, 1.0, 1.0]. Else, use value of [LOCKED: banknifty_all_pcrs]]",
    "previous_eod_oi": {
      "...": "..." // Generate a new key-value map for BankNifty
    }
  }
}


---

 PART 4: MANDATORY COMPLIANCE AUDIT

[Instructions: Answer YES/NO to every check. A single NO invalidates the entire output.]
1.  Was the IS_INITIAL_RUN check performed and the main analysis correctly skipped if true? [YES/NO]
2.  Was PVA_ANCHOR used for confirmation instead of raw volume? [YES/NO]
3.  Was the REGIME correctly identified and used to select PCR thresholds? [YES/NO]
4.  Was the PRIMARY_TREND based on a 3-day rule using Monthly Nifty data ONLY? [YES/NO]
5.  Was the ALIGNMENT check with BankNifty performed and the score adjusted for divergence? [YES/NO]
6.  Was WEEKLY_WALL/FLOOR derived from static Weekly OI only? [YES/NO]
7.  Does the [ANALYSIS_NARRATIVE] contain ONLY values present in the [LOCKED_VALUES_SUMMARY] or input data? [YES/NO]
8.  Was the [STATE_BLOCK_FOR_NEXT_SESSION] correctly generated with EXPLICIT logic for both initial and subsequent runs? [YES/NO]

[AUDIT COMPLETE. END OF PROCESS.]

[HISTORICAL_STATE_BLOCK]
{
  "generated_on": "2025-11-04",
  "nifty_state": {
    "last_3_trading_dates": ["2025-11-04", "2025-11-04", "2025-11-04"],
    "last_3_eod_spots": [25598, 25598, 25598],
    "last_3_pcr_ratios": [1.0, 1.0, 1.0],
    "previous_atm_straddle_price": 0.2,
    "previous_eod_oi": {
      "22850_CALL": "28",
      "22850_PUT": "19819",
      "22900_CALL": "5",
      "22900_PUT": "8175",
      "22950_CALL": "10",
      "22950_PUT": "5736",
      "23000_CALL": "58",
      "23000_PUT": "11419",
      "23050_CALL": "27",
      "23050_PUT": "247",
      "23100_CALL": "7",
      "23100_PUT": "904",
      "23150_CALL": "10",
      "23150_PUT": "759",
      "23200_CALL": "2",
      "23200_PUT": "1251",
      "23250_CALL": "14",
      "23250_PUT": "570",
      "23300_CALL": "16",
      "23300_PUT": "7420",
      "23350_CALL": "12",
      "23350_PUT": "1118",
      "23400_CALL": "20",
      "23400_PUT": "8787",
      "23450_CALL": "15",
      "23450_PUT": "406",
      "23500_CALL": "61",
      "23500_PUT": "12713",
      "23550_CALL": "4",
      "23550_PUT": "767",
      "23600_CALL": "12",
      "23600_PUT": "2557",
      "23650_CALL": "3",
      "23650_PUT": "1222",
      "23700_CALL": "32",
      "23700_PUT": "2961",
      "23750_CALL": "16",
      "23750_PUT": "1554",
      "23800_CALL": "1",
      "23800_PUT": "3335",
      "23850_CALL": "3",
      "23850_PUT": "1233",
      "23900_CALL": "1",
      "23900_PUT": "1900",
      "23950_CALL": "8",
      "23950_PUT": "1370",
      "24000_CALL": "288",
      "24000_PUT": "37129",
      "24050_CALL": "37",
      "24050_PUT": "1163",
      "24100_CALL": "12",
      "24100_PUT": "2542",
      "24150_CALL": "4",
      "24150_PUT": "1730",
      "24200_CALL": "21",
      "24200_PUT": "2354",
      "24250_CALL": "3",
      "24250_PUT": "1543",
      "24300_CALL": "8",
      "24300_PUT": "2093",
      "24350_CALL": "2",
      "24350_PUT": "5088",
      "24400_CALL": "13",
      "24400_PUT": "7129",
      "24450_CALL": "2",
      "24450_PUT": "3331",
      "24500_CALL": "110",
      "24500_PUT": "36586",
      "24550_CALL": "12",
      "24550_PUT": "8196",
      "24600_CALL": "51",
      "24600_PUT": "12268",
      "24650_CALL": "11",
      "24650_PUT": "6692",
      "24700_CALL": "88",
      "24700_PUT": "26286",
      "24750_CALL": "34",
      "24750_PUT": "8752",
      "24800_CALL": "173",
      "24800_PUT": "33064",
      "24850_CALL": "57",
      "24850_PUT": "15948",
      "24900_CALL": "351",
      "24900_PUT": "43287",
      "24950_CALL": "95",
      "24950_PUT": "17534",
      "25000_CALL": "920",
      "25000_PUT": "124249",
      "25050_CALL": "50",
      "25050_PUT": "18187",
      "25100_CALL": "288",
      "25100_PUT": "50277",
      "25150_CALL": "236",
      "25150_PUT": "24924",
      "25200_CALL": "1267",
      "25200_PUT": "60437",
      "25250_CALL": "249",
      "25250_PUT": "30320",
      "25300_CALL": "1281",
      "25300_PUT": "70819",
      "25350_CALL": "823",
      "25350_PUT": "35909",
      "25400_CALL": "2428",
      "25400_PUT": "70594",
      "25450_CALL": "3536",
      "25450_PUT": "55175",
      "25500_CALL": "15369",
      "25500_PUT": "99527",
      "25550_CALL": "44416",
      "25550_PUT": "139668",
      "25600_CALL": "296925",
      "25600_PUT": "301878",
      "25650_CALL": "218899",
      "25650_PUT": "55236",
      "25700_CALL": "191815",
      "25700_PUT": "67727",
      "25750_CALL": "107027",
      "25750_PUT": "19291",
      "25800_CALL": "163127",
      "25800_PUT": "13559",
      "25850_CALL": "63330",
      "25850_PUT": "6121",
      "25900_CALL": "90784",
      "25900_PUT": "15428",
      "25950_CALL": "58422",
      "25950_PUT": "3902",
      "26000_CALL": "130460",
      "26000_PUT": "22846",
      "26050_CALL": "60159",
      "26050_PUT": "2889",
      "26100_CALL": "101414",
      "26100_PUT": "8696",
      "26150_CALL": "63255",
      "26150_PUT": "3169",
      "26200_CALL": "125335",
      "26200_PUT": "4361",
      "26250_CALL": "60960",
      "26250_PUT": "1789",
      "26300_CALL": "93026",
      "26300_PUT": "1707",
      "26350_CALL": "34187",
      "26350_PUT": "299",
      "26400_CALL": "70041",
      "26400_PUT": "752",
      "26450_CALL": "23711",
      "26450_PUT": "350",
      "26500_CALL": "107834",
      "26500_PUT": "1319",
      "26550_CALL": "20556",
      "26550_PUT": "289",
      "26600_CALL": "43214",
      "26600_PUT": "610",
      "26650_CALL": "13247",
      "26650_PUT": "225",
      "26700_CALL": "74675",
      "26700_PUT": "264",
      "26750_CALL": "24235",
      "26750_PUT": "107",
      "26800_CALL": "59110",
      "26800_PUT": "194",
      "26850_CALL": "18276",
      "26850_PUT": "97",
      "26900_CALL": "40461",
      "26900_PUT": "141",
      "26950_CALL": "13356",
      "26950_PUT": "29",
      "27000_CALL": "92901",
      "27000_PUT": "472",
      "27050_CALL": "12849",
      "27050_PUT": "19",
      "27100_CALL": "32688",
      "27100_PUT": "47",
      "27150_CALL": "13393",
      "27150_PUT": "3",
      "27200_CALL": "19650",
      "27200_PUT": "13",
      "27250_CALL": "5769",
      "27250_PUT": "6",
      "27300_CALL": "22350",
      "27300_PUT": "6",
      "27350_CALL": "9711",
      "27350_PUT": "5",
      "27400_CALL": "28212",
      "27400_PUT": "7",
      "27450_CALL": "1686",
      "27450_PUT": "5",
      "27500_CALL": "34529",
      "27500_PUT": "13",
      "27550_CALL": "1893",
      "27550_PUT": "3",
      "27600_CALL": "24208",
      "27600_PUT": "3",
      "27650_CALL": "1964",
      "27650_PUT": "4",
      "27700_CALL": "12021",
      "27700_PUT": "48",
      "27750_CALL": "3264",
      "27750_PUT": "0",
      "27800_CALL": "12426",
      "27800_PUT": "0"
    }
  },
  "banknifty_state": {
    "last_3_pcr_ratios": [1.0, 1.0, 1.0],
    "previous_eod_oi": {
      "46000_CALL": "8",
      "46000_PUT": "1069",
      "46500_CALL": "1",
      "46500_PUT": "669",
      "47000_CALL": "1",
      "47000_PUT": "1103",
      "47500_CALL": "0",
      "47500_PUT": "357",
      "48000_CALL": "2302",
      "48000_PUT": "2105",
      "48500_CALL": "21",
      "48500_PUT": "210",
      "48700_CALL": "0",
      "48700_PUT": "20",
      "48800_CALL": "0",
      "48800_PUT": "0",
      "48900_CALL": "0",
      "48900_PUT": "0",
      "49000_CALL": "529",
      "49000_PUT": "981",
      "49100_CALL": "0",
      "49100_PUT": "89",
      "49200_CALL": "0",
      "49200_PUT": "0",
      "49300_CALL": "0",
      "49300_PUT": "0",
      "49400_CALL": "0",
      "49400_PUT": "14",
      "49500_CALL": "10",
      "49500_PUT": "382",
      "49600_CALL": "1",
      "49600_PUT": "0",
      "49700_CALL": "1",
      "49700_PUT": "0",
      "49800_CALL": "1",
      "49800_PUT": "30",
      "49900_CALL": "2",
      "49900_PUT": "0",
      "50000_CALL": "2764",
      "50000_PUT": "5797",
      "50100_CALL": "1",
      "50100_PUT": "0",
      "50200_CALL": "2",
      "50200_PUT": "0",
      "50300_CALL": "4",
      "50300_PUT": "20",
      "50400_CALL": "2",
      "50400_PUT": "0",
      "50500_CALL": "30",
      "50500_PUT": "237",
      "50600_CALL": "2",
      "50600_PUT": "0",
      "50700_CALL": "3",
      "50700_PUT": "0",
      "50800_CALL": "2",
      "50800_PUT": "0",
      "50900_CALL": "8",
      "50900_PUT": "1",
      "51000_CALL": "635",
      "51000_PUT": "2882",
      "51100_CALL": "9",
      "51100_PUT": "0",
      "51200_CALL": "8",
      "51200_PUT": "0",
      "51300_CALL": "11",
      "51300_PUT": "0",
      "51400_CALL": "11",
      "51400_PUT": "0",
      "51500_CALL": "27",
      "51500_PUT": "431",
      "51600_CALL": "12",
      "51600_PUT": "2",
      "51700_CALL": "16",
      "51700_PUT": "4",
      "51800_CALL": "17",
      "51800_PUT": "0",
      "51900_CALL": "17",
      "51900_PUT": "2",
      "52000_CALL": "1536",
      "52000_PUT": "3175",
      "52100_CALL": "23",
      "52100_PUT": "21",
      "52200_CALL": "17",
      "52200_PUT": "0",
      "52300_CALL": "18",
      "52300_PUT": "0",
      "52400_CALL": "17",
      "52400_PUT": "0",
      "52500_CALL": "30",
      "52500_PUT": "1430",
      "52600_CALL": "22",
      "52600_PUT": "0",
      "52700_CALL": "19",
      "52700_PUT": "0",
      "52800_CALL": "18",
      "52800_PUT": "0",
      "52900_CALL": "17",
      "52900_PUT": "0",
      "53000_CALL": "659",
      "53000_PUT": "7730",
      "53100_CALL": "15",
      "53100_PUT": "87",
      "53200_CALL": "23",
      "53200_PUT": "74",
      "53300_CALL": "14",
      "53300_PUT": "47",
      "53400_CALL": "21",
      "53400_PUT": "60",
      "53500_CALL": "580",
      "53500_PUT": "7822",
      "53600_CALL": "20",
      "53600_PUT": "179",
      "53700_CALL": "21",
      "53700_PUT": "82",
      "53800_CALL": "43",
      "53800_PUT": "265",
      "53900_CALL": "21",
      "53900_PUT": "214",
      "54000_CALL": "1868",
      "54000_PUT": "12162",
      "54100_CALL": "22",
      "54100_PUT": "412",
      "54200_CALL": "111",
      "54200_PUT": "137",
      "54300_CALL": "28",
      "54300_PUT": "390",
      "54400_CALL": "139",
      "54400_PUT": "184",
      "54500_CALL": "560",
      "54500_PUT": "6137",
      "54600_CALL": "22",
      "54600_PUT": "560",
      "54700_CALL": "57",
      "54700_PUT": "480",
      "54800_CALL": "61",
      "54800_PUT": "402",
      "54900_CALL": "90",
      "54900_PUT": "486",
      "55000_CALL": "3305",
      "55000_PUT": "18308",
      "55100_CALL": "27",
      "55100_PUT": "492",
      "55200_CALL": "21",
      "55200_PUT": "1072",
      "55300_CALL": "32",
      "55300_PUT": "514",
      "55400_CALL": "185",
      "55400_PUT": "504",
      "55500_CALL": "2691",
      "55500_PUT": "8822",
      "55600_CALL": "63",
      "55600_PUT": "2047",
      "55700_CALL": "35",
      "55700_PUT": "1272",
      "55800_CALL": "60",
      "55800_PUT": "1390",
      "55900_CALL": "78",
      "55900_PUT": "1420",
      "56000_CALL": "4509",
      "56000_PUT": "20662",
      "56100_CALL": "42",
      "56100_PUT": "1463",
      "56200_CALL": "116",
      "56200_PUT": "1305",
      "56300_CALL": "85",
      "56300_PUT": "1485",
      "56400_CALL": "84",
      "56400_PUT": "1150",
      "56500_CALL": "2195",
      "56500_PUT": "12629",
      "56600_CALL": "142",
      "56600_PUT": "1749",
      "56700_CALL": "238",
      "56700_PUT": "1770",
      "56800_CALL": "235",
      "56800_PUT": "2402",
      "56900_CALL": "234",
      "56900_PUT": "1244",
      "57000_CALL": "27952",
      "57000_PUT": "36004",
      "57100_CALL": "260",
      "57100_PUT": "1896",
      "57200_CALL": "373",
      "57200_PUT": "2411",
      "57300_CALL": "228",
      "57300_PUT": "1605",
      "57400_CALL": "497",
      "57400_PUT": "2371",
      "57500_CALL": "4946",
      "57500_PUT": "14489",
      "57600_CALL": "1388",
      "57600_PUT": "2783",
      "57700_CALL": "1863",
      "57700_PUT": "3667",
      "57800_CALL": "3338",
      "57800_PUT": "5997",
      "57900_CALL": "4329",
      "57900_PUT": "4688",
      "58000_CALL": "36637",
      "58000_PUT": "49036",
      "58100_CALL": "6557",
      "58100_PUT": "3531",
      "58200_CALL": "10047",
      "58200_PUT": "5140",
      "58300_CALL": "6815",
      "58300_PUT": "4814",
      "58400_CALL": "5068",
      "58400_PUT": "2233",
      "58500_CALL": "27987",
      "58500_PUT": "14320",
      "58600_CALL": "4187",
      "58600_PUT": "1927",
      "58700_CALL": "3476",
      "58700_PUT": "1091",
      "58800_CALL": "4281",
      "58800_PUT": "2075",
      "58900_CALL": "3529",
      "58900_PUT": "1381",
      "59000_CALL": "26187",
      "59000_PUT": "7769",
      "59100_CALL": "2511",
      "59100_PUT": "1716",
      "59200_CALL": "2733",
      "59200_PUT": "257",
      "59300_CALL": "2352",
      "59300_PUT": "175",
      "59400_CALL": "1933",
      "59400_PUT": "108",
      "59500_CALL": "16112",
      "59500_PUT": "1200",
      "59600_CALL": "1533",
      "59600_PUT": "132",
      "59700_CALL": "2149",
      "59700_PUT": "129",
      "59800_CALL": "2189",
      "59800_PUT": "86",
      "59900_CALL": "1399",
      "59900_PUT": "59",
      "60000_CALL": "31575",
      "60000_PUT": "3411",
      "60100_CALL": "1480",
      "60100_PUT": "32",
      "60200_CALL": "2761",
      "60200_PUT": "21",
      "60300_CALL": "1494",
      "60300_PUT": "16",
      "60400_CALL": "1472",
      "60400_PUT": "39",
      "60500_CALL": "11993",
      "60500_PUT": "44",
      "60600_CALL": "821",
      "60600_PUT": "23",
      "60700_CALL": "905",
      "60700_PUT": "15",
      "60800_CALL": "907",
      "60800_PUT": "23",
      "60900_CALL": "646",
      "60900_PUT": "13",
      "61000_CALL": "16995",
      "61000_PUT": "677",
      "61100_CALL": "2769",
      "61100_PUT": "6",
      "61200_CALL": "1526",
      "61200_PUT": "11",
      "61300_CALL": "628",
      "61300_PUT": "7",
      "61400_CALL": "577",
      "61400_PUT": "7",
      "61500_CALL": "7497",
      "61500_PUT": "22",
      "61600_CALL": "435",
      "61600_PUT": "15",
      "61700_CALL": "320",
      "61700_PUT": "8",
      "61800_CALL": "518",
      "61800_PUT": "10",
      "61900_CALL": "530",
      "61900_PUT": "9",
      "62000_CALL": "19111",
      "62000_PUT": "1597",
      "62100_CALL": "950",
      "62100_PUT": "7",
      "62200_CALL": "501",
      "62200_PUT": "6",
      "62300_CALL": "211",
      "62300_PUT": "9",
      "62400_CALL": "444",
      "62400_PUT": "8",
      "62500_CALL": "6492",
      "62500_PUT": "14",
      "62600_CALL": "332",
      "62600_PUT": "13",
      "62700_CALL": "129",
      "62700_PUT": "9",
      "62800_CALL": "239",
      "62800_PUT": "6",
      "62900_CALL": "45",
      "62900_PUT": "9",
      "63000_CALL": "12001",
      "63000_PUT": "1383",
      "63100_CALL": "278",
      "63100_PUT": "0",
      "63200_CALL": "114",
      "63200_PUT": "0",
      "63300_CALL": "58",
      "63300_PUT": "0",
      "63400_CALL": "16",
      "63400_PUT": "0",
      "63500_CALL": "1686",
      "63500_PUT": "86",
      "64000_CALL": "4279",
      "64000_PUT": "96",
      "64500_CALL": "1351",
      "64500_PUT": "27",
      "65000_CALL": "6386",
      "65000_PUT": "999",
      "65500_CALL": "4644",
      "65500_PUT": "2",
      "66000_CALL": "3598",
      "66000_PUT": "0"
    }
  }
}
[HISTORICAL_STATE_BLOCK END]
=================================================================================
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