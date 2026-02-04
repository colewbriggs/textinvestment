"""SQLAlchemy database models."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertFrequency(enum.Enum):
    """How often to send alerts to the user."""

    CORRECTIONS = "corrections"  # Only on significant market drops
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"


class MessageRole(enum.Enum):
    """Role in a conversation."""

    USER = "user"
    ASSISTANT = "assistant"


class User(Base):
    """User account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    preferences: Mapped["UserPreferences"] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    watchlist: Mapped[list["Watchlist"]] = relationship(
        "Watchlist", back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[list["Alert"]] = relationship(
        "Alert", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["ConversationHistory"]] = relationship(
        "ConversationHistory", back_populates="user", cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    """User's investment preferences and alert settings."""

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    alert_frequency: Mapped[AlertFrequency] = mapped_column(
        Enum(AlertFrequency), default=AlertFrequency.DAILY
    )
    favorite_industries: Mapped[list] = mapped_column(JSON, default=list)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)

    # Investment types to receive alerts for (Stocks, ETFs, Commodities, Crypto)
    investment_types: Mapped[list] = mapped_column(
        JSON, default=lambda: ["Stocks", "ETFs", "Commodities", "Crypto"]
    )

    # Value investing thresholds (Buffett defaults, user-editable)
    min_drop_threshold: Mapped[float] = mapped_column(Float, default=0.10)  # 10%
    max_pe: Mapped[float] = mapped_column(Float, default=25.0)
    max_debt_equity: Mapped[float] = mapped_column(Float, default=1.5)
    min_roe: Mapped[float] = mapped_column(Float, default=0.15)  # 15%
    prefer_stocks_over_etfs: Mapped[bool] = mapped_column(Boolean, default=True)
    etf_min_drop: Mapped[float] = mapped_column(Float, default=0.15)  # 15%

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="preferences")


class Watchlist(Base):
    """User's stock watchlist."""

    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="watchlist")


class Alert(Base):
    """Alerts sent to users."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)
    opportunity_score: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="alerts")


class StocksCache(Base):
    """Cached stock data."""

    __tablename__ = "stocks_cache"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weekly_change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % change over past week
    fifty_two_week_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fifty_two_week_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pe_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    roe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit_margin: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConversationHistory(Base):
    """Conversation history for AI context."""

    __tablename__ = "conversation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    related_ticker: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="conversations")
