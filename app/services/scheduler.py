"""APScheduler setup for scheduled market scans and alerts."""

from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Alert, AlertFrequency, User, UserPreferences
from app.analysis.dip_detector import find_top_opportunities
from app.analysis.defaults import STOCKS_BY_SECTOR
from app.services.market_data import get_market_data_service
from app.services.sms_service import get_sms_service


def generate_alert_message(opportunity) -> str:
    """Generate a natural, educational alert message."""
    stock = opportunity.stock
    drop_pct = opportunity.drop_from_high * 100

    # Build the message
    lines = [
        f"{stock.ticker} is down {drop_pct:.0f}% from its 52-week high.",
        "",
    ]

    # Add relevant metrics with context
    if stock.pe_ratio:
        lines.append(f"P/E Ratio: {stock.pe_ratio:.1f}")
    if stock.roe:
        lines.append(f"ROE: {stock.roe:.0%}")
    if stock.debt_to_equity:
        lines.append(f"Debt/Equity: {stock.debt_to_equity:.2f}")

    lines.append("")

    # Add educational context based on the opportunity reasons
    if opportunity.reasons:
        lines.append("Why this caught our eye:")
        for reason in opportunity.reasons[:3]:  # Limit to top 3 reasons
            lines.append(f"• {reason}")

    lines.append("")
    lines.append("Reply with any questions about this opportunity!")

    return "\n".join(lines)


async def refresh_stock_data(db: Session):
    """Refresh cached stock data for all tracked stocks."""
    market_service = get_market_data_service()

    # Get all unique tickers
    all_tickers = set()
    for sector_stocks in STOCKS_BY_SECTOR.values():
        all_tickers.update(sector_stocks)

    # Refresh stale data (older than 24 hours)
    await market_service.refresh_stale_stocks(db, list(all_tickers), max_age_hours=24)


async def scan_and_alert_realtime():
    """Scan for opportunities and send realtime alerts."""
    db = SessionLocal()
    try:
        sms_service = get_sms_service()

        # Get all active users with realtime alerts
        users = (
            db.query(User)
            .join(UserPreferences)
            .filter(
                User.is_active == True,
                UserPreferences.is_paused == False,
                UserPreferences.alert_frequency == AlertFrequency.REALTIME,
            )
            .all()
        )

        for user in users:
            if not user.preferences:
                continue

            # Find top opportunities for this user
            opportunities = find_top_opportunities(db, user.preferences, limit=1)

            for opp in opportunities:
                # Check if we already sent an alert for this stock today
                today = datetime.utcnow().date()
                existing = (
                    db.query(Alert)
                    .filter(
                        Alert.user_id == user.id,
                        Alert.ticker == opp.ticker,
                    )
                    .order_by(Alert.sent_at.desc())
                    .first()
                )

                if existing and existing.sent_at.date() == today:
                    continue  # Already alerted today

                # Generate and send alert
                message = generate_alert_message(opp)
                sms_service.send_alert(user.phone_number, opp.ticker, message)

                # Record the alert
                alert = Alert(
                    user_id=user.id,
                    ticker=opp.ticker,
                    opportunity_score=opp.score,
                    message=message,
                )
                db.add(alert)
                db.commit()

    finally:
        db.close()


async def send_daily_digest():
    """Send daily digest to users who prefer daily alerts."""
    db = SessionLocal()
    try:
        sms_service = get_sms_service()

        # Get all active users with daily alerts
        users = (
            db.query(User)
            .join(UserPreferences)
            .filter(
                User.is_active == True,
                UserPreferences.is_paused == False,
                UserPreferences.alert_frequency == AlertFrequency.DAILY,
            )
            .all()
        )

        for user in users:
            if not user.preferences:
                continue

            # Find top 3 opportunities for this user
            opportunities = find_top_opportunities(db, user.preferences, limit=3)

            if not opportunities:
                continue

            # Build digest message
            lines = ["📊 Daily Investment Digest", ""]

            for i, opp in enumerate(opportunities, 1):
                stock = opp.stock
                drop_pct = opp.drop_from_high * 100
                lines.append(f"{i}. {stock.ticker}: -{drop_pct:.0f}% from high")
                if stock.pe_ratio:
                    lines.append(f"   P/E: {stock.pe_ratio:.1f}")

            lines.append("")
            lines.append("Reply with a ticker for more details!")

            message = "\n".join(lines)
            sms_service.send_sms(user.phone_number, message)

            # Record alerts
            for opp in opportunities:
                alert = Alert(
                    user_id=user.id,
                    ticker=opp.ticker,
                    opportunity_score=opp.score,
                    message=f"Daily digest: {opp.ticker}",
                )
                db.add(alert)

            db.commit()

    finally:
        db.close()


async def send_weekly_digest():
    """Send weekly digest to users who prefer weekly alerts."""
    db = SessionLocal()
    try:
        sms_service = get_sms_service()

        # Get all active users with weekly alerts
        users = (
            db.query(User)
            .join(UserPreferences)
            .filter(
                User.is_active == True,
                UserPreferences.is_paused == False,
                UserPreferences.alert_frequency == AlertFrequency.WEEKLY,
            )
            .all()
        )

        for user in users:
            if not user.preferences:
                continue

            # Find top 5 opportunities for this user
            opportunities = find_top_opportunities(db, user.preferences, limit=5)

            if not opportunities:
                continue

            # Build weekly digest message
            lines = ["📈 Weekly Investment Roundup", ""]
            lines.append("Top opportunities this week:")
            lines.append("")

            for i, opp in enumerate(opportunities, 1):
                stock = opp.stock
                drop_pct = opp.drop_from_high * 100
                pe_info = f" (P/E: {stock.pe_ratio:.0f})" if stock.pe_ratio else ""
                lines.append(f"{i}. {stock.ticker}: -{drop_pct:.0f}%{pe_info}")

            lines.append("")
            lines.append("Reply with any ticker to learn more!")

            message = "\n".join(lines)
            sms_service.send_sms(user.phone_number, message)

            # Record alerts
            for opp in opportunities:
                alert = Alert(
                    user_id=user.id,
                    ticker=opp.ticker,
                    opportunity_score=opp.score,
                    message=f"Weekly digest: {opp.ticker}",
                )
                db.add(alert)

            db.commit()

    finally:
        db.close()


# Scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def setup_scheduler():
    """Set up scheduled jobs."""
    scheduler = get_scheduler()

    # Refresh stock data every hour during market hours (9 AM - 5 PM ET, Mon-Fri)
    scheduler.add_job(
        refresh_stock_data_job,
        CronTrigger(hour="9-17", minute=0, day_of_week="mon-fri"),
        id="refresh_stock_data",
        replace_existing=True,
    )

    # Scan for realtime alerts every 30 minutes during market hours
    scheduler.add_job(
        scan_and_alert_realtime,
        CronTrigger(hour="9-16", minute="0,30", day_of_week="mon-fri"),
        id="realtime_alerts",
        replace_existing=True,
    )

    # Send daily digest at 4:30 PM ET (after market close)
    scheduler.add_job(
        send_daily_digest,
        CronTrigger(hour=16, minute=30, day_of_week="mon-fri"),
        id="daily_digest",
        replace_existing=True,
    )

    # Send weekly digest on Sunday at 7 PM ET
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(hour=19, minute=0, day_of_week="sun"),
        id="weekly_digest",
        replace_existing=True,
    )


async def refresh_stock_data_job():
    """Wrapper for refresh_stock_data that creates its own session."""
    db = SessionLocal()
    try:
        await refresh_stock_data(db)
    finally:
        db.close()
