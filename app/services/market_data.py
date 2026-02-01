"""Alpha Vantage market data integration."""

from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import StocksCache

settings = get_settings()

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


class MarketDataService:
    """Service for fetching market data from Alpha Vantage."""

    def __init__(self):
        self.api_key = settings.alpha_vantage_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_quote(self, ticker: str) -> Optional[dict]:
        """Get current quote for a ticker."""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": self.api_key,
        }
        try:
            response = await self.client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if "Global Quote" not in data or not data["Global Quote"]:
                return None

            quote = data["Global Quote"]
            return {
                "ticker": ticker,
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                "volume": int(quote.get("06. volume", 0)),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
            }
        except Exception:
            return None

    async def get_company_overview(self, ticker: str) -> Optional[dict]:
        """Get company overview including fundamentals."""
        params = {
            "function": "OVERVIEW",
            "symbol": ticker,
            "apikey": self.api_key,
        }
        try:
            response = await self.client.get(ALPHA_VANTAGE_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            if not data or "Symbol" not in data:
                return None

            return {
                "ticker": ticker,
                "name": data.get("Name"),
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "pe_ratio": _safe_float(data.get("PERatio")),
                "pb_ratio": _safe_float(data.get("PriceToBookRatio")),
                "roe": _safe_float(data.get("ReturnOnEquityTTM")),
                "debt_to_equity": _safe_float(data.get("DebtToEquity")),
                "profit_margin": _safe_float(data.get("ProfitMargin")),
                "fifty_two_week_high": _safe_float(data.get("52WeekHigh")),
                "fifty_two_week_low": _safe_float(data.get("52WeekLow")),
            }
        except Exception:
            return None

    async def update_stock_cache(self, db: Session, ticker: str) -> Optional[StocksCache]:
        """Fetch and cache stock data."""
        # Get both quote and overview
        quote = await self.get_quote(ticker)
        overview = await self.get_company_overview(ticker)

        if not quote and not overview:
            return None

        # Check if stock exists in cache
        stock = db.query(StocksCache).filter(StocksCache.ticker == ticker).first()

        if stock is None:
            stock = StocksCache(ticker=ticker)
            db.add(stock)

        # Update with quote data
        if quote:
            stock.last_price = quote.get("price")

        # Update with overview data
        if overview:
            stock.company_name = overview.get("name")
            stock.sector = overview.get("sector")
            stock.industry = overview.get("industry")
            stock.pe_ratio = overview.get("pe_ratio")
            stock.pb_ratio = overview.get("pb_ratio")
            stock.roe = overview.get("roe")
            stock.debt_to_equity = overview.get("debt_to_equity")
            stock.profit_margin = overview.get("profit_margin")
            stock.fifty_two_week_high = overview.get("fifty_two_week_high")
            stock.fifty_two_week_low = overview.get("fifty_two_week_low")

        stock.last_updated = datetime.utcnow()
        db.commit()
        db.refresh(stock)

        return stock

    async def refresh_stale_stocks(
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
                result = await self.update_stock_cache(db, ticker)
                if result:
                    updated.append(result)

        return updated


def _safe_float(value: Optional[str]) -> Optional[float]:
    """Safely convert a string to float."""
    if value is None or value == "None" or value == "-":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


# Singleton instance
_market_data_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """Get or create the market data service singleton."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service
