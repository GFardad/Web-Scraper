#!/bin/bash

# Stop script on any error
set -e

echo "Starting installation process..."

# 1. Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 not found. Please install it first: sudo apt install python3"
    exit 1
fi

# 2. Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment (venv)..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# 3. Install Python packages
echo "Installing Python libraries..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Playwright browsers
echo "Downloading Chromium browser (this may take a while)..."
playwright install chromium

echo "Installation completed successfully!"
echo "To run the scraper, execute:"
echo "./venv/bin/python main_engine.py"
echo ""
echo "To run the admin dashboard, execute:"
echo "./venv/bin/streamlit run dashboard.py"
