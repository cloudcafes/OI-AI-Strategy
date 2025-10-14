import sqlite3

# Database file path (matching the main script)
DB_FILE = "oi_data.db"
MAX_FETCH_CYCLES = 10

def display_all_oi_data():
    """Display all rows from oi_data table exactly as stored, like SELECT * FROM oi_data."""
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get distinct fetch cycles (up to MAX_FETCH_CYCLES)
        cursor.execute("""
            SELECT DISTINCT fetch_cycle 
            FROM oi_data 
            ORDER BY fetch_cycle DESC 
            LIMIT ?
        """, (MAX_FETCH_CYCLES,))
        cycles = cursor.fetchall()
        
        if not cycles:
            print("No data found in the oi_data table.")
            conn.close()
            return
        
        # Get total fetches from app_state
        cursor.execute("SELECT value FROM app_state WHERE key = 'total_fetches'")
        total_fetches_result = cursor.fetchone()
        total_fetches = total_fetches_result[0] if total_fetches_result else 0
        
        # Display all columns in oi_data
        columns = [
            'id', 'fetch_cycle', 'fetch_timestamp', 'nifty_value', 'expiry_date', 
            'strike_price', 'ce_change_oi', 'ce_volume', 'ce_ltp', 'ce_oi', 
            'pe_change_oi', 'pe_volume', 'pe_ltp', 'pe_oi', 'created_at'
        ]
        
        # Iterate through each fetch cycle
        for cycle in cycles:
            fetch_cycle = cycle[0]
            
            # Fetch all data for this cycle
            cursor.execute("""
                SELECT * FROM oi_data 
                WHERE fetch_cycle = ? 
                ORDER BY strike_price
            """, (fetch_cycle,))
            rows = cursor.fetchall()
            
            if not rows:
                print(f"\nFetch Cycle: {fetch_cycle} (No data)")
                continue
            
            # Display header for the cycle
            print(f"\nFetch Cycle: {fetch_cycle}/{MAX_FETCH_CYCLES} (Total Fetches: {total_fetches})")
            print("Columns: " + ", ".join(columns))
            print("-" * 80)
            
            # Display each row exactly as stored
            for row in rows:
                # Convert row to strings, handling None values
                row_str = [str(val) if val is not None else "NULL" for val in row]
                print(", ".join(row_str))
            
            print("-" * 80)
        
        # Show available cycles
        cursor.execute("SELECT DISTINCT fetch_cycle FROM oi_data ORDER BY fetch_cycle")
        available_cycles = [str(row[0]) for row in cursor.fetchall()]
        print(f"\nAvailable cycles in DB: {', '.join(available_cycles)}")
        print(f"\nDisplayed all available fetch cycles (up to {MAX_FETCH_CYCLES}).")
        
        conn.close()
    
    except Exception as e:
        print(f"Error reading from database: {e}")
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    display_all_oi_data()