"""Detect buying opportunities based on user preferences."""

from sqlalchemy.orm import Session

from app.models import StocksCache, UserPreferences
from app.analysis.defaults import STOCKS_BY_SECTOR, MAJOR_ETFS
from app.analysis.stock_scorer import Opportunity, calculate_score, meets_criteria


def get_stocks_for_industries(db: Session, industries: list[str]) -> list[str]:
    """Get list of stock tickers for the given industries."""
    tickers = []
    for industry in industries:
        if industry in STOCKS_BY_SECTOR:
            tickers.extend(STOCKS_BY_SECTOR[industry])
    return list(set(tickers))  # Remove duplicates


def find_opportunities(
    db: Session,
    prefs: UserPreferences,
    include_etfs: bool = True,
) -> list[Opportunity]:
    """
    Find stocks that match user's criteria.

    Uses their personalized thresholds (prefilled from Buffett defaults, possibly edited).
    """
    opportunities = []

    # Get tickers to scan based on user's favorite industries
    tickers_to_scan = get_stocks_for_industries(db, prefs.favorite_industries)

    # Add ETFs if user wants them
    if include_etfs and not prefs.prefer_stocks_over_etfs:
        tickers_to_scan.extend(MAJOR_ETFS)

    if not tickers_to_scan:
        # If no industries selected, scan all stocks
        tickers_to_scan = []
        for sector_stocks in STOCKS_BY_SECTOR.values():
            tickers_to_scan.extend(sector_stocks)
        tickers_to_scan = list(set(tickers_to_scan))

    # Query cached stock data
    stocks = db.query(StocksCache).filter(StocksCache.ticker.in_(tickers_to_scan)).all()

    for stock in stocks:
        # Check if stock meets criteria
        passes, drop = meets_criteria(stock, prefs)
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
