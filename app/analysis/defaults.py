"""Default values for investment strategies."""

# Warren Buffett value investing defaults
BUFFETT_DEFAULTS = {
    "min_drop_threshold": 0.10,  # 10% from 52-week high
    "max_pe": 25.0,
    "max_debt_equity": 1.5,
    "min_roe": 0.15,  # 15%
    "prefer_stocks_over_etfs": True,
    "etf_min_drop": 0.15,  # 15% for ETFs
}

# Available industries for user selection
INDUSTRIES = [
    "Technology",
    "Healthcare",
    "Financial Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Industrials",
    "Energy",
    "Utilities",
    "Real Estate",
    "Materials",
    "Communication Services",
]

# Common ETFs to track
MAJOR_ETFS = [
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "VTI",   # Total Stock Market
    "IWM",   # Russell 2000
    "DIA",   # Dow Jones
]

# Popular stocks by sector for scanning
STOCKS_BY_SECTOR = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMZN", "CRM", "ADBE", "INTC", "AMD"],
    "Healthcare": ["JNJ", "UNH", "PFE", "MRK", "ABBV", "LLY", "TMO", "ABT", "BMY", "AMGN"],
    "Financial Services": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP", "V"],
    "Consumer Discretionary": ["TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "CMG", "LULU"],
    "Consumer Staples": ["PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL", "MDLZ", "KHC"],
    "Industrials": ["CAT", "HON", "UNP", "UPS", "BA", "GE", "MMM", "LMT", "RTX", "DE"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "KMI"],
    "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC"],
    "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB"],
    "Materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "DOW", "DD", "PPG"],
    "Communication Services": ["GOOG", "META", "DIS", "NFLX", "CMCSA", "VZ", "T", "CHTR", "TMUS", "EA"],
}
