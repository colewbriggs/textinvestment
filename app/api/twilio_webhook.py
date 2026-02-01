"""Twilio webhook endpoint for receiving SMS messages."""

from fastapi import APIRouter, Depends, Form, Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/sms/webhook")
async def sms_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: Session = Depends(get_db),
):
    """Twilio webhook endpoint for incoming SMS messages."""
    from_number = From.strip()
    message = Body.strip()

    # Find user
    user = db.query(User).filter(User.phone_number == from_number).first()

    if not user:
        twiml = MessagingResponse()
        twiml.message("Hi! I don't recognize your number. Please sign up at our website to start receiving investment alerts.")
        return Response(content=str(twiml), media_type="application/xml")

    # Try to process with AI, fall back to simple response on error
    try:
        from app.handlers.sms_handler import handle_incoming_sms
        response_text = await handle_incoming_sms(db, from_number, message)
    except Exception as e:
        response_text = f"Got your message! (AI temporarily unavailable: {str(e)[:100]})"

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
    users = db.query(User).all()
    return {
        "count": len(users),
        "users": [{"id": u.id, "phone": u.phone_number} for u in users]
    }
