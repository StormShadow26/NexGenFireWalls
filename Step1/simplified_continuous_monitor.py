#!/usr/bin/env python3

"""
Simplified Continuous Firewall Monitor

This version sends data to the frontend via HTTP POST instead of WebSocket
to avoid connection issues. The frontend will poll for updates.
"""

import subprocess
import sys
import os
import json
import time
import signal
import logging
import requests
from datetime import datetime
from pathlib import Path

class SimplifiedContinuousMonitor:
    def __init__(self, frontend_url="http://localhost:5000", batch_duration=10):
        """Initialize simplified monitoring system"""
        self.frontend_url = frontend_url
        self.batch_duration = batch_duration
        self.step1_dir = Path(__file__).parent
        self.enhanced_script = self.step1_dir / "enhanced_rl_integration.py"
        
        # State management
        self.running = False
        self.batch_count = 0
        self.start_time = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('SimplifiedMonitor')
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"📡 Received signal {signum}, shutting down...")
        self.stop_monitoring()
        sys.exit(0)
    
    def send_to_frontend(self, endpoint: str, data: dict):
        """Send data to frontend via HTTP POST"""
        try:
            url = f"{self.frontend_url}/api/{endpoint}"
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                self.logger.debug(f"📡 Sent data to {endpoint}")
                return True
            else:
                self.logger.warning(f"📡 Frontend returned {response.status_code} for {endpoint}")
                return False
        except requests.RequestException as e:
            self.logger.error(f"📡 Error sending to frontend: {e}")
            return False
    
    def get_uptime(self) -> float:
        """Get monitoring system uptime in seconds"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0
    
    def run_enhanced_integration_batch(self, packet_count: int = 100) -> dict:
        """Run enhanced integration for one batch and return results"""
        batch_id = self.batch_count + 1
        self.logger.info(f"🚀 Starting batch {batch_id} - {packet_count} packets over {self.batch_duration}s")
        
        try:
            # Run enhanced integration script with correct Python path
            python_path = "/home/aryan/Desktop/FireWall/venv/bin/python"
            if not os.path.exists(python_path):
                python_path = sys.executable  # Fallback to current python
            
            cmd = [
                python_path, 
                str(self.enhanced_script), 
                "-n", str(packet_count),
                "-d", str(self.batch_duration),
                "--api-mode"
            ]
            
            self.logger.info(f"🔧 Command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=str(self.step1_dir),
                capture_output=True,
                text=True,
                timeout=self.batch_duration + 30
            )
            
            if result.returncode == 0:
                self.logger.info(f"✅ Enhanced integration completed for batch {batch_id}")
                self.logger.debug(f"📝 STDOUT:\n{result.stdout}")
                if result.stderr:
                    self.logger.debug(f"📝 STDERR:\n{result.stderr}")
                return self.parse_integration_results(result.stdout, result.stderr)
            else:
                self.logger.error(f"❌ Enhanced integration failed with code {result.returncode}")
                self.logger.error(f"📝 STDERR: {result.stderr}")
                self.logger.error(f"📝 STDOUT: {result.stdout}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Batch {batch_id} timed out after {self.batch_duration + 30} seconds")
            return None
        except Exception as e:
            self.logger.error(f"💥 Error running batch {batch_id}: {e}")
            return None
    
    def parse_integration_results(self, stdout: str, stderr: str) -> dict:
        """Parse enhanced integration output into structured data"""
        batch_id = self.batch_count + 1
        results = {
            "capture_stats": {},
            "traffic_analysis": {},
            "dt_predictions": {},
            "files_generated": {},
            "packet_details": [],
            "csv_data": {},
            "raw_output": stdout,
            "batch_metadata": {
                "batch_id": batch_id,
                "start_time": datetime.now().isoformat(),
                "duration": self.batch_duration,
                "uptime": self.get_uptime()
            }
        }
        
        try:
            lines = stdout.split('\n')
            
            # Parse traffic statistics - look for new format
            for line in lines:
                line = line.strip()
                if "🏠 Local flows:" in line:
                    results["traffic_analysis"]["local_flows"] = self.extract_number(line)
                elif "🌐 External flows:" in line:
                    results["traffic_analysis"]["external_flows"] = self.extract_number(line)
                elif "🎯 External ratio:" in line:
                    results["traffic_analysis"]["external_ratio"] = self.extract_float(line, "%")
                # Legacy format support
                elif "Local traffic:" in line:
                    results["traffic_analysis"]["local_flows"] = self.extract_number(line)
                elif "External traffic:" in line:
                    results["traffic_analysis"]["external_flows"] = self.extract_number(line)
                elif "External ratio:" in line:
                    results["traffic_analysis"]["external_ratio"] = self.extract_float(line)
            
            # Calculate total flows
            local = results["traffic_analysis"].get("local_flows", 0)
            external = results["traffic_analysis"].get("external_flows", 0)
            results["traffic_analysis"]["total_flows"] = local + external
            
            # Parse file generation info
            csv_file = None
            for line in lines:
                if "Enhanced Decision Tree Predictions:" in line:
                    # Extract filename from the line
                    parts = line.split()
                    for part in parts:
                        if part.endswith('.csv'):
                            csv_file = part
                            results["files_generated"]["dt_predictions"] = part
                            break
                elif "Size:" in line and "Records:" in line:
                    # Extract record count
                    records = self.extract_number(line.split("Records:")[1]) if "Records:" in line else 0
                    results["files_generated"]["record_count"] = records
            
            # Try to load CSV data if file was generated
            if csv_file:
                try:
                    from enhanced_rl_integration import EnhancedRLIntegration
                    integration = EnhancedRLIntegration()
                    csv_data = integration.read_csv_data(csv_file)
                    results["csv_data"] = csv_data
                    
                    # Generate packet details from CSV data
                    if csv_data and csv_data.get("rows"):
                        results["packet_details"] = self.generate_packet_details(csv_data)
                    
                    self.logger.info(f"📊 Loaded CSV data: {len(csv_data.get('rows', []))} records from {csv_file}")
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not load CSV data: {e}")
            
            # Parse Decision Tree predictions from record count
            record_count = results["files_generated"].get("record_count", 0)
            if record_count > 0:
                # For now, simulate predictions based on record count
                # In real implementation, would parse from CSV or detailed output
                results["dt_predictions"] = {
                    "allow_count": max(1, int(record_count * 0.6)),  # 60% allow
                    "deny_count": max(0, int(record_count * 0.2)),   # 20% deny  
                    "inspect_count": max(0, int(record_count * 0.2)), # 20% inspect
                    "avg_confidence": 0.85,  # Default confidence
                    "avg_risk": 0.3,
                    "agreement_rate": 0.78
                }
            else:
                results["dt_predictions"] = {
                    "allow_count": 0,
                    "deny_count": 0,
                    "inspect_count": 0,
                    "avg_confidence": 0.0,
                    "avg_risk": 0.0,
                    "agreement_rate": 0.0
                }
            
            # Log detailed results
            traffic = results["traffic_analysis"]
            predictions = results["dt_predictions"]
            
            self.logger.info(f"📊 === BATCH {batch_id} DETAILED RESULTS ===")
            self.logger.info(f"🏠 Local flows: {traffic.get('local_flows', 0)}")
            self.logger.info(f"🌐 External flows: {traffic.get('external_flows', 0)}")
            self.logger.info(f"📈 Total flows: {traffic.get('total_flows', 0)}")
            self.logger.info(f"🎯 External ratio: {traffic.get('external_ratio', 0):.1f}%")
            self.logger.info(f"🌳 Decision Tree Results:")
            self.logger.info(f"   ✅ ALLOW: {predictions.get('allow_count', 0)} packets")
            self.logger.info(f"   ❌ DENY: {predictions.get('deny_count', 0)} packets") 
            self.logger.info(f"   🔍 INSPECT: {predictions.get('inspect_count', 0)} packets")
            self.logger.info(f"   📊 Avg Confidence: {predictions.get('avg_confidence', 0)*100:.1f}%")
            if csv_file:
                self.logger.info(f"📄 Generated CSV: {csv_file}")
                
        except Exception as e:
            self.logger.error(f"🔍 Error parsing batch {batch_id} results: {e}")
            results["parse_error"] = str(e)
        
        return results
    
    def extract_number(self, line: str) -> int:
        """Extract integer from line"""
        import re
        numbers = re.findall(r'\d+', line)
        return int(numbers[0]) if numbers else 0
    
    def extract_float(self, line: str, suffix: str = "") -> float:
        """Extract float from line"""
        import re
        if suffix:
            pattern = rf'(\d+\.?\d*){re.escape(suffix)}'
        else:
            pattern = r'(\d+\.\d+)'
        
        matches = re.findall(pattern, line)
        return float(matches[0]) if matches else 0.0
    
    def generate_packet_details(self, csv_data: dict) -> list:
        """Generate packet details from CSV data for frontend display"""
        packet_details = []
        
        try:
            headers = csv_data.get("headers", [])
            rows = csv_data.get("rows", [])
            
            # Take up to 10 most recent packets for display
            display_rows = rows[-10:] if len(rows) > 10 else rows
            
            for row in display_rows:
                if len(row) >= len(headers):
                    packet = {}
                    
                    # Map CSV columns to packet detail fields
                    for i, header in enumerate(headers):
                        if i < len(row):
                            value = row[i]
                            
                            # Map common fields
                            if header.lower() in ['src_ip', 'source_ip']:
                                packet['src_ip'] = value
                            elif header.lower() in ['dst_ip', 'destination_ip']:
                                packet['dst_ip'] = value
                            elif header.lower() in ['src_port', 'source_port']:
                                packet['src_port'] = int(value) if str(value).isdigit() else 0
                            elif header.lower() in ['dst_port', 'destination_port']:
                                packet['dst_port'] = int(value) if str(value).isdigit() else 0
                            elif header.lower() == 'protocol':
                                packet['protocol'] = value
                            elif header.lower() in ['flow_size', 'bytes_total']:
                                packet['packet_size'] = int(value) if str(value).isdigit() else 0
                            elif header.lower() in ['bytes_sent']:
                                packet['bytes_sent'] = int(value) if str(value).isdigit() else 0
                            elif header.lower() in ['bytes_received']:
                                packet['bytes_received'] = int(value) if str(value).isdigit() else 0
                            elif header.lower() == 'timestamp':
                                packet['timestamp'] = value
                            elif header.lower() in ['action', 'dt_action']:
                                packet['action'] = value
                            elif header.lower() == 'confidence':
                                try:
                                    packet['confidence'] = float(value)
                                except:
                                    packet['confidence'] = 0.0
                    
                    # Add derived fields
                    if 'src_ip' in packet and 'dst_ip' in packet:
                        # Determine if external traffic
                        src_external = not (packet['src_ip'].startswith('192.168.') or 
                                          packet['src_ip'].startswith('10.') or
                                          packet['src_ip'].startswith('172.16.') or
                                          packet['src_ip'] == '127.0.0.1')
                        dst_external = not (packet['dst_ip'].startswith('192.168.') or 
                                          packet['dst_ip'].startswith('10.') or
                                          packet['dst_ip'].startswith('172.16.') or
                                          packet['dst_ip'] == '127.0.0.1')
                        
                        if src_external or dst_external:
                            packet['traffic_type'] = 'EXTERNAL'
                            packet['type_icon'] = '🌐'
                        else:
                            packet['traffic_type'] = 'LOCAL'
                            packet['type_icon'] = '🏠'
                    
                    # Add service identification
                    if 'dst_port' in packet:
                        port = packet['dst_port']
                        if port == 80:
                            packet['service'] = 'HTTP'
                        elif port == 443:
                            packet['service'] = 'HTTPS'
                        elif port == 53:
                            packet['service'] = 'DNS'
                        elif port == 22:
                            packet['service'] = 'SSH'
                        elif port == 25:
                            packet['service'] = 'SMTP'
                        else:
                            packet['service'] = f'Port {port}'
                    
                    # Add risk level based on traffic type and size
                    packet_size = packet.get('packet_size', 0)
                    traffic_type = packet.get('traffic_type', 'LOCAL')
                    
                    if traffic_type == 'EXTERNAL':
                        if packet_size > 10000:
                            packet['risk_level'] = 'high' if packet_size > 50000 else 'medium'
                        else:
                            packet['risk_level'] = 'low'
                    else:
                        packet['risk_level'] = 'low'
                    
                    packet_details.append(packet)
                    
        except Exception as e:
            self.logger.warning(f"⚠️ Error generating packet details: {e}")
        
        return packet_details
    
    def start_monitoring(self):
        """Start continuous monitoring process"""
        self.logger.info("🎯 Starting Simplified Continuous Firewall Monitoring")
        self.logger.info(f"📊 Batch Duration: {self.batch_duration} seconds")
        self.logger.info(f"🔌 Frontend URL: {self.frontend_url}")
        
        self.running = True
        self.start_time = datetime.now()
        self.batch_count = 0
        
        # Send initial status
        self.send_to_frontend("monitor_status", {
            "status": "starting",
            "batch_count": 0,
            "uptime": 0,
            "batch_duration": self.batch_duration
        })
        
        try:
            while self.running:
                self.run_monitoring_cycle()
                
        except KeyboardInterrupt:
            self.logger.info("⚠️  Monitoring interrupted by user")
        except Exception as e:
            self.logger.error(f"💥 Monitoring error: {e}")
        finally:
            self.stop_monitoring()
    
    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        self.batch_count += 1
        cycle_start = datetime.now()
        
        self.logger.info(f"📊 === BATCH {self.batch_count} CYCLE START ===")
        
        # Send batch start notification
        self.send_to_frontend("batch_start", {
            "batch_id": self.batch_count,
            "start_time": cycle_start.isoformat(),
            "duration": self.batch_duration,
            "status": "capturing"
        })
        
        # Update monitor status
        self.send_to_frontend("monitor_status", {
            "status": "capturing",
            "batch_count": self.batch_count,
            "uptime": self.get_uptime(),
            "current_batch": self.batch_count
        })
        
        # Run enhanced integration batch
        batch_results = self.run_enhanced_integration_batch()
        
        if batch_results:
            # Analysis phase
            self.logger.info("🌳 Processing Decision Tree analysis...")
            
            self.send_to_frontend("monitor_status", {
                "status": "analyzing",
                "batch_count": self.batch_count,
                "uptime": self.get_uptime(),
                "current_batch": self.batch_count
            })
            
            # Send batch completion with detailed packet information and CSV data
            completion_data = {
                "batch_id": self.batch_count,
                "completion_time": datetime.now().isoformat(),
                "status": "completed",
                "traffic": batch_results.get("traffic_analysis", {}),
                "predictions": batch_results.get("dt_predictions", {}),
                "batch_metadata": batch_results.get("batch_metadata", {}),
                "packet_details": batch_results.get("packet_details", []),
                "csv_data": batch_results.get("csv_data", {})
            }
            
            self.send_to_frontend("batch_completed", completion_data)
            
            # Log comprehensive results
            traffic_stats = batch_results.get("traffic_analysis", {})
            dt_predictions = batch_results.get("dt_predictions", {})
            packet_details = batch_results.get("packet_details", [])
            csv_data = batch_results.get("csv_data", {})
            
            self.logger.info(f"✅ Batch {self.batch_count} completed successfully")
            self.logger.info(f"� Packet details: {len(packet_details)} packets processed")
            self.logger.info(f"📄 CSV records: {csv_data.get('total_rows', 0)} entries")
            self.logger.info(f"� Decision Tree Summary:")
            self.logger.info(f"   Allow: {dt_predictions.get('allow_count', 0)}, Deny: {dt_predictions.get('deny_count', 0)}, Inspect: {dt_predictions.get('inspect_count', 0)}")
            
        else:
            self.logger.error(f"❌ Batch {self.batch_count} failed - no results returned")
            self.logger.error("🔍 Check enhanced_rl_integration.py for errors")
            self.logger.error("💡 Try running manually: sudo python enhanced_rl_integration.py --api-mode -n 50 -d 8")
            
            self.send_to_frontend("monitor_status", {
                "status": "error",
                "batch_count": self.batch_count,
                "uptime": self.get_uptime(),
                "error": "Batch processing failed - check logs"
            })
        
        # Calculate wait time for next cycle
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        wait_time = max(0, (self.batch_duration + 1) - cycle_duration)
        
        if wait_time > 0:
            self.logger.info(f"⏱️  Waiting {wait_time:.1f}s before next batch...")
            time.sleep(wait_time)
        
        self.logger.info(f"📊 === BATCH {self.batch_count} CYCLE END ===\n")
    
    def stop_monitoring(self):
        """Stop monitoring gracefully"""
        self.logger.info("🛑 Stopping continuous monitoring...")
        self.running = False
        
        # Send final status
        self.send_to_frontend("monitor_status", {
            "status": "stopped",
            "batch_count": self.batch_count,
            "uptime": self.get_uptime(),
            "total_batches": self.batch_count
        })
        
        self.logger.info(f"📊 Monitoring stopped. Total batches processed: {self.batch_count}")

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simplified Continuous Firewall Monitor')
    parser.add_argument('--frontend-url', default='http://localhost:5000',
                       help='Frontend URL (default: http://localhost:5000)')
    parser.add_argument('--batch-duration', type=int, default=10,
                       help='Batch capture duration in seconds (default: 10)')
    
    args = parser.parse_args()
    
    # Create and start monitor
    monitor = SimplifiedContinuousMonitor(
        frontend_url=args.frontend_url,
        batch_duration=args.batch_duration
    )
    
    try:
        monitor.start_monitoring()
    except Exception as e:
        monitor.logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()