"""
Settings API endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    """Model for updating settings."""
    settings: Dict[str, Any]


class SingleSettingUpdate(BaseModel):
    """Model for updating a single setting."""
    key: str
    value: Any


@router.get("")
async def get_settings():
    """Get all current settings."""
    return {
        "settings": settings_manager.get_all(),
        "healthy": settings_manager.is_healthy()
    }


@router.get("/{key}")
async def get_setting(key: str):
    """Get a specific setting value."""
    value = settings_manager.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"key": key, "value": value}


@router.put("")
async def update_settings(update: SettingsUpdate):
    """Update multiple settings at once."""
    try:
        settings_manager.save_settings(update.settings)
        return {
            "success": True, 
            "message": "Settings updated",
            "settings": settings_manager.get_all()
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{key}")
async def update_single_setting(key: str, update: SingleSettingUpdate):
    """Update a single setting."""
    try:
        settings_manager.set(key, update.value)
        return {
            "success": True,
            "key": key,
            "value": settings_manager.get(key)
        }
    except Exception as e:
        logger.error(f"Error updating setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_settings():
    """Reset all settings to defaults."""
    settings_manager.reset_to_defaults()
    return {
        "success": True,
        "message": "Settings reset to defaults",
        "settings": settings_manager.get_all()
    }


@router.get("/paths/download")
async def get_download_path():
    """Get current download folder path."""
    return {
        "path": str(settings_manager.get_download_folder()),
        "exists": settings_manager.get_download_folder().exists()
    }


@router.get("/paths/all")
async def get_all_paths():
    """Get all configured paths."""
    return {
        "download_folder": str(settings_manager.get_download_folder()),
        "temp_folder": str(settings_manager.get_temp_folder()),
        "bin_folder": str(settings_manager.get_bin_folder()),
        "data_folder": str(settings_manager.get_data_folder())
    }


@router.get("/spotify/status")
async def get_spotify_status():
    """Check if Spotify credentials are configured."""
    credentials = settings_manager.get_spotify_credentials()
    return {
        "configured": credentials is not None,
        "use_credentials": settings_manager.get("use_spotify_credentials", False)
    }
