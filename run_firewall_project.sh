#!/bin/bash

# ========================================================================
# 🔥 FIREWALL AI PROJECT - COMPLETE TEST RUNNER
# ========================================================================
# This script runs the complete firewall testing pipeline:
# 1. Compiles the packet capture tool
# 2. Generates network traffic
# 3. Captures packets and creates CSV
# 4. Runs RL/AI testing with MDP enhancement
# 5. Displays results
# 6. Cleans up temporary files
# ========================================================================

# Color codes for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored headers
print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} $1"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${MAGENTA}ℹ️  $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "This script requires root privileges for packet capture"
    echo "Usage: sudo ./run_firewall_project.sh"
    exit 1
fi

# Store the main project directory
PROJECT_DIR="/home/aryan/Desktop/FireWall"
STEP1_DIR="$PROJECT_DIR/Step1"
RL_DIR="$PROJECT_DIR/RL_testing"

# Welcome banner
clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║        🔥 FIREWALL AI PROJECT - COMPLETE TEST SUITE 🔥         ║"
echo "║                                                                  ║"
echo "║     Packet Capture + Machine Learning + MDP Enhancement         ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
print_info "Starting complete firewall testing pipeline..."
echo ""
sleep 2

# ========================================================================
# STEP 1: COMPILATION
# ========================================================================
print_header "STEP 1: Compiling Packet Capture Tool"

cd "$STEP1_DIR" || exit 1

print_step "Checking for existing binary..."
if [ -f "capture" ]; then
    print_success "Capture binary already exists"
else
    print_step "Compiling capture.c with all modules..."
    gcc -Wall -Wextra -std=gnu11 capture.c preprocess.c denylist.c rate_limit.c malformed.c malformed_log.c -o capture -lpcap -lpthread
    
    if [ $? -eq 0 ]; then
        print_success "Compilation successful!"
    else
        print_error "Compilation failed!"
        exit 1
    fi
fi

# ========================================================================
# STEP 2: CLEANUP OLD FILES
# ========================================================================
print_header "STEP 2: Cleanup Old Files"

print_step "Removing old CSV files..."
rm -f summary_batch_1.csv
rm -f "$RL_DIR/network_traffic_data.csv"
rm -f "$RL_DIR/mdp_enhanced_predictions_*.csv"
rm -f "$RL_DIR/predictions_*.csv"
print_success "Old files cleaned up"

# ========================================================================
# STEP 3: TRAFFIC GENERATION & PACKET CAPTURE
# ========================================================================
print_header "STEP 3: Traffic Generation & Packet Capture"

print_step "Starting background traffic generation..."
(
    # Generate ICMP traffic
    for i in {1..30}; do
        ping -c 1 -W 1 8.8.8.8 > /dev/null 2>&1 &
        ping -c 1 -W 1 127.0.0.1 > /dev/null 2>&1 &
        sleep 0.3
    done
) &

TRAFFIC_PID=$!
print_success "Traffic generation started (PID: $TRAFFIC_PID)"

# Give traffic a head start
sleep 2

print_step "Capturing 50 network packets..."
echo ""
./capture -n 50

# Wait for traffic generation
wait $TRAFFIC_PID 2>/dev/null
print_success "Traffic generation completed"

# ========================================================================
# STEP 4: VERIFY CAPTURE RESULTS
# ========================================================================
print_header "STEP 4: Verify Capture Results"

if [ ! -f "summary_batch_1.csv" ]; then
    print_error "CSV file was not created!"
    print_warning "Capture may have failed - check network interfaces"
    exit 1
fi

LINE_COUNT=$(($(wc -l < summary_batch_1.csv) - 1))
FILE_SIZE=$(du -h summary_batch_1.csv | cut -f1)

print_success "CSV file generated successfully!"
print_info "File: summary_batch_1.csv"
print_info "Size: $FILE_SIZE"
print_info "Flows captured: $LINE_COUNT"

echo ""
print_step "Preview of captured data:"
echo ""
head -6 summary_batch_1.csv | column -t -s, 2>/dev/null || head -6 summary_batch_1.csv

if [ $LINE_COUNT -gt 5 ]; then
    echo ""
    print_info "... and $(($LINE_COUNT - 5)) more flows"
fi

# ========================================================================
# STEP 5: PREPARE FOR RL TESTING
# ========================================================================
print_header "STEP 5: Prepare for RL/AI Testing"

if [ ! -d "$RL_DIR" ]; then
    print_error "RL_testing directory not found at $RL_DIR"
    exit 1
fi

print_step "Copying CSV to RL_testing directory..."
cp summary_batch_1.csv "$RL_DIR/network_traffic_data.csv"

if [ ! -f "$RL_DIR/network_traffic_data.csv" ]; then
    print_error "Failed to copy CSV to RL_testing"
    exit 1
fi

print_success "CSV copied to RL_testing/network_traffic_data.csv"

# ========================================================================
# STEP 6: RUN RL/AI TESTING
# ========================================================================
print_header "STEP 6: Running RL/AI Testing with MDP Enhancement"

cd "$RL_DIR" || exit 1

print_step "Checking for trained models..."
MODEL_COUNT=$(ls -1 *.pth 2>/dev/null | wc -l)

if [ $MODEL_COUNT -eq 0 ]; then
    print_error "No trained models (.pth files) found in RL_testing directory!"
    print_warning "Please ensure model files are present before running"
    exit 1
fi

print_success "Found $MODEL_COUNT trained model(s)"
echo ""

print_step "Launching AI Firewall Tester..."
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Python3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python3 is not installed!"
    exit 1
fi

# Run the RL testing
python3 mdp_enhanced_reasoning.py

RL_EXIT_CODE=$?

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ $RL_EXIT_CODE -eq 0 ]; then
    print_success "RL Testing completed successfully!"
else
    print_warning "RL Testing exited with code $RL_EXIT_CODE"
fi

# ========================================================================
# STEP 7: DISPLAY RESULTS
# ========================================================================
print_header "STEP 7: Results Summary"

# Check for output CSV files
RESULT_FILES=$(ls -1 mdp_enhanced_predictions_*.csv 2>/dev/null | tail -1)

if [ -n "$RESULT_FILES" ]; then
    print_success "Enhanced prediction results saved:"
    print_info "$RESULT_FILES"
    echo ""
    
    print_step "Quick preview of results:"
    echo ""
    head -3 "$RESULT_FILES" | column -t -s, 2>/dev/null || head -3 "$RESULT_FILES"
    echo ""
    print_info "Full results available in: $RL_DIR/$RESULT_FILES"
else
    print_warning "No result files generated"
fi

# ========================================================================
# STEP 8: CLEANUP
# ========================================================================
print_header "STEP 8: Cleanup Temporary Files"

cd "$PROJECT_DIR" || exit 1

print_step "Removing temporary CSV files..."
rm -f "$STEP1_DIR/summary_batch_1.csv"
rm -f "$RL_DIR/network_traffic_data.csv"

if [ ! -f "$STEP1_DIR/summary_batch_1.csv" ] && [ ! -f "$RL_DIR/network_traffic_data.csv" ]; then
    print_success "Temporary files cleaned up successfully"
else
    print_warning "Some temporary files may still exist"
fi

# ========================================================================
# FINAL SUMMARY
# ========================================================================
echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║           🎉 FIREWALL AI PROJECT TEST COMPLETED! 🎉            ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

print_info "Summary:"
echo "  • Packets captured: $LINE_COUNT flows"
echo "  • Models tested: $MODEL_COUNT"
echo "  • Results location: $RL_DIR/"
echo ""

if [ -n "$RESULT_FILES" ]; then
    echo -e "${CYAN}📊 To view detailed results:${NC}"
    echo "   cat $RL_DIR/$RESULT_FILES"
    echo ""
fi

echo -e "${CYAN}📝 To run again:${NC}"
echo "   sudo ./run_firewall_project.sh"
echo ""

print_success "All done! 🚀"
echo ""

exit 0
