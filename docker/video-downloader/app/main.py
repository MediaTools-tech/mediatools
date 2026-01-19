"""
Video Downloader Docker - FastAPI Application
Main entry point for the web application.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get app directory
APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Video Downloader Docker...")
    
    # Initialize core services
    from app.core.settings_manager import settings_manager
    from app.core.download_service import download_service
    from app.utils.tools import tool_manager
    from app.api.websocket import setup_callbacks
    
    # Set up WebSocket callbacks
    setup_callbacks()
    
    # Ensure Deno is available and up-to-date
    logger.info("Checking Deno availability...")
    if tool_manager.ensure_deno():
        deno_status = tool_manager.deno.get_status()
        logger.info(f"Deno is ready (Version: {deno_status.get('version', 'Unknown')})")
    else:
        logger.warning("Deno could not be ensured. Some features may be limited.")
    
    logger.info(f"Download folder: {settings_manager.get_download_folder()}")
    logger.info(f"FFmpeg available: {download_service.context.ffmpeg_status.get('available', False)}")
    logger.info("Application ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Video Downloader Docker...")
    try:
        from app.core.download_service import download_service
        download_service.cancel()
        logger.info("Active downloads cancelled.")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")


# Create FastAPI app
app = FastAPI(
    title="Video Downloader Docker",
    description="Download videos and audio from YouTube, Spotify, and more",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Include API routers
from app.api import downloads, queue, settings, system, websocket

app.include_router(downloads.router)
app.include_router(queue.router)
app.include_router(settings.router)
app.include_router(system.router)
app.include_router(websocket.router)


# === HTML Routes ===

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page - download interface."""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Video Downloader"
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page."""
    from app.core.settings_manager import settings_manager
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "Settings",
        "settings": settings_manager.get_all()
    })


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """History page."""
    from app.core.queue_manager import queue_manager
    
    return templates.TemplateResponse("history.html", {
        "request": request,
        "title": "History",
        "history": queue_manager.get_history(100),
        "failed": queue_manager.get_failed_urls()
    })


# === Health Check ===

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    from app.core.settings_manager import settings_manager
    from app.core.download_service import download_service
    
    return {
        "status": "healthy",
        "settings": settings_manager.is_healthy(),
        "ffmpeg": download_service.context.ffmpeg_status.get("available", False)
    }


# === Error Handlers ===

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    if request.url.path.startswith("/api/"):
        return {"error": "Not found", "path": request.url.path}
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "title": "Video Downloader"},
        status_code=404
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
