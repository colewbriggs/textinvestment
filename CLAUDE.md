# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server (with hot reload)
uvicorn app.main:app --reload --port 8000

# Run with virtual environment
source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Expose local server for Twilio webhooks
ngrok http 8000
```

## Architecture

This is a **text-based investment alert service** built with FastAPI. Users sign up via web, receive SMS alerts when markets drop significantly, and can reply to ask questions via Claude AI.

### Three Main Request Flows

1. **Web Flow**: `/signup` → Creates user with default preferences → Redirects to `/dashboard`

2. **SMS Incoming Flow**: Twilio webhook (`/api/sms/webhook`) → `sms_handler.py` → `ConversationService` (Claude AI with tools) → Returns TwiML response

3. **Background Alert Flow**: APScheduler jobs → `MarketDataService` fetches data → `DipDetector` + `StockScorer` find opportunities → `SMSService` sends alerts

### Service Layer (Singletons)

- **ConversationService** (`services/conversation.py`): Claude AI integration with tools (add/remove watchlist, pause alerts, get stock info)
- **SMSService** (`services/sms_service.py`): Twilio wrapper, gracefully handles unconfigured state
- **MarketDataService** (`services/market_data.py`): Alpha Vantage API client with DB caching (24hr TTL)
- **Scheduler** (`services/scheduler.py`): APScheduler background jobs for market scans and digests

### Analysis Engine

- **defaults.py**: Stock universe (~100 stocks across 11 sectors), Buffett-style thresholds, major ETFs
- **dip_detector.py**: Filters stocks by user criteria (drop %, P/E, D/E, ROE)
- **stock_scorer.py**: Scores opportunities 0-100 based on value metrics

### Data Models

```
User (1:1) → UserPreferences (alert_frequency, thresholds, is_paused)
User (1:*) → Watchlist, Alert, ConversationHistory
StocksCache (global) → Cached market data
```

### Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, lifespan (DB init, scheduler start) |
| `app/web/routes.py` | All web endpoints (signup, dashboard, settings) |
| `app/api/twilio_webhook.py` | SMS receive endpoint |
| `app/handlers/sms_handler.py` | Routes SMS to conversation service |
| `app/services/conversation.py` | Claude AI with tool_use protocol |
| `app/models.py` | SQLAlchemy ORM models |

### Alert Frequency Enum

`AlertFrequency`: CORRECTIONS (big drops only), REALTIME, DAILY, WEEKLY

### Current MVP State

The app is simplified to MVP mode:
- Single-page signup (phone → dashboard)
- Monitors all assets (stocks, crypto, commodities)
- Only alerts on significant corrections
- Dashboard shows "Coming Soon" for advanced features
