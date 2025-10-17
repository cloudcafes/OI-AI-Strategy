# stock_database.py
# SQLite database operations for unique stock discovery tracking

import sqlite3
import datetime
from typing import List, Dict, Any, Optional

class StockDatabase:
    def __init__(self, db_path: str = "stock_discoveries.db"):
        self.db_path = db_path
        self.connection = None
        self.init_database()
    
    def init_database(self) -> bool:
        """Initialize database connection and create tables"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.create_tables()
            print(f"✅ Database initialized: {self.db_path}")
            return True
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def create_tables(self) -> None:
        """Create necessary tables if they don't exist"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS unique_discoveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            discovery_date DATE NOT NULL,
            discovery_time TIME NOT NULL,
            trend_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_symbol_date ON unique_discoveries(symbol, discovery_date)",
            "CREATE INDEX IF NOT EXISTS idx_date ON unique_discoveries(discovery_date)"
        ]
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(create_table_query)
            
            for index_query in create_index_queries:
                cursor.execute(index_query)
            
            self.connection.commit()
            print("✅ Database tables and indexes created successfully")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise
    
    def is_stock_discovered_today(self, symbol: str, current_date: str) -> bool:
        """Check if stock was already discovered today"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT COUNT(*) FROM unique_discoveries 
            WHERE symbol = ? AND discovery_date = ?
            """
            cursor.execute(query, (symbol, current_date))
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"❌ Error checking stock discovery: {e}")
            return False
    
    def record_unique_discovery(self, symbol: str, current_date: str, current_time: str, 
                              trend_type: str, confidence: float) -> bool:
        """Record a new unique stock discovery"""
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO unique_discoveries 
            (symbol, discovery_date, discovery_time, trend_type, confidence)
            VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(query, (symbol, current_date, current_time, trend_type, confidence))
            self.connection.commit()
            print(f"✅ Recorded unique discovery: {symbol} on {current_date} at {current_time}")
            return True
        except Exception as e:
            print(f"❌ Error recording unique discovery: {e}")
            return False
    
    def get_today_unique_stocks(self, current_date: str) -> List[Dict[str, Any]]:
        """Get all unique stocks discovered today"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT symbol, trend_type, confidence, discovery_time 
            FROM unique_discoveries 
            WHERE discovery_date = ? 
            ORDER BY discovery_time
            """
            cursor.execute(query, (current_date,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'symbol': row[0],
                    'trend_type': row[1],
                    'confidence': row[2],
                    'discovery_time': row[3]
                })
            return results
        except Exception as e:
            print(f"❌ Error fetching today's unique stocks: {e}")
            return []
    
    def get_unique_discoveries_count(self, current_date: str) -> int:
        """Get count of unique discoveries for today"""
        try:
            cursor = self.connection.cursor()
            query = "SELECT COUNT(*) FROM unique_discoveries WHERE discovery_date = ?"
            cursor.execute(query, (current_date,))
            return cursor.fetchone()[0]
        except Exception as e:
            print(f"❌ Error counting unique discoveries: {e}")
            return 0
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> bool:
        """Clean up records older than specified days"""
        try:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            cursor = self.connection.cursor()
            query = "DELETE FROM unique_discoveries WHERE discovery_date < ?"
            cursor.execute(query, (cutoff_date,))
            self.connection.commit()
            deleted_count = cursor.rowcount
            print(f"✅ Cleaned up {deleted_count} records older than {cutoff_date}")
            return True
        except Exception as e:
            print(f"❌ Error cleaning up old records: {e}")
            return False
    
    def close_connection(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("✅ Database connection closed")
    
    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close_connection()


# Global database instance
stock_db = None

def get_database_instance(db_path: str = "stock_discoveries.db") -> StockDatabase:
    """Get or create global database instance"""
    global stock_db
    if stock_db is None:
        stock_db = StockDatabase(db_path)
    return stock_db

def close_database_connection() -> None:
    """Close global database connection"""
    global stock_db
    if stock_db:
        stock_db.close_connection()
        stock_db = None