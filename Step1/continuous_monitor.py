#!/usr/bin/env python3

"""
Continuous Firewall Monitoring System

This script runs enhanced RL integration every 10 seconds:
1. Captures packets for 10 seconds
2. Processes with RL analysis between batches (10th-11th second)
3. Sends results to frontend via WebSocket
4. Repeats continuously

Architecture:
- Batch Processing: 10-second capture cycles
- Real-time Analysis: RL predictions between captures
- Frontend Integration: WebSocket streaming to dashboard
- Continuous Operation: Infinite monitoring loop
"""

import subprocess
import sys
import os
import json
import time
import threading
import signal
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import socketio
import requests
from pathlib import Path

class ContinuousFirewallMonitor:
    def __init__(self, frontend_url="http://localhost:5000", batch_duration=10):
        """Initialize continuous monitoring system"""
        self.frontend_url = frontend_url
        self.batch_duration = batch_duration
        self.step1_dir = Path(__file__).parent
        self.enhanced_script = self.step1_dir / "enhanced_rl_integration.py"
        
        # State management
        self.running = False
        self.batch_count = 0
        self.start_time = None
        self.current_batch_data = {}
        
        # WebSocket client for frontend communication
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,
            reconnection_delay=1,
            reconnection_delay_max=5
        )
        
        # Setup logging
        self.setup_logging()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Setup WebSocket event handlers
        self.setup_websocket_handlers()
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.step1_dir / 'continuous_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('ContinuousMonitor')
    
    def setup_websocket_handlers(self):
        """Setup WebSocket event handlers"""
        @self.sio.event
        def connect():
            self.logger.info("🔌 Connected to frontend WebSocket")
            self.send_monitor_status("connected")
        
        @self.sio.event
        def disconnect():
            self.logger.warning("🔌 Disconnected from frontend WebSocket")
        
        @self.sio.event
        def connect_error(data):
            self.logger.error(f"🔌 WebSocket connection error: {data}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"📡 Received signal {signum}, shutting down...")
        self.stop_monitoring()
        sys.exit(0)
    
    def connect_to_frontend(self, max_retries=5):
        """Connect to frontend WebSocket with retries"""
        for attempt in range(max_retries):
            try:
                self.sio.connect(self.frontend_url)
                return True
            except Exception as e:
                self.logger.warning(f"🔌 Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        self.logger.error("🔌 Failed to connect to frontend after all retries")
        return False
    
    def send_to_frontend(self, event: str, data: Dict[str, Any]):
        """Send data to frontend via WebSocket"""
        try:
            if self.sio.connected:
                self.sio.emit(event, data)
                self.logger.debug(f"📡 Sent {event} to frontend: {len(str(data))} bytes")
            else:
                self.logger.warning("🔌 Not connected to frontend, attempting reconnection...")
                self.connect_to_frontend(max_retries=2)
        except Exception as e:
            self.logger.error(f"📡 Error sending to frontend: {e}")
    
    def send_monitor_status(self, status: str, details: Optional[Dict] = None):
        """Send monitoring status updates to frontend"""
        status_data = {
            "status": status,
            "batch_count": self.batch_count,
            "uptime": self.get_uptime(),
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.send_to_frontend("monitor_status", status_data)
    
    def send_batch_start(self, batch_id: int):
        """Send batch start notification"""
        batch_data = {
            "batch_id": batch_id,
            "duration": self.batch_duration,
            "start_time": datetime.now().isoformat(),
            "status": "capturing"
        }
        self.send_to_frontend("batch_start", batch_data)
    
    def send_batch_results(self, batch_id: int, results: Dict[str, Any]):
        """Send completed batch results"""
        batch_data = {
            "batch_id": batch_id,
            "completion_time": datetime.now().isoformat(),
            "status": "completed",
            "results": results
        }
        self.send_to_frontend("batch_results", batch_data)
    
    def get_uptime(self) -> float:
        """Get monitoring system uptime in seconds"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0
    
    def run_enhanced_integration_batch(self, packet_count: int = 100) -> Optional[Dict[str, Any]]:
        """Run enhanced integration for one batch and return structured results"""
        self.logger.info(f"🚀 Starting batch {self.batch_count + 1} - {packet_count} packets over {self.batch_duration}s")
        
        try:
            # Run enhanced integration script
            cmd = [
                sys.executable, 
                str(self.enhanced_script), 
                "-n", str(packet_count),
                "-d", str(self.batch_duration),
                "--api-mode"  # We'll add this flag
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.step1_dir),
                capture_output=True,
                text=True,
                timeout=self.batch_duration + 30  # Extra time for processing
            )
            
            if result.returncode == 0:
                # Parse results from enhanced integration
                return self.parse_integration_results(result.stdout, result.stderr)
            else:
                self.logger.error(f"❌ Enhanced integration failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Batch {self.batch_count + 1} timed out")
            return None
        except Exception as e:
            self.logger.error(f"💥 Error running batch: {e}")
            return None
    
    def parse_integration_results(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse enhanced integration output into structured data"""
        results = {
            "capture_stats": {},
            "traffic_analysis": {},
            "rl_predictions": {},
            "files_generated": {},
            "performance": {},
            "raw_output": stdout
        }
        
        try:
            lines = stdout.split('\n')
            
            # Parse traffic analysis
            for line in lines:
                if "Local traffic:" in line:
                    results["traffic_analysis"]["local_flows"] = self.extract_number(line)
                elif "External traffic:" in line:
                    results["traffic_analysis"]["external_flows"] = self.extract_number(line)
                elif "Total allowed flows:" in line:
                    results["traffic_analysis"]["total_flows"] = self.extract_number(line)
                elif "External ratio:" in line:
                    results["traffic_analysis"]["external_ratio"] = self.extract_float(line)
            
            # Parse RL prediction summary
            for line in lines:
                if "ALLOW:" in line and "packets" in line:
                    results["rl_predictions"]["allow_count"] = self.extract_number(line)
                elif "DENY:" in line and "packets" in line:
                    results["rl_predictions"]["deny_count"] = self.extract_number(line)
                elif "INSPECT:" in line and "packets" in line:
                    results["rl_predictions"]["inspect_count"] = self.extract_number(line)
                elif "Average Confidence:" in line:
                    results["rl_predictions"]["avg_confidence"] = self.extract_float(line)
                elif "Average Risk Score:" in line:
                    results["rl_predictions"]["avg_risk"] = self.extract_float(line)
                elif "DQN-MDP Agreement:" in line and "%" in line:
                    results["rl_predictions"]["agreement_rate"] = self.extract_float(line, "%")
            
            # Find generated files
            for line in lines:
                if "enhanced_allowed_packets_" in line and ".csv" in line:
                    results["files_generated"]["allowed_csv"] = line.strip()
                elif "enhanced_rl_predictions_" in line and ".csv" in line:
                    results["files_generated"]["predictions_csv"] = line.strip()
            
            # Load actual CSV data if files exist
            self.load_csv_data(results)
            
        except Exception as e:
            self.logger.error(f"🔍 Error parsing results: {e}")
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
    
    def load_csv_data(self, results: Dict[str, Any]):
        """Load actual CSV data for detailed analysis"""
        try:
            import pandas as pd
            
            # Load allowed packets CSV
            if "allowed_csv" in results["files_generated"]:
                allowed_file = results["files_generated"]["allowed_csv"]
                if os.path.exists(allowed_file):
                    df_allowed = pd.read_csv(allowed_file)
                    results["csv_data"] = {
                        "allowed_packets": df_allowed.head(10).to_dict('records'),  # First 10 rows
                        "allowed_count": len(df_allowed)
                    }
            
            # Load predictions CSV
            if "predictions_csv" in results["files_generated"]:
                pred_file = results["files_generated"]["predictions_csv"]
                if os.path.exists(pred_file):
                    df_pred = pd.read_csv(pred_file)
                    results["csv_data"]["rl_predictions"] = df_pred.head(10).to_dict('records')
                    results["csv_data"]["predictions_count"] = len(df_pred)
                    
        except ImportError:
            self.logger.warning("📊 pandas not available, skipping CSV data loading")
        except Exception as e:
            self.logger.error(f"📊 Error loading CSV data: {e}")
    
    def start_monitoring(self):
        """Start continuous monitoring process"""
        self.logger.info("🎯 Starting Continuous Firewall Monitoring System")
        self.logger.info(f"📊 Batch Duration: {self.batch_duration} seconds")
        self.logger.info(f"🔌 Frontend URL: {self.frontend_url}")
        
        # Connect to frontend
        if not self.connect_to_frontend():
            self.logger.error("🔌 Cannot connect to frontend, monitoring will continue without WebSocket")
        
        self.running = True
        self.start_time = datetime.now()
        self.batch_count = 0
        
        self.send_monitor_status("starting", {
            "batch_duration": self.batch_duration,
            "enhanced_script": str(self.enhanced_script)
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
        """Run one complete monitoring cycle (10s capture + 1s analysis)"""
        self.batch_count += 1
        cycle_start = datetime.now()
        
        self.logger.info(f"📊 === BATCH {self.batch_count} CYCLE START ===")
        
        # Send batch start notification
        self.send_batch_start(self.batch_count)
        self.send_monitor_status("capturing", {"current_batch": self.batch_count})
        
        # Run enhanced integration batch (capture for batch_duration seconds)
        batch_results = self.run_enhanced_integration_batch()
        
        if batch_results:
            # Analysis phase (between 10th and 11th second)
            self.logger.info("🧠 Processing RL analysis...")
            self.send_monitor_status("analyzing", {"current_batch": self.batch_count})
            
            # Add batch metadata
            batch_results["batch_metadata"] = {
                "batch_id": self.batch_count,
                "start_time": cycle_start.isoformat(),
                "completion_time": datetime.now().isoformat(),
                "duration": self.batch_duration,
                "uptime": self.get_uptime()
            }
            
            # Send results to frontend
            self.send_batch_results(self.batch_count, batch_results)
            
            self.logger.info(f"✅ Batch {self.batch_count} completed successfully")
            self.logger.info(f"📊 External ratio: {batch_results.get('traffic_analysis', {}).get('external_ratio', 0):.1f}%")
            
        else:
            self.logger.error(f"❌ Batch {self.batch_count} failed")
            self.send_monitor_status("error", {"current_batch": self.batch_count, "error": "Batch processing failed"})
        
        # Calculate cycle duration and wait if needed
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        if cycle_duration < self.batch_duration + 1:  # +1 second for analysis
            wait_time = (self.batch_duration + 1) - cycle_duration
            self.logger.info(f"⏱️  Waiting {wait_time:.1f}s before next batch...")
            time.sleep(wait_time)
        
        self.logger.info(f"📊 === BATCH {self.batch_count} CYCLE END ===\n")
    
    def stop_monitoring(self):
        """Stop monitoring gracefully"""
        self.logger.info("🛑 Stopping continuous monitoring...")
        self.running = False
        
        if self.sio.connected:
            self.send_monitor_status("stopped", {"total_batches": self.batch_count})
            self.sio.disconnect()
        
        self.logger.info(f"📊 Monitoring stopped. Total batches processed: {self.batch_count}")

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Continuous Firewall Monitoring System')
    parser.add_argument('--frontend-url', default='http://localhost:5000',
                       help='Frontend WebSocket URL (default: http://localhost:5000)')
    parser.add_argument('--batch-duration', type=int, default=10,
                       help='Batch capture duration in seconds (default: 10)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start monitor
    monitor = ContinuousFirewallMonitor(
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