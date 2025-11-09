#!/bin/bash

# ================================================================
# 🔥 RL Firewall Dashboard Launcher
# ================================================================

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        🔥 RL-Based Firewall Dashboard Starting...          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Navigate to frontend directory
cd "$(dirname "$0")"

# Check if Python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed!"
    echo "Please install Python3 first: sudo apt-get install python3 python3-pip"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
if [ ! -f ".installed" ]; then
    echo "📥 Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
    
    touch .installed
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Create necessary directories
mkdir -p static templates

# Check if template and static files exist
if [ ! -f "templates/index.html" ] || [ ! -f "static/style.css" ] || [ ! -f "static/script.js" ]; then
    echo "⚠️  Warning: Some frontend files are missing!"
    echo "Please ensure the following files exist:"
    echo "  - templates/index.html"
    echo "  - static/style.css"
    echo "  - static/script.js"
fi

# Launch the dashboard
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Firewall Dashboard..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Dashboard will be available at: http://localhost:5000"
echo "📊 Open this URL in your browser to view the dashboard"
echo ""
echo "💡 Press Ctrl+C to stop the server"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the Flask app
python3 app.py

# Deactivate virtual environment on exit
deactivate
