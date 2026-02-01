"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.web.routes import router as web_router
from app.api.twilio_webhook import router as api_router
from app.services.scheduler import get_scheduler, setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()

    # Set up and start scheduler
    scheduler = get_scheduler()
    setup_scheduler()
    scheduler.start()

    yield

    # Shutdown
    scheduler.shutdown()


app = FastAPI(
    title="Investment Advisor",
    description="A conversational text-based investment advisor",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(web_router)
app.include_router(api_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
