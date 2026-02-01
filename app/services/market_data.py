"""Yahoo Finance market data integration."""

from datetime import datetime, timedelta
from typing import Optional

import yfinance as yf
from sqlalchemy.orm import Session

from app.models import StocksCache


class MarketDataService:
    """Service for fetching market data from Yahoo Finance."""

    def get_stock_data(self, ticker: str) -> Optional[dict]:
        """Get current data for a ticker."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or 'currentPrice' not in info:
                # Try fast_info for basic price data
                fast = stock.fast_info
                if hasattr(fast, 'last_price') and fast.last_price:
                    return {
                        "ticker": ticker,
                        "price": fast.last_price,
                        "fifty_two_week_high": getattr(fast, 'year_high', None),
                        "fifty_two_week_low": getattr(fast, 'year_low', None),
                    }
                return None

            return {
                "ticker": ticker,
                "name": info.get("shortName") or info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": info.get("returnOnEquity"),
                "debt_to_equity": _convert_debt_equity(info.get("debtToEquity")),
                "profit_margin": info.get("profitMargins"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    def update_stock_cache(self, db: Session, ticker: str) -> Optional[StocksCache]:
        """Fetch and cache stock data."""
        data = self.get_stock_data(ticker)

        if not data:
            return None

        # Check if stock exists in cache
        stock = db.query(StocksCache).filter(StocksCache.ticker == ticker).first()

        if stock is None:
            stock = StocksCache(ticker=ticker)
            db.add(stock)

        # Update with data
        stock.last_price = data.get("price")
        stock.company_name = data.get("name")
        stock.sector = data.get("sector")
        stock.industry = data.get("industry")
        stock.pe_ratio = data.get("pe_ratio")
        stock.pb_ratio = data.get("pb_ratio")
        stock.roe = data.get("roe")
        stock.debt_to_equity = data.get("debt_to_equity")
        stock.profit_margin = data.get("profit_margin")
        stock.fifty_two_week_high = data.get("fifty_two_week_high")
        stock.fifty_two_week_low = data.get("fifty_two_week_low")
        stock.last_updated = datetime.utcnow()

        db.commit()
        db.refresh(stock)

        return stock

    def refresh_stale_stocks(
        self,
        db: Session,
        tickers: list[str],
        max_age_hours: int = 24,
    ) -> list[StocksCache]:
        """Refresh stocks that haven't been updated recently."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        updated = []

        for ticker in tickers:
            stock = db.query(StocksCache).filter(StocksCache.ticker == ticker).first()

            if stock is None or stock.last_updated < cutoff:
                result = self.update_stock_cache(db, ticker)
                if result:
                    updated.append(result)

        return updated

    def refresh_all_stocks(self, db: Session, tickers: list[str]) -> list[StocksCache]:
        """Refresh all stocks regardless of age."""
        updated = []
        for ticker in tickers:
            result = self.update_stock_cache(db, ticker)
            if result:
                updated.append(result)
        return updated


def _convert_debt_equity(value) -> Optional[float]:
    """Convert debt/equity from percentage to ratio if needed."""
    if value is None:
        return None
    # yfinance returns D/E as percentage (e.g., 150 for 1.5 ratio)
    if value > 10:
        return value / 100
    return value


# Singleton instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get or create the market data service singleton."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
