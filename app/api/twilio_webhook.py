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

        # Try to process with AI
        try:
            from app.services.conversation import get_conversation_service
            service = get_conversation_service()
            response_text = await service.handle_message(db, user, message)
        except Exception as ai_error:
            response_text = f"Thanks for your message! Our AI assistant is temporarily unavailable. We'll get back to you soon."

        twiml = MessagingResponse()
        twiml.message(response_text)
        return Response(content=str(twiml), media_type="application/xml")

    except Exception as e:
        twiml = MessagingResponse()
        twiml.message(f"Something went wrong. Please try again later.")
        return Response(content=str(twiml), media_type="application/xml")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/debug/anthropic")
async def debug_anthropic():
    """Test if anthropic can be imported."""
    try:
        import anthropic
        from app.config import get_settings
        settings = get_settings()
        has_key = bool(settings.anthropic_api_key)
        key_preview = settings.anthropic_api_key[:10] + "..." if has_key else "NOT SET"
        return {
            "anthropic_imported": True,
            "api_key_set": has_key,
            "key_preview": key_preview
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/debug/users")
async def debug_users(db: Session = Depends(get_db)):
    """Debug endpoint to check users in database."""
    users = db.query(User).all()
    return {
        "count": len(users),
        "users": [{"id": u.id, "phone": u.phone_number} for u in users]
    }
