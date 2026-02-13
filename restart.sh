#!/bin/bash

# Darkstar E2EE Automation System - Restart Script
# Author: Darkstar Boii Sahiil
# Version: 3.0 - Production Ready

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       🔄 RESTARTING DARKSTAR E2EE AUTOMATION 🔄             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Stop first
echo -e "${YELLOW}[1/2]${NC} Stopping all services..."
./stop.sh
sleep 2

# Start again
echo ""
echo -e "${YELLOW}[2/2]${NC} Starting all services..."
./start.sh

echo ""
echo -e "${GREEN}Restart complete!${NC}"
echo ""