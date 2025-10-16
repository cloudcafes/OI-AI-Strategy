# stock-main.py - MODIFIED FOR IMMEDIATE FILE WRITING
# Main executor with immediate file writing and continuous analysis mode

import time
import datetime
import os
from typing import List, Dict, Any

from stock_config import STOCK_LIST, ENABLE_AI_ANALYSIS, RATE_LIMIT_DELAY
from stock_fetcher import get_stock_data, initialize_session
from stock_analyzer import perform_python_analysis, format_analysis_for_display
from stock_trend_classifier import classify_stock_trend

class StockAnalysisExecutor:
    def __init__(self, continuous_mode: bool = False):
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        self.session = None
        self.strong_trend_stocks = []  # Store stocks with strong trends
        self.continuous_mode = continuous_mode
        self.iteration_count = 0
        self.selected_stocks_file = "selected_stocks.txt"

    def initialize(self):
        """Initialize the analysis executor"""
        self.start_time = datetime.datetime.now()
        mode_info = "CONTINUOUS MODE" if self.continuous_mode else "SINGLE SCAN MODE"
        
        print(f"\n🎯 STOCK F&O ANALYSIS STARTED - {mode_info}")
        print(f"📊 Total Stocks: {len(STOCK_LIST)}")
        print(f"🤖 AI Analysis: {'ENABLED' if ENABLE_AI_ANALYSIS else 'DISABLED'}")
        print(f"⏰ Start Time: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Displaying ONLY: STRONG_BULLISH & STRONG_BEARISH trends")
        print(f"💾 Saving results IMMEDIATELY to: {self.selected_stocks_file}")
        print("=" * 80)
        
        try:
            self.session = initialize_session()
            print("✅ Session initialized successfully")
        except Exception as e:
            print(f"❌ Session initialization failed: {e}")
            return False
        return True
    
    def save_single_stock_to_file(self, stock_data: Dict[str, Any]):
        """Save a single strong trend stock to file immediately"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            iteration_info = f" (Iteration #{self.iteration_count})" if self.continuous_mode else ""
            
            symbol = stock_data['symbol']
            trend = stock_data['trend_result']['trend']
            confidence = stock_data['trend_result']['confidence']
            oi_pcr = stock_data['aggregate_metrics']['OI PCR']
            volume_pcr = stock_data['aggregate_metrics']['Volume PCR']
            
            header = f"🎯 STRONG TREND STOCK FOUND - {timestamp}{iteration_info}"
            separator = "=" * 80
            
            # Create content for this stock
            new_content = f"{header}\n{separator}\n"
            new_content += f"📈 {symbol}: {trend} ({confidence}% confidence)\n"
            new_content += f"   📊 OI PCR: {oi_pcr:.3f} | Volume PCR: {volume_pcr:.3f}\n"
            new_content += f"   ⏰ Discovery Time: {timestamp}\n"
            new_content += f"   🔍 Total CE OI Change: {stock_data['aggregate_metrics']['Total CE OI Change']:+,}\n"
            new_content += f"   🔍 Total PE OI Change: {stock_data['aggregate_metrics']['Total PE OI Change']:+,}\n"
            new_content += separator + "\n\n"
            
            # Read existing content if file exists
            existing_content = ""
            if os.path.exists(self.selected_stocks_file):
                with open(self.selected_stocks_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            
            # Write new content + existing content (latest on top)
            with open(self.selected_stocks_file, 'w', encoding='utf-8') as f:
                f.write(new_content + existing_content)
            
            print(f"💾 IMMEDIATELY SAVED: {symbol} to {self.selected_stocks_file}")
            
        except Exception as e:
            print(f"❌ Error saving {stock_data['symbol']} to {self.selected_stocks_file}: {e}")

    def process_single_stock(self, symbol: str) -> bool:
        """Fetch, analyze, classify trend for a single stock"""
        try:
            print(f"🔄 Processing {symbol}...")
            
            # Fetch complete option chain data
            oi_data = get_stock_data(symbol, self.session)
            if not oi_data:
                print(f"❌ No data retrieved for {symbol}")
                self.error_count += 1
                return False
            
            # Perform Python analysis with aggregate metrics
            analysis_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            python_analysis = perform_python_analysis(oi_data)
            python_analysis['analysis_timestamp'] = analysis_timestamp

            # Get aggregate metrics for trend classification
            aggregate_metrics = python_analysis.get('aggregate_metrics', {})
            
            if not aggregate_metrics:
                print(f"❌ No aggregate metrics for {symbol}")
                self.error_count += 1
                return False
            
            # Classify stock trend - FIX: Check if result is not empty
            trend_result = classify_stock_trend(aggregate_metrics)
            
            # Only store and display STRONG_BULLISH and STRONG_BEARISH stocks
            if trend_result and trend_result.get('trend') in ['STRONG_BULLISH', 'STRONG_BEARISH']:
                stock_data = {
                    'symbol': symbol,
                    'analysis': python_analysis,
                    'trend_result': trend_result,
                    'aggregate_metrics': aggregate_metrics
                }
                self.strong_trend_stocks.append(stock_data)
                self._display_strong_trend_stock(stock_data)
                
                # ✅ IMMEDIATELY SAVE TO FILE when strong trend is found
                self.save_single_stock_to_file(stock_data)
                
            else:
                # Handle cases where trend_result is empty (confidence < 50%) or not strong trend
                trend_display = trend_result.get('trend', 'LOW_CONFIDENCE') if trend_result else 'LOW_CONFIDENCE'
                print(f"⏭️  {symbol}: {trend_display} (Filtered out)")
            
            self.processed_count += 1
            return True
            
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
            self.error_count += 1
            return False

    def _display_strong_trend_stock(self, stock_data: Dict[str, Any]):
        """Display detailed output for strong trend stocks"""
        symbol = stock_data['symbol']
        metrics = stock_data['aggregate_metrics']
        trend_result = stock_data['trend_result']
        
        print(f"\n{'='*80}")
        print(f"🎯 {trend_result['trend']} - {symbol} (Confidence: {trend_result['confidence']}%)")
        print(f"{'='*80}")
        
        # Display aggregate metrics
        print(f"📊 AGGREGATE METRICS:")
        print(f"  Total CE OI Change: {metrics['Total CE OI Change']:+,} ({metrics['Total CE OI Change%']}%)")
        print(f"  Total PE OI Change: {metrics['Total PE OI Change']:+,} ({metrics['Total PE OI Change%']}%)")
        print(f"  OI PCR: {metrics['OI PCR']:.3f}")
        print(f"  Volume PCR: {metrics['Volume PCR']:.3f}")
        
        # Display scores
        scores = trend_result['scores']
        print(f"\n📈 SCORES:")
        print(f"  Bullish: {scores['bullish']} | Bearish: {scores['bearish']} | Net: {scores['net']}")
        
        # Display signals
        print(f"\n🔍 SIGNALS:")
        for signal in trend_result['signals']:
            print(f"  ✓ {signal}")
        
        print(f"{'='*80}")

    def execute_single_scan(self):
        """Execute a single scan of all stocks"""
        self.iteration_count += 1
        self.strong_trend_stocks = []  # Reset for each iteration
        self.processed_count = 0
        self.error_count = 0
        
        iteration_header = f"ITERATION #{self.iteration_count}" if self.continuous_mode else "SINGLE SCAN"
        print(f"\n🚀 Starting {iteration_header} of {len(STOCK_LIST)} stocks...")
        print(f"⏳ This may take several minutes due to rate limiting...")
        
        # Process all stocks
        for index, symbol in enumerate(STOCK_LIST, 1):
            self.process_single_stock(symbol)
            
            # Progress update every 10 stocks
            if index % 10 == 0:
                progress = (index / len(STOCK_LIST)) * 100
                print(f"\n📈 Progress: {index}/{len(STOCK_LIST)} ({progress:.1f}%)")
                print(f"✅ Strong trends found: {len(self.strong_trend_stocks)}")
            
            # Rate limit between fetches
            if index < len(STOCK_LIST):
                time.sleep(RATE_LIMIT_DELAY)

        # Display final summary
        self._print_iteration_summary()

    def execute_continuous_analysis(self):
        """Execute continuous analysis until cancelled"""
        if not self.initialize():
            return
        
        print(f"\n🔄 CONTINUOUS ANALYSIS MODE ACTIVATED")
        print(f"💡 Press Ctrl+C to stop the analysis")
        print(f"📁 Results will be saved IMMEDIATELY to: {self.selected_stocks_file}")
        
        try:
            while True:
                self.execute_single_scan()
                
                # Wait before next iteration
                wait_time = 300  # 5 minutes between scans
                print(f"\n⏰ Waiting {wait_time//60} minutes before next scan...")
                print(f"💡 Next scan at: {(datetime.datetime.now() + datetime.timedelta(seconds=wait_time)).strftime('%H:%M:%S')}")
                
                # Countdown with progress updates
                for remaining in range(wait_time, 0, -60):  # Update every minute
                    if remaining > 60:
                        print(f"   Next scan in {remaining//60} minutes...")
                    else:
                        print(f"   Next scan in {remaining} seconds...")
                    time.sleep(60)
                
                print(f"\n🔄 Starting next scan iteration...")
                
        except KeyboardInterrupt:
            print(f"\n⏹️ Continuous analysis stopped by user")
        except Exception as e:
            print(f"\n💥 Fatal error in continuous analysis: {e}")
        finally:
            self.cleanup()

    def execute_analysis(self):
        """Main execution: single scan or continuous mode"""
        if not self.initialize():
            return
        
        if self.continuous_mode:
            self.execute_continuous_analysis()
        else:
            self.execute_single_scan()
            self.cleanup()

    def _print_iteration_summary(self):
        """Print iteration summary"""
        end_time = datetime.datetime.now()
        duration = end_time - self.start_time
        
        iteration_info = f" - Iteration #{self.iteration_count}" if self.continuous_mode else ""
        
        print(f"\n{'='*80}")
        print(f"📊 EXECUTION SUMMARY{iteration_info}")
        print(f"{'='*80}")
        print(f"✅ Successfully processed: {self.processed_count} stocks")
        print(f"❌ Errors encountered: {self.error_count} stocks")
        print(f"🎯 Strong trend stocks found: {len(self.strong_trend_stocks)}")
        print(f"⏰ Scan duration: {duration}")
        print(f"🏁 End Time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Display strong trend stocks summary
        if self.strong_trend_stocks:
            print(f"\n🏆 STRONG TREND STOCKS FOUND:")
            for stock in self.strong_trend_stocks:
                trend = stock['trend_result']['trend']
                confidence = stock['trend_result']['confidence']
                print(f"  {stock['symbol']}: {trend} ({confidence}% confidence)")
        else:
            print(f"\n📭 No strong trend stocks found in this scan.")
        
        if self.processed_count > 0:
            avg_time_per_stock = duration.total_seconds() / self.processed_count
            print(f"📈 Average time per stock: {avg_time_per_stock:.2f} seconds")
        
        if self.processed_count > 0:
            success_rate = (self.processed_count / len(STOCK_LIST)) * 100
            print(f"🎯 Success rate: {success_rate:.1f}%")
        
        print(f"{'='*80}")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.session:
            self.session.close()
            print("✅ Session closed")

def main():
    """Main entry point using configuration variable"""
    from stock_config import CONTINUOUS_MODE
    
    executor = StockAnalysisExecutor(continuous_mode=CONTINUOUS_MODE)
    
    try:
        executor.execute_analysis()
    except KeyboardInterrupt:
        print(f"\n⏹️ Analysis interrupted by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
    finally:
        executor.cleanup()

if __name__ == "__main__":
    from stock_config import CONTINUOUS_MODE
    mode = "CONTINUOUS" if CONTINUOUS_MODE else "SINGLE SCAN"
    print(f"💡 Running in {mode} mode (configure in stock_config.py)")
    main()