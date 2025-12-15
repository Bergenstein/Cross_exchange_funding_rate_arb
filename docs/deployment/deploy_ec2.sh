#!/bin/bash
# EC2 Deployment Script for Funding Rate Arbitrage Bot

set -e

echo "=================================="
echo "EC2 Setup - Funding Rate Arbitrage"
echo "=================================="

# Update system
echo "1. Updating system..."
sudo yum update -y || sudo apt-get update -y

# Install Python 3.9+
echo "2. Installing Python..."
sudo yum install python3 python3-pip git -y || sudo apt-get install python3 python3-pip git -y

# Create directory
echo "3. Creating working directory..."
mkdir -p ~/funding-arb
cd ~/funding-arb

# Upload files prompt
echo ""
echo "=================================="
echo "UPLOAD FILES TO EC2"
echo "=================================="
echo "From your local machine, run:"
echo ""
echo "scp -i your-key.pem -r /Users/israelbergenstein/Desktop/Trading_Strategies/Funding_Rate_Arb/* ec2-user@YOUR_EC2_IP:~/funding-arb/"
echo ""
echo "Press ENTER after uploading files..."
read

# Install dependencies
echo "4. Installing Python dependencies..."
pip3 install --user -r requirements_live.txt

# Setup .env
echo "5. Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.template .env
    echo ""
    echo "=================================="
    echo "CONFIGURE API KEYS"
    echo "=================================="
    echo "Edit .env file with your API keys:"
    echo "nano .env"
    echo ""
    echo "Press ENTER after editing .env..."
    read
fi

# Test paper trading
echo "6. Testing paper trading (60 seconds)..."
python3 live_trading_system.py --mode test --duration 60

# Check if test passed
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✓ SETUP COMPLETE"
    echo "=================================="
    echo ""
    echo "To start live trading:"
    echo "  screen -S funding-arb"
    echo "  python3 live_trading_system.py --mode live"
    echo "  # Press Ctrl+A then D to detach"
    echo ""
    echo "To view dashboard:"
    echo "  python3 live_dashboard.py"
    echo ""
    echo "To emergency stop:"
    echo "  python3 emergency_shutdown.py"
    echo ""
else
    echo ""
    echo "✗ Test failed. Check errors above."
fi
