"""SMS message handler - routes all messages through conversation AI."""

from sqlalchemy.orm import Session

from app.models import User
from app.services.conversation import get_conversation_service
from app.services.sms_service import get_sms_service


async def handle_incoming_sms(db: Session, from_number: str, message: str) -> str:
    """
    Handle an incoming SMS message.

    All messages go through the AI conversation handler - no command parsing needed.
    The AI understands natural language and takes appropriate actions.

    Returns the response message to send back.
    """
    # Find the user by phone number
    user = db.query(User).filter(User.phone_number == from_number).first()

    if not user:
        # Unknown user - prompt them to sign up
        return (
            "Hi! I don't recognize your number. "
            "Please sign up at our website to start receiving investment alerts."
        )

    if not user.is_active:
        # Reactivate user if they message us
        user.is_active = True
        db.commit()

    # Route through conversation AI
    conversation_service = get_conversation_service()
    response = await conversation_service.handle_message(db, user, message)

    return response


async def send_sms_response(to_number: str, message: str):
    """Send an SMS response to the user."""
    sms_service = get_sms_service()
    sms_service.send_sms(to_number, message)
