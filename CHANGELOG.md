# MediaTools Changelog

All notable changes to the MediaTools project will be documented in this file.

## [Unreleased]

### Planned
- macOS build support for all tools
- Additional media processing tools
- Enhanced plugin system

## [2.2.0] - 2026-02-10

### Added
- **MediaTools Video Transcoder** Refinements
  - **Robust Audio Copy**: New mapping system (`FFMPEG_TO_FRONTEND_AUDIO`) and intelligent fallback (e.g., MKV defaults to Opus) for cross-container compatibility.
  - **Docker Job Management**: New `/api/jobs/{id}/cancel` endpoint and frontend **Cancel** button with safe process termination.
  - **Dynamic CRF Labels**: Video Quality dropdown now shows actual CRF values based on the selected codec (e.g., AV1 shows CRF-34 for Standard).
  - **Queue Intelligence**: Added "Enqueue Again" for Done/Error items and duplicate file collision detection.
  - **Stop & Cancel Logic**: Refined interruption handling with `_stopped` and `_cancelled` file suffixes.

### Fixed
- Resolved `NameError: ui_callback` when stopping tasks in `TranscoderService`.
- Improved FFmpeg progress parsing in Docker service for better reliability.
- Added detailed FFmpeg command logging for better transparency and debugging.

## [2.1.0] - 2026-01-03

### Added
- **MediaTools Video Downloader** v2.1.0 released
  - spotdl integration.
  - Added yt-dlp recommended deno executable as part of package.
  - Code refactored for better code modularity.
  - Enhanced update system.
  - New settings options for spotdl/spotify credentials.

## [2.0.0] - 2025-11-26

### Added
- **MediaTools Video Downloader** v2.0.0 released
  - Audio download feature (MP3, M4A, Best Audio).
  - Thumbnail embedding for audio files.
  - Dedicated audio folder organization.
  - Enhanced update system.
  - New audio settings panel.

### Changed
- Updated documentation and project metadata.

## [1.0.0] - 2025-10-20


### Added
- **MediaTools Video Downloader** v1.0.0 released
  - Multi-platform support (Windows, Linux)
  - Video downloading from 1000+ sites via yt-dlp
  - Queue management system
  - GUI interface with settings panel
  - Automatic dependency management

### Infrastructure
- Multi-app project structure established
- Cross-platform build system (Windows, Linux)
- Automated dependency handling
- Shared library code in `src/mediatools/`

### Technical
- PyInstaller build system
- Modular architecture for future tools
- Development tooling and scripts