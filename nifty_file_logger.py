# example_usage.py
from nifty_file_logger import (
    resend_latest_ai_query, 
    resend_specific_ai_query, 
    list_ai_query_files
)

def demonstrate_resend_functionality():
    """Demonstrate how to use the resend functionality"""
    
    print("🔄 AI QUERY RESEND DEMONSTRATION")
    print("=" * 50)
    
    # Option 1: List available files
    print("\n1. 📁 Listing available AI query files:")
    files = list_ai_query_files(limit=5)
    
    # Option 2: Resend the latest file
    print("\n2. 🔄 Resending latest AI query:")
    success = resend_latest_ai_query()
    
    if success:
        print("✅ Latest query resent successfully!")
    else:
        print("❌ Failed to resend latest query")
    
    # Option 3: Resend a specific file (if files exist)
    if files:
        print(f"\n3. 📄 Resending specific file: {files[0]}")
        success = resend_specific_ai_query(files[0])
        
        if success:
            print("✅ Specific query resent successfully!")
        else:
            print("❌ Failed to resend specific query")

if __name__ == "__main__":
    demonstrate_resend_functionality()