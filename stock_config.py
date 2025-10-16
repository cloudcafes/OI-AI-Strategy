# stock-config.py
# Configuration and stock list for F&O analysis

# Analysis Configuration
ENABLE_AI_ANALYSIS = False  # Set to False for Python-only analysis
RATE_LIMIT_DELAY = 3  # Increased delay to avoid rate limiting
MAX_RETRIES = 3
REQUEST_TIMEOUT = 20
SHOW_ONLY_FILTERED=True

# F&O Stock List (150+ symbols) - Reduced for testing
# STOCK_LIST = [
#     'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR',
#     'ICICIBANK', 'KOTAKBANK', 'HCLTECH', 'SBIN', 'BHARTIARTL',
#     'ITC', 'ASIANPAINT', 'DMART', 'BAJFINANCE', 'MARUTI',
#     'TITAN', 'SUNPHARMA', 'TATAMOTORS', 'LT', 'AXISBANK'
# ]

STOCK_LIST = [
    'PERSISTENT', 'IDEA', 'PRESTIGE', 'IIFL', 
    'BAJFINANCE', 'NESTLEIND', 'AUBANK', 'NCC', 'GODREJPROP', 
    'CHOLAFIN', 'COFORGE', 'HFCL', 'LTF', 'BAJAJFINSV', 
    '360ONE', 'PHOENIXLTD', 'HDFCAMC', 'LTIM', 'RBLBANK', 
    'CROMPTON', 'TRENT', 'ASIANPAINT', 'CANBK', 'LODHA', 
    'HDFCLIFE', 'OBEROIRLTY', 'PAYTM', 'JIOFIN', 'UNITDSPR', 
    'UNOMINDA', 'ETERNAL', 'NYKAA', 'LT', 'BLUESTARCO', 
    'NHPC', 'KEI', 'DLF', 'TIINDIA', 'HUDCO', 
    'HAL', 'INDUSTOWER', 'RVNL', 'TVSMOTOR', 'BPCL', 
    'RECLTD', 'PFC', 'ULTRACEMCO', 'MAZDOCK', 'ABCAPITAL', 
    'MANAPPURAM', 'BANKINDIA', 'OIL', 'ANGELONE', 'IRCTC', 
    'UNIONBANK', 'SBICARD', 'BHEL', 'ADANIPORTS', 'NBCC', 
    'BANKBARODA', 'KALYANKJIL', 'GAIL', 'INDIGO', 'ALKEM', 
    'ADANIENSOL', 'POWERGRID', 'CAMS', 'BEL', 'NUVAMA', 
    'CGPOWER', 'TATASTEEL', 'MPHASIS', 'HINDZINC', 'MCX', 
    'DMART', 'GRASIM', 'TATAPOWER', 'MUTHOOTFIN', 'SBILIFE', 
    'ASTRAL', 'DABUR', 'GMRAIRPORT', 'JSWSTEEL', 'TATATECH', 
    'VOLTAS', 'COLPAL', 'ADANIGREEN', 'SRF', 'ONGC', 
    'HINDPETRO', 'ABB', 'UPL', 'NAUKRI', 'BIOCON', 
    'PETRONET', 'SBIN', 'JSWENERGY', 'CDSL', 'ICICIBANK', 
    'BRITANNIA', 'PNB', 'HAVELLS', 'FORTIS', 'BHARTIARTL', 
    'COALINDIA', 'TORNTPOWER', 'INDHOTEL', 'INDIANB', 
    'KFINTECH', 'NATIONALUM', 'BOSCHLTD', 'INOXWIND', 'SHREECEM', 
    'SUPREMEIND', 'ITC', 'GODREJCP', 'ADANIENT', 'DIXON', 
    'POLYCAB', 'WIPRO', 'TITAGARH', 'BDL', 'KAYNES', 
    'SAIL', 'NTPC', 'PPLPHARMA', 'NMDC', 'AMBUJACEM', 
    'BHARATFORG', 'APOLLOHOSP', 'IOC', 'PNBHOUSING', 'HINDALCO', 
    'VBL', 'LICHSGFIN', 'PIDILITIND', 'JINDALSTEL', 'PAGEIND', 
    'JUBLFOOD', 'KPITTECH', 'IRFC', 'TATAELXSI', 'SHRIRAMFIN', 
    'BANDHANBNK', 'HINDUNILVR', 'FEDERALBNK', 'APLAPOLLO', 'IREDA', 
    'CONCOR', 'VEDL', 'TORNTPHARM', 'SOLARINDS', 'SYNGENE', 
    'SIEMENS', 'TCS', 'IGL', 'CUMMINSIND', 'PGEL', 
    'DALBHARAT', 'ASHOKLEY', 'BSE', 'CIPLA', 'IDFCFIRSTB', 
    'SONACOMS', 'YESBANK', 'SAMMAANCAP', 'PATANJALI', 'TITAN', 
    'LUPIN', 'HDFCBANK', 'POWERINDIA', 'MANKIND', 'EICHERMOT', 
    'HCLTECH', 'PIIND', 'SUZLON', 'MARICO', 'DIVISLAB', 
    'RELIANCE', 'SUNPHARMA', 'MOTHERSON', 'KOTAKBANK', 'LICI', 
    'IEX', 'GLENMARK', 'MFSL', 'MARUTI', 'MAXHEALTH', 
    'LAURUSLABS', 'AXISBANK', 'ZYDUSLIFE', 'EXIDEIND', 'AMBER', 
    'DRREDDY', 'TATACONSUM', 'HEROMOTOCO', 'TECHM', 'TATAMOTORS', 
    'BAJAJ-AUTO', 'INFY', 'AUROPHARMA', 'INDUSINDBK', 'ICICIPRULI', 
    'DELHIVERY', 'POLICYBZR', 'OFSS', 'CYIENT'
]

# API Headers Configuration
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/",
    "Origin": "https://www.nseindia.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

# Display Configuration
SHOW_DETAILED_OUTPUT = True