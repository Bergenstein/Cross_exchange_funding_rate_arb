#!/bin/bash

# EC2 Setup Script for Funding Rate Arbitrage Live Trading
# Run this on a fresh Ubuntu 22.04 EC2 instance

set -e

echo "=========================================="
echo "EC2 Setup for Funding Rate Arbitrage Bot"
echo "=========================================="

# Update system
echo "[1/8] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.10+
echo "[2/8] Installing Python 3.10..."
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Install required system packages
echo "[3/8] Installing system dependencies..."
sudo apt-get install -y git build-essential libssl-dev libffi-dev python3-dev
sudo apt-get install -y supervisor postgresql postgresql-contrib

# Create app directory
echo "[4/8] Setting up application directory..."
mkdir -p ~/funding_arb
cd ~/funding_arb

# Clone or create project
echo "[5/8] Setting up project files..."
# If you have a git repo:
# git clone https://github.com/yourusername/funding-rate-arb.git .

# For now, we'll assume you'll copy files manually

# Create Python virtual environment
echo "[6/8] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "[7/8] Installing Python dependencies..."
pip install --upgrade pip
pip install ccxt pandas numpy python-dotenv APScheduler requests

# Create necessary directories
mkdir -p logs
mkdir -p data

# Create systemd service
echo "[8/8] Setting up systemd service..."
sudo tee /etc/systemd/system/funding-arb.service > /dev/null <<EOF
[Unit]
Description=Funding Rate Arbitrage Trading Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/funding_arb
Environment="PATH=/home/$USER/funding_arb/venv/bin"
ExecStart=/home/$USER/funding_arb/venv/bin/python3 live_trading_system.py --mode=paper
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Set up log rotation
sudo tee /etc/logrotate.d/funding-arb > /dev/null <<EOF
/home/$USER/funding_arb/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $USER $USER
    sharedscripts
}
EOF

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Copy your code files to ~/funding_arb/"
echo "2. Create .env file with your API keys"
echo "3. Test the system:"
echo "   cd ~/funding_arb"
echo "   source venv/bin/activate"
echo "   python3 live_trading_system.py --mode=paper"
echo ""
echo "4. To run as a service:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable funding-arb"
echo "   sudo systemctl start funding-arb"
echo "   sudo systemctl status funding-arb"
echo ""
echo "5. View logs:"
echo "   tail -f ~/funding_arb/live_trading.log"
echo "   sudo journalctl -u funding-arb -f"
echo ""
echo "=========================================="
