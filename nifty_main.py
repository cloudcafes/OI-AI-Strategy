import datetime
import time
import signal
import sys
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from nifty_file_logger import (save_ai_query_data)
from nifty_core_config import (SYMBOL, FETCH_INTERVAL, running,
                              signal_handler, initialize_session,
                              format_greek_value, should_run_ai_analysis,
                              should_run_loop, should_display_stocks, get_fetch_interval,
                              TOP_NIFTY_STOCKS, should_enable_multi_expiry, get_expiry_type_constants,
                              should_enable_single_ai_query, should_enable_multi_ai_query, get_ai_query_mode)
from nifty_data_fetcher import (fetch_option_chain, parse_option_chain, calculate_pcr_values,
                               calculate_pcr_for_expiry_data, fetch_banknifty_data, fetch_all_stock_data)
from nifty_ai_analyzer import NiftyAIAnalyzer
from nifty_file_logger import save_ai_query_data
from multi_expiry_file_logger import save_multi_expiry_ai_query_data, save_daily_eod_state_block

MULTI_EXPIRY_LOGGER_AVAILABLE = True
ai_analyzer = NiftyAIAnalyzer()

def display_nifty_single_expiry(oi_data, oi_pcr, volume_pcr):
    """Display Nifty OI data for single expiry (backward compatible)"""
    if not oi_data:
        return

    current_value = oi_data[0]['nifty_value']
    expiry_date = oi_data[0]['expiry_date']

    print(f"\n{'='*80}")
    print(f"OI Data for NIFTY - Current: {current_value}, Expiry: {expiry_date}")
    print(f"Full Chain PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}")
    print(f"{'='*80}")
    print(f"{'CALL OPTION':<50}| STRIKE |{'PUT OPTION':<52}| {'CHG OI DIFF':<18}")
    print(f"{'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} {'OI'.rjust(10)} {'IV'.rjust(7)} | "
          f"{'Price'.center(9)} | {'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} "
          f"{'OI'.rjust(10)} {'IV'.rjust(7)} | {'CE-PE'.rjust(16)}")
    print("-" * 150)

    for data in oi_data:
        strike_price = data['strike_price']
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

        formatted_row = (f"{ce_oi_formatted.rjust(10)} {ce_volume_formatted.rjust(10)} {ce_ltp_formatted.rjust(8)} "
                        f"{ce_oi_total_formatted.rjust(10)} {ce_iv_formatted.rjust(7)} | "
                        f"{str(strike_price).center(9)} | "
                        f"{pe_oi_formatted.rjust(10)} {pe_volume_formatted.rjust(10)} {pe_ltp_formatted.rjust(8)} "
                        f"{pe_oi_total_formatted.rjust(10)} {pe_iv_formatted.rjust(7)} | "
                        f"{chg_oi_diff_formatted.rjust(16)}")
        print(formatted_row)

    print("=" * 150)
    print(f"NIFTY PCR: OI PCR = {oi_pcr:.2f}, Volume PCR = {volume_pcr:.2f}")

def display_nifty_multi_expiry(expiry_data, pcr_values):
    """Display Nifty OI data for multiple expiries"""
    if not expiry_data:
        return

    constants = get_expiry_type_constants()

    for expiry_type in constants['ALL_TYPES']:
        if expiry_type in expiry_data and expiry_data[expiry_type]:
            oi_data = expiry_data[expiry_type]
            current_value = oi_data[0]['nifty_value']
            expiry_date = oi_data[0]['expiry_date']
            expiry_pcr = pcr_values.get(expiry_type, {})
            oi_pcr = expiry_pcr.get('oi_pcr', 1.0)
            volume_pcr = expiry_pcr.get('volume_pcr', 1.0)
            strike_count = expiry_pcr.get('strike_count', 0)

            print(f"\n{'='*80}")
            expiry_label = expiry_type.upper().replace('_', ' ')
            print(f"📅 NIFTY {expiry_label} - Current: {current_value}, Expiry: {expiry_date}")
            print(f"PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}, Strikes: {strike_count}")
            print(f"{'='*80}")
            print(f"{'CALL OPTION':<50}| STRIKE |{'PUT OPTION':<52}| {'CHG OI DIFF':<18}")
            print(f"{'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} {'OI'.rjust(10)} {'IV'.rjust(7)} | "
                  f"{'Price'.center(9)} | {'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} "
                  f"{'OI'.rjust(10)} {'IV'.rjust(7)} | {'CE-PE'.rjust(16)}")
            print("-" * 150)

            for data in oi_data:
                strike_price = data['strike_price']
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

                formatted_row = (f"{ce_oi_formatted.rjust(10)} {ce_volume_formatted.rjust(10)} {ce_ltp_formatted.rjust(8)} "
                                f"{ce_oi_total_formatted.rjust(10)} {ce_iv_formatted.rjust(7)} | "
                                f"{str(strike_price).center(9)} | "
                                f"{pe_oi_formatted.rjust(10)} {pe_volume_formatted.rjust(10)} {pe_ltp_formatted.rjust(8)} "
                                f"{pe_oi_total_formatted.rjust(10)} {pe_iv_formatted.rjust(7)} | "
                                f"{chg_oi_diff_formatted.rjust(16)}")
                print(formatted_row)

            print("=" * 150)

def display_banknifty_data(banknifty_data):
    """Display BANKNIFTY OI data without Greeks - Show ALL strikes"""
    if not banknifty_data or 'data' not in banknifty_data:
        return

    monthly_data = banknifty_data['data'].get('monthly', [])
    if not monthly_data:
        return

    current_value = banknifty_data['current_value']
    expiry_date = banknifty_data['expiry_date']
    pcr_values = banknifty_data.get('pcr_values', {})
    monthly_pcr = pcr_values.get('monthly', {})
    oi_pcr = monthly_pcr.get('oi_pcr', 1.0)
    volume_pcr = monthly_pcr.get('volume_pcr', 1.0)

    print(f"\n{'='*80}")
    print(f"🏦 BANKNIFTY MONTHLY - Current: {current_value}, Expiry: {expiry_date}")
    print(f"PCR: OI={oi_pcr:.2f}, Volume={volume_pcr:.2f}")
    print(f"{'='*80}")
    print(f"{'CALL OPTION':<50}| STRIKE |{'PUT OPTION':<52}| {'CHG OI DIFF':<18}")
    print(f"{'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} {'OI'.rjust(10)} {'IV'.rjust(7)} | "
          f"{'Price'.center(9)} | {'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} "
          f"{'OI'.rjust(10)} {'IV'.rjust(7)} | {'CE-PE'.rjust(16)}")
    print("-" * 150)

    for data in monthly_data:
        strike_price = data['strike_price']
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

        formatted_row = (f"{ce_oi_formatted.rjust(10)} {ce_volume_formatted.rjust(10)} {ce_ltp_formatted.rjust(8)} "
                        f"{ce_oi_total_formatted.rjust(10)} {ce_iv_formatted.rjust(7)} | "
                        f"{str(strike_price).center(9)} | "
                        f"{pe_oi_formatted.rjust(10)} {pe_volume_formatted.rjust(10)} {pe_ltp_formatted.rjust(8)} "
                        f"{pe_oi_total_formatted.rjust(10)} {pe_iv_formatted.rjust(7)} | "
                        f"{chg_oi_diff_formatted.rjust(16)}")
        print(formatted_row)

    print("=" * 150)
    print(f"BANKNIFTY PCR: OI PCR = {oi_pcr:.2f}, Volume PCR = {volume_pcr:.2f}")

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
    print(f"{'CALL OPTION':<50}| STRIKE |{'PUT OPTION':<52}| {'CHG OI DIFF':<18}")
    print(f"{'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} {'OI'.rjust(10)} {'IV'.rjust(7)} | "
          f"{'Price'.center(9)} | {'Chg OI'.rjust(10)} {'Volume'.rjust(10)} {'LTP'.rjust(8)} "
          f"{'OI'.rjust(10)} {'IV'.rjust(7)} | {'CE-PE'.rjust(16)}")
    print("-" * 150)

    for data in stock_data:
        strike_price = data['strike_price']
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

        formatted_row = (f"{ce_oi_formatted.rjust(10)} {ce_volume_formatted.rjust(10)} {ce_ltp_formatted.rjust(8)} "
                        f"{ce_oi_total_formatted.rjust(10)} {ce_iv_formatted.rjust(7)} | "
                        f"{str(strike_price).center(9)} | "
                        f"{pe_oi_formatted.rjust(10)} {pe_volume_formatted.rjust(10)} {pe_ltp_formatted.rjust(8)} "
                        f"{pe_oi_total_formatted.rjust(10)} {pe_iv_formatted.rjust(7)} | "
                        f"{chg_oi_diff_formatted.rjust(16)}")
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

def print_ai_query_configuration():
    """Print current AI query configuration"""
    single_enabled = should_enable_single_ai_query()
    multi_enabled = should_enable_multi_ai_query()
    query_mode = get_ai_query_mode()
    
    print(f"\n🤖 AI QUERY CONFIGURATION:")
    print(f"   Single AI Query: {'ENABLED' if single_enabled else 'DISABLED'}")
    print(f"   Multi AI Query:  {'ENABLED' if multi_enabled else 'DISABLED'}")
    print(f"   Query Mode:      {query_mode.upper()}")
    
    if not single_enabled and not multi_enabled:
        print("   ⚠️  Both query types are disabled - no AI analysis will be performed")
    elif query_mode == "both" and (not single_enabled or not multi_enabled):
        print("   ⚠️  Query mode is 'both' but one query type is disabled")

def data_collection_cycle():
    """Perform one complete data collection and analysis cycle"""
    session = None
    try:
        if session is None:
            session = initialize_session()

        print(f"Fetching {SYMBOL} option chain...")
        data = fetch_option_chain(session)
        expiry_data = parse_option_chain(data)
        pcr_values = calculate_pcr_for_expiry_data(expiry_data)

        if should_enable_multi_expiry() and len(expiry_data) > 1:
            print(f"\n🎯 Multi-Expiry Analysis Enabled ({len(expiry_data)} timeframes)")
            display_nifty_multi_expiry(expiry_data, pcr_values)
        else:
            constants = get_expiry_type_constants()
            current_week_data = expiry_data.get(constants['CURRENT_WEEK'], [])
            if current_week_data:
                current_pcr = pcr_values.get(constants['CURRENT_WEEK'], {})
                oi_pcr = current_pcr.get('oi_pcr', 1.0)
                volume_pcr = current_pcr.get('volume_pcr', 1.0)
                display_nifty_single_expiry(current_week_data, oi_pcr, volume_pcr)

        banknifty_data = fetch_banknifty_data()
        if banknifty_data:
            display_banknifty_data(banknifty_data)

        stock_data = fetch_all_stock_data()

        print("\n💾 Saving AI query data to file and sending to Telegram...")
        constants = get_expiry_type_constants()
        current_week_data = expiry_data.get(constants['CURRENT_WEEK'], [])
        current_pcr = pcr_values.get(constants['CURRENT_WEEK'], {})
        oi_pcr = current_pcr.get('oi_pcr', 1.0)
        volume_pcr = current_pcr.get('volume_pcr', 1.0)
        current_nifty = current_week_data[0]['nifty_value'] if current_week_data else 0
        expiry_date = current_week_data[0]['expiry_date'] if current_week_data else "N/A"

        file_path = save_ai_query_data(oi_data=current_week_data,
                                     oi_pcr=oi_pcr,
                                     volume_pcr=volume_pcr,
                                     current_nifty=current_nifty,
                                     expiry_date=expiry_date,
                                     banknifty_data=banknifty_data)

        # Multi-expiry logging
        try:
            from multi_expiry_file_logger import save_multi_expiry_ai_query_data
            multi_file_path = save_multi_expiry_ai_query_data(expiry_data=expiry_data,
                                                            pcr_values=pcr_values,
                                                            current_nifty=current_nifty,
                                                            banknifty_data=banknifty_data,
                                                            stock_data=stock_data)
            if multi_file_path:
                print(f"✅ Multi-expiry data saved to: {multi_file_path}")
            else:
                print("⚠️ Multi-expiry logging disabled or failed")
        except ImportError:
            print("⚠️ Multi-expiry logger not available")
        except Exception as e:
            print(f"⚠️ Multi-expiry logging failed: {e}")

        print("\n📊 Generating daily EOD state block...")
        try:
            eod_filepath = save_daily_eod_state_block(expiry_data=expiry_data,
                                                    pcr_values=pcr_values,
                                                    current_nifty=current_nifty,
                                                    banknifty_data=banknifty_data,
                                                    stock_data=stock_data)
            if eod_filepath:
                print(f"✅ Daily EOD state block saved to: {eod_filepath}")
            else:
                print("⚠️ Daily EOD state block generation failed")
        except Exception as e:
            print(f"⚠️ Error generating daily EOD state block: {e}")

        if should_display_stocks() and stock_data:
            display_stocks_summary(stock_data)
            for symbol, info in stock_data.items():
                display_stock_data(info['data'])

        # AI Analysis Section
        if should_run_ai_analysis():
            print_ai_query_configuration()
            
            single_enabled = should_enable_single_ai_query()
            multi_enabled = should_enable_multi_ai_query()
            query_mode = get_ai_query_mode()
            
            if not single_enabled and not multi_enabled:
                print("❌ AI analysis skipped: Both query types are disabled")
            else:
                print("\n" + "="*80)
                print("REQUESTING AI ANALYSIS...")
                print("="*80)
                
                try:
                    # Prepare parameters for single analysis
                    single_params = {}
                    if single_enabled or query_mode == "both":
                        single_params = {
                            'oi_data': expiry_data,
                            'oi_pcr': oi_pcr,
                            'volume_pcr': volume_pcr,
                            'current_nifty': current_nifty,
                            'expiry_date': expiry_date,
                            'stock_data': stock_data,
                            'banknifty_data': banknifty_data
                        }
                    
                    # Call the enhanced AI analyzer
                    ai_analysis = ai_analyzer.get_ai_analysis(**single_params)
                    print(ai_analysis)
                    
                except Exception as ai_error:
                    print(f"⚠️ AI analysis failed: {ai_error}")
                    print("Continuing without AI analysis...")

        print("="*80)
        constants = get_expiry_type_constants()
        current_week_data = expiry_data.get(constants['CURRENT_WEEK'], [])
        if current_week_data:
            print(f"Nifty: {current_week_data[0]['nifty_value']}, Expiry: {current_week_data[0]['expiry_date']}")
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
                    time.sleep(30)
                    continue

                if running:
                    print(f"\nWaiting {get_fetch_interval()} seconds for next cycle...")
                    for _ in range(get_fetch_interval()):
                        if not running:
                            break
                        time.sleep(1)
        else:
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
    print(f" AI Analysis: {'ENABLED' if should_run_ai_analysis() else 'DISABLED'}")
    print(f" Loop Mode: {'ENABLED' if should_run_loop() else 'DISABLED'}")
    print(f" Stock Display: {'ENABLED' if should_display_stocks() else 'DISABLED'}")
    print(f" Multi-Expiry: {'ENABLED' if should_enable_multi_expiry() else 'DISABLED'}")
    print(f" Data Processing: Full Options Chains")
    
    # Print AI query configuration
    print_ai_query_configuration()
    
    if should_run_loop():
        print(f" Fetch interval: {get_fetch_interval()} seconds")
    else:
        print(" Single execution mode")

    if should_run_ai_analysis():
        single_enabled = should_enable_single_ai_query()
        multi_enabled = should_enable_multi_ai_query()
        query_mode = get_ai_query_mode()
        
        if single_enabled and multi_enabled:
            print(" Both single and multi AI analysis will be performed")
        elif single_enabled:
            print(" Single AI analysis will be performed")
        elif multi_enabled:
            print(" Multi AI analysis will be performed")
        else:
            print(" AI analysis enabled but both query types are disabled")
    else:
        print(" AI analysis disabled - displaying raw data only")

    if should_enable_multi_expiry():
        print(" Multi-expiry analysis enabled - showing current_week, next_week, monthly")
    else:
        print(" Single expiry mode - showing current week only")

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
        os._exit(0)

if __name__ == "__main__":
    main()