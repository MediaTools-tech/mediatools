"""
Download API endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional
import logging

from app.core.download_service import download_service
from app.core.download_context import DownloadStatus
from app.core.queue_manager import queue_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/download", tags=["downloads"])


class DownloadRequest(BaseModel):
    """Request model for download endpoint."""
    url: str
    type: str = "video"  # "video" or "audio"


class DownloadResponse(BaseModel):
    """Response model for download endpoint."""
    success: bool
    message: str
    download_id: Optional[str] = None


@router.post("", response_model=DownloadResponse)
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """
    Start a new download.
    The download runs in background and progress is reported via WebSocket.
    """
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    if request.type not in ["video", "audio"]:
        raise HTTPException(status_code=400, detail="Type must be 'video' or 'audio'")
    
    # Add to queue
    queue_manager.add_url(request.url, request.type)
    
    # Start worker in background
    background_tasks.add_task(download_service.start_worker)
    
    # Check if already downloading to provide accurate message
    current_status = download_service.get_status()
    is_busy = current_status["status"] not in [DownloadStatus.IDLE.value, 
                                             DownloadStatus.COMPLETED.value,
                                             DownloadStatus.ERROR.value,
                                             DownloadStatus.CANCELLED.value]
    
    message = f"Download started for {request.url}"
    if is_busy:
        message = "Added to queue - another download is in progress"
        
    logger.info(f"Accepted download request: {request.url} ({request.type})")
    
    return DownloadResponse(
        success=True,
        message=message
    )


@router.post("/cancel")
async def cancel_download():
    """Cancel the current download."""
    download_service.cancel()
    return {"success": True, "message": "Download cancelled"}


@router.post("/pause")
async def pause_download():
    """Pause the current download (limited support)."""
    download_service.pause()
    return {"success": True, "message": "Download paused"}


@router.post("/resume")
async def resume_download():
    """Resume a paused download."""
    download_service.resume()
    return {"success": True, "message": "Download resumed"}


@router.get("/status")
async def get_download_status():
    """Get current download status."""
    return download_service.get_status()
