"""Cron endpoints for Vercel scheduled jobs."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertFrequency, User
from app.services.sms_service import get_sms_service
from app.analysis.dip_detector import find_top_opportunities

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/scan")
async def run_market_scan(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
):
    """
    Run market scan and send alerts to users.
    Called by Vercel Cron every 4 hours.
    """
    # In production, verify the request is from Vercel Cron
    # by checking the Authorization header matches CRON_SECRET

    sms_service = get_sms_service()

    # Get all active users with corrections-only alerts
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
        significant = [o for o in opportunities if o.drop_percent >= 0.10]

        if not significant:
            continue

        # Build and send alert message
        opp = significant[0]  # Top opportunity
        message = (
            f"{opp.ticker} is down {opp.drop_percent:.0%} from its recent high.\n\n"
            f"{opp.reason}\n\n"
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

    return {"status": "ok", "alerts_sent": alerts_sent, "users_checked": len(users)}
