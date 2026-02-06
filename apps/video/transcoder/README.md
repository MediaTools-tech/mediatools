# MediaTools Video Transcoder

A powerful, cross-platform desktop application for batch video transcoding, powered by FFmpeg. Part of the [MediaTools](https://github.com/MediaTools-tech/mediatools) suite.

## Table of Contents

- [About](#about)
- [What's New in v1.0.0](#whats-new-in-v100)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Dependencies](#dependencies)
- [Support](#support)
- [License](#license)
- [Legal Disclaimer](#️-legal-disclaimer)
- [Credits](#credits)

## About

MediaTools Video Transcoder is a streamlined GUI for FFmpeg that simplifies complex video conversion tasks. Whether you need to shrink file sizes, change formats for device compatibility, or apply professional sharpening filters, this tool provides a robust and intuitive interface for high-quality results.

![](./docs/images/transcoder_screenshot.png)

## What's New in v1.0.0

- **First Major Release**: Complete video transcoding suite with support for H.264, H.265, AV1, and VP9.
- **Queue Management**: Advanced right-click context menu for reordering and managing batch tasks.
- **Auto-FFmpeg Management**: Automatically detects, downloads, and extracts the latest FFmpeg binaries.
- **Silent Operation**: Zero command-line windows on Windows; all processing happens in the background.
- **Graceful Shutdown**: Intelligent handling of FFmpeg processes ensuring no stray tasks are left running on app close.

## Features

### Advanced Transcoding

- **Multiple Codec Support**: H.264, H.265 (HEVC), AV1 (SVT-AV1), and VP9.
- **Universal Containers**: MP4, MKV, AVI, WebM, and MOV.
- **Audio Pass-Through**: Option to "Copy" original audio to maintain 1:1 quality.
- **Professional Filters**: Integrated sharpening filters (Unsharp, CAS) for enhanced visual clarity.
- **CRF Control**: Easy-to-use quality presets or custom CRF values for bitrate balance.

### Intelligent Workflow

- **Batch Processing**: Add individual files or entire folders with recursive scanning.
- **Queue Persistence**: Remembers your pending tasks and settings across sessions.
- **Output Management**: Automatic collision handling (e.g., `_1`, `_2`) without overwriting original files.
- **Interactive UI**: Drag-and-drop feeling with right-click queue management.

## System Requirements

- **Operating System**: Windows 10/11, Ubuntu 20.04+
- **macOS**: Supported
- **Dependencies**:
  - `FFmpeg` (automatically managed by the application)

## Installation

1. Download the latest release for your platform.
2. Run the executable file:
   - **Windows**: `mt-vtr.exe`
   - **Linux**: `mt-vtr` (make it executable with `chmod +x mt-vtr`)
3. The application will automatically check for FFmpeg and offer to download it on the first run.

## Quick Start

1. Launch MediaTools Video Transcoder.
2. Click **+ Add Files** or **+ Add Folder** to populate your queue.
3. Select your desired **Video Codec**, **Container**, and **Resolution**.
4. Click **START CONVERSION**. Use **CANCEL** to stop a batch or **EXIT** to close the app.
5. Your files will be saved to the configured output directory (Browse to change).

## Documentation

For detailed usage instructions and troubleshooting:

- See **UserGuide.md** in the `docs/` folder.
- Access the **Walkthrough** for a feature-by-feature tour.
- Complete documentation: [docs/UserGuide.md](docs/UserGuide.md)

## Dependencies

This application uses:

- **FFmpeg**: Media processing engine ([https://ffmpeg.org](https://ffmpeg.org))

FFmpeg is automatically downloaded and managed by the application to ensure compatibility.

## Support

For issues, questions, or feature requests:

- **GitHub Issues**: [https://github.com/MediaTools-tech/mediatools/issues](https://github.com/MediaTools-tech/mediatools/issues)
- **Website**: [mediatools.tech](https://mediatools.tech)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Disclaimer

This software is a GUI tool for FFmpeg. Users are solely responsible for ensuring they have the legal right to transcode and distribute the media files processed by this application.

## Credits

- **Developed by**: Bala
- **Organization**: MediaTools
- **Website**: [mediatools.tech](https://mediatools.tech)

---

**Version**: 1.0.0  
Copyright (c) 2026 MediaTools. All rights reserved.
