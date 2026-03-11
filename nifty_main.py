import time
import signal
import sys
import urllib3

# Disable SSL Warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import our modularized components
import nifty_config
from nifty_config import (
    SYMBOL, FETCH_INTERVAL, ENABLE_AI_ANALYSIS, 
    ENABLE_LOOP_FETCHING, ENABLE_STOCK_DISPLAY
)
from nifty_fetcher import (
    fetch_option_chain, parse_option_chain, calculate_pcr_values,
    fetch_banknifty_data, fetch_all_stock_data, stop_playwright
)
# UPDATED IMPORT: Swapped format_strike_row for format_csv_row
from nifty_logger import save_ai_query_data, format_csv_row
from nifty_ai import NiftyAIAnalyzer

# Initialize the AI Analyzer
ai_analyzer = NiftyAIAnalyzer()

# ---------------------------------------------------------
# CONSOLE DISPLAY HELPERS
# ---------------------------------------------------------
def print_table_header():
    """Prints the standardized CSV header for options data."""
    print("CE_ChgOI,CE_Vol,CE_LTP,CE_OI,CE_IV,STRIKE,PE_ChgOI,PE_Vol,PE_LTP,PE_OI,PE_IV,CE-PE_DIFF")
    print("-" * 100)

def display_nifty_data(oi_data, oi_pcr, volume_pcr):
    """Displays Nifty OI data to the console."""
    if not oi_data: return

    current_value = oi_data[0]['nifty_value']
    expiry_date = oi_data[0]['expiry_date']

    print(f"\n{'='*80}")
    print(f"OI Data for NIFTY - Current: {current_value}, Expiry: {expiry_date}")
    print(f"Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}")
    print(f"{'='*80}")
    print_table_header()

    # UPDATED: Use format_csv_row
    for data in oi_data:
        print(format_csv_row(data), end="")

    print("=" * 100)

def display_banknifty_data(banknifty_data):
    """Displays BANKNIFTY OI data to the console."""
    if not banknifty_data or 'data' not in banknifty_data: return

    data_list = banknifty_data['data']
    if not data_list: return

    print(f"\n{'='*80}")
    print(f"🏦 BANKNIFTY MONTHLY - Current: {banknifty_data['current_value']}, Expiry: {banknifty_data['expiry_date']}")
    print(f"{'='*80}")
    print_table_header()

    # UPDATED: Use format_csv_row
    for data in data_list:
        print(format_csv_row(data), end="")

    print("=" * 100)

def display_stocks_summary(stock_data):
    """Displays a summary of top stocks."""
    if not stock_data: return

    print(f"\n{'='*80}\nTOP 10 NIFTY STOCKS SUMMARY\n{'='*80}")
    print(f"{'SYMBOL':<15} {'WEIGHT':<10} {'PRICE':<10} {'OI PCR':<10} {'VOL PCR':<10}")
    print("-" * 80)

    for symbol, info in stock_data.items():
        print(f"{symbol:<15} {info.get('weight', 0):<10.4f} {info.get('current_price', 0):<10} "
              f"{info.get('oi_pcr', 0):<10.2f} {info.get('volume_pcr', 0):<10.2f}")
    print("=" * 80)

# ---------------------------------------------------------
# CORE EXECUTION CYCLE
# ---------------------------------------------------------
def data_collection_cycle():
    """Performs one complete data fetch, log, and AI analysis cycle."""
    print(f"\nFetching {SYMBOL} option chain...")
    
    try:
        # 1. Fetch & Parse Nifty
        raw_data = fetch_option_chain()
        oi_data = parse_option_chain(raw_data)
        
        if not oi_data:
            print("❌ No valid expiry data parsed. Skipping this cycle.")
            return False
            
        oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
        
        # 2. Fetch BankNifty & Stocks
        banknifty_data = fetch_banknifty_data()
        stock_data = fetch_all_stock_data() if ENABLE_STOCK_DISPLAY else None

        # 3. Console Display
        display_nifty_data(oi_data, oi_pcr, volume_pcr)
        if banknifty_data: display_banknifty_data(banknifty_data)
        if stock_data: display_stocks_summary(stock_data)

        # 4. Save Logs & Email
        print("\n💾 Archiving data and preparing email...")
        current_nifty = oi_data[0]['nifty_value']
        expiry_date = oi_data[0]['expiry_date']
        
        save_ai_query_data(
            oi_data=oi_data,
            oi_pcr=oi_pcr,
            volume_pcr=volume_pcr,
            current_nifty=current_nifty,
            expiry_date=expiry_date,
            banknifty_data=banknifty_data
        )

        # 5. Execute AI Analysis & Telegram Alert
        if ENABLE_AI_ANALYSIS:
            print("\n" + "="*80 + "\nREQUESTING AI ANALYSIS...\n" + "="*80)
            ai_analysis = ai_analyzer.get_ai_analysis()
            print(ai_analysis)

        print("="*80)
        print(f"✅ Cycle complete. Nifty: {current_nifty} | Expiry: {expiry_date}")
        return True

    except Exception as e:
        print(f"❌ Error in data collection cycle: {e}")
        return False

# ---------------------------------------------------------
# LOOP MANAGER
# ---------------------------------------------------------
def data_collection_loop():
    """Manages the continuous loop or single execution based on config."""
    try:
        if ENABLE_LOOP_FETCHING:
            cycle_count = 0
            while nifty_config.running:
                cycle_count += 1
                print(f"\n{'#'*80}\nDATA COLLECTION CYCLE {cycle_count}\n{'#'*80}")
                
                success = data_collection_cycle()
                
                if not success:
                    print("⚠️ Cycle failed, waiting 30 seconds before retry...")
                    time.sleep(30)
                    continue

                if nifty_config.running:
                    print(f"\n⏳ Waiting {FETCH_INTERVAL} seconds for next cycle...")
                    for _ in range(FETCH_INTERVAL):
                        if not nifty_config.running: break
                        time.sleep(1)
        else:
            data_collection_cycle()
            print("\n✅ Single execution mode completed successfully.")

    except Exception as e:
        print(f"❌ Fatal error in execution loop: {e}")
    finally:
        nifty_config.running = False

# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
def main():
    # Hook up Ctrl+C termination signals to our config's safe shutdown
    signal.signal(signal.SIGINT, nifty_config.signal_handler)
    signal.signal(signal.SIGTERM, nifty_config.signal_handler)

    nifty_config.print_configuration_status()

    try:
        data_collection_loop()
    except KeyboardInterrupt:
        print("\n🛑 Manual interruption caught.")
    finally:
        print("🧹 Cleaning up background processes...")
        stop_playwright()
        print("✅ Application shutdown complete.")
        sys.exit(0)

if __name__ == "__main__":
    main()
