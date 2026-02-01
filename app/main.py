"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.web.routes import router as web_router
from app.api.twilio_webhook import router as api_router
from app.api.cron import router as cron_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()

    yield

    # Shutdown (nothing to clean up for serverless)


app = FastAPI(
    title="Investment Advisor",
    description="A conversational text-based investment advisor",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files (only if directory exists)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(web_router)
app.include_router(api_router)
app.include_router(cron_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
