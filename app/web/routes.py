"""Web routes for signup, settings, and dashboard."""

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertFrequency, User, UserPreferences, Watchlist
from app.analysis.defaults import BUFFETT_DEFAULTS, INDUSTRIES, INVESTMENT_TYPES
from app.services.sms_service import get_sms_service

router = APIRouter()
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect to signup page."""
    return RedirectResponse(url="/signup")


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Display the signup form."""
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    """Privacy policy page."""
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    """Terms of service page."""
    return templates.TemplateResponse("terms.html", {"request": request})


@router.post("/signup")
async def signup_submit(
    request: Request,
    phone_number: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle signup form submission."""
    # Normalize phone number
    phone_number = phone_number.strip()
    if not phone_number.startswith("+"):
        phone_number = "+1" + phone_number.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

    # Check if user already exists - redirect to their dashboard
    existing = db.query(User).filter(User.phone_number == phone_number).first()
    if existing:
        return RedirectResponse(url=f"/dashboard/{existing.id}", status_code=303)

    # Check if Twilio is configured (only needed for new signups)
    sms_service = get_sms_service()
    if not sms_service.is_configured:
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "SMS service is not configured. Please try again later.",
            },
        )

    # Create user
    user = User(
        phone_number=phone_number,
        onboarding_complete=True,
    )
    db.add(user)
    db.flush()

    # Create preferences with defaults (corrections only, all industries, all investment types)
    prefs = UserPreferences(
        user_id=user.id,
        alert_frequency=AlertFrequency.CORRECTIONS,
        investment_types=BUFFETT_DEFAULTS["investment_types"],
        favorite_industries=[],
        min_drop_threshold=BUFFETT_DEFAULTS["min_drop_threshold"],
        max_pe=BUFFETT_DEFAULTS["max_pe"],
        max_debt_equity=BUFFETT_DEFAULTS["max_debt_equity"],
        min_roe=BUFFETT_DEFAULTS["min_roe"],
        prefer_stocks_over_etfs=BUFFETT_DEFAULTS["prefer_stocks_over_etfs"],
    )
    db.add(prefs)
    db.commit()

    # Send welcome SMS
    sms_service.send_welcome(phone_number)

    # Go directly to dashboard
    return RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)


@router.get("/settings/{user_id}", response_class=HTMLResponse)
async def settings_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Display user settings page."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.preferences

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "prefs": prefs,
            "industries": INDUSTRIES,
            "investment_types": INVESTMENT_TYPES,
        },
    )


@router.post("/settings/{user_id}")
async def settings_submit(
    request: Request,
    user_id: int,
    alert_frequency: str = Form("daily"),
    investment_types: list[str] = Form([]),
    industries: list[str] = Form([]),
    min_drop_threshold: float = Form(BUFFETT_DEFAULTS["min_drop_threshold"]),
    max_pe: float = Form(BUFFETT_DEFAULTS["max_pe"]),
    max_debt_equity: float = Form(BUFFETT_DEFAULTS["max_debt_equity"]),
    min_roe: float = Form(BUFFETT_DEFAULTS["min_roe"]),
    prefer_stocks: bool = Form(True),
    is_paused: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Handle settings form submission."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.preferences
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)

    prefs.alert_frequency = AlertFrequency(alert_frequency)
    prefs.investment_types = investment_types if investment_types else INVESTMENT_TYPES
    prefs.favorite_industries = industries
    prefs.min_drop_threshold = min_drop_threshold / 100 if min_drop_threshold > 1 else min_drop_threshold
    prefs.max_pe = max_pe
    prefs.max_debt_equity = max_debt_equity
    prefs.min_roe = min_roe / 100 if min_roe > 1 else min_roe
    prefs.prefer_stocks_over_etfs = prefer_stocks
    prefs.is_paused = is_paused

    db.commit()

    return RedirectResponse(url=f"/settings/{user_id}?saved=1", status_code=303)


@router.post("/settings/{user_id}/watchlist/add")
async def add_to_watchlist(
    user_id: int,
    ticker: str = Form(...),
    db: Session = Depends(get_db),
):
    """Add a ticker to the user's watchlist."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ticker = ticker.upper().strip()

    # Check if already exists
    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.ticker == ticker)
        .first()
    )
    if not existing:
        item = Watchlist(user_id=user_id, ticker=ticker)
        db.add(item)
        db.commit()

    return RedirectResponse(url=f"/settings/{user_id}", status_code=303)


@router.post("/settings/{user_id}/watchlist/remove/{ticker}")
async def remove_from_watchlist(
    user_id: int,
    ticker: str,
    db: Session = Depends(get_db),
):
    """Remove a ticker from the user's watchlist."""
    item = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user_id, Watchlist.ticker == ticker)
        .first()
    )
    if item:
        db.delete(item)
        db.commit()

    return RedirectResponse(url=f"/settings/{user_id}", status_code=303)


@router.get("/dashboard/{user_id}", response_class=HTMLResponse)
async def dashboard_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Display user dashboard."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.preferences
    alerts = (
        db.query(Alert)
        .filter(Alert.user_id == user_id)
        .order_by(Alert.sent_at.desc())
        .limit(10)
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "prefs": prefs,
            "alerts": alerts,
        },
    )


@router.post("/dashboard/{user_id}/toggle")
async def toggle_monitoring(user_id: int, db: Session = Depends(get_db)):
    """Toggle monitoring on/off."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.preferences
    if prefs:
        prefs.is_paused = not prefs.is_paused
        db.commit()

    return RedirectResponse(url=f"/dashboard/{user_id}", status_code=303)
