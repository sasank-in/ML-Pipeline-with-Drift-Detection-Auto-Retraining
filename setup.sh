#!/bin/bash
# Setup script for Linux/Mac

echo "=========================================="
echo "  ML Pipeline Setup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.9+ first"
    exit 1
fi

echo "✅ Python is installed"
echo ""

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3 -m venv venv
echo "✅ Virtual environment created"
echo ""

# Activate and install dependencies
echo "🔌 Activating virtual environment..."
source venv/bin/activate

echo ""
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Create directories
echo "📁 Creating directories..."
mkdir -p data logs models
echo "✅ Directories created"
echo ""

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x run_all_services.sh
chmod +x stop_all_services.sh
echo "✅ Scripts ready"
echo ""

echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run: ./run_all_services.sh"
echo "  2. Wait 10 seconds"
echo "  3. Run: python demo.py"
echo "  4. Open: http://localhost:8050"
echo ""
