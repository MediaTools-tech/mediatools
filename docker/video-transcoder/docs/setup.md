# Complete Setup Guide - Phase 1

This guide will walk you through setting up the Video Transcoder project from scratch.

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Git installed
- [ ] Docker & Docker Compose installed
- [ ] Python 3.11+ installed (for local development)
- [ ] FFmpeg installed (for local development)
- [ ] Code editor (VS Code, PyCharm, etc.)

## 🚀 Step-by-Step Setup

### Step 1: Clone and Setup Directory Structure

```bash
# Create project directory
mkdir video-transcoder
cd video-transcoder

# Initialize git
git init

# Run the setup script (after copying all files)
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Step 2: Configure Environment

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your preferred settings:
```bash
# Minimal required configuration
DEBUG=true
UPLOAD_DIR=./storage/uploads
OUTPUT_DIR=./storage/outputs
```

### Step 3: Docker Setup (Recommended)

This is the easiest way to get started:

```bash
# Build and start containers
docker-compose up --build

# Or run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

Access the application:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### Step 4: Local Development Setup (Alternative)

If you prefer local development without Docker:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools

# Create storage directories
mkdir -p storage/{uploads,outputs,temp}

# Run the application
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Verify Installation

### Test 1: Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-02T10:30:00",
  "ffmpeg_available": true
}
```

### Test 2: Upload a Video

```bash
# Download a test video (small file)
curl -o test.mp4 "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"

# Upload it
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test.mp4"
```

### Test 3: Run Automated Tests

```bash
# Activate virtual environment if not already
source venv/bin/activate

# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# With coverage report
pytest --cov=api --cov-report=html
```

## 📁 Project Structure Verification

Your project should look like this:

```
video-transcoder/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py
│   │   ├── jobs.py
│   │   └── upload.py
│   └── services/
│       ├── __init__.py
│       ├── job_manager.py
│       ├── storage.py
│       └── transcoder.py
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
├── storage/
│   ├── uploads/.gitkeep
│   ├── outputs/.gitkeep
│   └── temp/.gitkeep
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── scripts/
│   └── setup.sh
├── docs/
│   └── SETUP.md
├── .env
├── .env.example
├── .gitignore
├── .dockerignore
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🐛 Troubleshooting

### Issue: "FFmpeg not found"

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use port 8001 instead
```

### Issue: "Permission denied" on storage directories

**Solution:**
```bash
# Fix permissions
sudo chmod -R 777 storage/

# Or for Docker
sudo chown -R $USER:$USER storage/
```

### Issue: "Module not found" errors

**Solution:**
```bash
# Make sure you're in virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify Python path
python -c "import sys; print(sys.path)"
```

### Issue: Docker build fails

**Solution:**
```bash
# Clear Docker cache
docker-compose down -v
docker system prune -a

# Rebuild from scratch
docker-compose up --build --force-recreate
```

## 🔧 Development Workflow

### Running in Development Mode

```bash
# Option 1: Docker with hot reload
docker-compose up

# Changes to Python files will auto-reload

# Option 2: Local with hot reload
source venv/bin/activate
uvicorn api.main:app --reload
```

### Code Quality Checks

```bash
# Format code
black api/ tests/

# Sort imports
isort api/ tests/

# Lint code
flake8 api/ tests/

# Type checking
mypy api/
```

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f api

# Local logs (printed to console)
# Check terminal where uvicorn is running
```

## 📊 Monitoring & Debugging

### Check Application Status

```bash
# Health check
curl http://localhost:8000/api/health

# List all jobs
curl http://localhost:8000/api/jobs/

# Get specific job
curl http://localhost:8000/api/jobs/{job_id}
```

### Access Container Shell

```bash
# Access running container
docker-compose exec api bash

# Check FFmpeg in container
docker-compose exec api ffmpeg -version

# View files
docker-compose exec api ls -la storage/
```

### Debug Mode

Edit `.env`:
```bash
DEBUG=true
```

This will:
- Enable detailed error messages
- Show stack traces
- Enable FastAPI debug mode

## 🎯 Next Steps

Once Phase 1 is working:

1. **Test thoroughly**
   - Upload various video formats
   - Test large files
   - Test error cases

2. **Document your progress**
   - Take screenshots
   - Write blog post
   - Update README with your learnings

3. **Optimize**
   - Tune FFmpeg settings
   - Test different codecs
   - Measure performance

4. **Prepare for Phase 2**
   - Read Redis documentation
   - Study PostgreSQL basics
   - Plan worker architecture

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Docker Documentation](https://docs.docker.com/)
- [Python Async/Await Tutorial](https://realpython.com/async-io-python/)

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify FFmpeg: `docker-compose exec api ffmpeg -version`
3. Test API manually: http://localhost:8000/docs
4. Check storage permissions: `ls -la storage/`

## ✅ Setup Complete Checklist

- [ ] All files created and in correct locations
- [ ] Docker containers build successfully
- [ ] Application accessible at http://localhost:8000
- [ ] Health check returns "healthy"
- [ ] Can upload a test video
- [ ] Progress bar updates in real-time
- [ ] Can download transcoded video
- [ ] Automated tests pass

Congratulations! Your Phase 1 setup is complete. 🎉