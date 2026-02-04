"""Detect buying opportunities based on user preferences."""

from sqlalchemy.orm import Session

from app.models import StocksCache, UserPreferences
from app.analysis.defaults import (
    STOCKS_BY_SECTOR,
    MAJOR_ETFS,
    COMMODITIES,
    CRYPTO,
    BUFFETT_DEFAULTS,
    get_tickers_for_investment_types,
)
from app.analysis.stock_scorer import Opportunity, calculate_score, meets_criteria


def get_stocks_for_industries(db: Session, industries: list[str]) -> list[str]:
    """Get list of stock tickers for the given industries."""
    tickers = []
    for industry in industries:
        if industry in STOCKS_BY_SECTOR:
            tickers.extend(STOCKS_BY_SECTOR[industry])
    return list(set(tickers))  # Remove duplicates


def get_ticker_type(ticker: str) -> str:
    """Determine the investment type of a ticker."""
    if ticker in MAJOR_ETFS:
        return "ETFs"
    elif ticker in COMMODITIES:
        return "Commodities"
    elif ticker in CRYPTO:
        return "Crypto"
    else:
        return "Stocks"


def find_opportunities(
    db: Session,
    prefs: UserPreferences,
    include_etfs: bool = True,
) -> list[Opportunity]:
    """
    Find stocks that match user's criteria.

    Uses their personalized thresholds (prefilled from Buffett defaults, possibly edited).
    Filters based on user's investment type preferences.
    """
    opportunities = []

    # Get user's selected investment types (default to all if not set)
    investment_types = prefs.investment_types if prefs.investment_types else [
        "Stocks", "ETFs", "Commodities", "Crypto"
    ]

    # Start with tickers from selected investment types
    allowed_tickers = set(get_tickers_for_investment_types(investment_types))

    # Get tickers to scan based on user's favorite industries (for stocks only)
    if "Stocks" in investment_types:
        if prefs.favorite_industries:
            # Filter stocks by favorite industries
            industry_tickers = get_stocks_for_industries(db, prefs.favorite_industries)
            # Keep only stocks from favorite industries
            stock_tickers = set(industry_tickers)
            # Remove all stocks, keep only industry-filtered ones
            all_stocks = set(get_tickers_for_investment_types(["Stocks"]))
            allowed_tickers = (allowed_tickers - all_stocks) | stock_tickers

    # Handle ETF preference (existing behavior for backward compatibility)
    if "ETFs" in investment_types and prefs.prefer_stocks_over_etfs:
        # ETFs will be filtered later with stricter drop threshold
        pass
    elif "ETFs" not in investment_types:
        # Remove ETFs entirely
        allowed_tickers -= set(MAJOR_ETFS)

    tickers_to_scan = list(allowed_tickers)

    if not tickers_to_scan:
        # If nothing selected, scan all stocks as fallback
        tickers_to_scan = []
        for sector_stocks in STOCKS_BY_SECTOR.values():
            tickers_to_scan.extend(sector_stocks)
        tickers_to_scan = list(set(tickers_to_scan))

    # Query cached stock data
    stocks = db.query(StocksCache).filter(StocksCache.ticker.in_(tickers_to_scan)).all()

    # Get min weekly drop threshold
    min_weekly_drop = BUFFETT_DEFAULTS.get("min_weekly_drop", 0.05)

    for stock in stocks:
        # Check if stock meets criteria (including 5% weekly drop freshness filter)
        passes, drop = meets_criteria(stock, prefs, min_weekly_drop)
        if not passes:
            continue

        # Handle ETFs differently
        is_etf = stock.ticker in MAJOR_ETFS
        if is_etf and prefs.prefer_stocks_over_etfs:
            # Only include ETF if drop is significant enough
            if drop < prefs.etf_min_drop:
                continue

        # Score the opportunity
        score, reasons = calculate_score(stock, prefs)

        opportunities.append(
            Opportunity(
                stock=stock,
                score=score,
                drop_from_high=drop,
                reasons=reasons,
            )
        )

    # Sort by score descending
    return sorted(opportunities, key=lambda x: x.score, reverse=True)


def find_top_opportunities(
    db: Session,
    prefs: UserPreferences,
    limit: int = 5,
) -> list[Opportunity]:
    """Find the top N opportunities for a user."""
    all_opportunities = find_opportunities(db, prefs)
    return all_opportunities[:limit]
