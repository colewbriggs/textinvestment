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
    try:
        from_number = From.strip()
        message = Body.strip()

        # Normalize phone number - ensure it has + prefix
        if not from_number.startswith("+"):
            from_number = "+" + from_number

        # Find user
        user = db.query(User).filter(User.phone_number == from_number).first()

        if not user:
            twiml = MessagingResponse()
            twiml.message("Hi! I don't recognize your number. Please sign up at textinvestment.com to start receiving investment alerts.")
            return Response(content=str(twiml), media_type="application/xml")

        # Process with AI
        try:
            from app.services.conversation import get_conversation_service
            service = get_conversation_service()
            response_text = await service.handle_message(db, user, message)
        except Exception:
            response_text = "Thanks for your message! Our AI assistant is temporarily unavailable. We'll get back to you soon."

        twiml = MessagingResponse()
        twiml.message(response_text)
        return Response(content=str(twiml), media_type="application/xml")

    except Exception:
        twiml = MessagingResponse()
        twiml.message("Something went wrong. Please try again later.")
        return Response(content=str(twiml), media_type="application/xml")
