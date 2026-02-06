#!/bin/bash
# Setup script for Video Transcoder project

set -e  # Exit on error

echo "🎬 Video Transcoder - Setup Script"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if running in project directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p api/routers api/services api/schemas
mkdir -p worker
mkdir -p frontend/{css,js,assets}
mkdir -p storage/{uploads,outputs,temp}
mkdir -p k8s tests scripts docs shared

# Create __init__.py files
touch api/__init__.py
touch api/routers/__init__.py
touch api/services/__init__.py
touch api/schemas/__init__.py
touch worker/__init__.py
touch shared/__init__.py
touch tests/__init__.py

# Create .gitkeep files for storage
touch storage/uploads/.gitkeep
touch storage/outputs/.gitkeep
touch storage/temp/.gitkeep

print_success "Directory structure created"

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp .env.example .env
    print_success ".env file created"
    print_info "Please edit .env file with your configuration"
else
    print_info ".env file already exists, skipping"
fi

# Check for Docker
echo ""
echo "🐳 Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_success "Docker is installed ($(docker --version))"
else
    print_error "Docker is not installed"
    echo "   Install from: https://docs.docker.com/get-docker/"
fi

if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose is installed ($(docker-compose --version))"
else
    print_error "Docker Compose is not installed"
    echo "   Install from: https://docs.docker.com/compose/install/"
fi

# Check for Python
echo ""
echo "🐍 Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Python is installed ($PYTHON_VERSION)"
    
    # Check Python version
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
        print_success "Python version is 3.11 or higher"
    else
        print_error "Python 3.11 or higher is required"
    fi
else
    print_error "Python 3 is not installed"
fi

# Check for FFmpeg (optional for local development)
echo ""
echo "🎥 Checking FFmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
    print_success "FFmpeg is installed ($FFMPEG_VERSION)"
else
    print_info "FFmpeg is not installed (required for local development)"
    echo "   Install: sudo apt-get install ffmpeg (Ubuntu/Debian)"
    echo "   Install: brew install ffmpeg (macOS)"
fi

# Setup virtual environment (optional)
echo ""
read -p "Do you want to create a Python virtual environment? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
    print_info "Activate it with: source venv/bin/activate"
    
    # Ask to install dependencies
    read -p "Do you want to install Python dependencies now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        print_success "Dependencies installed"
    fi
fi

# Final instructions
echo ""
echo "======================================"
echo "✨ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Review and edit .env file if needed"
echo ""
echo "2. Start with Docker:"
echo "   docker-compose up --build"
echo ""
echo "   OR"
echo ""
echo "   Start locally (with virtual environment):"
echo "   source venv/bin/activate"
echo "   uvicorn api.main:app --reload"
echo ""
echo "3. Open http://localhost:8000 in your browser"
echo ""
echo "4. Check API docs at http://localhost:8000/docs"
echo ""
print_success "Happy coding! 🚀"