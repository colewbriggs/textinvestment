"""Twilio SMS integration for sending and receiving messages."""

from typing import Optional

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.config import get_settings

settings = get_settings()


class SMSService:
    """Service for sending SMS messages via Twilio."""

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number
        self._client: Optional[Client] = None

    @property
    def is_configured(self) -> bool:
        """Check if Twilio credentials are configured."""
        return bool(self.account_sid and self.auth_token and self.from_number)

    @property
    def client(self) -> Optional[Client]:
        """Lazy initialization of Twilio client."""
        if not self.is_configured:
            return None
        if self._client is None:
            self._client = Client(self.account_sid, self.auth_token)
        return self._client

    def send_sms(self, to_number: str, message: str) -> Optional[str]:
        """
        Send an SMS message.

        Returns the message SID if successful, None otherwise.
        """
        if not self.is_configured:
            print(f"[SMS] Twilio not configured. Would send to {to_number}: {message[:50]}...")
            return None

        try:
            # Truncate message if too long (SMS limit is 1600 chars for concatenated)
            if len(message) > 1600:
                message = message[:1597] + "..."

            msg = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number,
            )
            return msg.sid
        except TwilioRestException as e:
            print(f"Failed to send SMS to {to_number}: {e}")
            return None

    def send_alert(self, to_number: str, ticker: str, alert_message: str) -> Optional[str]:
        """Send an investment alert SMS."""
        return self.send_sms(to_number, alert_message)

    def send_welcome(self, to_number: str) -> Optional[str]:
        """Send a welcome message to a new user."""
        message = (
            "Welcome to Investment Advisor! 📈\n\n"
            "You'll receive alerts when we spot opportunities matching your preferences.\n\n"
            "Reply anytime with questions like:\n"
            "• 'What's on my watchlist?'\n"
            "• 'Add AAPL to my list'\n"
            "• 'Tell me about this stock'\n"
            "• 'Stop' to pause alerts\n\n"
            "Happy investing!"
        )
        return self.send_sms(to_number, message)

    def send_confirmation(self, to_number: str, ticker: str, action: str) -> Optional[str]:
        """Send a confirmation message for an action."""
        message = f"Got it! {action} {ticker}."
        return self.send_sms(to_number, message)


# Singleton instance
_sms_service: Optional[SMSService] = None


def get_sms_service() -> SMSService:
    """Get or create the SMS service singleton."""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
