#!/bin/bash

# Darkstar E2EE Automation System - Stop Script
# Author: Darkstar Boii Sahiil
# Version: 3.0 - Production Ready

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🛑 STOPPING DARKSTAR E2EE AUTOMATION SYSTEM 🛑         ║"
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

# Check if orchestrator is running
ORCHESTRATOR_PID=$(pgrep -f "orchestrator.py" | head -n 1)
if [ -n "$ORCHESTRATOR_PID" ]; then
    print_info "Stopping Orchestrator (PID: $ORCHESTRATOR_PID)..."
    kill $ORCHESTRATOR_PID
    sleep 2
    
    # Force kill if still running
    if pgrep -f "orchestrator.py" > /dev/null; then
        print_warning "Forcing shutdown..."
        pkill -9 -f "orchestrator.py"
        sleep 1
    fi
    print_success "Orchestrator stopped"
else
    print_warning "Orchestrator is not running"
fi

# Check if streamlit is running
STREAMLIT_PID=$(pgrep -f "streamlit run app_enhanced.py" | head -n 1)
if [ -n "$STREAMLIT_PID" ]; then
    print_info "Stopping Streamlit (PID: $STREAMLIT_PID)..."
    kill $STREAMLIT_PID
    sleep 2
    
    # Force kill if still running
    if pgrep -f "streamlit run app_enhanced.py" > /dev/null; then
        print_warning "Forcing shutdown..."
        pkill -9 -f "streamlit run app_enhanced.py"
        sleep 1
    fi
    print_success "Streamlit stopped"
else
    print_warning "Streamlit is not running"
fi

# Kill any remaining python processes related to the app
print_info "Cleaning up remaining processes..."
pkill -f "app_enhanced.py" 2>/dev/null || true
pkill -f "automation_engine" 2>/dev/null || true
pkill -f "monitoring_system" 2>/dev/null || true
sleep 1

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     🛑 STOPPED SUCCESSFULLY 🛑              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
print_success "All services stopped successfully!"
echo ""