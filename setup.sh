#!/bin/bash

# Setup script for MAC-577IF-2E Air Conditioner Controller
# This script automates the installation process

set -e  # Exit on any error

echo "🚀 Setting up MAC-577IF-2E Air Conditioner Controller..."
echo

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version is compatible (requires 3.7+)"
else
    echo "❌ Python $python_version is too old. Please install Python 3.7 or newer."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

echo
echo "✅ Setup complete!"
echo
echo "📖 Quick start:"
echo "   source venv/bin/activate  # Activate the virtual environment"
echo "   python3 ac_control.py --ip YOUR_AC_IP --status"
echo
echo "📚 For detailed usage instructions, see INSTALL.md"
echo "🔍 To find your AC's IP address, check your router or run: nmap -sn 192.168.1.0/24"
echo
