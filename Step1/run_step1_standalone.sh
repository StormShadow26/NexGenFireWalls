#!/bin/bash
# =============================================================================
# Step1 Standalone Runner - Complete Firewall Packet Capture System
# =============================================================================
# This script runs the Step1 firewall components independently with full
# traffic generation, capture, filtering, and analysis capabilities.
#
# Features:
# - Builds the capture tool with all filters
# - Generates real network traffic 
# - Captures and processes packets through all firewall stages
# - Displays comprehensive statistics and results
# - Integrates with RL testing system
# - Provides interactive mode for testing
#
# Usage: sudo ./run_step1_standalone.sh [options]
# =============================================================================

set -e  # Exit on any error

# =============================================================================
# Configuration & Variables
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Default settings
PACKET_COUNT=100
INTERFACE="any"
GENERATE_TRAFFIC="true"
RUN_RL_TEST="false"
CLEAN_AFTER="true"
VERBOSE="false"
INTERACTIVE="false"

# =============================================================================
# Helper Functions
# =============================================================================
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        🔥 Step1 Firewall Standalone Runner                    ║"
    echo "║                                                                               ║"
    echo "║  Complete packet capture and filtering system with:                           ║"
    echo "║  • Traffic Generation & Capture                                               ║"
    echo "║  • IP/Port Denylist Filtering                                                 ║"
    echo "║  • Rate Limiting & Malformed Packet Detection                                ║"
    echo "║  • Statistical Analysis & CSV Export                                          ║"
    echo "║  • Optional RL Integration                                                    ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}  $1${NC}"
    echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC}  $1"
}

show_help() {
    echo "Usage: sudo ./run_step1_standalone.sh [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  -n, --packets NUM     Number of packets to capture (default: 100)"
    echo "  -i, --interface IF    Network interface to use (default: any)"
    echo "  -t, --no-traffic      Don't generate synthetic traffic"
    echo "  -r, --run-rl          Run RL testing after capture"
    echo "  -k, --keep-files      Keep CSV files after completion"
    echo "  -v, --verbose         Enable verbose output"
    echo "  -I, --interactive     Interactive mode with menu"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "EXAMPLES:"
    echo "  sudo ./run_step1_standalone.sh"
    echo "  sudo ./run_step1_standalone.sh -n 200 -r"
    echo "  sudo ./run_step1_standalone.sh -i eth0 --verbose"
    echo "  sudo ./run_step1_standalone.sh --interactive"
    echo ""
}

check_requirements() {
    print_section "🔍 Checking System Requirements"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        print_error "This script requires sudo privileges for packet capture"
        echo "Usage: sudo $0 [options]"
        exit 1
    fi
    print_status "Running with sudo privileges"
    
    # Check required tools
    local missing_tools=""
    for tool in gcc make ping curl; do
        if ! command -v $tool &> /dev/null; then
            missing_tools="$missing_tools $tool"
        fi
    done
    
    if [ -n "$missing_tools" ]; then
        print_error "Missing required tools:$missing_tools"
        print_info "Install with: apt update && apt install -y$missing_tools"
        exit 1
    fi
    print_status "All required tools available"
    
    # Check for pcap library
    if ! ldconfig -p | grep -q libpcap; then
        print_error "libpcap library not found"
        print_info "Install with: apt install -y libpcap-dev"
        exit 1
    fi
    print_status "libpcap library found"
    
    # Check network interfaces
    local interfaces=$(ip link show | grep -E "^[0-9]+" | cut -d: -f2 | tr -d ' ' | grep -v lo)
    if [ -z "$interfaces" ]; then
        print_warning "No active network interfaces found (except loopback)"
        INTERFACE="lo"
    fi
    print_status "Network interfaces available"
}

show_configuration() {
    print_section "⚙️  Current Configuration"
    
    echo -e "${WHITE}Capture Settings:${NC}"
    echo "  📦 Packets to capture: $PACKET_COUNT"
    echo "  🌐 Network interface: $INTERFACE"
    echo "  🚦 Generate traffic: $([[ $GENERATE_TRAFFIC == "true" ]] && echo "Yes" || echo "No")"
    echo "  🧠 Run RL testing: $([[ $RUN_RL_TEST == "true" ]] && echo "Yes" || echo "No")"
    echo "  🧹 Clean after run: $([[ $CLEAN_AFTER == "true" ]] && echo "Yes" || echo "No")"
    echo ""
    
    echo -e "${WHITE}Filter Configuration:${NC}"
    if [ -f "IP.txt" ]; then
        local ip_count=$(wc -l < IP.txt)
        echo "  🚫 Blocked IPs: $ip_count entries"
        if [ $ip_count -gt 0 ]; then
            echo "      $(head -3 IP.txt | tr '\n' ' ')$([ $ip_count -gt 3 ] && echo "...")"
        fi
    else
        echo "  🚫 Blocked IPs: No IP.txt file found"
    fi
    
    if [ -f "Ports.txt" ]; then
        local port_count=$(wc -l < Ports.txt)
        echo "  🔒 Blocked Ports: $port_count entries"
        if [ $port_count -gt 0 ]; then
            echo "      $(head -3 Ports.txt | tr '\n' ' ')$([ $port_count -gt 3 ] && echo "...")"
        fi
    else
        echo "  🔒 Blocked Ports: No Ports.txt file found"
    fi
}

build_system() {
    print_section "🔨 Building Firewall System"
    
    # Clean previous builds
    if [ -f "Makefile" ]; then
        print_info "Cleaning previous build..."
        make clean &>/dev/null || true
        print_status "Previous build cleaned"
    fi
    
    # Build the capture tool
    print_info "Compiling capture tool with all filters..."
    if make all; then
        print_status "Build completed successfully"
        
        # Verify binary exists and is executable
        if [ -x "./capture" ]; then
            print_status "Capture binary ready: $(ls -lh ./capture | awk '{print $5}')"
        else
            print_error "Build failed - capture binary not found"
            exit 1
        fi
    else
        print_error "Build failed - check compiler errors above"
        exit 1
    fi
}

generate_traffic() {
    if [ "$GENERATE_TRAFFIC" != "true" ]; then
        return 0
    fi
    
    print_section "🚦 Generating Network Traffic"
    
    print_info "Starting background traffic generation..."
    
    # Function to generate various types of traffic
    (
        # ICMP traffic (ping)
        for i in $(seq 1 20); do
            ping -c 1 -W 1 8.8.8.8 &>/dev/null &
            ping -c 1 -W 1 127.0.0.1 &>/dev/null &
            ping -c 1 -W 1 1.1.1.1 &>/dev/null &
            sleep 0.1
        done
        
        # HTTP traffic simulation
        for i in $(seq 1 10); do
            curl -s -m 2 http://httpbin.org/ip &>/dev/null &
            curl -s -m 2 http://example.com &>/dev/null &
            sleep 0.2
        done
        
        # Local traffic
        for i in $(seq 1 15); do
            nc -z 127.0.0.1 22 &>/dev/null &
            nc -z 127.0.0.1 80 &>/dev/null &
            sleep 0.1
        done
        
    ) &
    
    TRAFFIC_PID=$!
    print_status "Traffic generation started (PID: $TRAFFIC_PID)"
    
    # Give traffic time to start
    sleep 2
}

run_capture() {
    print_section "📡 Packet Capture & Filtering"
    
    local capture_cmd="./capture -n $PACKET_COUNT"
    if [ "$INTERFACE" != "any" ]; then
        capture_cmd="$capture_cmd -i $INTERFACE"
    fi
    
    print_info "Starting packet capture: $capture_cmd"
    print_info "This will capture $PACKET_COUNT packets through all filter stages..."
    echo ""
    
    # Run the capture with real-time output
    if $capture_cmd; then
        print_status "Packet capture completed successfully"
    else
        local exit_code=$?
        print_error "Packet capture failed (exit code: $exit_code)"
        
        # Stop traffic generation if it's running
        if [ -n "$TRAFFIC_PID" ] && kill -0 "$TRAFFIC_PID" 2>/dev/null; then
            kill "$TRAFFIC_PID" 2>/dev/null || true
        fi
        
        return $exit_code
    fi
    
    # Stop traffic generation
    if [ -n "$TRAFFIC_PID" ] && kill -0 "$TRAFFIC_PID" 2>/dev/null; then
        kill "$TRAFFIC_PID" 2>/dev/null || true
        print_info "Traffic generation stopped"
    fi
}

analyze_results() {
    print_section "📊 Results Analysis"
    
    if [ ! -f "summary_batch_1.csv" ]; then
        print_error "No results file found (summary_batch_1.csv)"
        print_info "The capture may have failed or no packets were processed"
        return 1
    fi
    
    print_status "Results file generated: summary_batch_1.csv"
    
    # Get file statistics
    local file_size=$(du -h summary_batch_1.csv | cut -f1)
    local line_count=$(($(wc -l < summary_batch_1.csv) - 1))
    
    echo -e "${WHITE}File Statistics:${NC}"
    echo "  📁 File size: $file_size"
    echo "  📝 Network flows: $line_count"
    echo ""
    
    if [ $line_count -eq 0 ]; then
        print_warning "No network flows captured - check network activity"
        return 1
    fi
    
    # Show sample data
    echo -e "${WHITE}Sample Data (first 5 flows):${NC}"
    if command -v column &> /dev/null; then
        head -6 summary_batch_1.csv | column -t -s, | head -6
    else
        head -6 summary_batch_1.csv
    fi
    
    if [ $line_count -gt 5 ]; then
        echo "  ... and $((line_count - 5)) more flows"
    fi
    echo ""
    
    # Analyze the data for filtering statistics
    if [ $line_count -gt 1 ]; then
        echo -e "${WHITE}Filter Analysis:${NC}"
        
        # Count different actions (assuming CSV has action column)
        local allowed_count=$(tail -n +2 summary_batch_1.csv | grep -c ",allow," 2>/dev/null || echo "N/A")
        local blocked_count=$(tail -n +2 summary_batch_1.csv | grep -c ",block," 2>/dev/null || echo "N/A")
        local inspect_count=$(tail -n +2 summary_batch_1.csv | grep -c ",inspect," 2>/dev/null || echo "N/A")
        
        echo "  ✅ Allowed packets: $allowed_count"
        echo "  🚫 Blocked packets: $blocked_count"  
        echo "  🔍 Inspected packets: $inspect_count"
    fi
    
    print_status "Analysis completed"
}

run_rl_integration() {
    if [ "$RUN_RL_TEST" != "true" ]; then
        return 0
    fi
    
    print_section "🧠 RL Testing Integration"
    
    local rl_dir="../RL_testing"
    
    if [ ! -d "$rl_dir" ]; then
        print_warning "RL_testing directory not found at $rl_dir"
        print_info "Skipping RL integration"
        return 1
    fi
    
    print_info "Copying data to RL_testing directory..."
    cp summary_batch_1.csv "$rl_dir/network_traffic_data.csv"
    
    if [ ! -f "$rl_dir/network_traffic_data.csv" ]; then
        print_error "Failed to copy data to RL directory"
        return 1
    fi
    print_status "Data copied successfully"
    
    print_info "Running RL analysis..."
    echo ""
    
    # Run RL testing
    cd "$rl_dir"
    if python3 mdp_enhanced_reasoning.py; then
        print_status "RL analysis completed successfully"
    else
        print_error "RL analysis failed"
        cd - > /dev/null
        return 1
    fi
    cd - > /dev/null
    
    print_status "RL integration completed"
}

cleanup_files() {
    if [ "$CLEAN_AFTER" != "true" ]; then
        return 0
    fi
    
    print_section "🧹 Cleanup"
    
    local files_to_clean=("summary_batch_1.csv")
    if [ "$RUN_RL_TEST" == "true" ]; then
        files_to_clean+=("../RL_testing/network_traffic_data.csv")
    fi
    
    print_info "Cleaning temporary files..."
    
    local cleaned_count=0
    for file in "${files_to_clean[@]}"; do
        if [ -f "$file" ]; then
            rm -f "$file"
            cleaned_count=$((cleaned_count + 1))
            print_info "Removed: $file"
        fi
    done
    
    if [ $cleaned_count -gt 0 ]; then
        print_status "Cleaned $cleaned_count temporary files"
    else
        print_info "No temporary files to clean"
    fi
}

interactive_mode() {
    print_section "🎮 Interactive Mode"
    
    while true; do
        echo -e "${WHITE}Choose an option:${NC}"
        echo "  1) Quick Test (100 packets, with traffic)"
        echo "  2) Extended Test (500 packets, with traffic + RL)"
        echo "  3) Custom Configuration"
        echo "  4) View Current Configuration"
        echo "  5) Show System Status"
        echo "  6) Run Standalone Test"
        echo "  0) Exit"
        echo ""
        
        read -p "Enter choice [0-6]: " choice
        
        case $choice in
            1)
                PACKET_COUNT=100
                GENERATE_TRAFFIC="true"
                RUN_RL_TEST="false"
                CLEAN_AFTER="true"
                break
                ;;
            2)
                PACKET_COUNT=500
                GENERATE_TRAFFIC="true"
                RUN_RL_TEST="true"
                CLEAN_AFTER="true"
                break
                ;;
            3)
                echo ""
                read -p "Number of packets [100]: " input
                PACKET_COUNT=${input:-100}
                
                read -p "Network interface [any]: " input
                INTERFACE=${input:-any}
                
                read -p "Generate traffic? [y/N]: " input
                GENERATE_TRAFFIC=$([[ "$input" =~ ^[Yy] ]] && echo "true" || echo "false")
                
                read -p "Run RL testing? [y/N]: " input
                RUN_RL_TEST=$([[ "$input" =~ ^[Yy] ]] && echo "true" || echo "false")
                
                read -p "Clean files after? [Y/n]: " input
                CLEAN_AFTER=$([[ "$input" =~ ^[Nn] ]] && echo "false" || echo "true")
                break
                ;;
            4)
                show_configuration
                echo ""
                ;;
            5)
                print_info "System Status:"
                echo "  🔧 Build status: $([ -f "./capture" ] && echo "Ready" || echo "Not built")"
                echo "  📁 Working directory: $PWD"
                echo "  👤 User: $(whoami)"
                echo "  🌐 Interfaces: $(ip link show | grep -E "^[0-9]+" | wc -l) available"
                echo ""
                ;;
            6)
                echo ""
                print_info "Starting standalone test with current configuration..."
                break
                ;;
            0)
                print_info "Exiting interactive mode"
                exit 0
                ;;
            *)
                print_error "Invalid choice. Please enter 0-6."
                ;;
        esac
    done
}

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--packets)
                PACKET_COUNT="$2"
                shift 2
                ;;
            -i|--interface)
                INTERFACE="$2"
                shift 2
                ;;
            -t|--no-traffic)
                GENERATE_TRAFFIC="false"
                shift
                ;;
            -r|--run-rl)
                RUN_RL_TEST="true"
                shift
                ;;
            -k|--keep-files)
                CLEAN_AFTER="false"
                shift
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -I|--interactive)
                INTERACTIVE="true"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Set verbose mode if requested
    if [ "$VERBOSE" == "true" ]; then
        set -x
    fi
    
    # Main execution flow
    print_banner
    
    check_requirements
    
    if [ "$INTERACTIVE" == "true" ]; then
        interactive_mode
    fi
    
    show_configuration
    
    # Confirm execution (unless in non-interactive mode with args)
    if [ "$INTERACTIVE" != "true" ] && [ $# -eq 0 ]; then
        echo ""
        read -p "Proceed with execution? [Y/n]: " confirm
        if [[ "$confirm" =~ ^[Nn] ]]; then
            print_info "Execution cancelled by user"
            exit 0
        fi
    fi
    
    # Execute the pipeline
    local start_time=$(date +%s)
    
    build_system
    generate_traffic
    run_capture
    analyze_results
    run_rl_integration
    cleanup_files
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    # Final summary
    print_section "🏁 Execution Complete"
    print_status "Total execution time: ${duration}s"
    print_status "Step1 firewall system test completed successfully!"
    
    if [ "$CLEAN_AFTER" != "true" ]; then
        print_info "Output files preserved in current directory"
    fi
    
    echo ""
    echo -e "${GREEN}✨ Step1 Standalone Run Complete! ✨${NC}"
}

# =============================================================================
# Script Execution
# =============================================================================
main "$@"