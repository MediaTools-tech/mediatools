"""
Download Service for Docker deployment.
Handles video/audio downloads using yt-dlp and Spotify downloads using spotdl.
Adapted from desktop version, removing Tkinter dependencies.
"""

import os
import re
import sys
import time
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
import logging
import tempfile
import json
import shutil

import yt_dlp
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TRCK, TPE2
from mutagen.easyid3 import EasyID3
from mutagen.oggopus import OggOpus
from mutagen.flac import Picture
from PIL import Image
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
import glob
import traceback

from app.core.settings_manager import settings_manager
from app.core.queue_manager import queue_manager
from app.core.download_context import (
    DownloadContext, DownloadStatus, DownloadType, 
    DownloadProgress, download_context
)

logger = logging.getLogger(__name__)


class DownloadService:
    """
    Clean download service with WebSocket-compatible progress reporting.
    Uses yt-dlp Python API for video/audio and spotdl for Spotify.
    """
    
    def __init__(self):
        self.settings = settings_manager
        self.queue = queue_manager
        self.context = download_context
        
        # Progress callback for WebSocket updates
        self._progress_callback: Optional[Callable] = None
        self._status_callback: Optional[Callable] = None
        
        # Worker state
        self._is_processing = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # Spotify client (lazy initialized)
        self.sp: Optional[spotipy.Spotify] = None
        
        # Check tool availability
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            self.context.ffmpeg_status["available"] = result.returncode == 0
            
            if result.returncode == 0:
                output = result.stdout
                self.context.ffmpeg_status["has_libopus"] = "libopus" in output
                self.context.ffmpeg_status["has_libvorbis"] = "libvorbis" in output
                logger.info("FFmpeg is available")
            else:
                logger.warning("FFmpeg not available")
        except FileNotFoundError:
            logger.warning("FFmpeg not found")
            self.context.ffmpeg_status["available"] = False
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def set_status_callback(self, callback: Callable):
        """Set callback for status updates."""
        self._status_callback = callback
    
    def _update_status(self, status: DownloadStatus, message: str = ""):
        """Update status and notify callback with enriched message."""
        # Enrich message if it's a generic one or if we have more context
        if not message:
            # Get default message from context logic
            self.context.set_status(status)
            message = self.context.status_message
        
        enriched_message = message
        
        # Add playlist index if applicable
        if self.context.total_videos > 1 and self.context.video_index > 0:
            index_prefix = f"[{self.context.video_index}/{self.context.total_videos}] "
            if not enriched_message.startswith("["):
                enriched_message = f"{index_prefix}{enriched_message}"
        
        # Add video title if applicable and not already in message (for active states)
        is_active = status in [
            DownloadStatus.DOWNLOADING, 
            DownloadStatus.CONVERTING, 
            DownloadStatus.MERGING, 
            DownloadStatus.POST_PROCESSING
        ]
        
        if is_active and self.context.current_video_title:
            title_suffix = f": {self.context.current_video_title}"
            if title_suffix not in enriched_message:
                enriched_message = f"{enriched_message}{title_suffix}"

        # Override for terminal states to be clean
        if status == DownloadStatus.COMPLETED:
            enriched_message = f"Done! ({self.context.total_videos} tracks)" if self.context.total_videos > 1 else "Done!"
        elif status == DownloadStatus.IDLE:
            enriched_message = "Ready"

        logger.info(f"Status update: {status} - {enriched_message}")
        self.context.set_status(status, enriched_message)
        if self._status_callback:
            try:
                self._status_callback(self.context.to_status_dict())
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    def _update_progress(self, **kwargs):
        """Update progress and notify callback."""
        self.context.update_progress(**kwargs)
        if self._progress_callback:
            try:
                self._progress_callback(self.context.to_status_dict())
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    # === URL Type Detection & Platform Support ===
    
    def _get_url_type(self, url: str) -> str:
        """Determine the type of URL (spotify, youtube, or generic)."""
        url_lower = url.lower()
        
        if "spotify.com" in url_lower or "open.spotify" in url_lower:
            return "spotify"
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        else:
            return "generic"
            
    def get_platform_for_downloader(self, url: str) -> str:
        """Optimized for video/audio downloader apps, matching original code."""
        if 'youtube' in url.lower() or 'youtu.be' in url.lower():
            return 'youtube'
        elif 'spotify' in url.lower():
            return 'spotify'
        else:
            try:
                return self.get_platform(url)
            except:
                return 'other'

    def get_platform(self, url: str) -> str:
        """
        Extract platform from URL using rsplit.
        SIMPLE, NO DEPENDENCIES, WORKS 100% - matching original code.
        """
        # Clean: remove protocol, path, port
        if '://' in url:
            url = url.split('://', 1)[1]
        
        domain = url.split('/')[0].split(':')[0]
        
        # Handle all cases with simple logic
        parts = domain.split('.')
        
        if len(parts) == 1:
            return parts[0]  # No dots
        
        # For 2+ parts, get the meaningful middle part
        if len(parts) == 2:
            return parts[0]  # example.com
        
        # For 3+ parts, need to skip subdomains and TLD parts
        # Common subdomains to skip
        skip_first = {'www', 'm', 'mobile', 'api', 'open', 'music'}
        
        # Common TLD parts to check
        tld_parts = {'co', 'com', 'org', 'net'}
        
        # Start from position 1 (skip first if it's a subdomain)
        start = 1 if parts[0] in skip_first else 0
        
        # Check if we have a country TLD pattern
        if len(parts) - start >= 3 and parts[start+1] in tld_parts:
            return parts[start]  # youtube.co.uk
        
        return parts[start]  # www.youtube.com
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        url_pattern = re.compile(
            r'^https?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
        )
        return url_pattern.match(url) is not None

    def sanitize_filename(self, title: str) -> str:
        """Ported from original code: handles safe filename creation."""
        # Allow: alphanumeric, space, hyphen, underscore, dot, parentheses, ampersand
        title = re.sub(r'[^\w\s\-\.\(\)&]', '', title)  # Keep only whitelisted chars
        title = re.sub(r'\s+', ' ', title).strip()      # Collapse multiple spaces
        title = title.rstrip(' .') # Strip trailing dots and spaces
        return title[:250]  # Limit length

    def get_yt_metadata(self, url: str, is_playlist: bool) -> Optional[Dict[str, Any]]:
        """Ported from original code: Get metadata fields using yt_dlp Python API."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist' if is_playlist else False,
            'skip_download': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(url, download=False)
                
                if not data:
                    return None

                if is_playlist:
                    result_metadata = {
                        'collection_type': 'youtube_playlist',
                        'collection_id': data.get('id', ''),
                        'collection_name': (
                            data.get("title") or 
                            data.get("playlist_title") or 
                            data.get("playlist") or 
                            "YouTube_Playlist"
                        ),
                        'collection_artist': data.get('uploader', ''),
                        'tracks': [],
                        'total_tracks': 0
                    }
                    
                    entries = data.get('entries', [])
                    if entries:
                        for idx, entry in enumerate(entries, 1):
                            if entry:
                                track_data = {
                                    'youtube_url': f"https://youtube.com/watch?v={entry.get('id', '')}",
                                    'title': entry.get('title', f'Track {idx}'),
                                    'artist': entry.get('uploader', ''),
                                    'album': result_metadata['collection_name'],
                                    'track_number': idx,
                                    'file_name': f"{idx:02d} - {entry.get('title', f'Track {idx}')}",
                                    'album_artist': result_metadata['collection_artist'],
                                    'duration_ms': int(entry.get('duration', 0) * 1000) if entry.get('duration') else 0
                                }
                                result_metadata['tracks'].append(track_data)
                        
                        result_metadata['total_tracks'] = len(result_metadata['tracks'])
                    
                    return result_metadata
                else:
                    return {
                        'title': data.get('title', 'Unknown'),
                        'artist': data.get('uploader', 'Unknown'),
                        'duration': str(data.get('duration', 0))
                    }
        except Exception as e:
            logger.error(f"Error extracting YouTube metadata: {e}")
            return None

    def save_metadata_json(self, collection_id: str, metadata: Dict[str, Any]) -> bool:
        """Save Spotify metadata to file, keep only latest 20 files."""
        try:
            self._cleanup_metadata_jsons()
            
            data_folder = self.settings.get_data_folder()
            file_path = data_folder / f"{collection_id}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved metadata for: {collection_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving metadata file: {e}")
            return False

    def load_metadata_json(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """Load Spotify metadata from file."""
        data_folder = self.settings.get_data_folder()
        file_path = data_folder / f"{collection_id}.json"
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"Loaded metadata for: {collection_id}")
                return data
            except Exception as e:
                logger.error(f"Error reading metadata file: {e}")
        return None

    def _cleanup_metadata_jsons(self):
        """Enforce 20-file limit by removing the oldest file."""
        try:
            data_folder = self.settings.get_data_folder()
            json_files = list(data_folder.glob("*.json"))
            
            # Filter for collection JSONs (exclude settings.json and others)
            # Collection IDs are typically 22 alphanumeric chars (Spotify) or similar
            collection_files = []
            for f in json_files:
                stem = f.stem
                if stem != "settings" and (len(stem) >= 20 or stem.isalnum()):
                    collection_files.append(f)
            
            if len(collection_files) >= 20:
                # Find oldest file
                oldest_file = min(collection_files, key=lambda p: p.stat().st_mtime)
                oldest_file.unlink()
                logger.info(f"Removed oldest metadata cache: {oldest_file.name}")
        except Exception as e:
            logger.error(f"Error cleaning up metadata files: {e}")
    
    # === Main Download Entry Point ===
    
    async def download(self, url: str, download_type: str = "video") -> Dict[str, Any]:
        """
        Main download entry point.
        Returns result dict with success status and details.
        """
        logger.info(f"Requesting download for {url} ({download_type})")
        if not url or not self._is_valid_url(url):
            return {"success": False, "error": "Invalid URL"}
        
        self.context.current_url = url
        self.context.download_type = DownloadType(download_type)
        
        try:
            url_type = self._get_url_type(url)
            
            if url_type == "spotify":
                return await self._download_spotify(url, download_type)
            else:
                return await self._download_ytdlp(url, download_type)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Download error: {error_msg}")
            self._update_status(DownloadStatus.ERROR, error_msg)
            self.context.last_error = error_msg
            
            # Add to failed URLs
            self.queue.add_failed_url(url, download_type, error_msg)
            
            return {"success": False, "error": error_msg}
    
    # === yt-dlp Download ===
    
    async def _download_ytdlp(self, url: str, download_type: str) -> Dict[str, Any]:
        """Download using yt-dlp with metadata and playlist support."""
        
        self._update_status(DownloadStatus.FETCHING_METADATA, "Fetching video information...")
        
        # Check if playlist
        is_playlist = "list=" in url or "/playlist" in url
        yt_metadata = self.get_yt_metadata(url, is_playlist)
        
        # Dynamic path resolution matching original code logic
        base_download_folder = self.settings.get_download_folder()
        
        if download_type == "video":
            download_folder = base_download_folder / "Video"
        else:
            download_folder = base_download_folder / "Audio"
            
        if self.settings.get("platform_specific_download_folders"):
            platform_name = self.get_platform_for_downloader(url)
            download_folder = download_folder / platform_name
        tracks = []
        collection_name = ""
        
        if is_playlist and yt_metadata:
            collection_name = f"{yt_metadata['collection_name']} - {yt_metadata['collection_artist']}"
            download_folder = download_folder / self.sanitize_filename(collection_name)
            tracks = yt_metadata.get("tracks", [])
            self.context.is_playlist = True
            self.context.total_videos = len(tracks)
        elif yt_metadata:
            tracks = [{"youtube_url": url, "file_name": yt_metadata.get('title', 'Unknown'), "title": yt_metadata.get('title'), "artist": yt_metadata.get('artist')}]
            self.context.is_playlist = False
            self.context.total_videos = 1
        else:
            # Fallback if metadata extraction fails
            tracks = [{"youtube_url": url, "file_name": "Downloaded_Video", "title": "Unknown", "artist": "Unknown"}]
            self.context.is_playlist = False
            self.context.total_videos = 1

        # Ensure directories exist
        download_folder.mkdir(parents=True, exist_ok=True)
        temp_folder = self.settings.get_temp_folder()
        temp_folder.mkdir(parents=True, exist_ok=True)
        
        results = []
        num_succeeded = 0
        
        for i, track in enumerate(tracks):
            if self.context.is_cancelled():
                break
                
            self.context.video_index = i + 1
            self.context.current_video_title = track.get('title', 'Unknown')
            track_url = track.get("youtube_url", url)
            file_name_base = self.sanitize_filename(track.get("file_name", "Download"))
            
            # Build yt-dlp options for this specific track
            track_download_folder = download_folder
            ydl_opts = self._build_ytdlp_options(download_type, track_download_folder, temp_folder)
            
            # Download to temp first (matching original code behavior)
            ydl_opts["outtmpl"] = str(temp_folder / f"{file_name_base}.%(ext)s")
            
            self._update_status(DownloadStatus.DOWNLOADING)
            
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    self._run_ytdlp_download_single,
                    track_url, ydl_opts, download_type, track, collection_name, track_download_folder
                )
                if result.get("success"):
                    num_succeeded += 1
                results.append(result)
            except Exception as e:
                logger.error(f"Track download error: {e}")
                results.append({"success": False, "error": str(e)})

        if is_playlist and num_succeeded > 0:
            self.create_m3u_playlist(collection_name, download_folder)

        if num_succeeded > 0:
            self._update_status(DownloadStatus.COMPLETED, f"Download completed! ({num_succeeded} tracks)")
            return {"success": True, "count": num_succeeded}
        else:
            return {"success": False, "error": "All downloads failed"}
    
    def rename_file_as_per_metadata(self, src_file: str, dest_file_base: str) -> Optional[str]:
        """Ported from original: rename file based on metadata-derived base name."""
        try:
            ext = src_file.rsplit(".")[-1]
            file_final_name = f"{dest_file_base}.{ext}"
            
            if os.path.exists(src_file) and not os.path.exists(file_final_name):
                os.rename(src_file, file_final_name)
            
            if os.path.exists(file_final_name):
                return file_final_name
            elif os.path.exists(src_file):
                return src_file
        except Exception as e:
            logger.error(f"Rename error: {e}")
            return None
        return None

    def create_m3u_playlist(self, collection_name: str, download_folder: Path) -> Optional[Path]:
        """Ported from original: Create an M3U playlist file."""
        try:
            if not download_folder.exists():
                return None
            
            media_extensions = ['*.mp3', '*.m4a', '*.flac', '*.wav', '*.ogg', '*.opus', '*.aac', '*.mp4', '*.mkv', '*.webm']
            media_files = []
            for ext in media_extensions:
                media_files.extend(download_folder.glob(ext))
            
            if not media_files:
                return None
            
            def natural_sort_key(path):
                parts = re.split(r'(\d+)', path.name.lower())
                return [int(p) if p.isdigit() else p for p in parts]
            
            media_files.sort(key=natural_sort_key)
            
            playlist_name = self.sanitize_filename(collection_name or download_folder.name)
            playlist_path = download_folder / f"{playlist_name}.m3u"
            
            m3u_lines = ["#EXTM3U", f"#PLAYLIST:{playlist_name}", ""]
            
            for media_file in media_files:
                m3u_lines.append(f"#EXTINF:0,{media_file.stem}")
                m3u_lines.append(media_file.name)
                m3u_lines.append("")
            
            with open(playlist_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(m3u_lines))
                
            return playlist_path
        except Exception as e:
            logger.error(f"Error creating playlist: {e}")
            return None

    def inject_track_metadata(self, file_path: str, track_info: Dict[str, Any], 
                              album_name: str, album_artist: str) -> bool:
        """Inject metadata into audio files."""
        if not os.path.exists(file_path):
            return False
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext in ['.m4a', '.mp4']:
                return self._inject_m4a_metadata(file_path, track_info, album_name, album_artist)
            elif file_ext == '.mp3':
                return self._inject_mp3_metadata(file_path, track_info, album_name, album_artist)
            elif file_ext == '.opus':
                return self._inject_opus_metadata(file_path, track_info, album_name, album_artist)
            return False
        except Exception as e:
            logger.error(f"Metadata injection error: {e}")
            return False

    def _inject_m4a_metadata(self, file_path, track, album_name, album_artist):
        try:
            audio = MP4(file_path)
            audio['\xa9nam'] = track.get('title', 'Unknown Title')
            audio['\xa9ART'] = track.get('artist', 'Unknown Artist')
            audio['\xa9alb'] = album_name
            audio['aART'] = album_artist
            audio['trkn'] = [(track.get('track_number', 0), 0)]
            audio.save()
            return True
        except Exception: return False

    def _inject_mp3_metadata(self, file_path, track, album_name, album_artist):
        try:
            try:
                audio = EasyID3(file_path)
            except:
                audio = EasyID3()
            
            audio['title'] = track.get('title', 'Unknown Title')
            audio['artist'] = track.get('artist', 'Unknown Artist')
            audio['album'] = album_name
            audio['albumartist'] = album_artist
            audio['tracknumber'] = str(track.get('track_number', 0))
            audio.save(file_path)
            
            # Album artist tag
            try:
                id3 = ID3(file_path)
                id3.add(TPE2(encoding=3, text=album_artist))
                id3.save()
            except: pass
            
            return True
        except Exception: return False

    def _inject_opus_metadata(self, file_path, track, album_name, album_artist):
        try:
            audio = OggOpus(file_path)
            audio['title'] = track.get('title', 'Unknown Title')
            audio['artist'] = track.get('artist', 'Unknown Artist')
            audio['album'] = album_name
            audio['albumartist'] = album_artist
            
            track_num = track.get('track_number', 0)
            if track_num:
                audio['tracknumber'] = str(track_num)
            
            audio.save()
            return True
        except Exception:
            return self._inject_opus_metadata_ffmpeg_fallback(file_path, track, album_name, album_artist)

    def _inject_opus_metadata_ffmpeg_fallback(self, file_path, track, album_name, album_artist):
        temp_output = tempfile.mktemp(suffix='.opus')
        cmd = [
            "ffmpeg", "-i", file_path,
            "-metadata", f'title={track.get("title", "")}',
            "-metadata", f'artist={track.get("artist", "")}',
            "-metadata", f'album={album_name}',
            "-metadata", f'album_artist={album_artist}',
            "-metadata", f'track={track.get("track_number", 0)}',
            "-c:a", "copy", "-y", temp_output
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                shutil.move(temp_output, file_path)
                return True
        except Exception: pass
        finally:
            if os.path.exists(temp_output): os.remove(temp_output)
        return False

    def process_spotify_url(self, url: str):
        """Ported from original: Extract metadata and type from any Spotify URL."""
        url = url.strip()
        is_single_track = False
        
        if url.startswith('spotify:'):
            parts = url.split(':')
            if len(parts) >= 3:
                collection_type = parts[1]
                collection_id = parts[2]
                if collection_type == 'track':
                    is_single_track = True
                return collection_id, collection_type, is_single_track
        
        if "open.spotify.com" in url:
            clean_url = url.split('?')[0]
            if "/track/" in clean_url:
                collection_id = clean_url.split("/track/")[-1]
                return collection_id, "track", True
            elif "/artist/" in clean_url:
                collection_id = clean_url.split("/artist/")[-1]
                return collection_id, "artist", False
            elif "/album/" in clean_url:
                collection_id = clean_url.split("/album/")[-1]
                return collection_id, "album", False
            elif "/playlist/" in clean_url:
                collection_id = clean_url.split("/playlist/")[-1]
                return collection_id, "playlist", False
        
        if len(url) == 22 and url.isalnum():
            return url, "unknown", False
            
        raise ValueError(f"Could not parse Spotify URL: {url}")

    def get_urls_and_metadata(self, collection_id: str, collection_type: str):
        """Ported from original: Fetch Spotify metadata using Spotipy with JSON caching."""
        # Try loading from cache first
        cached_data = self.load_metadata_json(collection_id)
        if cached_data:
            return cached_data

        if not self.sp:
            client_id = self.settings.get("spotify_client_id")
            client_secret = self.settings.get("spotify_client_secret")
            if not client_id or not client_secret:
                return None
                
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            ))

        try:
            result = {
                'collection_type': collection_type,
                'collection_id': collection_id,
                'collection_name': '',
                'collection_artist': '',
                'tracks': [],
                'total_tracks': 0
            }

            if collection_type == 'album':
                album_info = self.sp.album(collection_id)
                result['collection_name'] = album_info['name']
                result['collection_artist'] = album_info['artists'][0]['name'] if album_info['artists'] else 'Unknown'
                result['total_tracks'] = album_info['total_tracks']
                
                for idx, track_data in enumerate(album_info['tracks']['items'], 1):
                    track_info = self._extract_track_metadata(track_data, track_number=idx)
                    result['tracks'].append(track_info)

            elif collection_type == 'playlist':
                playlist_info = self.sp.playlist(collection_id)
                result['collection_name'] = playlist_info['name']
                result['total_tracks'] = playlist_info['tracks']['total']
                
                for idx, item in enumerate(playlist_info['tracks']['items'], 1):
                    track_data = item['track']
                    if track_data:
                        track_info = self._extract_track_metadata(track_data, track_number=idx)
                        result['tracks'].append(track_info)

            elif collection_type == 'track':
                track_data = self.sp.track(collection_id)
                result['collection_name'] = track_data['name']
                result['total_tracks'] = 1
                track_info = self._extract_track_metadata(track_data, track_number=1)
                result['tracks'].append(track_info)

            # Save to cache if we got results
            if result['tracks']:
                self.save_metadata_json(collection_id, result)

            return result
        except Exception as e:
            logger.error(f"Spotify metadata error: {e}")
            return None

    def _extract_track_metadata(self, track_data, track_number):
        if not track_data: return None
        
        track_name = track_data.get('name', 'Unknown')
        artists = track_data.get('artists', [])
        artist_names = ', '.join([artist['name'] for artist in artists]) if artists else 'Unknown'
        
        album_data = track_data.get('album', {})
        album_name = album_data.get('name', '') if album_data else ''
        
        spotify_url = track_data['external_urls']['spotify'] if track_data.get('external_urls') else ''
        
        return {
            'spotify_url': spotify_url,
            'title': track_name,
            'artist': artist_names,
            'album': album_name,
            'track_number': track_number,
            'file_name': f"{track_number:02d} - {track_name}",
            'duration_ms': track_data.get('duration_ms', 0)
        }

    def _build_ytdlp_options(self, download_type: str, download_folder: Path, 
                              temp_folder: Path) -> Dict[str, Any]:
        """Build yt-dlp options dictionary."""
        
        # Base output template
        outtmpl = str(download_folder / "%(title)s.%(ext)s")
        
        opts = {
            "outtmpl": outtmpl,
            "progress_hooks": [self._ytdlp_progress_hook],
            "postprocessor_hooks": [self._ytdlp_postprocessor_hook],
            "quiet": True,
            "no_warnings": True,
            "noprogress": False,
            "paths": {"temp": str(temp_folder)},
            "restrictfilenames": True,
            "nopermissions": True,
            "no_mtime": True,
        }
        
        # Download speed limit
        speed_limit = self.settings.get("download_speed", "5M")
        if speed_limit:
            opts["ratelimit"] = self._parse_speed_limit(speed_limit)
        
        # Format selection
        if download_type == "audio":
            audio_format = self.settings.get("audio_format", "m4a")
            # For audio quality, we use the default 320 if not specified
            audio_quality = self.settings.get("audio_quality", "320")
            
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": audio_quality,
            }]
            
            if self.settings.get("embed_thumbnail_in_audio") == "Yes":
                opts["postprocessors"].append({
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                })
                opts["postprocessors"].append({
                    "key": "EmbedThumbnail",
                })
                opts["writethumbnail"] = True
                
        else:  # video
            stream_format = self.settings.get(
                "stream_and_merge_format", 
                "bestvideo+bestaudio/best-mkv"
            )
            
            # Extract format from stream_and_merge_format (e.g., best-mkv -> mkv)
            video_format = "mp4"
            if "mkv" in stream_format:
                video_format = "mkv"
            elif "mp4" in stream_format:
                video_format = "mp4"
                
            opts["format"] = stream_format.split("-")[0] if "-" in stream_format else stream_format
            opts["merge_output_format"] = video_format
            
            # Metadata embedding was a default in original
            # We'll keep it as a default for now
            opts["postprocessors"] = opts.get("postprocessors", [])
            opts["postprocessors"].append({
                "key": "FFmpegMetadata",
            })
        
        # Cookies
        cookies_cmd = self.settings.get_cookies_cmd()
        if cookies_cmd:
            opts["cookiefile"] = cookies_cmd[1]  # --cookies filepath
        
        # SponsorBlock
        if self.settings.get("enable_sponsorblock"):
            opts["postprocessors"] = opts.get("postprocessors", [])
            opts["postprocessors"].append({
                "key": "SponsorBlock",
            })
            opts["postprocessors"].append({
                "key": "ModifyChapters",
                "remove_sponsor_segments": ["sponsor"],
            })
        
        # Download archive (skip already downloaded)
        if self.settings.get("enable_download_archive"):
            archive_path = self.settings.get_data_folder() / "download_archive.txt"
            opts["download_archive"] = str(archive_path)
        
        return opts
    
    def _parse_speed_limit(self, speed: str) -> int:
        """Parse speed limit string to bytes per second."""
        speed = speed.upper().strip()
        multipliers = {"K": 1024, "M": 1024*1024, "G": 1024*1024*1024}
        
        for suffix, mult in multipliers.items():
            if speed.endswith(suffix):
                return int(float(speed[:-1]) * mult)
        
        try:
            return int(speed)
        except ValueError:
            return 5 * 1024 * 1024  # Default 5MB/s
    
    def _run_ytdlp_download_single(self, url: str, opts: Dict[str, Any], 
                                  download_type: str, track_info: Dict[str, Any], 
                                  collection_name: str, final_download_folder: Path) -> Dict[str, Any]:
        """Run single yt-dlp download, tagging and moving to final destination after finish."""
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                if self.context.is_cancelled():
                    return {"success": False, "error": "Cancelled"}
                
                # Download the file
                info = ydl.extract_info(url, download=True)
                if not info:
                    return {"success": False, "error": "No info"}

                # Get the final filename from yt-dlp
                final_filename = ydl.prepare_filename(info)
                
                # Check for merged file if applicable
                ext = info.get('ext')
                if not os.path.exists(final_filename):
                    # Try common extensions if prepare_filename doesn't match
                    for e in ['mp4', 'mkv', 'mp3', 'm4a', 'opus', 'webm']:
                        alt_name = os.path.splitext(final_filename)[0] + f".{e}"
                        if os.path.exists(alt_name):
                            final_filename = alt_name
                            break

                if not os.path.exists(final_filename):
                    return {"success": False, "error": "Downloaded file not found"}

                # Post-processing: Tagging and Renaming
                if download_type == "audio":
                    album = collection_name or track_info.get('album', 'YouTube')
                    artist = track_info.get('artist', 'Unknown Artist')
                    self.inject_track_metadata(final_filename, track_info, album, artist)

                # Final rename and move to final destination
                dest_base = os.path.join(str(final_download_folder), self.sanitize_filename(track_info.get('file_name', info.get('title', 'Download'))))
                
                final_path = self.rename_file_as_per_metadata(final_filename, dest_base)
                
                # Add to history
                self.queue.add_to_history(url, download_type, os.path.basename(final_path), success=True)
                
                return {"success": True, "file": final_path}

        except Exception as e:
            logger.error(f"Download error for {url}: {e}")
            return {"success": False, "error": str(e)}
    
    def _ytdlp_progress_hook(self, d: Dict[str, Any]):
        """Progress hook for yt-dlp."""
        
        if self.context.is_cancelled():
            raise yt_dlp.utils.DownloadError("Download cancelled")
        
        status = d.get("status")
        
        if status == "downloading":
            # If we are paused, block here until resume_event is set
            if self.context.status == DownloadStatus.PAUSED:
                logger.debug("Download is paused, waiting...")
                self.context.pause_event.wait()
                logger.debug("Download resumed")
            
            # Update status to downloading if not already in a special state
            if self.context.status not in [DownloadStatus.PAUSED, DownloadStatus.CONVERTING, DownloadStatus.MERGING]:
                self._update_status(DownloadStatus.DOWNLOADING)
            
            # Parse progress info
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0)
            eta = d.get("eta", 0)
            filename = d.get("filename", "")
            
            # Calculate percentage
            if total > 0:
                percentage = (downloaded / total) * 100
            else:
                percentage = d.get("_percent_str", "0%")
                if isinstance(percentage, str):
                    percentage = float(percentage.strip("%").strip())
            
            # Format speed
            if speed:
                if speed >= 1024 * 1024:
                    speed_str = f"{speed / (1024*1024):.1f} MB/s"
                elif speed >= 1024:
                    speed_str = f"{speed / 1024:.1f} KB/s"
                else:
                    speed_str = f"{speed:.0f} B/s"
            else:
                speed_str = ""
            
            # Format ETA
            if eta:
                if eta >= 3600:
                    eta_str = f"{eta // 3600}h {(eta % 3600) // 60}m"
                elif eta >= 60:
                    eta_str = f"{eta // 60}m {eta % 60:.2f}s"
                else:
                    eta_str = f"{eta:.2f}s"
            else:
                eta_str = ""
            
            self._update_progress(
                percentage=percentage,
                speed=speed_str,
                eta=eta_str,
                filename=Path(filename).name if filename else "",
                downloaded_bytes=downloaded,
                total_bytes=total
            )
            
        elif status == "finished":
            self._update_status(DownloadStatus.POST_PROCESSING, "Processing...")
            
        elif status == "error":
            self._update_status(DownloadStatus.ERROR, d.get("error", "Unknown error"))
    
    def _ytdlp_postprocessor_hook(self, d: Dict[str, Any]):
        """Post-processor hook for yt-dlp."""
        
        status = d.get("status")
        postprocessor = d.get("postprocessor", "")
        
        if status == "started":
            if "FFmpegExtractAudio" in postprocessor:
                self._update_status(DownloadStatus.CONVERTING, "Converting...")
            elif "FFmpegMerger" in postprocessor or "Merger" in postprocessor:
                self._update_status(DownloadStatus.MERGING, "Merging...")
            elif "EmbedThumbnail" in postprocessor:
                self._update_status(DownloadStatus.POST_PROCESSING, "Embedding thumbnail...")
            elif "FFmpegMetadata" in postprocessor:
                self._update_status(DownloadStatus.POST_PROCESSING, "Embedding metadata...")
            else:
                self._update_status(DownloadStatus.POST_PROCESSING)
    
    # === Spotify Download ===
    
    async def _download_spotify(self, url: str, download_type: str) -> Dict[str, Any]:
        """Download from Spotify with metadata and collection support."""
        
        self._update_status(DownloadStatus.FETCHING_METADATA, "Fetching Spotify metadata...")
        
        try:
            cid, ctype, is_single = self.process_spotify_url(url)
            metadata = self.get_urls_and_metadata(cid, ctype)
            
            if not metadata:
                raise Exception("Could not fetch Spotify metadata. Check your credentials.")

            # Dynamic path resolution
            base_download_folder = self.settings.get_download_folder()
            if download_type == "video":
                download_folder = base_download_folder / "Video"
            else:
                download_folder = base_download_folder / "Audio"
            
            if self.settings.get("platform_specific_download_folders"):
                download_folder = download_folder / "spotify"
            
            collection_name = metadata.get('collection_name', 'Spotify Download')
            if not is_single:
                download_folder = download_folder / self.sanitize_filename(collection_name)
            
            download_folder.mkdir(parents=True, exist_ok=True)
            temp_folder = self.settings.get_temp_folder()
            temp_folder.mkdir(parents=True, exist_ok=True)
            
            tracks = metadata.get('tracks', [])
            self.context.is_playlist = not is_single
            self.context.total_videos = len(tracks)
            
            num_succeeded = 0
            for i, track in enumerate(tracks):
                if self.context.is_cancelled():
                    break
                    
                self.context.video_index = i + 1
                self.context.current_video_title = track.get('title', 'Unknown')
                self._update_status(DownloadStatus.DOWNLOADING)
                
                # Check for pause
                if self.context.status == DownloadStatus.PAUSED:
                    logger.debug("Spotify download is paused, waiting...")
                    self.context.pause_event.wait()
                    logger.debug("Spotify download resumed")

                # Get YouTube URL for the Spotify track
                yt_url = await self._get_youtube_url_for_spotify_track(track, collection_name)
                if not yt_url:
                    logger.warning(f"Could not find YouTube match for: {track.get('title')}")
                    continue
                
                # Use same yt-dlp logic for the matched audio/video
                ydl_opts = self._build_ytdlp_options(download_type, download_folder, temp_folder)
                file_name_base = self.sanitize_filename(track.get("file_name", "Download"))
                ydl_opts["outtmpl"] = str(temp_folder / f"{file_name_base}.%(ext)s")
                
                try:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, 
                        self._run_ytdlp_download_single,
                        yt_url, ydl_opts, download_type, track, collection_name, download_folder
                    )
                    if result.get("success"):
                        num_succeeded += 1
                except Exception as e:
                    logger.error(f"Spotify track download error: {e}")

                # Sleep interval as per settings
                await asyncio.sleep(self.settings.get("sleep_interval_between_downloads", 2))

            if not is_single and num_succeeded > 0:
                self.create_m3u_playlist(collection_name, download_folder)

            if num_succeeded > 0:
                self._update_status(DownloadStatus.COMPLETED, f"Download completed! ({num_succeeded} tracks)")
                return {"success": True, "count": num_succeeded}
            else:
                return {"success": False, "error": "All Spotify tracks failed to download"}

        except Exception as e:
            logger.error(f"Spotify download error: {e}")
            raise Exception(str(e))

    async def _get_youtube_url_for_spotify_track(self, track: Dict[str, Any], collection_name: str) -> Optional[str]:
        """Matched original logic: convert spotify track to youtube url."""
        try:
            spotify_url = track.get('spotify_url')
            if not spotify_url:
                return None
            
            loop = asyncio.get_event_loop()
            
            # Try spotdl first (more accurate)
            # Find spotdl binary
            bin_dir = self.settings.get_bin_folder()
            spotdl_bin = bin_dir / ("spotdl.exe" if os.name == 'nt' else "spotdl")
            cmd = [str(spotdl_bin) if spotdl_bin.exists() else "spotdl", "url", spotify_url]
            
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    url_match = re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+', output)
                    if url_match:
                        return url_match.group(0)
            except Exception as e:
                logger.warning(f"spotdl url conversion failed: {e}")
            
            # Fallback to youtube search
            search_query = f"{track.get('title')} {track.get('artist')}"
            search_cmd = ["yt-dlp", f"ytsearch1:{search_query}", "--print", "webpage_url"]
            
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(search_cmd, capture_output=True, text=True, timeout=20)
                )
                
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception as e:
                logger.warning(f"yt-search conversion failed: {e}")
                
        except Exception as e:
            logger.error(f"Error matching Spotify track to YouTube: {e}")
            
        return None
    
    # === Control Methods ===
    
    def cancel(self):
        """Cancel current download."""
        self.context.cancel()
        self._update_status(DownloadStatus.CANCELLED, "Download cancelled")
    
    def pause(self):
        """Pause current download."""
        self.context.pause_event.clear()
        self._update_status(DownloadStatus.PAUSED, "Download paused")
    
    def resume(self):
        """Resume paused download."""
        self.context.pause_event.set()
        self._update_status(DownloadStatus.DOWNLOADING, "Resuming download...")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current download status."""
        return self.context.to_status_dict()
    
    # === Queue Processing ===
    
    async def start_worker(self):
        """Start the queue processing worker if not already running."""
        if self._is_processing:
            logger.info("Worker already running")
            return
        
        # Ensure we're in an idle-like state before starting
        current_status = self.get_status()["status"]
        if current_status not in [DownloadStatus.IDLE.value, DownloadStatus.COMPLETED.value, 
                                 DownloadStatus.ERROR.value, DownloadStatus.CANCELLED.value]:
            logger.info(f"Cannot start worker, current status: {current_status}")
            return

        self._is_processing = True
        logger.info("Starting background worker")
        
        # Clear any previous cancellation state before starting
        self.context.cancel_event.clear()
        self.context.cancel_spotdl_event.clear()
        
        try:
            # We don't use BackgroundTasks here because we want to track the task in the service
            # but we must be careful with event loops.
            # In FastAPI, we can use asyncio.create_task if we're in an async context.
            await self.process_queue()
        finally:
            self._is_processing = False
            logger.info("Background worker stopped")

    async def process_queue(self):
        """Process all URLs in the queue."""
        logger.info("Worker: Starting queue processing")
        
        while self.queue.has_queued_urls():
            next_item = self.queue.get_next_url()
            if not next_item:
                await asyncio.sleep(0.5)
                continue

            url, download_type = next_item
            logger.info(f"Worker: Processing next URL: {url} ({download_type})")
            
            try:
                # Reset context for each new top-level item from the queue
                self.context.reset()
                
                # Actually perform the download
                result = await self.download(url, download_type)
                
                if result.get("success"):
                    # Remove from queue ONLY on success or if explicitly handled
                    self.queue.remove_url(url, download_type)
                else:
                    # If it failed, it's already moved to failed list by download()
                    # so we just remove it from the active queue
                    self.queue.remove_url(url, download_type)
            except Exception as e:
                logger.error(f"Worker: Unexpected error during download: {e}")
                self.queue.add_failed_url(url, download_type, str(e))
                self.queue.remove_url(url, download_type)
        
        self._update_status(DownloadStatus.IDLE, "Ready")
        logger.info("Worker: Queue empty, going idle")


# Singleton instance
download_service = DownloadService()
