import os
import datetime
from typing import Dict, Any, List
import urllib3

from nifty_config import format_greek_value, AI_LOGS_DIR, RESEND_API_KEY, EMAIL_TO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------------------------------------------------
# EMAIL (RESEND) INITIALIZATION
# ---------------------------------------------------------
try:
    import resend
    RESEND_AVAILABLE = True
    resend.api_key = RESEND_API_KEY
    print("✅ Resend module loaded successfully")
except ImportError:
    RESEND_AVAILABLE = False
    print("⚠️ Resend module not installed. Email functionality disabled.")
except Exception as e:
    RESEND_AVAILABLE = False
    print(f"⚠️ Resend configuration error: {e}")

# ---------------------------------------------------------
# HELPER: ROW FORMATTER (Applies DRY Principle)
# ---------------------------------------------------------
def format_strike_row(data: dict) -> str:
    """Formats a single options chain row for text logs."""
    strike_price = data['strike_price']
    
    # CE Data
    ce_oi = str(data['ce_change_oi']).rjust(10)
    ce_vol = str(data['ce_volume']).rjust(10)
    ce_ltp = f"{data['ce_ltp']:.1f}".rjust(8) if data['ce_ltp'] else "0".rjust(8)
    ce_oi_total = str(data['ce_oi']).rjust(10)
    ce_iv = format_greek_value(data['ce_iv'], 1).rjust(7)
    
    # PE Data
    pe_oi = str(data['pe_change_oi']).rjust(10)
    pe_vol = str(data['pe_volume']).rjust(10)
    pe_ltp = f"{data['pe_ltp']:.1f}".rjust(8) if data['pe_ltp'] else "0".rjust(8)
    pe_oi_total = str(data['pe_oi']).rjust(10)
    pe_iv = format_greek_value(data['pe_iv'], 1).rjust(7)
    
    # Diff
    chg_oi_diff = str(data['ce_change_oi'] - data['pe_change_oi']).rjust(16)
    
    return (
        f"{ce_oi}  {ce_vol}  {ce_ltp}  {ce_oi_total}  {ce_iv}  |  "
        f"{str(strike_price).center(9)}  |  "
        f"{pe_oi}  {pe_vol}  {pe_ltp}  {pe_oi_total}  {pe_iv}  |  "
        f"{chg_oi_diff}\n"
    )

# ---------------------------------------------------------
# EMAIL SENDING LOGIC
# ---------------------------------------------------------
def send_email_with_file_content(filepath: str, subject: str = None) -> bool:
    """Sends the complete text file content as an email using Resend API."""
    if not RESEND_AVAILABLE or not RESEND_API_KEY or "YOUR_" in RESEND_API_KEY:
        print("❌ Cannot send email: Resend module not available or key not configured")
        return False
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        if not subject:
            timestamp = datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
            subject = f"🤖 Nifty AI Analysis - {timestamp}"
        
        # Basic text to HTML conversion
        html_content = file_content.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        
        # Add simple HTML envelope for better reading
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: 'Courier New', monospace; font-size: 14px; background: #f5f5f5; color: #333; padding: 20px;">
            <div style="max-width: 1100px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px;">
                <h2 style="color: #007acc;">🤖 NIFTY AI TRADING ANALYSIS</h2>
                <p><strong>Generated:</strong> {datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")}</p>
                <hr>
                <div>{html_content}</div>
            </div>
        </body>
        </html>
        """
        
        params = {
            "from": "onboarding@resend.dev",
            "to": EMAIL_TO,
            "subject": subject,
            "html": html_template
        }
        
        result = resend.Emails.send(params)
        print(f"✅ Email sent successfully! ID: {result['id']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email via Resend: {e}")
        return False

# ---------------------------------------------------------
# FILE SAVING LOGIC
# ---------------------------------------------------------
def save_ai_query_data(oi_data: List[Dict[str, Any]], 
                      oi_pcr: float, 
                      volume_pcr: float, 
                      current_nifty: float,
                      expiry_date: str,
                      banknifty_data: Dict[str, Any] = None) -> str:
    """Saves formatted option chain data to a text file and triggers email."""    
    
    timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    filepath = os.path.join(AI_LOGS_DIR, f"ai_query_{timestamp}.txt")
    
    # Using a list to build the string (Massive performance optimization)
    lines = []
    fetch_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Add AI Prompt Header (Keep this identical to your prompt requirement)
    system_prompt = """
# ===================================================================
# NIFTY INTRADAY + REVERSAL PROMPT v15.0 [FULLY FIXED + BLACK-BOX PROOF]
# LOGIC: "TREND → UNWIND → COUNTER → PAIN" + MAX PAIN + FULL TRACE
# ===================================================================
"""
    lines.append(system_prompt)
    
    # 2. Add Nifty Summary
    lines.append(f"\nCURRENT DATA FOR ANALYSIS - FETCHED AT: {fetch_time}\n")
    lines.append("=" * 80 + "\n")
    lines.append(f"NIFTY DATA:\n- Current Value: {current_nifty}\n- Expiry Date: {expiry_date}\n- OI PCR: {oi_pcr:.2f}\n- Volume PCR: {volume_pcr:.2f}\n")
    
    # 3. Add BankNifty Summary (If available)
    if banknifty_data and 'data' in banknifty_data:
        bn_curr = banknifty_data.get('current_value', 0)
        bn_exp = banknifty_data.get('expiry_date', 'N/A')
        bn_pcr = banknifty_data.get('pcr_values', {}).get('oi_pcr', 0)
        bn_vol_pcr = banknifty_data.get('pcr_values', {}).get('volume_pcr', 0)
        lines.append(f"\nBANKNIFTY DATA:\n- Current Value: {bn_curr}\n- Expiry Date: {bn_exp}\n- OI PCR: {bn_pcr:.2f}\n- Volume PCR: {bn_vol_pcr:.2f}\n")

    # 4. Add Nifty Data Table
    lines.append(f"\n\nCOMPLETE NIFTY OPTION CHAIN DATA:\n" + "=" * 80 + "\n")
    lines.append(f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n")
    lines.append(f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n")
    lines.append("-" * 150 + "\n")
    
    for data in oi_data:
        lines.append(format_strike_row(data))
        
    lines.append("=" * 150 + "\n\n")

    # 5. Add BankNifty Data Table (If available)
    if banknifty_data and 'data' in banknifty_data:
        lines.append(f"\nCOMPLETE BANKNIFTY OPTION CHAIN DATA:\n" + "=" * 80 + "\n")
        lines.append(f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}\n")
        lines.append(f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}\n")
        lines.append("-" * 150 + "\n")
        
        for data in banknifty_data['data']:
            lines.append(format_strike_row(data))
            
        lines.append("=" * 150 + "\n")

    # Final string compilation
    full_content = "".join(lines)
    
    # Write to File
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(full_content)
        print(f"✅ AI query data saved to: {os.path.basename(filepath)}")
        
        print("📧 Sending to Email...")
        if send_email_with_file_content(filepath):
            print("✅ Email dispatched successfully!")
            
        return filepath
    except Exception as e:
        print(f"❌ Error saving AI query data: {e}")
        return ""