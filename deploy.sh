#!/bin/bash

# Darkstar E2EE Automation System - Deployment Script
# Author: Darkstar Boii Sahiil
# Version: 3.0 - Production Ready

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="darkstar-e2ee"
APP_VERSION="3.0.0"
PYTHON_VERSION="3.11"
VENV_DIR="venv"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Darkstar E2EE Deployment Script v${APP_VERSION}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_warning "This script should not be run as root for security reasons."
    print_warning "Please run as a regular user with sudo privileges."
    exit 1
fi

# Step 1: System Update
print_info "Step 1/10: Updating system packages..."
sudo apt-get update -qq
print_success "System packages updated"

# Step 2: Install System Dependencies
print_info "Step 2/10: Installing system dependencies..."
sudo apt-get install -y \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    build-essential \
    libssl-dev \
    libffi-dev \
    pkg-config \
    cargo \
    rustc \
    git \
    curl \
    wget \
    tmux \
    supervisor \
    nginx \
    sqlite3 \
    > /dev/null 2>&1
print_success "System dependencies installed"

# Step 3: Install Chromium Browser
print_info "Step 3/10: Installing Chromium browser..."
sudo apt-get install -y chromium chromium-driver > /dev/null 2>&1
print_success "Chromium browser installed"

# Step 4: Create Virtual Environment
print_info "Step 4/10: Creating Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python${PYTHON_VERSION} -m venv $VENV_DIR
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists, skipping..."
fi

# Step 5: Activate Virtual Environment
print_info "Step 5/10: Activating virtual environment..."
source $VENV_DIR/bin/activate
print_success "Virtual environment activated"

# Step 6: Upgrade pip
print_info "Step 6/10: Upgrading pip..."
pip install --upgrade pip setuptools wheel -q
print_success "Pip upgraded"

# Step 7: Install Python Dependencies
print_info "Step 7/10: Installing Python dependencies..."
if [ -f "requirements_Version2.txt" ]; then
    pip install -r requirements_Version2.txt -q
    print_success "Python dependencies installed"
else
    print_error "requirements_Version2.txt not found!"
    exit 1
fi

# Step 8: Create Necessary Directories
print_info "Step 8/10: Creating application directories..."
mkdir -p data logs backups temp downloads
print_success "Application directories created"

# Step 9: Set Permissions
print_info "Step 9/10: Setting file permissions..."
chmod +x *.sh
chmod 755 data logs backups temp downloads
print_success "File permissions set"

# Step 10: Initialize Database
print_info "Step 10/10: Initializing database..."
python -c "import database_enhanced as db; db.get_database().initialize()"
print_success "Database initialized"

# Additional Setup
print_info "Setting up supervisor configuration..."
sudo tee /etc/supervisor/conf.d/${APP_NAME}.conf > /dev/null <<EOF
[supervisord]
nodaemon=false
user=$(whoami)

[program:${APP_NAME}-orchestrator]
command=$(pwd)/venv/bin/python orchestrator.py --daemon
directory=$(pwd)
user=$(whoami)
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$(pwd)/logs/orchestrator.log
environment=PYTHONUNBUFFERED="1"

[program:${APP_NAME}-streamlit]
command=$(pwd)/venv/bin/streamlit run app_enhanced.py --server.port=8501 --server.headless=true
directory=$(pwd)
user=$(whoami)
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$(pwd)/logs/streamlit.log
environment=PYTHONUNBUFFERED="1"
EOF

print_success "Supervisor configuration created"

# Nginx Configuration
print_info "Setting up Nginx configuration..."
sudo tee /etc/nginx/sites-available/${APP_NAME} > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t > /dev/null 2>&1
sudo systemctl restart nginx
print_success "Nginx configuration done"

# Create systemd service
print_info "Creating systemd service..."
sudo tee /etc/systemd/system/${APP_NAME}.service > /dev/null <<EOF
[Unit]
Description=Darkstar E2EE Automation System
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/python orchestrator.py --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${APP_NAME}.service
print_success "Systemd service created and enabled"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
print_info "Application deployed successfully!"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Start the application:"
echo -e "   ${YELLOW}sudo systemctl start ${APP_NAME}${NC}"
echo "   or"
echo -e "   ${YELLOW}sudo supervisorctl start ${APP_NAME}-orchestrator${NC}"
echo ""
echo "2. Check status:"
echo -e "   ${YELLOW}sudo systemctl status ${APP_NAME}${NC}"
echo "   or"
echo -e "   ${YELLOW}sudo supervisorctl status${NC}"
echo ""
echo "3. View logs:"
echo -e "   ${YELLOW}tail -f logs/orchestrator.log${NC}"
echo "   ${YELLOW}tail -f logs/streamlit.log${NC}"
echo ""
echo "4. Access the application:"
echo -e "   ${YELLOW}http://localhost:8501${NC}"
echo "   or via Nginx: ${YELLOW}http://your-server-ip${NC}"
echo ""
print_success "Enjoy your 24/7 automation system!"
echo ""