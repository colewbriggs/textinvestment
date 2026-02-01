"""Web routes for signup, settings, and dashboard."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Alert, AlertFrequency, User, UserPreferences, Watchlist
from app.analysis.defaults import BUFFETT_DEFAULTS, INDUSTRIES
from app.services.sms_service import get_sms_service

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect to signup page."""
    return RedirectResponse(url="/signup")


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Display the signup form."""
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get("/signup/a", response_class=HTMLResponse)
async def signup_a(request: Request):
    """Design option A - Dark/bold."""
    return templates.TemplateResponse("signup_a.html", {"request": request})


@router.get("/signup/b", response_class=HTMLResponse)
async def signup_b(request: Request):
    """Design option B - Minimal/clean."""
    return templates.TemplateResponse("signup_b.html", {"request": request})


@router.get("/signup/c", response_class=HTMLResponse)
async def signup_c(request: Request):
    """Design option C - Warm/friendly."""
    return templates.TemplateResponse("signup_c.html", {"request": request})


@router.get("/prototypes", response_class=HTMLResponse)
async def prototypes_page(request: Request):
    """Dashboard design prototypes."""
    return templates.TemplateResponse("dashboard_prototypes.html", {"request": request})


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
    skip_sms: str = Form(None),
    db: Session = Depends(get_db),
):
    """Handle signup form submission."""
    # Normalize phone number
    phone_number = phone_number.strip()
    if not phone_number.startswith("+"):
        phone_number = "+1" + phone_number.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")

    # Check if Twilio is configured (skip check if testing)
    sms_service = get_sms_service()
    if not sms_service.is_configured and not skip_sms:
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "SMS service is not configured. Please try again later.",
            },
        )

    # Check if user already exists
    existing = db.query(User).filter(User.phone_number == phone_number).first()
    if existing:
        # In test mode, just redirect to dashboard
        if skip_sms:
            return RedirectResponse(url=f"/dashboard/{existing.id}", status_code=303)
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "error": "This phone number is already registered.",
            },
        )

    # Create user
    user = User(
        phone_number=phone_number,
        onboarding_complete=False,
    )
    db.add(user)
    db.flush()

    # Create preferences with Buffett defaults
    prefs = UserPreferences(
        user_id=user.id,
        alert_frequency=AlertFrequency.DAILY,
        favorite_industries=[],
        min_drop_threshold=BUFFETT_DEFAULTS["min_drop_threshold"],
        max_pe=BUFFETT_DEFAULTS["max_pe"],
        max_debt_equity=BUFFETT_DEFAULTS["max_debt_equity"],
        min_roe=BUFFETT_DEFAULTS["min_roe"],
        prefer_stocks_over_etfs=BUFFETT_DEFAULTS["prefer_stocks_over_etfs"],
    )
    db.add(prefs)
    db.commit()

    # Set default preferences for MVP (all industries, corrections only)
    prefs.alert_frequency = AlertFrequency.CORRECTIONS
    prefs.favorite_industries = []  # Empty = all industries
    user.onboarding_complete = True
    db.commit()

    # Send welcome SMS
    sms_service.send_welcome(phone_number)

    # Go directly to dashboard
    return RedirectResponse(url=f"/dashboard/{user.id}", status_code=303)


@router.get("/onboarding/{user_id}", response_class=HTMLResponse)
async def onboarding_page(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Display onboarding wizard (Option B - layman friendly)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        "onboarding_b.html",
        {
            "request": request,
            "user": user,
            "industries": INDUSTRIES,
        },
    )


@router.get("/onboarding/{user_id}/a", response_class=HTMLResponse)
async def onboarding_page_a(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Display onboarding wizard (Option A - technical)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse(
        "onboarding.html",
        {
            "request": request,
            "user": user,
            "industries": INDUSTRIES,
        },
    )


# Strategy presets
STRATEGY_PRESETS = {
    "value": {
        "min_drop_threshold": 0.10,
        "max_pe": 25.0,
        "max_debt_equity": 1.5,
        "min_roe": 0.15,
        "prefer_stocks_over_etfs": True,
    },
    "growth": {
        "min_drop_threshold": 0.15,
        "max_pe": 50.0,
        "max_debt_equity": 2.0,
        "min_roe": 0.10,
        "prefer_stocks_over_etfs": True,
    },
    "dividend": {
        "min_drop_threshold": 0.08,
        "max_pe": 20.0,
        "max_debt_equity": 1.0,
        "min_roe": 0.12,
        "prefer_stocks_over_etfs": True,
    },
}


@router.post("/onboarding/{user_id}")
async def onboarding_submit(
    request: Request,
    user_id: int,
    strategy: str = Form("value"),
    industries: list[str] = Form([]),
    alert_frequency: str = Form("daily"),
    db: Session = Depends(get_db),
):
    """Handle onboarding form submission."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prefs = user.preferences
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)

    # Apply strategy preset
    preset = STRATEGY_PRESETS.get(strategy, STRATEGY_PRESETS["value"])
    prefs.min_drop_threshold = preset["min_drop_threshold"]
    prefs.max_pe = preset["max_pe"]
    prefs.max_debt_equity = preset["max_debt_equity"]
    prefs.min_roe = preset["min_roe"]
    prefs.prefer_stocks_over_etfs = preset["prefer_stocks_over_etfs"]

    # Set user selections
    prefs.favorite_industries = industries
    prefs.alert_frequency = AlertFrequency(alert_frequency)

    # Mark onboarding complete
    user.onboarding_complete = True

    db.commit()

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
        },
    )


@router.post("/settings/{user_id}")
async def settings_submit(
    request: Request,
    user_id: int,
    alert_frequency: str = Form("daily"),
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
