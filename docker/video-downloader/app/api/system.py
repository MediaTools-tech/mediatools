"""
System API endpoints.
Handles system operations like opening folders, playing media, and shutdown.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import platform
import subprocess
import os
import sys
from pathlib import Path
from typing import Optional, List
import logging

from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])

# Detect platform
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def is_wsl():
    """Check if the environment is WSL."""
    if not IS_LINUX:
        return False
    # Check platform release
    if "microsoft" in platform.release().lower():
        return True
    # Check proc version
    try:
        if os.path.exists("/proc/version"):
            with open("/proc/version", "r") as f:
                if "microsoft" in f.read().lower():
                    return True
    except:
        pass
    return False

def is_docker():
    """Check if the environment is Docker."""
    # Check for .dockerenv file (most reliable indicator)
    if os.path.exists("/.dockerenv"):
        return True
    # Check for docker in cgroup
    try:
        if os.path.exists("/proc/self/cgroup"):
            with open("/proc/self/cgroup", "r") as f:
                if "docker" in f.read().lower():
                    return True
    except:
        pass
    return False

IS_WSL = is_wsl()
IS_DOCKER = is_docker()


def open_path_in_explorer(path: Path) -> bool:
    """Open a path in the system file explorer, with WSL and Docker support."""
    try:
        path_str = str(path)
        
        # Docker doesn't have display/GUI access
        if IS_DOCKER:
            logger.warning(f"Docker environment detected - file explorer not available for {path_str}")
            return False
        
        if IS_WSL:
            # For WSL, we need to convert to Windows path and use explorer.exe
            try:
                # Try to use wslpath to get the Windows path
                win_path = subprocess.check_output(["wslpath", "-w", path_str], text=True, stderr=subprocess.DEVNULL).strip()
                # Run explorer.exe with the Windows path. 
                # Note: explorer.exe often returns 1 even on success in WSL.
                subprocess.run(["explorer.exe", win_path])
                return True # Assume success if we reached here
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback: explorer.exe can sometimes handle Linux paths relative to the root
                # but we disable check=True because of the exit code 1 issue
                subprocess.run(["explorer.exe", path_str])
                return True
        elif IS_WINDOWS:
            os.startfile(path_str)
        elif IS_MAC:
            subprocess.run(["open", path_str], check=True)
        elif IS_LINUX:
            subprocess.run(["xdg-open", path_str], check=True)
        else:
            logger.warning(f"Unsupported platform: {platform.system()}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Failed to open path {path}: {e}")
        return False


def play_media_file(file_path: Path) -> bool:
    """Play a media file with the default system player, with WSL and Docker support."""
    try:
        path_str = str(file_path)
        
        # Docker doesn't have display/GUI access
        if IS_DOCKER:
            logger.warning(f"Docker environment detected - media playback not available for {path_str}")
            return False
        
        if IS_WSL:
            # For WSL, we use 'cmd.exe /c start' with the Windows path
            try:
                win_path = subprocess.check_output(["wslpath", "-w", path_str], text=True, stderr=subprocess.DEVNULL).strip()
                # We need to escape the path for cmd.exe
                # Use start "" "path" to handle quotes correctly
                subprocess.run(["cmd.exe", "/c", "start", "", win_path])
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to explorer.exe which can also "open/play" files
                subprocess.run(["explorer.exe", path_str])
                return True
        elif IS_WINDOWS:
            os.startfile(path_str)
        elif IS_MAC:
            subprocess.run(["open", path_str], check=True)
        elif IS_LINUX:
            subprocess.run(["xdg-open", path_str], check=True)
        else:
            logger.warning(f"Unsupported platform: {platform.system()}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Failed to play media {file_path}: {e}")
        return False


def get_latest_media_file(download_dir: Path) -> Optional[Path]:
    """Find the most recently downloaded media file."""
    
    # Common media extensions
    media_extensions = {
        ".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv",  # Video
        ".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav", ".aac"  # Audio
    }
    
    # Partial download patterns to exclude
    partial_patterns = [".part", ".ytdl", ".temp", ".tmp"]
    
    latest_file = None
    latest_time = 0
    
    try:
        for file_path in download_dir.rglob("*"):
            if not file_path.is_file():
                continue
            
            # Check extension
            if file_path.suffix.lower() not in media_extensions:
                continue
            
            # Skip partial downloads
            if any(pattern in file_path.name.lower() for pattern in partial_patterns):
                continue
            
            # Check modification time
            mtime = file_path.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_file = file_path
        
        return latest_file
        
    except Exception as e:
        logger.error(f"Error finding latest media: {e}")
        return None


@router.get("/open/downloads")
async def open_downloads_folder():
    """Open the downloads folder in the system file explorer."""
    download_folder = settings_manager.get_download_folder()
    
    if not download_folder.exists():
        download_folder.mkdir(parents=True, exist_ok=True)
    
    # Docker-specific message
    if IS_DOCKER:
        return {
            "success": False,
            "message": "File explorer not available in Docker. Use the web interface to browse and download files.",
            "downloads_path": str(download_folder),
            "environment": "docker"
        }
    
    success = open_path_in_explorer(download_folder)
    
    if success:
        return {"success": True, "message": f"Opened: {download_folder}", "environment": "host"}
    else:
        raise HTTPException(
            status_code=500, 
            detail="Could not open downloads folder. This may not work in Docker without display access."
        )


@router.get("/open/docs")
async def open_docs_folder():
    """Open the docs folder in the system file explorer."""
    docs_folder = settings_manager.get_docs_folder()
    
    if not docs_folder.exists():
        docs_folder.mkdir(parents=True, exist_ok=True)
    
    # Docker-specific message
    if IS_DOCKER:
        return {
            "success": False,
            "message": "File explorer not available in Docker. Use the web interface to browse files.",
            "docs_path": str(docs_folder),
            "environment": "docker"
        }
    
    success = open_path_in_explorer(docs_folder)
    
    if success:
        return {"success": True, "message": f"Opened: {docs_folder}", "environment": "host"}
    else:
        raise HTTPException(
            status_code=500, 
            detail="Could not open docs folder. This may not work in Docker without display access."
        )


@router.get("/open/folder")
async def open_custom_folder(path: str):
    """Open a custom folder path in the system file explorer."""
    folder_path = Path(path)
    
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {path}")
    
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a folder: {path}")
    
    success = open_path_in_explorer(folder_path)
    
    if success:
        return {"success": True, "message": f"Opened: {folder_path}"}
    else:
        raise HTTPException(status_code=500, detail="Could not open folder")


@router.get("/play-latest")
async def play_latest_media():
    """Play the most recently downloaded media file with the default player."""
    download_folder = settings_manager.get_download_folder()
    
    latest_file = get_latest_media_file(download_folder)
    
    if not latest_file:
        raise HTTPException(
            status_code=404, 
            detail="No media files found in downloads folder"
        )
    
    # Docker-specific message
    if IS_DOCKER:
        return {
            "success": False,
            "message": "Media playback not available in Docker. Download the file and play it locally.",
            "file": {
                "name": latest_file.name,
                "path": str(latest_file),
                "size": latest_file.stat().st_size,
                "extension": latest_file.suffix
            },
            "environment": "docker"
        }
    
    success = play_media_file(latest_file)
    
    if success:
        return {
            "success": True, 
            "message": f"Playing: {latest_file.name}",
            "file": str(latest_file),
            "environment": "host"
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail="Could not play media file. This may not work in Docker without display access."
        )


@router.get("/latest-media")
async def get_latest_media_info():
    """Get information about the most recently downloaded media file."""
    download_folder = settings_manager.get_download_folder()
    
    latest_file = get_latest_media_file(download_folder)
    
    if not latest_file:
        return {"found": False, "message": "No media files found"}
    
    stat = latest_file.stat()
    
    return {
        "found": True,
        "file": {
            "name": latest_file.name,
            "path": str(latest_file),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "extension": latest_file.suffix
        }
    }


@router.post("/exit")
async def graceful_exit():
    """Gracefully shutdown the application by sending a signal."""
    import signal
    import asyncio
    
    logger.info("Shutdown requested via API")
    
    # Schedule signal after response is sent
    async def shutdown():
        await asyncio.sleep(0.5)
        # Send signal to the process or process group
        if IS_WINDOWS:
            # On Windows, we'll use SIGTERM which is generally better handled for exit
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            # On Linux/WSL, targeting the process group ensures both 
            # the app and any uvicorn reloader are terminated.
            try:
                os.killpg(os.getpgrp(), signal.SIGINT)
            except Exception as e:
                logger.warning(f"killpg failed, falling back to kill: {e}")
                os.kill(os.getpid(), signal.SIGINT)
        
        # Hard exit fallback after 5 seconds if still alive
        await asyncio.sleep(5)
        logger.warning("Application failed to exit gracefully, forcing exit.")
        os._exit(0)
    
    asyncio.create_task(shutdown())
    
    return {"success": True, "message": "Shutting down..."}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.core.download_service import download_service
    from app.core.queue_manager import queue_manager
    
    return {
        "status": "healthy",
        "settings_healthy": settings_manager.is_healthy(),
        "ffmpeg_available": download_service.context.ffmpeg_status.get("available", False),
        "queue_count": queue_manager.get_queue_count(),
        "platform": platform.system(),
        "environment": "docker" if IS_DOCKER else "wsl" if IS_WSL else "host"
    }


@router.get("/info")
async def system_info():
    """Get system information."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": sys.version,
        "environment": "docker" if IS_DOCKER else "wsl" if IS_WSL else "host",
        "display_access": False if IS_DOCKER else True,
        "paths": {
            "download_folder": str(settings_manager.get_download_folder()),
            "temp_folder": str(settings_manager.get_temp_folder()),
            "data_folder": str(settings_manager.get_data_folder()),
            "bin_folder": str(settings_manager.get_bin_folder())
        }
    }


@router.get("/files")
async def list_downloads(limit: int = 50):
    """List files in the downloads folder."""
    download_folder = settings_manager.get_download_folder()
    
    files = []
    
    try:
        for file_path in sorted(
            download_folder.rglob("*"), 
            key=lambda p: p.stat().st_mtime if p.is_file() else 0,
            reverse=True
        )[:limit]:
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(download_folder)),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "extension": file_path.suffix
                })
    except Exception as e:
        logger.error(f"Error listing files: {e}")
    
    return {"files": files, "count": len(files)}
