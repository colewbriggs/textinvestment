"""Twilio webhook endpoint for receiving SMS messages."""

from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from app.database import get_db
from app.handlers.sms_handler import handle_incoming_sms

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/sms/webhook")
async def sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Twilio webhook endpoint for incoming SMS messages.

    Twilio sends POST requests with:
    - From: The sender's phone number
    - Body: The message content
    - Plus other metadata we don't need

    We respond with TwiML containing the reply message.
    """
    from app.models import User

    # Normalize phone number
    from_number = From.strip()
    message = Body.strip()

    # Debug: try direct lookup
    user = db.query(User).filter(User.phone_number == from_number).first()
    if not user:
        # Return debug info
        all_phones = [u.phone_number for u in db.query(User).all()]
        twiml = MessagingResponse()
        twiml.message(f"Debug: Looking for '{from_number}', DB has: {all_phones}")
        return Response(content=str(twiml), media_type="application/xml")

    # Process the message through our handler
    response_text = await handle_incoming_sms(db, from_number, message)

    # Create TwiML response
    twiml = MessagingResponse()
    twiml.message(response_text)

    return Response(content=str(twiml), media_type="application/xml")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to check users in database."""
    from app.models import User
    users = db.query(User).all()
    return {
        "count": len(users),
        "users": [{"id": u.id, "phone": u.phone_number} for u in users]
    }


@router.get("/debug/lookup/{phone}")
async def debug_lookup(phone: str, db: Session = Depends(get_db)):
    """Debug endpoint to lookup a specific phone number."""
    from app.models import User
    # Try exact match
    user = db.query(User).filter(User.phone_number == phone).first()
    # Get all phones for comparison
    all_phones = [u.phone_number for u in db.query(User).all()]
    return {
        "searched_for": phone,
        "found": user is not None,
        "user_id": user.id if user else None,
        "all_phones_in_db": all_phones
    }
