#!/usr/bin/env python3

"""
Step1 + RL Integration (Simplified Version)

This script:
1. Captures allowed packets from Step1 firewall
2. Creates mock RL predictions (since PyTorch might not be available)
3. Generates output CSV file with RL-style predictions

This demonstrates the integration pipeline without requiring PyTorch installation.
"""

import subprocess
import sys
import os
import csv
import tempfile
import time
import random
from datetime import datetime
import argparse
import signal

class SimplifiedRLIntegration:
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
    
    def print_header(self, title):
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}")
    
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
    
    def generate_traffic(self, duration=3):
        """Generate realistic external network traffic"""
        self.log_info(f"Generating realistic external traffic for {duration} seconds...")
        
        # Use the realistic traffic generator
        realistic_generator = os.path.join(self.step1_dir, "realistic_traffic_generator.py")
        
        if os.path.exists(realistic_generator):
            try:
                # Run realistic traffic generator in background
                self.log_info("Starting realistic traffic generator...")
                process = subprocess.Popen(
                    [sys.executable, realistic_generator, str(duration)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Let it run for the specified duration
                time.sleep(duration + 2)  # Extra time for cleanup
                
                # Terminate if still running
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except:
                    process.kill()
                
                self.log_success("Realistic traffic generation completed")
                return True
                
            except Exception as e:
                self.log_warning(f"Realistic traffic generator failed: {e}")
                # Fallback to basic traffic
                return self.generate_basic_traffic(duration)
        else:
            self.log_warning("Realistic traffic generator not found, using basic traffic")
            return self.generate_basic_traffic(duration)
    
    def generate_basic_traffic(self, duration=3):
        """Fallback basic traffic generation"""
        self.log_info("Generating basic external traffic...")
        
        # Create basic external traffic
        traffic_commands = [
            # External DNS queries
            "nslookup google.com 8.8.8.8 > /dev/null 2>&1 &",
            "nslookup github.com 1.1.1.1 > /dev/null 2>&1 &",
            "nslookup stackoverflow.com 9.9.9.9 > /dev/null 2>&1 &",
            
            # External pings
            "ping -c 3 8.8.8.8 > /dev/null 2>&1 &",
            "ping -c 2 1.1.1.1 > /dev/null 2>&1 &",
            "ping -c 2 9.9.9.9 > /dev/null 2>&1 &",
            
            # External HTTP connections (if curl available)
            "timeout 5 curl -s --connect-timeout 2 http://httpbin.org/ip > /dev/null 2>&1 &",
            "timeout 5 curl -s --connect-timeout 2 https://api.github.com > /dev/null 2>&1 &",
            "timeout 5 curl -s --connect-timeout 2 http://example.com > /dev/null 2>&1 &",
            
            # External TCP connections
            "timeout 2 bash -c '</dev/tcp/8.8.8.8/53' 2>/dev/null &",
            "timeout 2 bash -c '</dev/tcp/1.1.1.1/53' 2>/dev/null &",
        ]
        
        # Execute traffic commands with proper spacing
        for cmd in traffic_commands:
            try:
                subprocess.run(cmd, shell=True, timeout=1)
            except:
                pass
            time.sleep(0.2)  # Spacing between commands
        
        # Wait for traffic to be generated
        time.sleep(duration)
        self.log_success("Basic traffic generation completed")
        return True
    
    def capture_packets(self, packet_count=100):
        """Capture packets and get the summary CSV"""
        self.log_info(f"Capturing {packet_count} packets...")
        
        try:
            # Run the capture
            result = subprocess.run(
                [self.capture_binary, "-n", str(packet_count)],
                cwd=self.step1_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                self.log_error(f"Capture failed: {result.stderr}")
                return None
            
            # Check if summary CSV was generated
            summary_csv = os.path.join(self.step1_dir, "summary_batch_1.csv")
            if os.path.exists(summary_csv):
                self.log_success(f"Capture completed")
                return summary_csv
            else:
                self.log_warning("No summary CSV generated, will create synthetic data")
                return None
                
        except subprocess.TimeoutExpired:
            self.log_error("Capture timed out")
            return None
        except Exception as e:
            self.log_error(f"Capture error: {e}")
            return None
    
    def create_allowed_packets_csv(self, summary_csv, output_csv):
        """Create allowed packets CSV from summary or generate synthetic data"""
        try:
            if summary_csv and os.path.exists(summary_csv):
                # Read existing summary
                with open(summary_csv, 'r') as infile:
                    content = infile.read()
                
                # Copy to new file (all packets in summary are allowed)
                with open(output_csv, 'w') as outfile:
                    outfile.write(content)
                
                # Count packets
                with open(output_csv, 'r') as f:
                    packet_count = sum(1 for _ in f) - 1  # Subtract header
                
                self.log_success(f"Extracted {packet_count} allowed packets from summary")
                
            else:
                # Generate synthetic allowed packets
                self.log_info("Generating synthetic allowed packets...")
                self.generate_synthetic_allowed_packets(output_csv)
            
            return True
            
        except Exception as e:
            self.log_error(f"Error creating allowed packets CSV: {e}")
            return False
    
    def generate_synthetic_allowed_packets(self, output_csv):
        """Generate synthetic allowed packets data"""
        synthetic_data = [
            {
                'src_ip': '192.168.1.100', 'dst_ip': '8.8.8.8', 'src_port': 45231, 'dst_port': 53,
                'protocol': 'UDP', 'bytes_sent': 64, 'bytes_received': 128, 'pkts_sent': 1, 'pkts_received': 1,
                'duration_sec': 0.1, 'avg_pkt_size': 96.0, 'pkt_rate': 10.0, 'syn_count': 0, 'ack_count': 0,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 0, 'syn_ack_ratio': 0.0, 'syn_fin_ratio': 0.0,
                'min_pkt_size': 64, 'max_pkt_size': 128, 'total_packets': 2, 'total_bytes': 192
            },
            {
                'src_ip': '10.0.0.50', 'dst_ip': '52.85.23.59', 'src_port': 54321, 'dst_port': 443,
                'protocol': 'TCP', 'bytes_sent': 156, 'bytes_received': 2048, 'pkts_sent': 3, 'pkts_received': 4,
                'duration_sec': 0.5, 'avg_pkt_size': 312.5, 'pkt_rate': 14.0, 'syn_count': 1, 'ack_count': 3,
                'fin_count': 1, 'rst_count': 0, 'psh_count': 2, 'syn_ack_ratio': 0.33, 'syn_fin_ratio': 1.0,
                'min_pkt_size': 52, 'max_pkt_size': 1024, 'total_packets': 7, 'total_bytes': 2204
            },
            {
                'src_ip': '172.16.1.200', 'dst_ip': '172.16.1.1', 'src_port': 33445, 'dst_port': 22,
                'protocol': 'TCP', 'bytes_sent': 88, 'bytes_received': 176, 'pkts_sent': 2, 'pkts_received': 2,
                'duration_sec': 0.2, 'avg_pkt_size': 132.0, 'pkt_rate': 20.0, 'syn_count': 1, 'ack_count': 1,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 1, 'syn_ack_ratio': 1.0, 'syn_fin_ratio': 999.0,
                'min_pkt_size': 88, 'max_pkt_size': 176, 'total_packets': 4, 'total_bytes': 264
            },
            {
                'src_ip': '192.168.1.105', 'dst_ip': '1.1.1.1', 'src_port': 49152, 'dst_port': 53,
                'protocol': 'UDP', 'bytes_sent': 72, 'bytes_received': 144, 'pkts_sent': 1, 'pkts_received': 1,
                'duration_sec': 0.05, 'avg_pkt_size': 108.0, 'pkt_rate': 40.0, 'syn_count': 0, 'ack_count': 0,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 0, 'syn_ack_ratio': 0.0, 'syn_fin_ratio': 0.0,
                'min_pkt_size': 72, 'max_pkt_size': 144, 'total_packets': 2, 'total_bytes': 216
            },
            {
                'src_ip': '10.0.0.75', 'dst_ip': '23.52.74.204', 'src_port': 65432, 'dst_port': 80,
                'protocol': 'TCP', 'bytes_sent': 234, 'bytes_received': 1876, 'pkts_sent': 4, 'pkts_received': 8,
                'duration_sec': 1.2, 'avg_pkt_size': 175.83, 'pkt_rate': 10.0, 'syn_count': 1, 'ack_count': 7,
                'fin_count': 0, 'rst_count': 0, 'psh_count': 3, 'syn_ack_ratio': 0.14, 'syn_fin_ratio': 999.0,
                'min_pkt_size': 54, 'max_pkt_size': 1024, 'total_packets': 12, 'total_bytes': 2110
            }
        ]
        
        # Write CSV
        with open(output_csv, 'w', newline='') as csvfile:
            fieldnames = list(synthetic_data[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(synthetic_data)
        
        self.log_success(f"Generated {len(synthetic_data)} synthetic allowed packets")
    
    def create_mock_rl_predictions(self, allowed_csv, output_csv):
        """Create mock RL predictions based on allowed packets"""
        self.log_info("Creating mock RL predictions (PyTorch not available)...")
        
        try:
            # Read allowed packets
            with open(allowed_csv, 'r') as f:
                reader = csv.DictReader(f)
                allowed_packets = list(reader)
            
            if not allowed_packets:
                self.log_error("No allowed packets to process")
                return False
            
            # Generate mock predictions for each packet
            predictions = []
            
            for packet in allowed_packets:
                # Create realistic mock predictions based on packet characteristics
                protocol = packet.get('protocol', 'TCP')
                dst_port = int(packet.get('dst_port', 80))
                bytes_sent = float(packet.get('bytes_sent', 100))
                
                # Simple rule-based mock predictions
                if protocol == 'UDP' and dst_port == 53:  # DNS
                    action = 0  # ALLOW
                    confidence = 0.95
                elif protocol == 'TCP' and dst_port in [80, 443]:  # HTTP/HTTPS
                    action = 0  # ALLOW
                    confidence = 0.88
                elif protocol == 'TCP' and dst_port == 22:  # SSH
                    action = 2  # INSPECT
                    confidence = 0.72
                elif bytes_sent > 10000:  # Large transfers
                    action = 2  # INSPECT  
                    confidence = 0.65
                else:
                    action = 0  # ALLOW
                    confidence = 0.80
                
                # Add some randomness
                confidence += random.uniform(-0.1, 0.1)
                confidence = max(0.1, min(0.99, confidence))
                
                # Generate Q-values
                q_allow = confidence if action == 0 else confidence * 0.3
                q_deny = confidence if action == 1 else confidence * 0.2  
                q_inspect = confidence if action == 2 else confidence * 0.4
                
                # Add random noise to Q-values
                q_allow += random.uniform(-0.2, 0.2)
                q_deny += random.uniform(-0.2, 0.2)
                q_inspect += random.uniform(-0.2, 0.2)
                
                # Mock MDP data
                mdp_recommendation = action
                agreement = random.choice([True, True, True, False])  # 75% agreement
                adjusted_confidence = confidence + random.uniform(-0.05, 0.05)
                session_risk = random.uniform(0.1, 0.8)
                
                action_names = {0: 'ALLOW', 1: 'DENY', 2: 'INSPECT'}
                
                # Create prediction record
                pred = packet.copy()
                pred.update({
                    'DQN_Predicted_Action': action,
                    'DQN_Confidence': f"{confidence:.3f}",
                    'Q_ALLOW': f"{q_allow:.3f}",
                    'Q_DENY': f"{q_deny:.3f}",
                    'Q_INSPECT': f"{q_inspect:.3f}",
                    'MDP_Recommendation': mdp_recommendation,
                    'DQN_MDP_Agreement': agreement,
                    'Adjusted_Confidence': f"{adjusted_confidence:.3f}",
                    'Session_Risk_Score': f"{session_risk:.3f}",
                    'State_Context': f"normal-pattern low-volume connection",
                    'DQN_Action_Name': action_names[action],
                    'MDP_Action_Name': action_names[mdp_recommendation],
                    'Final_Recommendation': mdp_recommendation,
                    'Final_Action_Name': action_names[mdp_recommendation],
                    'Model_Used': 'RegularisedDQN_5000 (Mock)',
                    'Prediction_Timestamp': datetime.now().isoformat()
                })
                
                predictions.append(pred)
            
            # Write predictions CSV
            if predictions:
                with open(output_csv, 'w', newline='') as csvfile:
                    fieldnames = list(predictions[0].keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(predictions)
                
                self.log_success(f"Generated RL predictions for {len(predictions)} packets")
                
                # Show summary
                allow_count = sum(1 for p in predictions if p['Final_Action_Name'] == 'ALLOW')
                deny_count = sum(1 for p in predictions if p['Final_Action_Name'] == 'DENY')  
                inspect_count = sum(1 for p in predictions if p['Final_Action_Name'] == 'INSPECT')
                
                print(f"\n📈 PREDICTION SUMMARY:")
                print(f"   🟢 ALLOW: {allow_count} packets")
                print(f"   🔴 DENY: {deny_count} packets")  
                print(f"   🔍 INSPECT: {inspect_count} packets")
                
                avg_confidence = sum(float(p['Adjusted_Confidence']) for p in predictions) / len(predictions)
                print(f"   💪 Average Confidence: {avg_confidence:.3f}")
                
                return True
            else:
                self.log_error("No predictions generated")
                return False
                
        except Exception as e:
            self.log_error(f"Error creating mock predictions: {e}")
            return False
    
    def run_pipeline(self, packet_count=100, generate_traffic=True):
        """Run the complete integration pipeline"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        allowed_csv = f"step1_allowed_packets_{timestamp}.csv"
        rl_csv = f"rl_predictions_{timestamp}.csv"
        
        self.print_header("🔥🤖 Step1 + RL Integration Pipeline (Simplified)")
        print("This version creates mock RL predictions when PyTorch is not available")
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Generate traffic if requested
        if generate_traffic:
            self.print_header("🚦 Traffic Generation")
            self.generate_traffic()
        
        # Capture packets
        self.print_header("📡 Packet Capture")
        summary_csv = self.capture_packets(packet_count)
        
        # Create allowed packets CSV
        self.print_header("📄 Processing Allowed Packets")
        if not self.create_allowed_packets_csv(summary_csv, allowed_csv):
            return False
        
        # Create mock RL predictions
        self.print_header("🤖 Mock RL Analysis")
        if not self.create_mock_rl_predictions(allowed_csv, rl_csv):
            return False
        
        # Show final results
        self.print_header("📊 Results")
        self.log_success("🎉 Integration pipeline completed successfully!")
        
        print(f"\n📁 Generated Files:")
        
        if os.path.exists(allowed_csv):
            size = os.path.getsize(allowed_csv)
            with open(allowed_csv, 'r') as f:
                count = sum(1 for _ in f) - 1
            print(f"   📄 Allowed Packets: {allowed_csv}")
            print(f"      Size: {size} bytes, Records: {count}")
            
        if os.path.exists(rl_csv):
            size = os.path.getsize(rl_csv)
            with open(rl_csv, 'r') as f:
                count = sum(1 for _ in f) - 1
            print(f"   🤖 RL Predictions: {rl_csv}")
            print(f"      Size: {size} bytes, Records: {count}")
            
        print(f"\n💡 Note: Mock predictions were used since PyTorch is not available.")
        print(f"    Install PyTorch to use the real RegularisedDQN_5000.pth model.")
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Step1 + RL Integration (Simplified)')
    parser.add_argument('-n', '--packets', type=int, default=100,
                       help='Number of packets to capture (default: 100)')
    parser.add_argument('--no-traffic', action='store_true',
                       help='Don\'t generate synthetic traffic')
    
    args = parser.parse_args()
    
    integration = SimplifiedRLIntegration()
    
    # Set up signal handler
    def signal_handler(sig, frame):
        print("\n⚠️  Interrupted by user")
        integration.cleanup()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = integration.run_pipeline(
            packet_count=args.packets,
            generate_traffic=not args.no_traffic
        )
        
        integration.cleanup()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        integration.log_error(f"Pipeline error: {e}")
        integration.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()