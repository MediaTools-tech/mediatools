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
