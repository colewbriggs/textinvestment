"""Default values for investment strategies."""

# Investment types users can choose to receive alerts for
INVESTMENT_TYPES = [
    "Stocks",
    "ETFs",
    "Commodities",
    "Crypto",
]

# Warren Buffett value investing defaults
BUFFETT_DEFAULTS = {
    "min_drop_threshold": 0.10,  # 10% from 52-week high
    "min_weekly_drop": 0.05,  # 5% drop in past week (freshness filter)
    "max_pe": 25.0,
    "max_debt_equity": 1.5,
    "min_roe": 0.15,  # 15%
    "prefer_stocks_over_etfs": False,  # ETFs use same threshold as stocks
    "etf_min_drop": 0.10,  # Same as stocks
    "investment_types": ["Stocks", "ETFs", "Commodities", "Crypto"],  # All enabled by default
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
    # Broad Market
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "VTI",   # Total Stock Market
    "IWM",   # Russell 2000
    "DIA",   # Dow Jones
    "VOO",   # Vanguard S&P 500
    "IVV",   # iShares S&P 500
    "VTV",   # Vanguard Value
    "VUG",   # Vanguard Growth
    "MDY",   # S&P MidCap 400
    # Sector ETFs
    "XLK",   # Technology
    "XLF",   # Financials
    "XLV",   # Healthcare
    "XLE",   # Energy
    "XLI",   # Industrials
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLU",   # Utilities
    "XLB",   # Materials
    "XLRE",  # Real Estate
    "XLC",   # Communication Services
    # Thematic / Popular
    "ARKK",  # ARK Innovation
    "SOXX",  # Semiconductors
    "IBB",   # Biotech
    "XBI",   # Biotech (equal weight)
    "SMH",   # Semiconductors (VanEck)
    "HACK",  # Cybersecurity
    "ICLN",  # Clean Energy
    "TAN",   # Solar
    # International
    "VEA",   # Developed Markets
    "VWO",   # Emerging Markets
    "EFA",   # EAFE (Europe, Australasia, Far East)
    "EEM",   # Emerging Markets (iShares)
    "IEMG",  # Core Emerging Markets
    # Bonds
    "TLT",   # 20+ Year Treasury
    "IEF",   # 7-10 Year Treasury
    "BND",   # Total Bond Market
    "LQD",   # Investment Grade Corporate
    "HYG",   # High Yield Corporate
    "AGG",   # Core U.S. Aggregate Bond
]

# Commodity tickers (ETFs that track commodities)
COMMODITIES = [
    "GLD",   # Gold
    "SLV",   # Silver
    "USO",   # Oil
    "UNG",   # Natural Gas
    "DBA",   # Agriculture
    "CORN",  # Corn
    "WEAT",  # Wheat
    "CPER",  # Copper
    "PALL",  # Palladium
    "PPLT",  # Platinum
]

# Crypto tickers (Yahoo Finance format)
CRYPTO = [
    "BTC-USD",   # Bitcoin
    "ETH-USD",   # Ethereum
    "SOL-USD",   # Solana
    "XRP-USD",   # Ripple
    "ADA-USD",   # Cardano
    "DOGE-USD",  # Dogecoin
    "AVAX-USD",  # Avalanche
    "DOT-USD",   # Polkadot
    "MATIC-USD", # Polygon
    "LINK-USD",  # Chainlink
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


def get_all_stocks() -> list[str]:
    """Get all stock tickers from all sectors."""
    tickers = []
    for sector_stocks in STOCKS_BY_SECTOR.values():
        tickers.extend(sector_stocks)
    return list(set(tickers))


def get_tickers_by_investment_type(investment_type: str) -> list[str]:
    """Get tickers for a specific investment type."""
    if investment_type == "Stocks":
        return get_all_stocks()
    elif investment_type == "ETFs":
        return MAJOR_ETFS.copy()
    elif investment_type == "Commodities":
        return COMMODITIES.copy()
    elif investment_type == "Crypto":
        return CRYPTO.copy()
    return []


def get_tickers_for_investment_types(investment_types: list[str]) -> list[str]:
    """Get all tickers for the given investment types."""
    tickers = []
    for inv_type in investment_types:
        tickers.extend(get_tickers_by_investment_type(inv_type))
    return list(set(tickers))
