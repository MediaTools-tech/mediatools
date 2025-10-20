# MediaTools

Comprehensive media processing tools for video, audio, image, and speech.

## Quick Links

- **Website:** [mediatools.tech](https://mediatools.tech)
- **Documentation:** [User Guides](docs/)
- **Issues:** [Report a Bug](https://github.com/MediaTools-tech/mediatools/issues)

## Applications

### Video Downloader
Download videos from 1000+ websites with a simple GUI or command-line interface.

- **Download:** [Latest Release](https://github.com/MediaTools-tech/mediatools/releases/latest)
- **Documentation:** [apps/video/downloader/docs/](apps/video/downloader/docs/)
- **Source:** [apps/video/downloader/](apps/video/downloader/)

### Coming Soon
- Audio Extractor

## For Developers

### Installation
```bash
# Clone the repository
git clone https://github.com/MediaTools-tech/mediatools.git
cd mediatools

# Install dependencies
pip install -r requirements.txt

# Install in development mode (optional)
pip install -e .
```

### Running Applications
```bash
# Video Downloader
cd apps/video/downloader
python launch.py
```

### Building Executables
```bash
# Build Video Downloader
cd apps/video/downloader/build
./build_onedir.sh      # Folder distribution
./build_onefile.sh     # Single executable
```

## Project Structure
```
mediatools/
├── src/              # Python library source code
├── apps/             # Standalone applications
├── docs/             # Documentation
├── tests/            # Tests
└── website/          # Project website
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation:** [docs/](docs/)
- **Issues:** [GitHub Issues](https://github.com/MediaTools-tech/mediatools/issues)
- **Contact:** bala.lv.555@gmail.com
