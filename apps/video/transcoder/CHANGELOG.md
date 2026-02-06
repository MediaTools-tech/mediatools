# Changelog

All notable changes to the MediaTools Video Transcoder will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-02-05

### Changed
- Renamed **STOP** button to **CANCEL** for better clarity.
- Added **EXIT** button for a dedicated way to close the application.
- Expanded queue context menu with **Move to Bottom**.
- Added **Enqueue Again** option for "Cancelled" tasks to quickly retry them.

## [1.0.0] - 2026-02-04

### Added
- **Initial Release**: Full-featured batch video transcoding application.
- **Hardware-Friendly Codecs**: Support for H.264, H.265 (HEVC), AV1, and VP9.
- **Container Selection**: Choice of MP4, MKV, WebM, AVI, and MOV.
- **Queue Management**: 
  - Right-click context menu (Move to Top, Up, Down, Remove).
  - Persistence across sessions (`queue.txt`).
- **Auto-FFmpeg Management**:
  - Automatic detection and 28-day update checks.
  - Background download and extraction.
- **UI/UX Refinements**:
  - Silent subprocess execution (no CMD windows on Windows).
  - "Downloads Folder" quick access button.
  - Intelligent status feedback during startup checks.
- **Robustness**:
  - Graceful exit handling (kills FFmpeg processes).
  - Smart collision handling for output filenames (no `_transcoded` suffix unless needed).
  - Exponential backoff for file handle management during extraction.

### Technical
- Modular architecture with `TranscoderEngine` and `TranscoderService`.
- Cross-platform path resolution compatible with PyInstaller `onedir` and `onefile` modes.
- Multi-threaded transcoding with real-time progress parsing.
