# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Smart format fallback system for improved download reliability
- Automatic retry with alternative formats (MKV → MP4 → pre-merged)

### Improved
- Download success rate for problematic videos and edge cases
- Error handling for container format and merging failures
- Progress tracking consistency during format switching

### Planned
- macOS build support
- Additional video/audio tools

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

### Technical
- PyInstaller build system for Windows and Linux
- Automated dependency management (yt-dlp, FFmpeg)
- Settings persistence
- Error handling and logging
- Cross-platform path handling