#!/bin/bash

#
# Continuous Firewall Monitoring System Launcher
#
# This script starts the complete monitoring pipeline:
# 1. Frontend Dashboard (Flask + Socket.IO)  
# 2. Continuous Monitor (10-second batch processing)
# 3. Traffic Generation and Analysis
#
# Usage: ./start_continuous_monitoring.sh [options]
#
# Options:
#   --frontend-only    Start only the frontend dashboard
#   --monitor-only     Start only the continuous monitor  
#   --batch-duration   Set batch duration in seconds (default: 10)
#   --frontend-port    Set frontend port (default: 5000)
#

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEP1_DIR="$SCRIPT_DIR/../Step1"
FRONTEND_DIR="$SCRIPT_DIR"

# Default configuration
FRONTEND_PORT=5000
BATCH_DURATION=10
FRONTEND_ONLY=false
MONITOR_ONLY=false
DEBUG_MODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# PID files for process management
FRONTEND_PID_FILE="/tmp/firewall_dashboard.pid"
MONITOR_PID_FILE="/tmp/continuous_monitor.pid"

print_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║              🔥🤖 Continuous Firewall Monitoring System                      ║"
    echo "║                                                                              ║"
    echo "║  🚀 Real-time batch processing every ${BATCH_DURATION} seconds                           ║"
    echo "║  📊 Live dashboard with Socket.IO streaming                                  ║"
    echo "║  🌐 External traffic generation and analysis                                 ║"
    echo "║  🤖 RL predictions with confidence scoring                                   ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_usage() {
    echo -e "${WHITE}Usage:${NC}"
    echo "  $0 [OPTIONS]"
    echo ""
    echo -e "${WHITE}Options:${NC}"
    echo -e "  ${GREEN}--frontend-only${NC}      Start only the frontend dashboard"
    echo -e "  ${GREEN}--monitor-only${NC}       Start only the continuous monitor"  
    echo -e "  ${GREEN}--batch-duration N${NC}   Set batch duration in seconds (default: 10)"
    echo -e "  ${GREEN}--frontend-port N${NC}    Set frontend port (default: 5000)"
    echo -e "  ${GREEN}--debug${NC}             Enable debug mode"
    echo -e "  ${GREEN}--help${NC}              Show this help message"
    echo ""
    echo -e "${WHITE}Examples:${NC}"
    echo -e "  ${CYAN}$0${NC}                                    # Start complete system"
    echo -e "  ${CYAN}$0 --batch-duration 15${NC}               # Use 15-second batches"
    echo -e "  ${CYAN}$0 --frontend-only --frontend-port 8080${NC}  # Frontend only on port 8080"
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --frontend-only)
                FRONTEND_ONLY=true
                shift
                ;;
            --monitor-only)
                MONITOR_ONLY=true
                shift
                ;;
            --batch-duration)
                BATCH_DURATION="$2"
                shift 2
                ;;
            --frontend-port)
                FRONTEND_PORT="$2"
                shift 2
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
}

check_dependencies() {
    echo -e "${CYAN}🔍 Checking dependencies...${NC}"
    
    # Check if running as root (needed for packet capture)
    if [ "$EUID" -ne 0 ] && [ "$FRONTEND_ONLY" = false ]; then
        echo -e "${RED}❌ Continuous monitoring requires root privileges for packet capture${NC}"
        echo -e "${YELLOW}💡 Run with sudo or use --frontend-only${NC}"
        exit 1
    fi
    
    # Check Python virtual environment
    if [ ! -d "$FRONTEND_DIR/venv" ]; then
        echo -e "${RED}❌ Python virtual environment not found${NC}"
        echo -e "${YELLOW}💡 Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
        exit 1
    fi
    
    # Check Step1 directory
    if [ ! -d "$STEP1_DIR" ] && [ "$FRONTEND_ONLY" = false ]; then
        echo -e "${RED}❌ Step1 directory not found: $STEP1_DIR${NC}"
        exit 1
    fi
    
    # Check enhanced integration script
    if [ ! -f "$STEP1_DIR/enhanced_rl_integration.py" ] && [ "$FRONTEND_ONLY" = false ]; then
        echo -e "${RED}❌ Enhanced integration script not found${NC}"
        exit 1
    fi
    
    # Check continuous monitor script
    if [ ! -f "$STEP1_DIR/simplified_continuous_monitor.py" ] && [ "$FRONTEND_ONLY" = false ]; then
        echo -e "${RED}❌ Simplified continuous monitor script not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All dependencies checked${NC}"
}

cleanup_processes() {
    echo -e "\n${YELLOW}🧹 Cleaning up processes...${NC}"
    
    # Kill frontend if running
    if [ -f "$FRONTEND_PID_FILE" ]; then
        FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
        if kill -0 "$FRONTEND_PID" 2>/dev/null; then
            echo -e "${CYAN}Stopping frontend dashboard (PID: $FRONTEND_PID)${NC}"
            kill "$FRONTEND_PID"
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    # Kill monitor if running
    if [ -f "$MONITOR_PID_FILE" ]; then
        MONITOR_PID=$(cat "$MONITOR_PID_FILE")
        if kill -0 "$MONITOR_PID" 2>/dev/null; then
            echo -e "${CYAN}Stopping continuous monitor (PID: $MONITOR_PID)${NC}"
            kill "$MONITOR_PID"
        fi
        rm -f "$MONITOR_PID_FILE"
    fi
    
    # Kill any remaining python processes
    pkill -f "realtime_dashboard.py" 2>/dev/null
    pkill -f "continuous_monitor.py" 2>/dev/null
    pkill -f "simplified_continuous_monitor.py" 2>/dev/null
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

start_frontend() {
    echo -e "${BLUE}🚀 Starting Frontend Dashboard...${NC}"
    
    cd "$FRONTEND_DIR"
    source venv/bin/activate
    
    DEBUG_FLAG=""
    if [ "$DEBUG_MODE" = true ]; then
        DEBUG_FLAG="--debug"
    fi
    
    python3 realtime_dashboard.py --host 0.0.0.0 --port "$FRONTEND_PORT" $DEBUG_FLAG &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$FRONTEND_PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 2
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${GREEN}✅ Frontend dashboard started (PID: $FRONTEND_PID)${NC}"
        echo -e "${WHITE}🌐 Dashboard URL: http://localhost:$FRONTEND_PORT${NC}"
    else
        echo -e "${RED}❌ Frontend dashboard failed to start${NC}"
        rm -f "$FRONTEND_PID_FILE"
        return 1
    fi
}

start_monitor() {
    echo -e "${BLUE}🚀 Starting Continuous Monitor...${NC}"
    
    cd "$STEP1_DIR"
    
    LOG_LEVEL="INFO"
    if [ "$DEBUG_MODE" = true ]; then
        LOG_LEVEL="DEBUG"
    fi
    
    python3 simplified_continuous_monitor.py \
        --frontend-url "http://localhost:$FRONTEND_PORT" \
        --batch-duration "$BATCH_DURATION" &
    
    MONITOR_PID=$!
    echo $MONITOR_PID > "$MONITOR_PID_FILE"
    
    # Wait a moment and check if it started successfully  
    sleep 3
    if kill -0 "$MONITOR_PID" 2>/dev/null; then
        echo -e "${GREEN}✅ Continuous monitor started (PID: $MONITOR_PID)${NC}"
        echo -e "${WHITE}📊 Batch Duration: ${BATCH_DURATION} seconds${NC}"
    else
        echo -e "${RED}❌ Continuous monitor failed to start${NC}"
        rm -f "$MONITOR_PID_FILE"
        return 1
    fi
}

wait_for_processes() {
    echo -e "\n${WHITE}🎯 Monitoring System Active${NC}"
    echo -e "${CYAN}Press Ctrl+C to stop the system${NC}"
    
    # Function to handle signals
    trap cleanup_and_exit SIGINT SIGTERM
    
    # Wait for processes
    while true; do
        # Check if frontend is still running (if it should be)
        if [ "$MONITOR_ONLY" = false ] && [ -f "$FRONTEND_PID_FILE" ]; then
            FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
            if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
                echo -e "${RED}❌ Frontend dashboard stopped unexpectedly${NC}"
                break
            fi
        fi
        
        # Check if monitor is still running (if it should be)
        if [ "$FRONTEND_ONLY" = false ] && [ -f "$MONITOR_PID_FILE" ]; then
            MONITOR_PID=$(cat "$MONITOR_PID_FILE")
            if ! kill -0 "$MONITOR_PID" 2>/dev/null; then
                echo -e "${RED}❌ Continuous monitor stopped unexpectedly${NC}"
                break
            fi
        fi
        
        sleep 5
    done
}

cleanup_and_exit() {
    echo -e "\n${YELLOW}⚠️  Received shutdown signal${NC}"
    cleanup_processes
    exit 0
}

show_system_info() {
    echo -e "\n${WHITE}📋 System Information:${NC}"
    echo -e "  ${CYAN}Frontend Port:${NC} $FRONTEND_PORT"
    echo -e "  ${CYAN}Batch Duration:${NC} ${BATCH_DURATION}s" 
    echo -e "  ${CYAN}Debug Mode:${NC} $DEBUG_MODE"
    echo -e "  ${CYAN}Frontend Only:${NC} $FRONTEND_ONLY"
    echo -e "  ${CYAN}Monitor Only:${NC} $MONITOR_ONLY"
    echo -e "  ${CYAN}Step1 Directory:${NC} $STEP1_DIR"
    echo -e "  ${CYAN}Frontend Directory:${NC} $FRONTEND_DIR"
}

main() {
    print_banner
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Show configuration
    show_system_info
    
    # Check dependencies
    check_dependencies
    
    # Cleanup any existing processes
    cleanup_processes
    
    echo -e "\n${GREEN}🚀 Starting Continuous Firewall Monitoring System...${NC}"
    
    # Start components based on options
    if [ "$MONITOR_ONLY" = false ]; then
        start_frontend
        if [ $? -ne 0 ]; then
            exit 1
        fi
        
        # Give frontend time to fully start
        sleep 3
    fi
    
    if [ "$FRONTEND_ONLY" = false ]; then
        start_monitor
        if [ $? -ne 0 ]; then
            cleanup_processes
            exit 1
        fi
    fi
    
    echo -e "\n${GREEN}🎉 All components started successfully!${NC}"
    
    if [ "$FRONTEND_ONLY" = false ] && [ "$MONITOR_ONLY" = false ]; then
        echo -e "${WHITE}📊 Complete monitoring pipeline is running:${NC}"
        echo -e "  ${GREEN}✅${NC} Frontend Dashboard: http://localhost:$FRONTEND_PORT"
        echo -e "  ${GREEN}✅${NC} Continuous Monitor: ${BATCH_DURATION}s batches"
        echo -e "  ${GREEN}✅${NC} Traffic Generation: Enhanced external focus"
        echo -e "  ${GREEN}✅${NC} RL Analysis: Mock predictions with confidence"
    elif [ "$FRONTEND_ONLY" = true ]; then
        echo -e "${WHITE}📊 Frontend dashboard is running:${NC}"
        echo -e "  ${GREEN}✅${NC} Dashboard URL: http://localhost:$FRONTEND_PORT"
        echo -e "  ${YELLOW}⚠️${NC}  Start the monitor separately for live data"
    elif [ "$MONITOR_ONLY" = true ]; then
        echo -e "${WHITE}📊 Continuous monitor is running:${NC}"
        echo -e "  ${GREEN}✅${NC} Batch processing: ${BATCH_DURATION}s intervals"
        echo -e "  ${YELLOW}⚠️${NC}  Start the frontend to view results"
    fi
    
    # Wait for processes and handle shutdown
    wait_for_processes
}

# Run main function
main "$@"