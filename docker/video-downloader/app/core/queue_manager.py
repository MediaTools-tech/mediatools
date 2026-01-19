"""
Queue Manager for Docker deployment.
Adapted from desktop version, removing Tkinter dependencies.
"""

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import logging
import re

from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class QueueManager:
    """
    Thread-safe queue manager for URL downloads.
    File-based persistence for Docker volume compatibility.
    """
    
    def __init__(self):
        self.settings = settings_manager
        self.queue_lock = threading.RLock()
        self._callbacks: List[callable] = []
        
        # Initialize file paths
        self._init_file_paths()
        
        # File state tracking for change detection
        self._last_queue_state = None
        self._last_failed_state = None
        
        # Session state
        self._session_handled = False
        
        logger.info("Queue manager initialized")
    
    def _init_file_paths(self):
        """Initialize file paths from settings."""
        data_folder = self.settings.get_data_folder()
        
        self.queue_file = data_folder / "queue.txt"
        self.queue_old_file = data_folder / "queue_old.txt"
        self.failed_file = data_folder / "failed_urls.txt"
        self.failed_old_file = data_folder / "failed_urls_old.txt"
        self.history_file = data_folder / "download_history.json"
        
        # Ensure files exist
        for filepath in [self.queue_file, self.failed_file]:
            self._ensure_file_exists(filepath)
    
    def _ensure_file_exists(self, filepath: Path):
        """Create file if it doesn't exist."""
        if not filepath.exists():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.touch()
    
    def _read_file_lines(self, filepath: Path) -> List[str]:
        """Read all lines from file, return empty list if file doesn't exist."""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines()]
                    return [line for line in lines if line]
        except IOError as e:
            logger.error(f"Error reading {filepath}: {e}")
        return []
    
    def _write_file_lines(self, filepath: Path, lines: List[str]):
        """Write lines to file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(f"{line}\n")
            self._notify_callbacks()
        except IOError as e:
            logger.error(f"Error writing {filepath}: {e}")
    
    def _append_to_file(self, filepath: Path, line_or_lines):
        """Append a line or lines to file, avoiding duplicates."""
        with self.queue_lock:
            existing = set(self._read_file_lines(filepath))
            
            lines_to_add = [line_or_lines] if isinstance(line_or_lines, str) else line_or_lines
            new_lines = [line for line in lines_to_add if line not in existing]
            
            if new_lines:
                try:
                    with open(filepath, 'a', encoding='utf-8') as f:
                        for line in new_lines:
                            f.write(f"{line}\n")
                    self._notify_callbacks()
                except IOError as e:
                    logger.error(f"Error appending to {filepath}: {e}")
    
    def add_url(self, url: str, download_type: str = "video") -> bool:
        """Add URL to queue (thread-safe)."""
        if not url or not url.strip():
            return False
        
        # Format: URL|TYPE|TIMESTAMP
        entry = f"{url.strip()}|{download_type}|{datetime.now().isoformat()}"
        
        with self.queue_lock:
            existing = self._read_file_lines(self.queue_file)
            
            # Check if URL and type combination already in queue
            existing_items = []
            for line in existing:
                parts = line.split("|")
                if len(parts) >= 2:
                    existing_items.append((parts[0], parts[1]))

            if (url.strip(), download_type) not in existing_items:
                self._append_to_file(self.queue_file, entry)
                logger.info(f"Added to queue: {url} ({download_type})")
                return True
            else:
                logger.info(f"URL with same type already in queue: {url} ({download_type})")
                return False
    
    def get_next_url(self) -> Optional[Tuple[str, str]]:
        """Get next URL from queue (thread-safe). Returns (url, download_type) or None."""
        with self.queue_lock:
            lines = self._read_file_lines(self.queue_file)
            
            if lines:
                entry = lines[0]
                parts = entry.split("|")
                url = parts[0]
                download_type = parts[1] if len(parts) > 1 else "video"
                return (url, download_type)
        
        return None
    
    def remove_url(self, url: str = None, download_type: str = None) -> bool:
        """Remove URL from queue (thread-safe). If no URL/type provided, removes first."""
        with self.queue_lock:
            lines = self._read_file_lines(self.queue_file)
            
            if not lines:
                return False
            
            if url and download_type:
                # Remove specific URL and type combination
                new_lines = []
                removed = False
                for line in lines:
                    parts = line.split("|")
                    if len(parts) >= 2 and parts[0] == url and parts[1] == download_type and not removed:
                        logger.info(f"Removed specific from queue: {url} ({download_type})")
                        removed = True
                        continue
                    new_lines.append(line)
                
                if removed:
                    self._write_file_lines(self.queue_file, new_lines)
                    return True
                else:
                    logger.warning(f"Did not find {url} ({download_type}) in queue to remove.")
                    return False
            elif url:
                # Fallback to remove all entries with the given URL (old behavior, for compatibility)
                new_lines = [line for line in lines if not line.startswith(url)]
                if len(new_lines) < len(lines):
                    self._write_file_lines(self.queue_file, new_lines)
                    logger.info(f"Removed all for URL: {url}")
                    return True
                else:
                    logger.warning(f"Did not find {url} in queue to remove.")
                    return False
            else:
                # Remove first item if no URL is provided
                removed_entry = lines[0]
                self._write_file_lines(self.queue_file, lines[1:])
                logger.info(f"Removed first from queue: {removed_entry.split('|')[0]}")
                return True
        
        return False
    
    def get_queue_count(self) -> int:
        """Get number of URLs in queue (thread-safe)."""
        with self.queue_lock:
            return len(self._read_file_lines(self.queue_file))
    
    def get_all_queued_urls(self) -> List[Dict[str, str]]:
        """Get all URLs in queue with metadata."""
        with self.queue_lock:
            lines = self._read_file_lines(self.queue_file)
            result = []
            
            for line in lines:
                parts = line.split("|")
                result.append({
                    "url": parts[0],
                    "type": parts[1] if len(parts) > 1 else "video",
                    "added_at": parts[2] if len(parts) > 2 else ""
                })
            
            return result
    
    def has_queued_urls(self) -> bool:
        """Check if there are URLs in queue."""
        return self.get_queue_count() > 0
    
    def clear_queue(self):
        """Clear all URLs from queue."""
        with self.queue_lock:
            self._write_file_lines(self.queue_file, [])
            logger.info("Queue cleared")
    
    # Failed URLs management
    
    def add_failed_url(self, url: str, download_type: str, error_message: str = ""):
        """Add URL to failed list."""
        # Format: URL|TYPE|TIMESTAMP|ERROR
        error_clean = error_message.replace("|", " ").replace("\n", " ")[:200]
        entry = f"{url}|{download_type}|{datetime.now().isoformat()}|{error_clean}"
        
        self._append_to_file(self.failed_file, entry)
        logger.info(f"Added to failed: {url}")
    
    def get_failed_urls(self) -> List[Dict[str, str]]:
        """Get all failed URLs with metadata."""
        lines = self._read_file_lines(self.failed_file)
        result = []
        
        for line in lines:
            parts = line.split("|")
            result.append({
                "url": parts[0],
                "type": parts[1] if len(parts) > 1 else "video",
                "failed_at": parts[2] if len(parts) > 2 else "",
                "error": parts[3] if len(parts) > 3 else ""
            })
        
        return result
    
    def get_failed_url_count(self) -> int:
        """Get number of failed URLs."""
        return len(self._read_file_lines(self.failed_file))
    
    def remove_failed_url(self, url: str) -> bool:
        """Remove a URL from failed list."""
        lines = self._read_file_lines(self.failed_file)
        new_lines = [line for line in lines if not line.startswith(url)]
        
        if len(new_lines) < len(lines):
            self._write_file_lines(self.failed_file, new_lines)
            return True
        return False
    
    def retry_failed_url(self, url: str) -> bool:
        """Move a failed URL back to the queue."""
        # Find the URL in failed list
        lines = self._read_file_lines(self.failed_file)
        
        for line in lines:
            if line.startswith(url):
                parts = line.split("|")
                download_type = parts[1] if len(parts) > 1 else "video"
                
                # Remove from failed
                self.remove_failed_url(url)
                
                # Add to queue
                self.add_url(url, download_type)
                
                logger.info(f"Retrying failed URL: {url}")
                return True
        
        return False
    
    def clear_failed(self):
        """Clear all failed URLs."""
        self._write_file_lines(self.failed_file, [])
        logger.info("Failed URLs cleared")
    
    # History management
    
    def add_to_history(self, url: str, download_type: str, filename: str, 
                       success: bool = True, error: str = ""):
        """Add download to history."""
        import json
        
        history = self._load_history()
        
        entry = {
            "url": url,
            "type": download_type,
            "filename": filename,
            "success": success,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        history.insert(0, entry)
        
        # Keep last 500 entries
        history = history[:500]
        
        self._save_history(history)
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load download history."""
        import json
        
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading history: {e}")
        
        return []
    
    def _save_history(self, history: List[Dict[str, Any]]):
        """Save download history."""
        import json
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving history: {e}")
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get download history."""
        history = self._load_history()
        return history[:limit]
    
    def clear_history(self):
        """Clear download history."""
        self._save_history([])
        logger.info("History cleared")
    
    # Callbacks for real-time updates
    
    def register_callback(self, callback: callable):
        """Register a callback for queue changes."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: callable):
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Notify all registered callbacks about queue changes."""
        for callback in self._callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in queue callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current queue status for API."""
        return {
            "queue_count": self.get_queue_count(),
            "failed_count": self.get_failed_url_count(),
            "queued_urls": self.get_all_queued_urls(),
            "failed_urls": self.get_failed_urls()
        }

    def is_session_handled(self) -> bool:
        """Check if session has been handled or ignored."""
        return self._session_handled
        
    def mark_session_handled(self):
        """Mark session as handled to prevent showing prompt again."""
        self._session_handled = True


# Singleton instance
queue_manager = QueueManager()
