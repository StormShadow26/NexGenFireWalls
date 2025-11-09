#!/bin/bash

# ===============================================================================
# 🔥 Step1 + RL Integration Suite
# 
# This master script provides access to all Step1 + RL integration options:
# 1. Full integration with real PyTorch model (if available)
# 2. Simplified integration with mock predictions
# 3. Standalone Step1 testing
# 4. Direct RL model testing
# ===============================================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_banner() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                    🔥🤖 Step1 + RL Integration Suite                          ║${NC}"
    echo -e "${PURPLE}║                                                                              ║${NC}"
    echo -e "${PURPLE}║  Complete firewall testing and RL integration tools                         ║${NC}"
    echo -e "${PURPLE}║                                                                              ║${NC}"
    echo -e "${PURPLE}║  📡 Step1: Packet capture with denylist, rate limiting, malformed detection ║${NC}"
    echo -e "${PURPLE}║  🤖 RL: Deep Q-Network with MDP reasoning (RegularisedDQN_5000.pth)        ║${NC}"
    echo -e "${PURPLE}║  📊 Output: Enhanced CSV with predictions and confidence scores             ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
}

show_menu() {
    echo -e "\n${WHITE}Choose an integration option:${NC}\n"
    
    echo -e "${GREEN}1. 🔥🤖 Full Integration Pipeline${NC}"
    echo -e "   ${CYAN}   • Generate allowed packets CSV from Step1 firewall${NC}"
    echo -e "   ${CYAN}   • Process through RegularisedDQN_5000.pth model${NC}"
    echo -e "   ${CYAN}   • Enhanced MDP reasoning and confidence adjustment${NC}"
    echo -e "   ${CYAN}   • Requires: PyTorch, pandas, numpy${NC}"
    
    echo -e "\n${YELLOW}2. 🔥📊 Simplified Integration (Mock RL)${NC}"
    echo -e "   ${CYAN}   • Generate allowed packets CSV from Step1 firewall${NC}"
    echo -e "   ${CYAN}   • Create realistic mock RL predictions${NC}" 
    echo -e "   ${CYAN}   • Rule-based decisions with confidence scores${NC}"
    echo -e "   ${CYAN}   • No PyTorch required - works everywhere${NC}"
    
    echo -e "\n${BLUE}3. 🌐🔥 Enhanced Integration (External Traffic Focus)${NC}"
    echo -e "   ${CYAN}   • Optimized for external network traffic capture${NC}"
    echo -e "   ${CYAN}   • Advanced traffic generation with real external connections${NC}"
    echo -e "   ${CYAN}   • Traffic type classification and analysis${NC}"
    echo -e "   ${CYAN}   • Enhanced mock RL predictions with traffic awareness${NC}"
    
    echo -e "\n${BLUE}4. 📡 Step1 Standalone Testing${NC}"
    echo -e "   ${CYAN}   • Interactive firewall component testing${NC}"
    echo -e "   ${CYAN}   • Traffic generation and packet capture${NC}"
    echo -e "   ${CYAN}   • Filtering analysis (denylist, rate limit, malformed)${NC}"
    echo -e "   ${CYAN}   • CSV output for manual analysis${NC}"
    
    echo -e "\n${PURPLE}5. 🤖 RL Model Testing Only${NC}"
    echo -e "   ${CYAN}   • Test existing CSV files with RL model${NC}"
    echo -e "   ${CYAN}   • Interactive single-row analysis${NC}"
    echo -e "   ${CYAN}   • Batch processing with MDP enhancement${NC}"
    echo -e "   ${CYAN}   • Requires: PyTorch and model files${NC}"
    
    echo -e "\n${WHITE}6. 📊 View Recent Results${NC}"
    echo -e "   ${CYAN}   • Show recently generated CSV files${NC}"
    echo -e "   ${CYAN}   • Display file statistics and samples${NC}"
    
    echo -e "\n${WHITE}7. 🧹 Clean Temporary Files${NC}"
    echo -e "   ${CYAN}   • Remove generated CSV files and logs${NC}"
    
    echo -e "\n${RED}0. Exit${NC}"
    
    echo -e "\n${WHITE}Enter your choice [0-7]:${NC} "
}

run_full_integration() {
    echo -e "\n${GREEN}🔥🤖 Running Full Integration Pipeline...${NC}"
    
    # Check if PyTorch is available
    python3 -c "import torch" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ PyTorch not available. Use option 2 for simplified integration.${NC}"
        return 1
    fi
    
    # Ask for parameters
    echo -e "${CYAN}Enter number of packets to capture (default: 100):${NC} "
    read packet_count
    packet_count=${packet_count:-100}
    
    echo -e "${CYAN}Generate synthetic traffic? (Y/n):${NC} "
    read generate_traffic
    if [[ $generate_traffic =~ ^[Nn] ]]; then
        traffic_flag="--no-traffic"
    else
        traffic_flag=""
    fi
    
    # Run full integration
    sudo "$SCRIPT_DIR/step1_rl_integration.sh" -n "$packet_count" $traffic_flag
}

run_simplified_integration() {
    echo -e "\n${YELLOW}🔥📊 Running Simplified Integration...${NC}"
    
    # Ask for parameters
    echo -e "${CYAN}Enter number of packets to capture (default: 50):${NC} "
    read packet_count
    packet_count=${packet_count:-50}
    
    echo -e "${CYAN}Generate synthetic traffic? (Y/n):${NC} "
    read generate_traffic
    if [[ $generate_traffic =~ ^[Nn] ]]; then
        traffic_flag="--no-traffic"
    else
        traffic_flag=""
    fi
    
    # Run simplified integration
    sudo python3 "$SCRIPT_DIR/step1_rl_simple.py" -n "$packet_count" $traffic_flag
}

run_step1_standalone() {
    echo -e "\n${BLUE}📡 Running Step1 Standalone Testing...${NC}"
    
    # Run the standalone Step1 script
    sudo "$SCRIPT_DIR/run_step1_standalone.sh" --interactive
}

run_enhanced_integration() {
    echo -e "\n${BLUE}🌐🔥 Running Enhanced Integration (External Traffic Focus)...${NC}"
    
    # Check if enhanced script exists
    if [ ! -f "$SCRIPT_DIR/enhanced_rl_integration.py" ]; then
        echo -e "${RED}❌ Enhanced integration script not found${NC}"
        return 1
    fi
    
    # Ask for parameters
    echo -e "${CYAN}Enter number of packets to capture (default: 200):${NC} "
    read packet_count
    packet_count=${packet_count:-200}
    
    echo -e "${CYAN}Enter traffic generation duration in seconds (default: 20):${NC} "
    read duration
    duration=${duration:-20}
    
    echo -e "\n${GREEN}🚀 Starting enhanced integration with ${packet_count} packets over ${duration} seconds...${NC}"
    
    # Run enhanced integration
    cd "$SCRIPT_DIR"
    sudo python3 enhanced_rl_integration.py -n "$packet_count" -d "$duration"
    
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ Enhanced integration completed successfully!${NC}"
    else
        echo -e "\n${RED}❌ Enhanced integration failed${NC}"
    fi
}

run_rl_testing() {
    echo -e "\n${PURPLE}🤖 Running RL Model Testing...${NC}"
    
    RL_DIR="$SCRIPT_DIR/../RL_testing"
    
    if [ ! -d "$RL_DIR" ]; then
        echo -e "${RED}❌ RL_testing directory not found${NC}"
        return 1
    fi
    
    # Check for CSV files
    csv_files=($(find "$SCRIPT_DIR" -name "*.csv" -type f 2>/dev/null))
    if [ ${#csv_files[@]} -eq 0 ]; then
        echo -e "${RED}❌ No CSV files found. Run option 1 or 2 first.${NC}"
        return 1
    fi
    
    echo -e "${CYAN}Available CSV files:${NC}"
    for i in "${!csv_files[@]}"; do
        echo -e "  $((i+1)). $(basename "${csv_files[i]}")"
    done
    
    echo -e "${CYAN}Choose a CSV file to test (1-${#csv_files[@]}):${NC} "
    read csv_choice
    
    if [[ $csv_choice -ge 1 && $csv_choice -le ${#csv_files[@]} ]]; then
        selected_csv="${csv_files[$((csv_choice-1))]}"
        echo -e "${GREEN}Testing with: $(basename "$selected_csv")${NC}"
        
        cd "$RL_DIR"
        python3 firewall_tester.py
    else
        echo -e "${RED}❌ Invalid choice${NC}"
    fi
}

view_recent_results() {
    echo -e "\n${WHITE}📊 Recent Results${NC}"
    echo -e "=================="
    
    # Find recent CSV files
    recent_files=($(find "$SCRIPT_DIR" -name "*.csv" -type f -mtime -1 2>/dev/null | sort -t _ -k 3))
    
    if [ ${#recent_files[@]} -eq 0 ]; then
        echo -e "${YELLOW}No recent CSV files found${NC}"
        return
    fi
    
    for file in "${recent_files[@]}"; do
        filename=$(basename "$file")
        size=$(du -h "$file" | cut -f1)
        record_count=$(tail -n +2 "$file" 2>/dev/null | wc -l)
        modified=$(stat -c %y "$file" | cut -d'.' -f1)
        
        echo -e "\n${GREEN}📄 $filename${NC}"
        echo -e "   Size: $size, Records: $record_count"
        echo -e "   Modified: $modified"
        
        # Show sample data for prediction files
        if [[ $filename == *"rl_predictions"* ]]; then
            echo -e "   ${CYAN}Sample predictions:${NC}"
            head -n 1 "$file" | cut -d',' -f1-4,25-27 2>/dev/null
            tail -n +2 "$file" | head -n 2 | cut -d',' -f1-4,25-27 2>/dev/null
        elif [[ $filename == *"allowed_packets"* ]]; then
            echo -e "   ${CYAN}Sample allowed packets:${NC}"
            head -n 3 "$file" | column -t -s ',' 2>/dev/null | head -n 3
        fi
    done
}

clean_temp_files() {
    echo -e "\n${WHITE}🧹 Cleaning Temporary Files${NC}"
    
    # List files to be cleaned
    temp_files=($(find "$SCRIPT_DIR" -name "*_202*" -type f 2>/dev/null))
    temp_files+=($(find "$SCRIPT_DIR" -name "summary_batch_*.csv" -type f 2>/dev/null))
    temp_files+=($(find "$SCRIPT_DIR" -name "capture_output.log" -type f 2>/dev/null))
    
    if [ ${#temp_files[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ No temporary files to clean${NC}"
        return
    fi
    
    echo -e "${CYAN}Files to be removed:${NC}"
    for file in "${temp_files[@]}"; do
        echo -e "  - $(basename "$file")"
    done
    
    echo -e "\n${YELLOW}Are you sure? (y/N):${NC} "
    read confirm
    
    if [[ $confirm =~ ^[Yy] ]]; then
        for file in "${temp_files[@]}"; do
            rm -f "$file"
        done
        echo -e "${GREEN}✅ Cleaned ${#temp_files[@]} files${NC}"
    else
        echo -e "${CYAN}Cancelled${NC}"
    fi
}

check_permissions() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  Running as root. Some options will run with elevated privileges.${NC}"
        return 0
    fi
    
    # Check if we can run with sudo
    if sudo -n true 2>/dev/null; then
        echo -e "${GREEN}✅ Sudo access available${NC}"
        return 0
    fi
    
    echo -e "${RED}⚠️  Some options require root privileges for packet capture.${NC}"
    echo -e "${CYAN}   You may be prompted for your password.${NC}"
    return 0
}

main() {
    print_banner
    check_permissions
    
    while true; do
        show_menu
        read choice
        
        case $choice in
            1)
                run_full_integration
                ;;
            2)
                run_simplified_integration
                ;;
            3)
                run_enhanced_integration
                ;;
            4)
                run_step1_standalone
                ;;
            5)
                run_rl_testing
                ;;
            6)
                view_recent_results
                ;;
            7)
                clean_temp_files
                ;;
            0)
                echo -e "${GREEN}👋 Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Invalid choice. Please try again.${NC}"
                ;;
        esac
        
        echo -e "\n${CYAN}Press Enter to continue...${NC}"
        read
    done
}

# Run main function
main "$@"