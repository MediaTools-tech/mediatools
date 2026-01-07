# MediaTools Changelog

All notable changes to the MediaTools project will be documented in this file.

## [Unreleased]

### Planned
- macOS build support for all tools
- Additional media processing tools
- Enhanced plugin system

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