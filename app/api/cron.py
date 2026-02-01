"""Cron endpoints for Vercel scheduled jobs."""

import asyncio
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertFrequency, User, StocksCache
from app.services.sms_service import get_sms_service
from app.services.market_data import get_market_data_service
from app.analysis.dip_detector import find_top_opportunities
from app.analysis.defaults import STOCKS_BY_SECTOR, MAJOR_ETFS

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/scan")
async def run_market_scan(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Run market scan and send alerts to users.
    Called by Vercel Cron every 4 hours.

    1. Refresh market data for key stocks
    2. Find opportunities
    3. Send alerts to users
    """
    market_service = get_market_data_service()
    sms_service = get_sms_service()

    # Get all tickers to monitor
    all_tickers = []
    for sector_stocks in STOCKS_BY_SECTOR.values():
        all_tickers.extend(sector_stocks)
    all_tickers.extend(MAJOR_ETFS)
    all_tickers = list(set(all_tickers))

    # Refresh stale stock data (Alpha Vantage free = 25 calls/day, so limit per run)
    # Refresh up to 5 stocks per cron run
    refreshed = await market_service.refresh_stale_stocks(db, all_tickers[:20], max_age_hours=24)

    # Get all active users
    users = (
        db.query(User)
        .join(User.preferences)
        .filter(User.is_active == True)
        .all()
    )

    alerts_sent = 0

    for user in users:
        prefs = user.preferences
        if not prefs or prefs.is_paused:
            continue

        # Find opportunities for this user
        opportunities = find_top_opportunities(db, prefs, limit=3)

        if not opportunities:
            continue

        # For corrections-only, only alert if there's a significant drop (>10%)
        significant = [o for o in opportunities if o.drop_from_high >= 0.10]

        if not significant:
            continue

        # Build and send alert message
        opp = significant[0]  # Top opportunity
        reason_text = opp.reasons[0] if opp.reasons else "Significant price drop detected"
        message = (
            f"{opp.ticker} is down {opp.drop_from_high:.0%} from its recent high.\n\n"
            f"{reason_text}\n\n"
            f"Reply with questions about this or any stock."
        )

        try:
            sms_service.send_alert(user.phone_number, opp.ticker, message)

            # Record alert
            alert = Alert(
                user_id=user.id,
                ticker=opp.ticker,
                opportunity_score=opp.score,
                message=message,
            )
            db.add(alert)
            alerts_sent += 1
        except Exception as e:
            print(f"Failed to send alert to {user.phone_number}: {e}")

    db.commit()

    await market_service.close()

    return {
        "status": "ok",
        "stocks_refreshed": len(refreshed),
        "alerts_sent": alerts_sent,
        "users_checked": len(users)
    }


@router.get("/refresh")
async def refresh_market_data(
    db: Session = Depends(get_db),
):
    """
    Manually refresh market data for all tracked stocks.
    Use sparingly due to API rate limits.
    """
    market_service = get_market_data_service()

    # Get all tickers
    all_tickers = []
    for sector_stocks in STOCKS_BY_SECTOR.values():
        all_tickers.extend(sector_stocks)
    all_tickers.extend(MAJOR_ETFS)
    all_tickers = list(set(all_tickers))

    # Refresh up to 20 stocks (API limit friendly)
    refreshed = await market_service.refresh_stale_stocks(db, all_tickers[:20], max_age_hours=1)

    await market_service.close()

    return {
        "status": "ok",
        "stocks_refreshed": len(refreshed),
        "tickers": [s.ticker for s in refreshed]
    }
