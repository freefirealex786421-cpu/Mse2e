#!/bin/bash

# Darkstar E2EE Automation System - Status Script
# Author: Darkstar Boii Sahiil
# Version: 3.0 - Production Ready

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║       📊 DARKSTAR E2EE SYSTEM STATUS MONITOR 📊            ║"
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

# Get process information
ORCHESTRATOR_PID=$(pgrep -f "orchestrator.py" | head -n 1)
STREAMLIT_PID=$(pgrep -f "streamlit run app_enhanced.py" | head -n 1)

# Check Orchestrator Status
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  ORCHESTRATOR STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -n "$ORCHESTRATOR_PID" ]; then
    # Get memory usage
    ORCHESTRATOR_MEM=$(ps -p $ORCHESTRATOR_PID -o rss= | awk '{print $1/1024 " MB"}')
    ORCHESTRATOR_CPU=$(ps -p $ORCHESTRATOR_PID -o %cpu= | awk '{print $1"%"}')
    ORCHESTRATOR_TIME=$(ps -p $ORCHESTRATOR_PID -o etime= | xargs)
    
    echo -e "  Status:        ${GREEN}Running${NC}"
    echo -e "  PID:           ${GREEN}$ORCHESTRATOR_PID${NC}"
    echo -e "  Memory Usage:  ${CYAN}$ORCHESTRATOR_MEM${NC}"
    echo -e "  CPU Usage:     ${CYAN}$ORCHESTRATOR_CPU${NC}"
    echo -e "  Uptime:        ${CYAN}$ORCHESTRATOR_TIME${NC}"
else
    echo -e "  Status:        ${RED}Stopped${NC}"
fi

echo ""

# Check Streamlit Status
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  STREAMLIT UI STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -n "$STREAMLIT_PID" ]; then
    # Get memory usage
    STREAMLIT_MEM=$(ps -p $STREAMLIT_PID -o rss= | awk '{print $1/1024 " MB"}')
    STREAMLIT_CPU=$(ps -p $STREAMLIT_PID -o %cpu= | awk '{print $1"%"}')
    STREAMLIT_TIME=$(ps -p $STREAMLIT_PID -o etime= | xargs)
    
    echo -e "  Status:        ${GREEN}Running${NC}"
    echo -e "  PID:           ${GREEN}$STREAMLIT_PID${NC}"
    echo -e "  Memory Usage:  ${CYAN}$STREAMLIT_MEM${NC}"
    echo -e "  CPU Usage:     ${CYAN}$STREAMLIT_CPU${NC}"
    echo -e "  Uptime:        ${CYAN}$STREAMLIT_TIME${NC}"
    echo -e "  URL:           ${GREEN}http://localhost:8501${NC}"
    echo -e "  Network URL:   ${GREEN}http://$(hostname -I | awk '{print $1}'):8501${NC}"
else
    echo -e "  Status:        ${RED}Stopped${NC}"
fi

echo ""

# Check Database
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  DATABASE STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "users.db" ]; then
    DB_SIZE=$(du -h users.db | awk '{print $1}')
    DB_DATE=$(stat -c %y users.db | cut -d'.' -f1)
    echo -e "  Status:        ${GREEN}Available${NC}"
    echo -e "  File:          ${CYAN}users.db${NC}"
    echo -e "  Size:          ${CYAN}$DB_SIZE${NC}"
    echo -e "  Last Modified: ${CYAN}$DB_DATE${NC}"
else
    echo -e "  Status:        ${RED}Not Found${NC}"
fi

echo ""

# Check Logs
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  LOG FILES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "logs/orchestrator.log" ]; then
    ORCH_LOG_SIZE=$(du -h logs/orchestrator.log | awk '{print $1}')
    ORCH_LOG_LINES=$(wc -l < logs/orchestrator.log)
    echo -e "  Orchestrator:  ${CYAN}$ORCH_LOG_SIZE${NC} (${CYAN}$ORCH_LOG_LINES lines${NC})"
else
    echo -e "  Orchestrator:  ${RED}Not found${NC}"
fi

if [ -f "logs/streamlit.log" ]; then
    STREAMLIT_LOG_SIZE=$(du -h logs/streamlit.log | awk '{print $1}')
    STREAMLIT_LOG_LINES=$(wc -l < logs/streamlit.log)
    echo -e "  Streamlit:     ${CYAN}$STREAMLIT_LOG_SIZE${NC} (${CYAN}$STREAMLIT_LOG_LINES lines${NC})"
else
    echo -e "  Streamlit:     ${RED}Not found${NC}"
fi

echo ""

# Check Backups
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  BACKUPS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

BACKUP_COUNT=$(ls backups/backup_*.db* 2>/dev/null | wc -l)
if [ $BACKUP_COUNT -gt 0 ]; then
    LATEST_BACKUP=$(ls -t backups/backup_*.db* 2>/dev/null | head -n 1)
    LATEST_BACKUP_DATE=$(stat -c %y "$LATEST_BACKUP" | cut -d'.' -f1)
    echo -e "  Total Backups:    ${GREEN}$BACKUP_COUNT${NC}"
    echo -e "  Latest Backup:    ${CYAN}$LATEST_BACKUP_DATE${NC}"
else
    echo -e "  Total Backups:    ${YELLOW}0${NC}"
    echo -e "  Status:           ${YELLOW}No backups found${NC}"
fi

echo ""

# System Resources
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  SYSTEM RESOURCES${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

MEM_TOTAL=$(free -h | awk '/^Mem:/ {print $2}')
MEM_USED=$(free -h | awk '/^Mem:/ {print $3}')
MEM_PERCENT=$(free | awk '/^Mem:/ {printf "%.1f", ($3/$2)*100}')
DISK_TOTAL=$(df -h . | awk 'NR==2 {print $2}')
DISK_USED=$(df -h . | awk 'NR==2 {print $3}')
DISK_PERCENT=$(df -h . | awk 'NR==2 {print $5}')

echo -e "  Memory:         ${CYAN}$MEM_USED / $MEM_TOTAL${NC} (${CYAN}$MEM_PERCENT%${NC})"
echo -e "  Disk:           ${CYAN}$DISK_USED / $DISK_TOTAL${NC} (${CYAN}$DISK_PERCENT${NC})"
echo -e "  Load Average:   ${CYAN}$(uptime | awk -F'load average:' '{print $2}'${NC}"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  QUICK COMMANDS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Start:          ${YELLOW}./start.sh${NC}"
echo -e "  Stop:           ${YELLOW}./stop.sh${NC}"
echo -e "  Restart:        ${YELLOW}./restart.sh${NC}"
echo -e "  View Logs:      ${YELLOW}tail -f logs/orchestrator.log${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Overall status
if [ -n "$ORCHESTRATOR_PID" ] && [ -n "$STREAMLIT_PID" ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    🟢 ALL SYSTEMS OPERATIONAL 🟢            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
elif [ -n "$ORCHESTRATOR_PID" ] || [ -n "$STREAMLIT_PID" ]; then
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║                   🟡 PARTIAL SYSTEM RUNNING 🟡              ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                    🔴 ALL SYSTEMS STOPPED 🔴                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
fi

echo ""