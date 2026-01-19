"""
Queue API endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import logging
from urllib.parse import unquote

from app.core.queue_manager import queue_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/queue", tags=["queue"])


class QueueItem(BaseModel):
    """Queue item model."""
    url: str
    type: str
    added_at: Optional[str] = None


class AddToQueueRequest(BaseModel):
    """Request to add URL to queue."""
    url: str
    type: str = "video"


@router.get("")
async def get_queue():
    """Get all queued URLs."""
    return {
        "queue": queue_manager.get_all_queued_urls(),
        "count": queue_manager.get_queue_count()
    }


@router.post("")
async def add_to_queue(request: AddToQueueRequest):
    """Add a URL to the queue."""
    if not request.url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    success = queue_manager.add_url(request.url, request.type)
    
    if success:
        return {"success": True, "message": "Added to queue"}
    else:
        return {"success": False, "message": "URL already in queue"}


@router.delete("/{url:path}")
async def remove_from_queue(url: str):
    """Remove a URL from the queue."""
    decoded_url = unquote(url)
    success = queue_manager.remove_url(decoded_url)
    
    if success:
        return {"success": True, "message": "Removed from queue"}
    else:
        raise HTTPException(status_code=404, detail="URL not found in queue")


@router.delete("")
async def clear_queue():
    """Clear all URLs from the queue."""
    queue_manager.clear_queue()
    return {"success": True, "message": "Queue cleared"}


# Failed URLs endpoints

@router.get("/failed")
async def get_failed_urls():
    """Get all failed URLs."""
    return {
        "failed": queue_manager.get_failed_urls(),
        "count": queue_manager.get_failed_url_count()
    }


@router.post("/retry/{url:path}")
async def retry_failed_url(url: str, background_tasks: BackgroundTasks):
    """Move a failed URL back to the queue for retry."""
    from app.core.download_service import download_service
    
    decoded_url = unquote(url)
    success = queue_manager.retry_failed_url(decoded_url)
    
    if success:
        # Start worker in background
        background_tasks.add_task(download_service.start_worker)
        return {"success": True, "message": "URL added back to queue"}
    else:
        raise HTTPException(status_code=404, detail="URL not found in failed list")


@router.delete("/failed/{url:path}")
async def remove_failed_url(url: str):
    """Remove a URL from the failed list."""
    decoded_url = unquote(url)
    success = queue_manager.remove_failed_url(decoded_url)
    
    if success:
        return {"success": True, "message": "Removed from failed list"}
    else:
        raise HTTPException(status_code=404, detail="URL not found in failed list")


@router.delete("/failed")
async def clear_failed():
    """Clear all failed URLs."""
    queue_manager.clear_failed()
    return {"success": True, "message": "Failed URLs cleared"}


# History endpoints

@router.get("/history")
async def get_history(limit: int = 100):
    """Get download history."""
    return {
        "history": queue_manager.get_history(limit),
        "limit": limit
    }


@router.delete("/history")
async def clear_history():
    """Clear download history."""
    queue_manager.clear_history()
    return {"success": True, "message": "History cleared"}


@router.get("/status")
async def get_queue_status():
    """Get full queue status including counts."""
    return queue_manager.get_status()


@router.get("/session")
async def check_session():
    """Check if there's a previous session with pending data."""
    from app.core.settings_manager import settings_manager
    from app.core.download_service import download_service
    
    # Only offer prompt if:
    # 1. Multisession support is enabled
    # 2. Session hasn't been handled yet
    # 3. Not currently processing a download
    if not settings_manager.get("multisession_queue_download_support", True):
        return {"needed": False}
        
    if queue_manager.is_session_handled():
        return {"needed": False}
        
    if download_service._is_processing:
        return {"needed": False}
        
    queue_count = queue_manager.get_queue_count()
    failed_count = queue_manager.get_failed_url_count()
    
    # If no data, mark as handled anyway to stop checking
    if queue_count == 0 and failed_count == 0:
        queue_manager.mark_session_handled()
        return {"needed": False}
        
    # Mark as handled as soon as we report it, so it only happens once per app start
    queue_manager.mark_session_handled()
    
    return {
        "needed": True,
        "queue_count": queue_count,
        "failed_count": failed_count
    }


class SessionActionRequest(BaseModel):
    action: str  # delete, ignore, continue


@router.post("/session/action")
async def handle_session_action(request: SessionActionRequest, background_tasks: BackgroundTasks):
    """Handle user action for previous session data."""
    from app.core.download_service import download_service
    
    action = request.action.lower()
    
    # Mark handled regardless of action (except invalid)
    queue_manager.mark_session_handled()
    
    if action == "delete":
        queue_manager.clear_queue()
        queue_manager.clear_failed()
        return {"success": True, "message": "Previous session data deleted"}
        
    elif action == "continue":
        # Start worker in background
        background_tasks.add_task(download_service.start_worker)
        return {"success": True, "message": "Resuming previous downloads"}
        
    elif action == "ignore":
        return {"success": True, "message": "Ignoring previous session for now"}
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
