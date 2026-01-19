"""
WebSocket endpoint for real-time updates.
Broadcasts download progress and status changes to connected clients.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Store the event loop for thread-safe broadcasting
_main_loop: asyncio.AbstractEventLoop = None

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        
        # Copy list to avoid modification during iteration
        async with self._lock:
            connections = self.active_connections.copy()
        
        disconnected = []
        
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")


# Global connection manager
manager = ConnectionManager()


def broadcast_status(status_dict: Dict[str, Any]):
    """
    Synchronous wrapper for broadcasting status updates.
    Called from download_service progress hooks.
    """
    _safe_broadcast({
        "type": "status_update",
        "data": status_dict
    })


def _safe_broadcast(message: Dict[str, Any]):
    """Safely schedule a broadcast from any thread."""
    global _main_loop
    
    if _main_loop is None:
        try:
            _main_loop = asyncio.get_event_loop()
        except RuntimeError:
            logger.warning("No event loop available for broadcast")
            return

    if _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(_async_broadcast(message), _main_loop)
    else:
        logger.warning("Main event loop is not running, cannot broadcast")


def broadcast_queue_update():
    """Broadcast queue changes."""
    from app.core.queue_manager import queue_manager
    
    _safe_broadcast({
        "type": "queue_update",
        "data": queue_manager.get_status()
    })


def broadcast_download_complete(url: str, files: List[str]):
    """Broadcast download completion."""
    _safe_broadcast({
        "type": "download_complete",
        "data": {
            "url": url,
            "files": files
        }
    })


def broadcast_download_failed(url: str, error: str):
    """Broadcast download failure."""
    _safe_broadcast({
        "type": "download_failed",
        "data": {
            "url": url,
            "error": error
        }
    })


async def _async_broadcast(message: Dict[str, Any]):
    """Internal async broadcast helper."""
    msg_type = message.get("type")
    msg_status = message.get("data", {}).get("status")
    logger.info(f"Broadcasting: type={msg_type}, status={msg_status}")
    await manager.broadcast(message)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    
    Message types sent to clients:
    - status_update: Current download status and progress
    - queue_update: Queue changed (added/removed items)
    - download_complete: Download finished successfully
    - download_failed: Download failed with error
    """
    await manager.connect(websocket)
    
    # Send initial status
    from app.core.download_service import download_service
    from app.core.queue_manager import queue_manager
    from app.core.settings_manager import settings_manager
    
    await manager.send_personal(websocket, {
        "type": "initial_state",
        "data": {
            "status": download_service.get_status(),
            "queue": queue_manager.get_status(),
            "settings": settings_manager.get_all()
        }
    })
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # Ping/pong timeout
                )
                
                # Handle client messages (if needed)
                try:
                    message = json.loads(data)
                    await handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {data}")
                    
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message: Dict[str, Any]):
    """Handle messages from WebSocket clients."""
    msg_type = message.get("type")
    
    if msg_type == "pong":
        # Client responded to ping
        pass
    
    elif msg_type == "get_status":
        # Client requests current status
        from app.core.download_service import download_service
        await manager.send_personal(websocket, {
            "type": "status_update",
            "data": download_service.get_status()
        })
    
    elif msg_type == "get_queue":
        # Client requests queue status
        from app.core.queue_manager import queue_manager
        await manager.send_personal(websocket, {
            "type": "queue_update",
            "data": queue_manager.get_status()
        })
    
    else:
        logger.debug(f"Unknown message type: {msg_type}")


def setup_callbacks():
    """Set up callbacks from core modules to WebSocket broadcasts."""
    global _main_loop
    
    # Capture the main loop
    try:
        _main_loop = asyncio.get_event_loop()
    except RuntimeError:
        logger.error("Could not get event loop in setup_callbacks")
    
    from app.core.download_service import download_service
    from app.core.queue_manager import queue_manager
    
    # Set download service callbacks
    download_service.set_progress_callback(broadcast_status)
    download_service.set_status_callback(broadcast_status)
    
    # Set queue manager callback
    queue_manager.register_callback(broadcast_queue_update)
    
    logger.info("WebSocket callbacks configured")
