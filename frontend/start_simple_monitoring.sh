#!/bin/bash
#
# Simple Continuous Firewall Monitoring System Launcher
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
BATCH_DURATION=10
FRONTEND_PORT=5000
DEBUG_MODE=false
FRONTEND_ONLY=false
MONITOR_ONLY=false

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STEP1_DIR="${SCRIPT_DIR}/../Step1"
FRONTEND_DIR="${SCRIPT_DIR}"

# PIDs for cleanup
FRONTEND_PID=""
MONITOR_PID=""

# Print banner
print_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║              🔥🤖 Simple Continuous Firewall Monitor                         ║"
    echo "║                                                                              ║"
    echo "║  🚀 Real-time batch processing with file-based communication              ║"
    echo "║  📊 Live dashboard with automatic updates                                   ║"
    echo "║  🌐 External traffic generation and analysis                                 ║"
    echo "║  🤖 RL predictions with confidence scoring                                   ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
}

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --batch-duration SECONDS    Batch duration in seconds (default: 10)"
    echo "  --frontend-port PORT        Frontend port (default: 5000)"
    echo "  --frontend-only            Start only the frontend dashboard"
    echo "  --monitor-only             Start only the continuous monitor"
    echo "  --debug                    Enable debug mode"
    echo "  --help                     Show this help"
    echo
    echo "Examples:"
    echo "  $0                         # Start complete system"
    echo "  $0 --batch-duration 8      # Use 8-second batches"
    echo "  $0 --frontend-only         # Frontend only"
    echo "  $0 --monitor-only          # Monitor only"
    echo
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --batch-duration)
                BATCH_DURATION="$2"
                shift 2
                ;;
            --frontend-port)
                FRONTEND_PORT="$2"
                shift 2
                ;;
            --frontend-only)
                FRONTEND_ONLY=true
                shift
                ;;
            --monitor-only)
                MONITOR_ONLY=true
                shift
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Print system information
print_info() {
    echo -e "${CYAN}📋 System Information:${NC}"
    echo "  Frontend Port: $FRONTEND_PORT"
    echo "  Batch Duration: ${BATCH_DURATION}s"
    echo "  Debug Mode: $DEBUG_MODE"
    echo "  Frontend Only: $FRONTEND_ONLY"
    echo "  Monitor Only: $MONITOR_ONLY"
    echo "  Step1 Directory: $STEP1_DIR"
    echo "  Frontend Directory: $FRONTEND_DIR"
    echo
}

# Cleanup function
cleanup_processes() {
    echo -e "${YELLOW}🧹 Cleaning up processes...${NC}"
    
    if [[ -n "$FRONTEND_PID" ]]; then
        echo "Stopping frontend dashboard (PID: $FRONTEND_PID)"
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi
    
    if [[ -n "$MONITOR_PID" ]]; then
        echo "Stopping continuous monitor (PID: $MONITOR_PID)"
        kill -TERM "$MONITOR_PID" 2>/dev/null || true
        wait "$MONITOR_PID" 2>/dev/null || true
    fi
    
    # Also kill by name as backup
    pkill -f "simple_continuous_monitor.py" 2>/dev/null || true
    pkill -f "simple_realtime_dashboard.py" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Setup signal handlers
trap cleanup_processes EXIT
trap 'echo -e "\n${YELLOW}⚠️  Received shutdown signal${NC}"; cleanup_processes; exit 0' INT TERM

# Check Python environment
check_python() {
    if [[ ! -f "${SCRIPT_DIR}/../venv/bin/python" ]]; then
        echo -e "${RED}❌ Virtual environment not found at ${SCRIPT_DIR}/../venv${NC}"
        echo "Please run the system from the correct directory or ensure the virtual environment exists."
        exit 1
    fi
    
    PYTHON="${SCRIPT_DIR}/../venv/bin/python"
}

# Start frontend dashboard
start_frontend() {
    echo -e "${BLUE}🚀 Starting Frontend Dashboard...${NC}"
    
    cd "$FRONTEND_DIR"
    
    if [[ "$DEBUG_MODE" == "true" ]]; then
        "$PYTHON" simple_realtime_dashboard.py &
    else
        "$PYTHON" simple_realtime_dashboard.py > /dev/null 2>&1 &
    fi
    
    FRONTEND_PID=$!
    sleep 2
    
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${GREEN}✅ Frontend dashboard started (PID: $FRONTEND_PID)${NC}"
        echo -e "${GREEN}🌐 Dashboard URL: http://localhost:$FRONTEND_PORT${NC}"
    else
        echo -e "${RED}❌ Failed to start frontend dashboard${NC}"
        exit 1
    fi
}

# Start continuous monitor
start_monitor() {
    echo -e "${BLUE}🚀 Starting Continuous Monitor...${NC}"
    
    cd "$STEP1_DIR"
    
    if [[ "$DEBUG_MODE" == "true" ]]; then
        "$PYTHON" simple_continuous_monitor.py \
            --batch-duration "$BATCH_DURATION" \
            --step1-dir "$STEP1_DIR" \
            --frontend-dir "$FRONTEND_DIR" &
    else
        "$PYTHON" simple_continuous_monitor.py \
            --batch-duration "$BATCH_DURATION" \
            --step1-dir "$STEP1_DIR" \
            --frontend-dir "$FRONTEND_DIR" &
    fi
    
    MONITOR_PID=$!
    sleep 2
    
    if kill -0 "$MONITOR_PID" 2>/dev/null; then
        echo -e "${GREEN}✅ Continuous monitor started (PID: $MONITOR_PID)${NC}"
        echo -e "${GREEN}📊 Batch Duration: ${BATCH_DURATION} seconds${NC}"
    else
        echo -e "${RED}❌ Failed to start continuous monitor${NC}"
        exit 1
    fi
}

# Main function
main() {
    print_banner
    parse_args "$@"
    print_info
    check_python
    
    cleanup_processes  # Clean any existing processes
    
    echo -e "${BLUE}🚀 Starting Simple Continuous Firewall Monitoring System...${NC}"
    
    if [[ "$MONITOR_ONLY" != "true" ]]; then
        start_frontend
    fi
    
    if [[ "$FRONTEND_ONLY" != "true" ]]; then
        start_monitor
    fi
    
    echo
    echo -e "${GREEN}🎉 All components started successfully!${NC}"
    echo -e "${GREEN}📊 Simple monitoring pipeline is running:${NC}"
    
    if [[ "$MONITOR_ONLY" != "true" ]]; then
        echo -e "${GREEN}  ✅ Frontend Dashboard: http://localhost:$FRONTEND_PORT${NC}"
    fi
    
    if [[ "$FRONTEND_ONLY" != "true" ]]; then
        echo -e "${GREEN}  ✅ Continuous Monitor: ${BATCH_DURATION}s batches${NC}"
        echo -e "${GREEN}  ✅ Traffic Generation: Enhanced external focus${NC}"
        echo -e "${GREEN}  ✅ RL Analysis: File-based communication${NC}"
    fi
    
    echo
    echo -e "${CYAN}🎯 Simple Monitoring System Active${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the system${NC}"
    
    # Wait for processes
    if [[ "$FRONTEND_ONLY" != "true" && -n "$MONITOR_PID" ]]; then
        wait "$MONITOR_PID"
    elif [[ "$MONITOR_ONLY" != "true" && -n "$FRONTEND_PID" ]]; then
        wait "$FRONTEND_PID"
    else
        # Both running, wait for either to finish
        while kill -0 "$FRONTEND_PID" 2>/dev/null || kill -0 "$MONITOR_PID" 2>/dev/null; do
            sleep 1
        done
    fi
}

# Run main function
main "$@"