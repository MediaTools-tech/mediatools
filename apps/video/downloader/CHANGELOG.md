# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- macOS build support
- Additional video/audio tools
- Enhanced format conversion options
- Batch processing improvements

## [2.1.0] - 2026-01-03

### Added

- **Spotify Support**: Download tracks, albums, and playlists from Spotify.
  - Metadata extraction for Spotify URLs (requires API credentials).
  - OAuth flow for private playlist access.
- **New Dependencies**: `spotdl` and `deno` are now automatically managed by the application.
- **Spotify Settings**: New options in the settings GUI to add Spotify Client ID and Secret.

### Improved

- **Code Refactoring**: Major refactoring for better modularity and maintainability.
- **Playlist Progress**: Improved status display for playlist downloads, showing current track number and total tracks.
- **Error Handling**: Better error handling for download processes.

### Technical

- Added `spotipy`, `mutagen`, and `Pillow` to `requirements.txt`.
- Updated documentation to reflect new features and dependencies.

## [2.0.0] - 2025-11-26

### Added

- **Audio Download Feature**: Extract audio from videos in multiple formats
  - MP3 format for universal compatibility
  - M4A format for superior quality
  - Best Audio for original quality preservation
- Audio thumbnail/cover art embedding support
- Dedicated Audio folder organization (`[Downloads]/Audio/`)
- Audio-specific queue management with "audio:" URL prefix
- Enhanced update system checking both yt-dlp and application updates
- New audio settings panel with format selection and thumbnail options

### Improved

- Queue management with audio/video type differentiation
- Settings organization with dedicated audio section
- Documentation comprehensive coverage of new features
- Updated `README.md` with more detailed information and a table of contents.
- Updated `pyproject.toml` and `setup.py` with new version and metadata.

### Technical

- Enhanced update checking mechanism
- Improved audio format handling
- Better error handling for audio extraction processes
- Updated dependencies and build system

## [1.0.0] - 2025-10-20

### Added

- Initial release of MediaTools Video Downloader
- Multi-platform support (Windows, Linux)
- Video downloading from 1000+ sites via yt-dlp
- Queue management system
- Settings configuration panel
- Auto-update feature for yt-dlp
- Cookie integration for private videos
- Format and quality selection
- Download speed control
- Thumbnail embedding support
- Smart format fallback system

### Technical

- PyInstaller build system for Windows and Linux
- Automated dependency management (yt-dlp, FFmpeg)
- Settings persistence
- Error handling and logging
- Cross-platform path handling
