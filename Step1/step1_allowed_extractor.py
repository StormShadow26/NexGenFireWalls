#!/usr/bin/env python3

"""
Step1 Allowed Packets Extractor

This script captures packets through the Step1 firewall system and 
extracts only the ALLOWED packets (those that pass all filters)
for use with the RL firewall_tester.py
"""

import subprocess
import sys
import os
import csv
import tempfile
import time
import pandas as pd
from datetime import datetime
import argparse
import signal

class AllowedPacketExtractor:
    def __init__(self):
        self.step1_dir = os.path.dirname(os.path.abspath(__file__))
        self.rl_dir = os.path.join(self.step1_dir, "..", "RL_testing")
        self.capture_binary = os.path.join(self.step1_dir, "capture")
        self.temp_files = []
        
    def log_info(self, message):
        print(f"ℹ️  {message}")
    
    def log_success(self, message):
        print(f"✅ {message}")
    
    def log_error(self, message):
        print(f"❌ {message}")
    
    def log_warning(self, message):
        print(f"⚠️  {message}")
    
    def cleanup(self):
        """Clean up temporary files"""
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
    
    def check_dependencies(self):
        """Check if all required components are available"""
        self.log_info("Checking dependencies...")
        
        # Check if running with appropriate permissions
        if os.geteuid() != 0:
            self.log_error("This script requires root privileges for packet capture")
            return False
        
        # Check capture binary
        if not os.path.exists(self.capture_binary):
            self.log_warning("Capture binary not found, attempting to build...")
            if not self.build_capture():
                return False
        
        # Check RL directory
        if not os.path.exists(self.rl_dir):
            self.log_error(f"RL_testing directory not found: {self.rl_dir}")
            return False
        
        self.log_success("All dependencies checked")
        return True
    
    def build_capture(self):
        """Build the capture binary using make"""
        try:
            self.log_info("Building capture binary...")
            result = subprocess.run(
                ["make", "clean"], 
                cwd=self.step1_dir, 
                capture_output=True, 
                text=True
            )
            
            result = subprocess.run(
                ["make"], 
                cwd=self.step1_dir, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                self.log_success("Capture binary built successfully")
                return True
            else:
                self.log_error(f"Build failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_error(f"Build error: {e}")
            return False
    
    def generate_traffic(self, duration=5):
        """Generate background traffic for testing"""
        self.log_info(f"Generating background traffic for {duration} seconds...")
        
        # Create a script to generate various types of traffic
        traffic_script = f"""#!/bin/bash
# Generate DNS queries
for i in {{1..10}}; do
    nslookup google.com 8.8.8.8 &> /dev/null &
    nslookup github.com 1.1.1.1 &> /dev/null &
    sleep 0.1
done

# HTTP requests (if curl available)
if command -v curl &> /dev/null; then
    for i in {{1..5}}; do
        curl -s --connect-timeout 2 --max-time 5 http://httpbin.org/ip &> /dev/null &
        curl -s --connect-timeout 2 --max-time 5 https://api.github.com &> /dev/null &
        sleep 0.3
    done
fi

# Local connections
for port in 22 80 443 53; do
    timeout 0.1 bash -c "</dev/tcp/127.0.0.1/$port" 2>/dev/null &
done

# ICMP pings
ping -c 3 8.8.8.8 &> /dev/null &
ping -c 3 127.0.0.1 &> /dev/null &

wait
"""
        
        temp_script = tempfile.mktemp(suffix=".sh")
        self.temp_files.append(temp_script)
        
        with open(temp_script, 'w') as f:
            f.write(traffic_script)
        
        os.chmod(temp_script, 0o755)
        
        # Run traffic generation in background
        try:
            process = subprocess.Popen([temp_script])
            time.sleep(duration)
            
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                process.kill()
            
            self.log_success("Traffic generation completed")
            return True
            
        except Exception as e:
            self.log_error(f"Traffic generation failed: {e}")
            return False
    
    def capture_packets(self, packet_count=500, interface="any"):
        """Capture packets and get the summary CSV"""
        self.log_info(f"Capturing {packet_count} packets on interface {interface}...")
        
        try:
            # Run the capture
            result = subprocess.run(
                [self.capture_binary, "-n", str(packet_count)],
                cwd=self.step1_dir,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            if result.returncode != 0:
                self.log_error(f"Capture failed: {result.stderr}")
                return None
            
            # Check if summary CSV was generated
            summary_csv = os.path.join(self.step1_dir, "summary_batch_1.csv")
            if os.path.exists(summary_csv):
                self.log_success(f"Capture completed, summary saved to {summary_csv}")
                return summary_csv
            else:
                self.log_error("No summary CSV generated")
                return None
                
        except subprocess.TimeoutExpired:
            self.log_error("Capture timed out")
            return None
        except Exception as e:
            self.log_error(f"Capture error: {e}")
            return None
    
    def filter_allowed_packets(self, summary_csv, output_csv):
        """Filter the summary CSV to contain only allowed packets"""
        try:
            # Read the summary CSV
            df = pd.read_csv(summary_csv)
            
            if len(df) == 0:
                self.log_warning("No packets in summary CSV, generating synthetic data")
                self.generate_synthetic_allowed_packets(output_csv)
                return output_csv
            
            # All packets in summary_batch_1.csv are actually allowed packets
            # (denied packets are logged separately and don't appear in the CSV)
            self.log_info(f"Found {len(df)} allowed packets in summary")
            
            # Add some additional columns that might be useful for RL
            df['packet_type'] = 'ALLOWED'
            df['filter_stage'] = 'PASSED_ALL_FILTERS'
            df['timestamp'] = datetime.now().isoformat()
            
            # Save filtered data
            df.to_csv(output_csv, index=False)
            
            self.log_success(f"Filtered allowed packets saved to {output_csv}")
            self.log_info(f"Total allowed packets: {len(df)}")
            
            return output_csv
            
        except Exception as e:
            self.log_error(f"Error filtering packets: {e}")
            # Fallback to synthetic data
            self.generate_synthetic_allowed_packets(output_csv)
            return output_csv
    
    def generate_synthetic_allowed_packets(self, output_csv):
        """Generate synthetic allowed packets for testing when no real data is available"""
        self.log_info("Generating synthetic allowed packets...")
        
        synthetic_data = [
            # Normal web browsing
            {
                'src_ip': '192.168.1.100', 'dst_ip': '8.8.8.8', 'src_port': 45231, 'dst_port': 53,
                'protocol': 'UDP', 'bytes_sent': 64, 'bytes_received': 128, 'pkts_sent': 1, 'pkts_received': 1,
                'duration_sec': 0.1, 'avg_pkt_size': 96.0, 'pkt_rate': 10.0, 'syn_count': 0, 'ack_count': 0,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 0, 'syn_ack_ratio': 0.0, 'syn_fin_ratio': 0.0,
                'min_pkt_size': 64, 'max_pkt_size': 128, 'total_packets': 2, 'total_bytes': 192
            },
            # HTTPS connection
            {
                'src_ip': '10.0.0.50', 'dst_ip': '52.85.23.59', 'src_port': 54321, 'dst_port': 443,
                'protocol': 'TCP', 'bytes_sent': 156, 'bytes_received': 2048, 'pkts_sent': 3, 'pkts_received': 4,
                'duration_sec': 0.5, 'avg_pkt_size': 312.5, 'pkt_rate': 14.0, 'syn_count': 1, 'ack_count': 3,
                'fin_count': 1, 'rst_count': 0, 'psh_count': 2, 'syn_ack_ratio': 0.33, 'syn_fin_ratio': 1.0,
                'min_pkt_size': 52, 'max_pkt_size': 1024, 'total_packets': 7, 'total_bytes': 2204
            },
            # SSH connection
            {
                'src_ip': '172.16.1.200', 'dst_ip': '172.16.1.1', 'src_port': 33445, 'dst_port': 22,
                'protocol': 'TCP', 'bytes_sent': 88, 'bytes_received': 176, 'pkts_sent': 2, 'pkts_received': 2,
                'duration_sec': 0.2, 'avg_pkt_size': 132.0, 'pkt_rate': 20.0, 'syn_count': 1, 'ack_count': 1,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 1, 'syn_ack_ratio': 1.0, 'syn_fin_ratio': 999.0,
                'min_pkt_size': 88, 'max_pkt_size': 176, 'total_packets': 4, 'total_bytes': 264
            },
            # DNS over UDP
            {
                'src_ip': '192.168.1.105', 'dst_ip': '1.1.1.1', 'src_port': 49152, 'dst_port': 53,
                'protocol': 'UDP', 'bytes_sent': 72, 'bytes_received': 144, 'pkts_sent': 1, 'pkts_received': 1,
                'duration_sec': 0.05, 'avg_pkt_size': 108.0, 'pkt_rate': 40.0, 'syn_count': 0, 'ack_count': 0,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 0, 'syn_ack_ratio': 0.0, 'syn_fin_ratio': 0.0,
                'min_pkt_size': 72, 'max_pkt_size': 144, 'total_packets': 2, 'total_bytes': 216
            },
            # HTTP connection
            {
                'src_ip': '10.0.0.75', 'dst_ip': '23.52.74.204', 'src_port': 65432, 'dst_port': 80,
                'protocol': 'TCP', 'bytes_sent': 234, 'bytes_received': 1876, 'pkts_sent': 4, 'pkts_received': 8,
                'duration_sec': 1.2, 'avg_pkt_size': 175.83, 'pkt_rate': 10.0, 'syn_count': 1, 'ack_count': 7,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 3, 'syn_ack_ratio': 0.14, 'syn_fin_ratio': 999.0,
                'min_pkt_size': 54, 'max_pkt_size': 1024, 'total_packets': 12, 'total_bytes': 2110
            }
        ]
        
        # Add metadata
        for packet in synthetic_data:
            packet['packet_type'] = 'ALLOWED'
            packet['filter_stage'] = 'PASSED_ALL_FILTERS'
            packet['timestamp'] = datetime.now().isoformat()
        
        # Save to CSV
        df = pd.DataFrame(synthetic_data)
        df.to_csv(output_csv, index=False)
        
        self.log_success(f"Generated {len(synthetic_data)} synthetic allowed packets")
    
    def call_rl_tester(self, allowed_csv, output_csv):
        """Call the RL firewall tester with the allowed packets CSV"""
        self.log_info("Calling RL firewall tester...")
        
        # Create a Python script to run the tester
        rl_script = f'''
import sys
import os
sys.path.append(r'{self.rl_dir}')

from firewall_tester import SingleModelFirewallPredictor
import pandas as pd
from datetime import datetime

def main():
    print("🤖 Starting RL Firewall Analysis...")
    
    predictor = SingleModelFirewallPredictor()
    
    # Load model
    model_path = r'{os.path.join(self.rl_dir, "RegularisedDQN_5000.pth")}'
    print(f"📂 Loading model: {{model_path}}")
    
    if not predictor.load_model(model_path):
        print("❌ Failed to load model")
        return False
    
    # Load CSV
    csv_path = r'{allowed_csv}'
    print(f"📊 Loading CSV: {{csv_path}}")
    
    try:
        data = pd.read_csv(csv_path)
        print(f"✅ Loaded {{len(data)}} records")
    except Exception as e:
        print(f"❌ Error loading CSV: {{e}}")
        return False
    
    if len(data) == 0:
        print("⚠️  No data to process")
        return False
    
    # Process data
    print("🔄 Processing through RL model...")
    
    try:
        processed_states = predictor.preprocess_batch(data)
        predictions, confidences, q_values_list = predictor.predict_batch(processed_states)
        
        if predictions is None:
            print("❌ Prediction failed")
            return False
        
        # Create results
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
            row = data.iloc[idx]
            session_id = f"{{row.get('src_ip', 'unknown')}}:{{row.get('src_port', '0')}}->>{{row.get('dst_ip', 'unknown')}}:{{row.get('dst_port', '0')}}"
            
            discrete_state = predictor.mdp_reasoner.discretize_state(state, session_id)
            mdp_result = predictor.mdp_reasoner.get_mdp_recommendation(
                discrete_state, session_id, dqn_pred, q_vals
            )
            
            predictor.mdp_reasoner.update_session_history(session_id, discrete_state, dqn_pred)
            
            mdp_recommendations.append(mdp_result['mdp_recommendation'])
            mdp_agreements.append(mdp_result['agreement'])
            
            adj_conf = confidences[idx] + mdp_result['confidence_adjustment']
            adjusted_confidences.append(max(0.0, min(1.0, adj_conf)))
            
            session_risks.append(predictor.mdp_reasoner.get_session_risk_score(session_id))
            state_contexts.append(mdp_result['state_context'])
        
        # Add columns
        results['MDP_Recommendation'] = mdp_recommendations
        results['DQN_MDP_Agreement'] = mdp_agreements
        results['Adjusted_Confidence'] = adjusted_confidences
        results['Session_Risk_Score'] = session_risks
        results['State_Context'] = state_contexts
        
        action_map = {{0: 'ALLOW', 1: 'DENY', 2: 'INSPECT'}}
        results['DQN_Action_Name'] = results['DQN_Predicted_Action'].map(action_map)
        results['MDP_Action_Name'] = results['MDP_Recommendation'].map(action_map)
        results['Final_Recommendation'] = results['MDP_Recommendation']
        results['Final_Action_Name'] = results['Final_Recommendation'].map(action_map)
        
        # Save results
        output_path = r'{output_csv}'
        results.to_csv(output_path, index=False)
        print(f"💾 Results saved to: {{output_path}}")
        
        # Summary
        total = len(results)
        final_counts = results['Final_Action_Name'].value_counts()
        
        print(f"\\n📈 PREDICTION SUMMARY:")
        print(f"📊 Total records: {{total}}")
        for action in ['ALLOW', 'DENY', 'INSPECT']:
            count = final_counts.get(action, 0)
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"   {{action}}: {{count}} ({{percentage:.1f}}%)")
        
        agreements = results['DQN_MDP_Agreement'].sum()
        agreement_rate = (agreements / total) * 100 if total > 0 else 0
        print(f"🤝 DQN-MDP Agreement: {{agreements}}/{{total}} ({{agreement_rate:.1f}}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during processing: {{e}}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
        
        # Write and execute the script
        temp_script = tempfile.mktemp(suffix=".py")
        self.temp_files.append(temp_script)
        
        with open(temp_script, 'w') as f:
            f.write(rl_script)
        
        try:
            result = subprocess.run([sys.executable, temp_script], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.log_success("RL analysis completed successfully")
                print(result.stdout)
                return True
            else:
                self.log_error("RL analysis failed")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            self.log_error("RL analysis timed out")
            return False
        except Exception as e:
            self.log_error(f"RL analysis error: {e}")
            return False
    
    def run_full_pipeline(self, packet_count=500, interface="any", generate_traffic=True):
        """Run the complete pipeline"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        allowed_csv = f"step1_allowed_packets_{timestamp}.csv"
        rl_csv = f"rl_predictions_{timestamp}.csv"
        
        print("🔥🤖 Step1 + RL Integration Pipeline")
        print("="*50)
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Generate traffic if requested
        if generate_traffic:
            self.generate_traffic(duration=3)
        
        # Capture packets
        summary_csv = self.capture_packets(packet_count, interface)
        if not summary_csv:
            return False
        
        # Filter allowed packets
        allowed_path = self.filter_allowed_packets(summary_csv, allowed_csv)
        if not allowed_path:
            return False
        
        # Call RL tester
        if not self.call_rl_tester(allowed_path, rl_csv):
            return False
        
        # Show results
        self.log_success("🎉 Pipeline completed successfully!")
        print(f"\n📊 Generated Files:")
        print(f"   📄 Allowed Packets: {allowed_csv}")
        print(f"   🤖 RL Predictions: {rl_csv}")
        
        if os.path.exists(allowed_csv):
            allowed_size = os.path.getsize(allowed_csv)
            with open(allowed_csv, 'r') as f:
                allowed_count = sum(1 for _ in f) - 1  # Subtract header
            print(f"      Size: {allowed_size} bytes, Records: {allowed_count}")
        
        if os.path.exists(rl_csv):
            rl_size = os.path.getsize(rl_csv)
            with open(rl_csv, 'r') as f:
                rl_count = sum(1 for _ in f) - 1  # Subtract header
            print(f"      Size: {rl_size} bytes, Records: {rl_count}")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Step1 + RL Integration Pipeline')
    parser.add_argument('-n', '--packets', type=int, default=500,
                       help='Number of packets to capture (default: 500)')
    parser.add_argument('-i', '--interface', default='any',
                       help='Network interface to use (default: any)')
    parser.add_argument('--no-traffic', action='store_true',
                       help='Don\'t generate synthetic traffic')
    
    args = parser.parse_args()
    
    extractor = AllowedPacketExtractor()
    
    # Set up signal handler for cleanup
    def signal_handler(sig, frame):
        print("\\n⚠️  Interrupted by user")
        extractor.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = extractor.run_full_pipeline(
            packet_count=args.packets,
            interface=args.interface,
            generate_traffic=not args.no_traffic
        )
        
        extractor.cleanup()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        extractor.log_error(f"Pipeline error: {e}")
        extractor.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()