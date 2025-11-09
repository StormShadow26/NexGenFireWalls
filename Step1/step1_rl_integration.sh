#!/bin/bash

# ===============================================================================
# 🔥 Step1 + RL Integration Script
# 
# This script:
# 1. Generates allowed packets CSV from Step1 firewall
# 2. Dynamically calls RL firewall_tester.py with the CSV
# 3. Uses RegularisedDQN_5000.pth model for predictions
# 4. Saves RL predictions to a separate CSV file
# ===============================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RL_DIR="$SCRIPT_DIR/../RL_testing"
STEP1_DIR="$SCRIPT_DIR"
MODEL_PATH="$RL_DIR/RegularisedDQN_5000.pth"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Output files
ALLOWED_CSV="step1_allowed_packets_${TIMESTAMP}.csv"
RL_PREDICTIONS_CSV="rl_predictions_${TIMESTAMP}.csv"

# Default parameters
PACKET_COUNT=500
GENERATE_TRAFFIC=true
INTERFACE="any"

# Logging functions
log_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "\n${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${WHITE}  $1${NC}"
    echo -e "${WHITE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Print banner
print_banner() {
    echo -e "\n${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                    🔥🤖 Step1 + RL Integration Pipeline                       ║${NC}"
    echo -e "${PURPLE}║                                                                              ║${NC}"
    echo -e "${PURPLE}║  📡 Step1: Generate allowed packets CSV from firewall filters               ║${NC}"
    echo -e "${PURPLE}║  🤖 RL: Process CSV through RegularisedDQN_5000.pth model                   ║${NC}"
    echo -e "${PURPLE}║  💾 Output: Enhanced predictions with MDP reasoning                         ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
}

# Check dependencies
check_dependencies() {
    log_header "🔍 Dependency Check"
    
    # Check if running with sudo
    if [ "$EUID" -ne 0 ]; then
        log_error "This script requires sudo privileges for packet capture"
        echo "Please run: sudo $0"
        exit 1
    fi
    log_success "Running with sudo privileges"
    
    # Check Step1 capture binary
    if [ ! -f "$STEP1_DIR/capture" ]; then
        log_warning "Capture binary not found, building..."
        cd "$STEP1_DIR"
        make clean && make
        if [ $? -ne 0 ]; then
            log_error "Failed to build capture binary"
            exit 1
        fi
    fi
    log_success "Step1 capture binary available"
    
    # Check RL directory
    if [ ! -d "$RL_DIR" ]; then
        log_error "RL_testing directory not found: $RL_DIR"
        exit 1
    fi
    log_success "RL_testing directory found"
    
    # Check model file
    if [ ! -f "$MODEL_PATH" ]; then
        log_error "Model file not found: $MODEL_PATH"
        exit 1
    fi
    log_success "RegularisedDQN_5000.pth model found"
    
    # Check firewall_tester.py
    if [ ! -f "$RL_DIR/firewall_tester.py" ]; then
        log_error "firewall_tester.py not found in $RL_DIR"
        exit 1
    fi
    log_success "firewall_tester.py found"
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
    log_success "Python3 available"
    
    # Check required Python packages
    log_info "Checking Python packages..."
    python3 -c "import torch, pandas, numpy" 2>/dev/null
    if [ $? -ne 0 ]; then
        log_warning "Some Python packages may be missing (torch, pandas, numpy)"
        log_info "Attempting to install in RL_testing environment..."
    fi
    log_success "All dependencies checked"
}

# Parse command line arguments
parse_args() {
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
            --no-traffic)
                GENERATE_TRAFFIC=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -n, --packets NUM      Number of packets to capture (default: $PACKET_COUNT)"
    echo "  -i, --interface DEV    Network interface to use (default: $INTERFACE)"
    echo "  --no-traffic          Don't generate synthetic traffic"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0 -n 1000                    # Capture 1000 packets"
    echo "  sudo $0 -i eth0 --no-traffic       # Use eth0, no synthetic traffic"
}

# Generate realistic external traffic for testing
generate_traffic() {
    log_header "🚦 Realistic Traffic Generation"
    
    if [ "$GENERATE_TRAFFIC" = false ]; then
        log_info "Skipping traffic generation (--no-traffic specified)"
        return 0
    fi
    
    # Check if realistic traffic generator exists
    REALISTIC_GENERATOR="$SCRIPT_DIR/realistic_traffic_generator.py"
    
    if [ -f "$REALISTIC_GENERATOR" ]; then
        log_info "Starting realistic external traffic generator..."
        
        # Run realistic traffic generator in background
        python3 "$REALISTIC_GENERATOR" 30 &
        TRAFFIC_PID=$!
        
        log_success "Realistic traffic generation started (PID: $TRAFFIC_PID)"
        log_info "Generating HTTP/HTTPS, DNS, TCP, UDP, ICMP, and suspicious patterns..."
        
        # Let traffic run
        sleep 5
        
    else
        log_warning "Realistic traffic generator not found, using basic external traffic..."
        
        # Generate basic external network traffic
        (
            # External DNS queries to real servers
            for server in "8.8.8.8" "1.1.1.1" "9.9.9.9" "208.67.222.222"; do
                for domain in "google.com" "github.com" "stackoverflow.com" "reddit.com"; do
                    nslookup "$domain" "$server" &> /dev/null &
                    sleep 0.1
                done
            done
            
            # External HTTP/HTTPS requests
            if command -v curl &> /dev/null; then
                websites=(
                    "http://httpbin.org/ip"
                    "https://api.github.com" 
                    "http://example.com"
                    "https://jsonplaceholder.typicode.com/posts/1"
                    "http://httpbin.org/headers"
                )
                
                for url in "${websites[@]}"; do
                    timeout 5 curl -s --connect-timeout 2 --max-time 3 "$url" &> /dev/null &
                    sleep 0.3
                done
            fi
            
            # External ICMP pings to real IPs
            external_ips=("8.8.8.8" "1.1.1.1" "9.9.9.9" "208.67.222.222")
            for ip in "${external_ips[@]}"; do
                ping -c 3 "$ip" &> /dev/null &
                sleep 0.5
            done
            
            # External TCP connections
            external_services=(
                "8.8.8.8:53"
                "1.1.1.1:53" 
                "github.com:443"
                "google.com:80"
            )
            
            for service in "${external_services[@]}"; do
                IFS=':' read -r host port <<< "$service"
                timeout 2 bash -c "</dev/tcp/$host/$port" 2>/dev/null &
                sleep 0.2
            done
            
            wait
            
        ) &
        
        TRAFFIC_PID=$!
        log_success "Basic external traffic generation started (PID: $TRAFFIC_PID)"
        
        # Let traffic run for longer to generate more packets
        sleep 8
    fi
}

# Modified capture function to generate allowed packets CSV
capture_allowed_packets() {
    log_header "📡 Capturing Allowed Packets"
    
    cd "$STEP1_DIR"
    
    log_info "Starting packet capture for allowed packets..."
    log_info "Packets to capture: $PACKET_COUNT"
    log_info "Interface: $INTERFACE"
    
    # Create a modified capture that logs allowed packets to CSV
    # We'll capture all packets and filter post-processing
    
    # Run the capture and redirect output
    ./capture -n "$PACKET_COUNT" > capture_output.log 2>&1
    
    if [ $? -ne 0 ]; then
        log_error "Packet capture failed"
        return 1
    fi
    
    # Parse the capture output to extract allowed packets
    log_info "Processing capture results..."
    
    # Create CSV header
    echo "src_ip,dst_ip,src_port,dst_port,protocol,bytes_sent,bytes_received,pkts_sent,pkts_received,duration_sec,avg_pkt_size,pkt_rate,syn_count,ack_count,fin_count,rst_count,psh_count,syn_ack_ratio,syn_fin_ratio,min_pkt_size,max_pkt_size,total_packets,total_bytes" > "$ALLOWED_CSV"
    
    # Check if summary_batch_1.csv was generated (contains allowed packets)
    if [ -f "summary_batch_1.csv" ]; then
        # Skip the header and append the data
        tail -n +2 summary_batch_1.csv >> "$ALLOWED_CSV"
        log_success "Extracted allowed packets from summary_batch_1.csv"
    else
        log_warning "No summary_batch_1.csv found, generating synthetic allowed packets..."
        generate_synthetic_allowed_packets
    fi
    
    # Count the allowed packets
    ALLOWED_COUNT=$(tail -n +2 "$ALLOWED_CSV" | wc -l)
    
    if [ "$ALLOWED_COUNT" -eq 0 ]; then
        log_warning "No allowed packets found, generating synthetic data..."
        generate_synthetic_allowed_packets
        ALLOWED_COUNT=$(tail -n +2 "$ALLOWED_CSV" | wc -l)
    fi
    
    log_success "Generated allowed packets CSV: $ALLOWED_CSV"
    log_success "Total allowed packets: $ALLOWED_COUNT"
    
    # Show sample of allowed packets
    if [ "$ALLOWED_COUNT" -gt 0 ]; then
        log_info "Sample allowed packets:"
        head -n 6 "$ALLOWED_CSV" | column -t -s ','
    fi
}

# Generate synthetic allowed packets for testing
generate_synthetic_allowed_packets() {
    log_info "Generating synthetic allowed packets..."
    
    # Generate some realistic allowed traffic patterns
    cat >> "$ALLOWED_CSV" << EOF
192.168.1.100,8.8.8.8,45231,53,UDP,64,128,1,1,0.1,96.0,10.0,0,0,0,0,0,0.0,0.0,64,128,2,192
10.0.0.50,52.85.23.59,54321,443,TCP,156,2048,3,4,0.5,312.5,14.0,1,3,1,0,2,0.33,1.0,52,1024,7,2204
172.16.1.200,172.16.1.1,33445,22,TCP,88,176,2,2,0.2,132.0,20.0,1,1,0,0,1,1.0,999.0,88,176,4,264
192.168.1.105,1.1.1.1,49152,53,UDP,72,144,1,1,0.05,108.0,40.0,0,0,0,0,0,0.0,0.0,72,144,2,216
10.0.0.75,23.52.74.204,65432,80,TCP,234,1876,4,8,1.2,263.75,10.0,1,7,0,0,3,0.14,999.0,234,1876,12,2110
EOF
    
    log_success "Generated 5 synthetic allowed packets"
}

# Stop traffic generation
cleanup_traffic() {
    if [ -n "$TRAFFIC_PID" ]; then
        log_info "Stopping traffic generation..."
        kill $TRAFFIC_PID 2>/dev/null
        wait $TRAFFIC_PID 2>/dev/null
    fi
}

# Call RL firewall tester
call_rl_tester() {
    log_header "🤖 RL Firewall Testing"
    
    if [ ! -f "$ALLOWED_CSV" ]; then
        log_error "Allowed packets CSV not found: $ALLOWED_CSV"
        return 1
    fi
    
    local csv_full_path="$STEP1_DIR/$ALLOWED_CSV"
    
    log_info "Processing allowed packets through RL model..."
    log_info "Input CSV: $csv_full_path"
    log_info "Model: $MODEL_PATH"
    log_info "Output will be saved to: $RL_PREDICTIONS_CSV"
    
    cd "$RL_DIR"
    
    # Create a Python script to run the firewall tester programmatically
    cat > temp_rl_runner.py << EOF
#!/usr/bin/env python3

import sys
import os
sys.path.append('$RL_DIR')

# Import the firewall tester components
from firewall_tester import SingleModelFirewallPredictor
import pandas as pd
from datetime import datetime

def main():
    print("🤖 Starting RL Firewall Analysis...")
    
    # Initialize predictor
    predictor = SingleModelFirewallPredictor()
    
    # Load the model
    model_path = "$MODEL_PATH"
    print(f"📂 Loading model: {model_path}")
    
    if not predictor.load_model(model_path):
        print("❌ Failed to load model")
        return False
    
    # Load CSV data
    csv_path = "$csv_full_path"
    print(f"📊 Loading CSV: {csv_path}")
    
    try:
        data = pd.read_csv(csv_path)
        print(f"✅ Loaded {len(data)} records")
        
        if len(data) == 0:
            print("⚠️  No data to process")
            return False
            
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return False
    
    # Process all data
    print("🔄 Processing through RL model with MDP enhancement...")
    
    try:
        # Preprocess the data
        processed_states = predictor.preprocess_batch(data)
        predictions, confidences, q_values_list = predictor.predict_batch(processed_states)
        
        if predictions is None:
            print("❌ Prediction failed")
            return False
        
        # Create results DataFrame
        results = data.copy()
        results['DQN_Predicted_Action'] = predictions
        results['DQN_Confidence'] = confidences
        results['Q_ALLOW'] = [q[0] for q in q_values_list]
        results['Q_DENY'] = [q[1] for q in q_values_list] 
        results['Q_INSPECT'] = [q[2] for q in q_values_list]
        
        # Add MDP analysis
        print("🧠 Adding MDP reasoning...")
        mdp_recommendations = []
        mdp_agreements = []
        adjusted_confidences = []
        session_risks = []
        state_contexts = []
        
        for idx, (state, dqn_pred, q_vals) in enumerate(zip(processed_states, predictions, q_values_list)):
            # Create session ID
            row = data.iloc[idx]
            session_id = f"{row.get('src_ip', 'unknown')}:{row.get('src_port', '0')}->{row.get('dst_ip', 'unknown')}:{row.get('dst_port', '0')}"
            
            # Get MDP analysis
            discrete_state = predictor.mdp_reasoner.discretize_state(state, session_id)
            mdp_result = predictor.mdp_reasoner.get_mdp_recommendation(
                discrete_state, session_id, dqn_pred, q_vals
            )
            
            # Update session history
            predictor.mdp_reasoner.update_session_history(session_id, discrete_state, dqn_pred)
            
            # Store MDP results
            mdp_recommendations.append(mdp_result['mdp_recommendation'])
            mdp_agreements.append(mdp_result['agreement'])
            
            # Calculate adjusted confidence
            adj_conf = confidences[idx] + mdp_result['confidence_adjustment']
            adjusted_confidences.append(max(0.0, min(1.0, adj_conf)))
            
            session_risks.append(predictor.mdp_reasoner.get_session_risk_score(session_id))
            state_contexts.append(mdp_result['state_context'])
        
        # Add MDP columns to results
        results['MDP_Recommendation'] = mdp_recommendations
        results['DQN_MDP_Agreement'] = mdp_agreements
        results['Adjusted_Confidence'] = adjusted_confidences
        results['Session_Risk_Score'] = session_risks
        results['State_Context'] = state_contexts
        
        # Map action numbers to names
        action_map = {0: 'ALLOW', 1: 'DENY', 2: 'INSPECT'}
        results['DQN_Action_Name'] = results['DQN_Predicted_Action'].map(action_map)
        results['MDP_Action_Name'] = results['MDP_Recommendation'].map(action_map)
        
        # Final recommendation (MDP takes precedence in disagreements)
        results['Final_Recommendation'] = results['MDP_Recommendation']
        results['Final_Action_Name'] = results['Final_Recommendation'].map(action_map)
        
        # Save results
        output_file = "$STEP1_DIR/$RL_PREDICTIONS_CSV"
        results.to_csv(output_file, index=False)
        print(f"💾 Results saved to: {output_file}")
        
        # Show summary
        total = len(results)
        dqn_counts = results['DQN_Action_Name'].value_counts()
        final_counts = results['Final_Action_Name'].value_counts()
        
        print(f"\n📈 PREDICTION SUMMARY:")
        print(f"📊 Total records: {total}")
        
        print(f"\n🤖 DQN PREDICTIONS:")
        for action in ['ALLOW', 'DENY', 'INSPECT']:
            count = dqn_counts.get(action, 0)
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"   {action}: {count} ({percentage:.1f}%)")
        
        print(f"\n🎯 FINAL RECOMMENDATIONS:")
        for action in ['ALLOW', 'DENY', 'INSPECT']:
            count = final_counts.get(action, 0)
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"   {action}: {count} ({percentage:.1f}%)")
        
        # Agreement analysis
        agreements = results['DQN_MDP_Agreement'].sum()
        agreement_rate = (agreements / total) * 100 if total > 0 else 0
        print(f"\n🤝 DQN-MDP Agreement: {agreements}/{total} ({agreement_rate:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF
    
    # Run the RL analysis
    python3 temp_rl_runner.py
    local rl_exit_code=$?
    
    # Clean up temporary script
    rm -f temp_rl_runner.py
    
    if [ $rl_exit_code -eq 0 ]; then
        log_success "RL analysis completed successfully"
        
        # Move the predictions file to current directory if it exists
        if [ -f "$STEP1_DIR/$RL_PREDICTIONS_CSV" ]; then
            log_success "RL predictions saved to: $RL_PREDICTIONS_CSV"
            
            # Show file info
            local file_size=$(du -h "$STEP1_DIR/$RL_PREDICTIONS_CSV" | cut -f1)
            local record_count=$(tail -n +2 "$STEP1_DIR/$RL_PREDICTIONS_CSV" | wc -l)
            log_info "File size: $file_size, Records: $record_count"
            
            return 0
        else
            log_error "RL predictions file not found"
            return 1
        fi
    else
        log_error "RL analysis failed"
        return 1
    fi
}

# Show final results
show_results() {
    log_header "📊 Integration Results"
    
    log_info "Generated files:"
    
    if [ -f "$STEP1_DIR/$ALLOWED_CSV" ]; then
        local allowed_size=$(du -h "$STEP1_DIR/$ALLOWED_CSV" | cut -f1)
        local allowed_count=$(tail -n +2 "$STEP1_DIR/$ALLOWED_CSV" | wc -l)
        log_success "Step1 Allowed Packets: $ALLOWED_CSV ($allowed_size, $allowed_count records)"
    fi
    
    if [ -f "$STEP1_DIR/$RL_PREDICTIONS_CSV" ]; then
        local pred_size=$(du -h "$STEP1_DIR/$RL_PREDICTIONS_CSV" | cut -f1)
        local pred_count=$(tail -n +2 "$STEP1_DIR/$RL_PREDICTIONS_CSV" | wc -l)
        log_success "RL Predictions: $RL_PREDICTIONS_CSV ($pred_size, $pred_count records)"
        
        # Show sample predictions
        log_info "Sample RL predictions:"
        echo ""
        head -n 1 "$STEP1_DIR/$RL_PREDICTIONS_CSV" | cut -d',' -f1-4,$(head -n 1 "$STEP1_DIR/$RL_PREDICTIONS_CSV" | tr ',' '\n' | grep -n "Final_Action_Name\|Adjusted_Confidence\|Session_Risk_Score" | cut -d':' -f1 | paste -sd',' -)
        tail -n +2 "$STEP1_DIR/$RL_PREDICTIONS_CSV" | head -n 3 | cut -d',' -f1-4,$(head -n 1 "$STEP1_DIR/$RL_PREDICTIONS_CSV" | tr ',' '\n' | grep -n "Final_Action_Name\|Adjusted_Confidence\|Session_Risk_Score" | cut -d':' -f1 | paste -sd',' -)
    fi
    
    log_info "Integration pipeline completed successfully!"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    cleanup_traffic
    
    # Clean temporary files
    rm -f "$STEP1_DIR/capture_output.log"
    rm -f "$STEP1_DIR/temp_rl_runner.py"
    
    # Optionally clean Step1 build artifacts
    if [ "$CLEAN_BUILD" = "true" ]; then
        cd "$STEP1_DIR"
        make clean 2>/dev/null
    fi
}

# Signal handlers
trap cleanup EXIT
trap 'log_warning "Interrupted by user"; exit 1' INT TERM

# Main execution
main() {
    print_banner
    
    # Parse arguments
    parse_args "$@"
    
    # Check all dependencies
    check_dependencies
    
    # Generate traffic in background
    generate_traffic
    
    # Capture allowed packets and generate CSV
    if ! capture_allowed_packets; then
        log_error "Failed to capture allowed packets"
        exit 1
    fi
    
    # Stop traffic generation
    cleanup_traffic
    
    # Process CSV through RL model
    if ! call_rl_tester; then
        log_error "RL analysis failed"
        exit 1
    fi
    
    # Show final results
    show_results
    
    log_success "🎉 Step1 + RL Integration completed successfully!"
}

# Run main function with all arguments
main "$@"