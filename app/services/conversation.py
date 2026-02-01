"""Claude AI conversation service for handling user questions and actions."""

import json
from typing import Optional

import anthropic
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Alert,
    ConversationHistory,
    MessageRole,
    StocksCache,
    User,
    UserPreferences,
    Watchlist,
)

settings = get_settings()

# Tools available to the AI for taking actions
TOOLS = [
    {
        "name": "add_to_watchlist",
        "description": "Add a stock ticker to the user's watchlist",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, TSLA)",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "remove_from_watchlist",
        "description": "Remove a stock ticker from the user's watchlist",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol to remove",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "get_watchlist",
        "description": "Get the user's current watchlist",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "pause_notifications",
        "description": "Pause all notifications for the user",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "resume_notifications",
        "description": "Resume notifications for the user",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_stock_info",
        "description": "Get current information about a specific stock",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                }
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "unsubscribe",
        "description": "Completely unsubscribe the user from the service",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


def build_system_prompt(
    user: User,
    prefs: UserPreferences,
    watchlist: list[str],
    recent_alert: Optional[Alert],
) -> str:
    """Build the system prompt with user context."""
    alert_context = ""
    if recent_alert:
        alert_context = f"""
The most recent alert sent to this user was about {recent_alert.ticker}:
"{recent_alert.message}"
"""

    return f"""You are a friendly investment advisor assistant helping users learn about investing through real opportunities.

User Context:
- Alert frequency: {prefs.alert_frequency.value}
- Notifications: {"paused" if prefs.is_paused else "active"}
- Favorite industries: {", ".join(prefs.favorite_industries) if prefs.favorite_industries else "none selected"}
- Watchlist: {", ".join(watchlist) if watchlist else "empty"}
- Investment thresholds: Min drop {prefs.min_drop_threshold:.0%}, Max P/E {prefs.max_pe}, Max D/E {prefs.max_debt_equity}, Min ROE {prefs.min_roe:.0%}
{alert_context}

Guidelines:
1. Be conversational and educational - explain concepts when users ask
2. Keep responses concise (this is SMS) but informative
3. Use the tools to take actions when users request them
4. When discussing stocks, mention relevant metrics like P/E, debt levels, ROE
5. Always relate advice back to the user's preferences when relevant
6. If a user asks about a recent alert, use the context above
7. Be encouraging but realistic - never promise returns
8. If unsure about a ticker, ask for clarification

Remember: You're teaching users to think like value investors while helping them manage their alerts and watchlist."""


class ConversationService:
    """Service for handling AI-powered conversations."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def get_recent_messages(
        self, db: Session, user_id: int, limit: int = 10
    ) -> list[dict]:
        """Get recent conversation history formatted for Claude."""
        messages = (
            db.query(ConversationHistory)
            .filter(ConversationHistory.user_id == user_id)
            .order_by(ConversationHistory.created_at.desc())
            .limit(limit)
            .all()
        )

        # Reverse to get chronological order
        messages = list(reversed(messages))

        return [{"role": msg.role.value, "content": msg.content} for msg in messages]

    def get_watchlist(self, db: Session, user_id: int) -> list[str]:
        """Get user's watchlist tickers."""
        items = db.query(Watchlist).filter(Watchlist.user_id == user_id).all()
        return [item.ticker for item in items]

    def get_last_alert(self, db: Session, user_id: int) -> Optional[Alert]:
        """Get the most recent alert sent to the user."""
        return (
            db.query(Alert)
            .filter(Alert.user_id == user_id)
            .order_by(Alert.sent_at.desc())
            .first()
        )

    def save_message(
        self,
        db: Session,
        user_id: int,
        role: MessageRole,
        content: str,
        related_ticker: Optional[str] = None,
    ):
        """Save a message to conversation history."""
        msg = ConversationHistory(
            user_id=user_id,
            role=role,
            content=content,
            related_ticker=related_ticker,
        )
        db.add(msg)
        db.commit()

    def execute_tool(
        self, db: Session, user: User, tool_name: str, tool_input: dict
    ) -> str:
        """Execute a tool call and return the result."""
        if tool_name == "add_to_watchlist":
            ticker = tool_input["ticker"].upper()
            # Check if already in watchlist
            existing = (
                db.query(Watchlist)
                .filter(Watchlist.user_id == user.id, Watchlist.ticker == ticker)
                .first()
            )
            if existing:
                return f"{ticker} is already on your watchlist."
            item = Watchlist(user_id=user.id, ticker=ticker)
            db.add(item)
            db.commit()
            return f"Added {ticker} to your watchlist."

        elif tool_name == "remove_from_watchlist":
            ticker = tool_input["ticker"].upper()
            item = (
                db.query(Watchlist)
                .filter(Watchlist.user_id == user.id, Watchlist.ticker == ticker)
                .first()
            )
            if item:
                db.delete(item)
                db.commit()
                return f"Removed {ticker} from your watchlist."
            return f"{ticker} wasn't on your watchlist."

        elif tool_name == "get_watchlist":
            items = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
            if not items:
                return "Your watchlist is empty."
            tickers = [item.ticker for item in items]
            return f"Your watchlist: {', '.join(tickers)}"

        elif tool_name == "pause_notifications":
            if user.preferences:
                user.preferences.is_paused = True
                db.commit()
            return "Notifications paused. Reply 'resume' anytime to start again."

        elif tool_name == "resume_notifications":
            if user.preferences:
                user.preferences.is_paused = False
                db.commit()
            return "Notifications resumed! You'll receive alerts when we spot opportunities."

        elif tool_name == "get_stock_info":
            ticker = tool_input["ticker"].upper()
            stock = db.query(StocksCache).filter(StocksCache.ticker == ticker).first()
            if not stock:
                return f"I don't have data for {ticker} yet. It may not be in our tracking list."

            info_parts = [f"{ticker}"]
            if stock.company_name:
                info_parts[0] = f"{stock.company_name} ({ticker})"
            if stock.last_price:
                info_parts.append(f"Price: ${stock.last_price:.2f}")
            if stock.pe_ratio:
                info_parts.append(f"P/E: {stock.pe_ratio:.1f}")
            if stock.roe:
                info_parts.append(f"ROE: {stock.roe:.1%}")
            if stock.debt_to_equity:
                info_parts.append(f"D/E: {stock.debt_to_equity:.2f}")
            if stock.fifty_two_week_high and stock.last_price:
                drop = (stock.fifty_two_week_high - stock.last_price) / stock.fifty_two_week_high
                info_parts.append(f"Down {drop:.1%} from 52-week high")

            return " | ".join(info_parts)

        elif tool_name == "unsubscribe":
            user.is_active = False
            db.commit()
            return "You've been unsubscribed. We're sorry to see you go! Reply anytime to resubscribe."

        return "Unknown action."

    async def handle_message(self, db: Session, user: User, message: str) -> str:
        """
        Handle an incoming message from a user.

        Uses Claude to understand intent, take actions, and generate a response.
        """
        # Get context
        prefs = user.preferences or UserPreferences(user_id=user.id)
        watchlist = self.get_watchlist(db, user.id)
        recent_alert = self.get_last_alert(db, user.id)
        history = self.get_recent_messages(db, user.id, limit=10)

        # Build messages for Claude
        messages = history + [{"role": "user", "content": message}]

        # Call Claude
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,  # Keep responses concise for SMS
            system=build_system_prompt(user, prefs, watchlist, recent_alert),
            tools=TOOLS,
            messages=messages,
        )

        # Process tool calls
        tool_results = []
        final_text = ""

        for block in response.content:
            if block.type == "tool_use":
                result = self.execute_tool(db, user, block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
            elif block.type == "text":
                final_text = block.text

        # If there were tool calls, get a final response
        if tool_results:
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            final_response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=build_system_prompt(user, prefs, watchlist, recent_alert),
                messages=messages,
            )

            for block in final_response.content:
                if block.type == "text":
                    final_text = block.text
                    break

        # Save conversation
        self.save_message(db, user.id, MessageRole.USER, message)
        self.save_message(db, user.id, MessageRole.ASSISTANT, final_text)

        return final_text


# Singleton instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """Get or create the conversation service singleton."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
