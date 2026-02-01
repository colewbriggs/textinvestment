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
    # Normalize phone number
    from_number = From.strip()
    message = Body.strip()

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
