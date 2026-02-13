#!/bin/bash

# Darkstar E2EE Automation System - Startup Script
# Author: Darkstar Boii Sahiil
# Version: 3.0 - Production Ready

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="darkstar-e2ee"
VENV_DIR="venv"
LOG_DIR="logs"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║     🚀 DARKSTAR E2EE AUTOMATION SYSTEM v3.0 🚀            ║"
echo "║                                                            ║"
echo "║     24/7 Non-Stop Production Ready                         ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    print_error "Virtual environment not found!"
    print_info "Please run ./deploy.sh first"
    exit 1
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source $VENV_DIR/bin/activate
print_success "Virtual environment activated"

# Create log directory if it doesn't exist
mkdir -p $LOG_DIR

# Check if already running
if pgrep -f "orchestrator.py" > /dev/null; then
    print_warning "Application is already running!"
    print_info "PID: $(pgrep -f orchestrator.py)"
    
    read -p "Do you want to restart? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Stopping existing instance..."
        pkill -f "orchestrator.py"
        sleep 2
    else
        print_info "Exiting..."
        exit 0
    fi
fi

# Start Orchestrator
print_info "Starting Orchestrator..."
nohup python orchestrator.py --daemon > $LOG_DIR/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
print_success "Orchestrator started (PID: $ORCHESTRATOR_PID)"

# Wait for orchestrator to initialize
print_info "Waiting for orchestrator to initialize..."
sleep 5

# Start Streamlit in background
print_info "Starting Streamlit UI..."
nohup streamlit run app_enhanced.py \
    --server.port=8501 \
    --server.headless=true \
    --server.address=0.0.0.0 \
    --browser.gatherUsageStats=false \
    > $LOG_DIR/streamlit.log 2>&1 &
STREAMLIT_PID=$!
print_success "Streamlit UI started (PID: $STREAMLIT_PID)"

# Wait for Streamlit to start
print_info "Waiting for Streamlit to start..."
sleep 3

# Display status
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    🎉 STARTUP SUCCESSFUL 🎉                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${CYAN}Orchestrator PID:${NC}   ${GREEN}$ORCHESTRATOR_PID${NC}"
echo -e "  ${CYAN}Streamlit PID:${NC}      ${GREEN}$STREAMLIT_PID${NC}"
echo -e "  ${CYAN}Orchestrator Log:${NC}   ${YELLOW}$LOG_DIR/orchestrator.log${NC}"
echo -e "  ${CYAN}Streamlit Log:${NC}      ${YELLOW}$LOG_DIR/streamlit.log${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Access Points:${NC}"
echo -e "  ${CYAN}• Local:${NC}           ${GREEN}http://localhost:8501${NC}"
echo -e "  ${CYAN}• Network:${NC}         ${GREEN}http://$(hostname -I | awk '{print $1}'):8501${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📋 Useful Commands:${NC}"
echo -e "  ${CYAN}• View logs:${NC}       ${YELLOW}tail -f logs/orchestrator.log${NC}"
echo -e "  ${CYAN}• View logs:${NC}       ${YELLOW}tail -f logs/streamlit.log${NC}"
echo -e "  ${CYAN}• Stop all:${NC}        ${YELLOW}./stop.sh${NC}"
echo -e "  ${CYAN}• Check status:${NC}    ${YELLOW}./status.sh${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show recent logs
print_info "Recent Orchestrator logs:"
tail -n 5 $LOG_DIR/orchestrator.log | while read line; do
    echo "  $line"
done

echo ""
print_success "Application is now running in 24/7 mode!"
echo ""