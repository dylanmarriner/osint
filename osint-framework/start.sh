#!/bin/bash

# OSINT Framework Startup Script

set -e

echo "================================"
echo "OSINT Framework Startup"
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check environment file
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please review .env and customize as needed"
fi

# Create reports directory if it doesn't exist
mkdir -p reports

# Run the application
echo "Starting OSINT Framework..."
python main.py
