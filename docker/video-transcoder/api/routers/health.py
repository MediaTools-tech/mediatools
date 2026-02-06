from fastapi import APIRouter
from datetime import datetime
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "ffmpeg_available": os.system("ffmpeg -version > /dev/null 2>&1") == 0
    }

@router.get("/readiness")
async def readiness_check():
    """Readiness check for Kubernetes"""
    # Check if storage directories exist
    from api.config import settings
    
    uploads_exist = os.path.exists(settings.UPLOAD_DIR)
    outputs_exist = os.path.exists(settings.OUTPUT_DIR)
    
    is_ready = uploads_exist and outputs_exist
    
    return {
        "ready": is_ready,
        "checks": {
            "uploads_dir": uploads_exist,
            "outputs_dir": outputs_exist
        }
    }