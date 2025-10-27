# nifty_main.py
import datetime
import time
import signal
import sys
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from nifty_file_logger import (
    save_ai_query_data, 
    resend_latest_ai_query, 
    resend_specific_ai_query, 
    list_ai_query_files
)

from nifty_core_config import (
    SYMBOL, FETCH_INTERVAL, running,
    signal_handler, initialize_session,
    format_greek_value, should_run_ai_analysis,
    should_run_loop, should_display_stocks, get_fetch_interval,
    TOP_NIFTY_STOCKS
)
from nifty_data_fetcher import (
    fetch_option_chain, parse_option_chain, calculate_pcr_values,
    fetch_banknifty_data, fetch_all_stock_data
)
from nifty_ai_analyzer import NiftyAIAnalyzer
from nifty_file_logger import save_ai_query_data


# Initialize AI analyzer globally
ai_analyzer = NiftyAIAnalyzer()

def display_nifty_data(oi_data, oi_pcr, volume_pcr):
    """Display Nifty OI data without Greeks - Show ALL strikes"""
    if not oi_data:
        return
    
    current_value = oi_data[0]['nifty_value']
    expiry_date = oi_data[0]['expiry_date']
    
    print(f"\n{'='*80}")
    print(f"OI Data for NIFTY - Current: {current_value}, Expiry: {expiry_date}")
    print(f"Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}")
    print(f"{'='*80}")
    print(f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}")
    print(
        f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  "
        f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  "
        f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}"
    )
    print("-" * 150)
    
    for data in oi_data:
        strike_price = data['strike_price']
        
        # Use raw values directly without formatting
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
        
        # Format the row without Greek columns
        formatted_row = (
            f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
            f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
            f"{str(strike_price).center(9)}  |  "
            f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
            f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
            f"{chg_oi_diff_formatted.rjust(16)}"
        )
        
        print(formatted_row)
    
    print("=" * 150)
    print(f"NIFTY PCR: OI PCR = {oi_pcr:.2f}, Volume PCR = {volume_pcr:.2f}")

def display_banknifty_data(banknifty_data):
    """Display BANKNIFTY OI data without Greeks - Show ALL strikes"""
    if not banknifty_data:
        return
    
    current_value = banknifty_data['current_value']
    expiry_date = banknifty_data['expiry_date']
    
    print(f"\n{'='*80}")
    print(f"OI Data for BANKNIFTY - Current: {current_value}, Expiry: {expiry_date}")
    print(f"Full Chain PCR: OI={banknifty_data['oi_pcr']:.2f}, Volume={banknifty_data['volume_pcr']:.2f}")
    print(f"{'='*80}")
    print(f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}")
    print(
        f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  "
        f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  "
        f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}"
    )
    print("-" * 150)
    
    for data in banknifty_data['data']:
        strike_price = data['strike_price']
        
        # Use raw values directly without formatting
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
        
        # Format the row without Greek columns
        formatted_row = (
            f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
            f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
            f"{str(strike_price).center(9)}  |  "
            f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
            f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
            f"{chg_oi_diff_formatted.rjust(16)}"
        )
        
        print(formatted_row)
    
    print("=" * 150)
    print(f"BANKNIFTY PCR: OI PCR = {banknifty_data['oi_pcr']:.2f}, Volume PCR = {banknifty_data['volume_pcr']:.2f}")

def display_stock_data(stock_data):
    """Display stock OI data without Greeks in required format - Show ALL strikes"""
    if not stock_data:
        return
        
    symbol = stock_data[0]['symbol']
    stock_info = TOP_NIFTY_STOCKS[symbol]
    current_price = stock_data[0]['stock_value']
    
    print(f"\n{'='*80}")
    print(f"OI Data for {stock_info['name']} ({symbol}) - Current Price: {current_price}")
    print(f"{'='*80}")
    print(f"{'CALL OPTION':<50}|   STRIKE   |{'PUT OPTION':<52}|  {'CHG OI DIFF':<18}")
    print(
        f"{'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  {'OI'.rjust(10)}  {'IV'.rjust(7)}  |  "
        f"{'Price'.center(9)}  |  {'Chg OI'.rjust(10)}  {'Volume'.rjust(10)}  {'LTP'.rjust(8)}  "
        f"{'OI'.rjust(10)}  {'IV'.rjust(7)}  |  {'CE-PE'.rjust(16)}"
    )
    print("-" * 150)
    
    for data in stock_data:
        strike_price = data['strike_price']
        
        # Use raw values directly without formatting
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
        
        # Format the row without Greek columns
        formatted_row = (
            f"{ce_oi_formatted.rjust(10)}  {ce_volume_formatted.rjust(10)}  {ce_ltp_formatted.rjust(8)}  "
            f"{ce_oi_total_formatted.rjust(10)}  {ce_iv_formatted.rjust(7)}  |  "
            f"{str(strike_price).center(9)}  |  "
            f"{pe_oi_formatted.rjust(10)}  {pe_volume_formatted.rjust(10)}  {pe_ltp_formatted.rjust(8)}  "
            f"{pe_oi_total_formatted.rjust(10)}  {pe_iv_formatted.rjust(7)}  |  "
            f"{chg_oi_diff_formatted.rjust(16)}"
        )
        
        print(formatted_row)
    
    print("=" * 150)

def display_stocks_summary(stock_data):
    """Display summary of all stocks with PCR values"""
    if not stock_data:
        return
        
    print(f"\n{'='*80}")
    print("TOP 10 NIFTY STOCKS SUMMARY")
    print(f"{'='*80}")
    print(f"{'SYMBOL':<15} {'WEIGHT':<10} {'PRICE':<10} {'OI PCR':<10} {'VOL PCR':<10}")
    print("-" * 80)
    
    for symbol, info in stock_data.items():
        price = info.get('current_price', 0)
        oi_pcr = info.get('oi_pcr', 0)
        vol_pcr = info.get('volume_pcr', 0)
        weight = info.get('weight', 0)
        
        print(f"{symbol:<15} {weight:<10.4f} {price:<10} {oi_pcr:<10.2f} {vol_pcr:<10.2f}")
    
    print("=" * 80)

def data_collection_cycle():
    """Perform one complete data collection and analysis cycle"""
    session = None
    try:
        # Initialize session if not already done
        if session is None:
            session = initialize_session()
        
        # Fetch Nifty data
        print(f"Fetching {SYMBOL} option chain...")
        data = fetch_option_chain(session)
        oi_data = parse_option_chain(data)
        
        # Calculate PCR values for full chain
        oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
        
        # Display Nifty data (ALL strikes)
        display_nifty_data(oi_data, oi_pcr, volume_pcr)
        
        # Fetch BANKNIFTY data
        banknifty_data = fetch_banknifty_data()
        if banknifty_data:
            display_banknifty_data(banknifty_data)
        
        # Fetch all stock data
        stock_data = fetch_all_stock_data()
        
        # NEW FEATURE: Save AI query data to file (always executed)
        print("\n💾 Saving AI query data to file and sending to Telegram...")
        file_path = save_ai_query_data(
            oi_data=oi_data,
            oi_pcr=oi_pcr,
            volume_pcr=volume_pcr,
            current_nifty=oi_data[0]['nifty_value'],
            expiry_date=oi_data[0]['expiry_date'],
            banknifty_data=banknifty_data
        )
        
        # Display stocks summary if enabled
        if should_display_stocks() and stock_data:
            display_stocks_summary(stock_data)
            
            # Display individual stock data if enabled
            for symbol, info in stock_data.items():
                display_stock_data(info['data'])
        
        # AI Analysis if enabled
        if should_run_ai_analysis():
            print("\n" + "="*80)
            print("REQUESTING AI ANALYSIS...")
            print("="*80)
            
            try:
                ai_analysis = ai_analyzer.get_ai_analysis(
                    oi_data=oi_data,
                    oi_pcr=oi_pcr,
                    volume_pcr=volume_pcr,
                    current_nifty=oi_data[0]['nifty_value'],
                    expiry_date=oi_data[0]['expiry_date'],
                    stock_data=stock_data,
                    banknifty_data=banknifty_data
                )
                print(ai_analysis)
            except Exception as ai_error:
                print(f"⚠️ AI analysis failed: {ai_error}")
                print("Continuing without AI analysis...")
        
        print("="*80)
        
        # Display brief info
        print(f"Nifty: {oi_data[0]['nifty_value']}, Expiry: {oi_data[0]['expiry_date']}")
        if banknifty_data:
            print(f"BankNifty: {banknifty_data['current_value']}, Expiry: {banknifty_data['expiry_date']}")
        
        print(f"✅ Data collection cycle completed.")
        
        return True
        
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received in data collection.")
        raise
    except Exception as e:
        print(f"Error in data collection cycle: {e}")
        return False
    finally:
        if session:
            session.close()

def data_collection_loop():
    """Main data collection loop with configurable behavior"""
    global running
    
    try:
        if should_run_loop():
            print(f"Starting continuous data collection (interval: {get_fetch_interval()} seconds)")
            cycle_count = 0
            
            while running:
                cycle_count += 1
                print(f"\n{'#'*80}")
                print(f"DATA COLLECTION CYCLE {cycle_count}")
                print(f"{'#'*80}")
                
                success = data_collection_cycle()
                
                if not success:
                    print("Cycle failed, waiting before retry...")
                    time.sleep(30)  # Shorter wait on failure
                    continue
                
                if running:
                    print(f"\nWaiting {get_fetch_interval()} seconds for next cycle...")
                    # Wait with interruptible sleep
                    for _ in range(get_fetch_interval()):
                        if not running:
                            break
                        time.sleep(1)
                
        else:
            # Single run mode
            print("Starting single data collection cycle...")
            data_collection_cycle()
            print("✅ Single data collection completed. Program exiting.")
            
    except KeyboardInterrupt:
        print("\nData collection loop interrupted by user.")
    except Exception as e:
        print(f"Fatal error in data collection loop: {e}")
    finally:
        running = False
        print("Data collection stopped.")

def main():
    print(f"Starting {SYMBOL} OI Data Analyzer")
    print(f"Configuration:")
    print(f"  AI Analysis: {'ENABLED' if should_run_ai_analysis() else 'DISABLED'}")
    print(f"  Loop Mode: {'ENABLED' if should_run_loop() else 'DISABLED'}")
    print(f"  Stock Display: {'ENABLED' if should_display_stocks() else 'DISABLED'}")
    print(f"  Data Processing: Full Options Chains")
    
    if should_run_loop():
        print(f"  Fetch interval: {get_fetch_interval()} seconds")
    else:
        print("  Single execution mode")
    
    if should_run_ai_analysis():
        print("  DeepSeek AI analysis will be performed")
    else:
        print("  AI analysis disabled - displaying raw data only")
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        data_collection_loop()
    except KeyboardInterrupt:
        print("\nMain: Keyboard interrupt caught")
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        print("Application shutdown complete")
        # Force exit to ensure script terminates
        os._exit(0)

if __name__ == "__main__":
    main()