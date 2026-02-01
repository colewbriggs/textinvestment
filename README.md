# Investment Advisor

A conversational text-based investment advisor with web signup. Users choose their investment philosophy (starting with Buffett-style value investing), receive SMS alerts with natural explanations of why opportunities matter, and can reply to ask follow-up questions.

## Features

- **Web GUI** for user signup and settings management
- **Pluggable Strategies** - Buffett value investing with easy extensibility
- **Configurable Alerts** - Realtime, daily digest, or weekly frequency
- **SMS Notifications** via Twilio
- **Conversational AI** - Reply with questions and get intelligent answers
- **Natural Learning** - Alerts explain the "why" behind opportunities

## Quick Start

1. **Install dependencies**
   ```bash
   cd investor
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Visit the signup page**
   ```
   http://localhost:8000/signup
   ```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key for market data |
| `ANTHROPIC_API_KEY` | Anthropic API key for conversational AI |
| `DATABASE_URL` | SQLite database URL (default: sqlite:///./investor.db) |
| `SECRET_KEY` | Secret key for sessions |
| `BASE_URL` | Base URL of your application |

## Twilio Webhook Setup

1. Use ngrok to expose your local server:
   ```bash
   ngrok http 8000
   ```

2. In Twilio console, set your phone number's webhook to:
   ```
   https://your-ngrok-url.ngrok.io/api/sms/webhook
   ```

## SMS Commands (Natural Language)

The AI understands natural language, so users can say things like:

- "Add Tesla to my watchlist"
- "What's on my list?"
- "Tell me more about that P/E ratio"
- "Why did you suggest this stock?"
- "Stop sending me alerts"
- "Resume notifications"

## Project Structure

```
investor/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment config
│   ├── models.py            # SQLAlchemy models
│   ├── database.py          # Database setup
│   ├── web/                 # Web GUI
│   │   ├── routes.py        # Web routes
│   │   └── templates/       # Jinja2 templates
│   ├── api/                 # API endpoints
│   │   └── twilio_webhook.py
│   ├── services/            # Business logic
│   │   ├── market_data.py   # Alpha Vantage client
│   │   ├── sms_service.py   # Twilio integration
│   │   ├── conversation.py  # Claude AI handler
│   │   └── scheduler.py     # APScheduler jobs
│   ├── analysis/            # Investment analysis
│   │   ├── defaults.py      # Buffett defaults
│   │   ├── dip_detector.py  # Opportunity finder
│   │   └── stock_scorer.py  # Value scoring
│   └── handlers/
│       └── sms_handler.py   # SMS message routing
├── requirements.txt
├── .env.example
└── README.md
```

## License

MIT
