# MediaTools Video Downloader

A cross-platform video and audio downloader application for downloading media from various platforms. For complete list of supported sites, check [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp).

## About

MediaTools Video Downloader is a user-friendly desktop application that allows you to download videos and audio in various formats and quality settings. The application provides an intuitive interface for managing downloads, organizing media files, and configuring download preferences.

## System Requirements

- **Operating System**: Windows 10/11, Ubuntu 20.04+
- **macOS**: *Coming soon*
- **Dependencies**:
  - yt-dlp (automatically managed)
  - FFmpeg (automatically managed)

## Installation

1. Download the latest release for your platform
2. Run the executable file:
   - **Windows**: `mt-vdl.exe`
   - **Linux**: `mt-vdl` (make executable with `chmod +x mt-vdl`)
3. The application will automatically download required dependencies on first run
4. Follow the on-screen setup wizard

## Quick Start

1. Launch MediaTools Video Downloader
2. Paste a video URL in the input field
3. Select your preferred format and quality
4. Click Download
5. Media files are saved to the configured downloads folder

## Features

### Video Download

- Auto update (yt-dlp & application)
- Download videos from 1000+ platforms
- Multiple format support (MKV, MP4)
- Quality selection (best quality, custom formats)
- Download speed control
- Custom download location
- Queue management for batch downloads
- Thumbnail embedding
- Cookie support for private videos
- Cross-platform compatibility
- Smart format fallback

### Audio Download (New in v2.0.0)

- Extract audio from videos
- Multiple audio formats (M4A, MP3, Best Audio)
- Thumbnail/cover art embedding
- Dedicated Audio folder organization
- Audio-specific queue management
- Quality preservation options

### Advanced Features

- Queue persistence between sessions
- Failed URL tracking
- Platform-specific folder organization
- Browser cookie integration
- Download archive to avoid duplicates

## Documentation

For detailed usage instructions, feature descriptions, and troubleshooting:

- See **UserGuide.pdf** in the application folder
- Or access Guide menu within the application
- Complete documentation: [docs/UserGuide.md](docs/UserGuide.md)

## Dependencies

This application uses:

- **yt-dlp**: Video downloading engine ([https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp))
- **FFmpeg**: Media processing ([https://ffmpeg.org](https://ffmpeg.org))

Both are automatically downloaded and managed by the application.

## What's New in v2.0.0

- **Audio Download**: Extract audio in MP3, M4A, or original quality
- **Enhanced Queue**: Support for audio-specific downloads with "audio:" prefix
- **Improved Updates**: Check for both yt-dlp and application updates
- **Better Organization**: Audio files automatically saved in dedicated folder
- **Quality Management**: Smart handling of audio format conversions

## Support

For issues, questions, or feature requests:

- **GitHub Issues**: [https://github.com/MediaTools-tech/mediatools/issues](https://github.com/MediaTools-tech/mediatools/issues)
- **Email**: [bala.lv.555@gmail.com](mailto:bala.lv.555@gmail.com)
- **Website**: [mediatools.tech](https://mediatools.tech)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Disclaimer

This software is a GUI tool for yt-dlp. Users are solely responsible for complying with copyright laws and platform terms of service. Only download content you have permission to access.

## Credits

- **Developed by**: Bala
- **Organization**: MediaTools
- **Website**: [mediatools.tech](https://mediatools.tech)
- **GitHub**: [https://github.com/MediaTools-tech/mediatools](https://github.com/MediaTools-tech/mediatools)

---

**Version**: 2.0.0  
Copyright (c) 2025 MediaTools. All rights reserved.
