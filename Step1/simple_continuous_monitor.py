#!/usr/bin/env python3
"""
Simplified Continuous Firewall Monitor
Runs batch monitoring with file-based communication to frontend
"""
import os
import sys
import time
import json
import signal
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class SimpleContinuousMonitor:
    def __init__(self, batch_duration: int = 10, step1_dir: str = None, frontend_dir: str = None):
        self.batch_duration = batch_duration
        self.step1_dir = Path(step1_dir) if step1_dir else Path(__file__).parent.absolute()
        self.frontend_dir = Path(frontend_dir) if frontend_dir else self.step1_dir.parent / "frontend"
        
        # Create shared data directory
        self.shared_data_dir = self.frontend_dir / "shared_data"
        self.shared_data_dir.mkdir(exist_ok=True)
        
        # File paths for communication
        self.status_file = self.shared_data_dir / "monitor_status.json"
        self.batches_file = self.shared_data_dir / "batch_results.json"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('SimpleContinuousMonitor')
        
        # State
        self.running = False
        self.batch_count = 0
        self.start_time = None
        
        # Signal handling
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"📡 Received signal {signum}, shutting down...")
        self.stop_monitoring()
        sys.exit(0)
    
    def update_status(self, status: str, details: Optional[Dict] = None):
        """Update status file for frontend"""
        status_data = {
            "status": status,
            "batch_count": self.batch_count,
            "uptime": int(time.time() - self.start_time) if self.start_time else 0,
            "last_update": datetime.now().isoformat(),
            "batch_duration": self.batch_duration
        }
        if details:
            status_data.update(details)
            
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f)
        except Exception as e:
            self.logger.error(f"📁 Error updating status file: {e}")
    
    def save_batch_result(self, batch_data: Dict[str, Any]):
        """Save batch result to file"""
        try:
            # Load existing results
            batches = []
            if self.batches_file.exists():
                with open(self.batches_file, 'r') as f:
                    data = json.load(f)
                    batches = data.get('batches', [])
            
            # Add new batch
            batches.append(batch_data)
            
            # Keep only last 50 batches
            if len(batches) > 50:
                batches = batches[-50:]
            
            # Save results
            results_data = {
                "batches": batches,
                "total_count": len(batches),
                "last_update": datetime.now().isoformat()
            }
            
            with open(self.batches_file, 'w') as f:
                json.dump(results_data, f)
                
            self.logger.info(f"💾 Saved batch {batch_data['batch_id']} results")
            
        except Exception as e:
            self.logger.error(f"💾 Error saving batch results: {e}")
    
    def run_enhanced_integration_batch(self) -> Dict[str, Any]:
        """Run a single batch of enhanced integration"""
        self.logger.info(f"🚀 Starting batch {self.batch_count + 1} - 100 packets over {self.batch_duration}s")
        
        batch_start = datetime.now()
        batch_data = {
            "batch_id": self.batch_count + 1,
            "start_time": batch_start.isoformat(),
            "duration": self.batch_duration,
            "status": "running",
            "total_packets": 0,
            "allowed_packets": 0,
            "blocked_packets": 0,
            "predictions": {
                "allow": 0,
                "block": 0,
                "total": 0,
                "accuracy": 0.0
            },
            "performance": {
                "capture_time": 0.0,
                "analysis_time": 0.0,
                "total_time": 0.0
            }
        }
        
        try:
            # Run enhanced integration in API mode
            integration_script = self.step1_dir / "enhanced_rl_integration.py"
            cmd = [
                sys.executable, str(integration_script),
                "--api-mode",
                "--batch-duration", str(self.batch_duration),
                "--packet-count", "100"
            ]
            
            self.logger.info("📡 Running enhanced RL integration...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.batch_duration + 30,  # Extra time for processing
                cwd=str(self.step1_dir)
            )
            
            if result.returncode == 0:
                # Parse results
                try:
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines:
                        if line.startswith('BATCH_RESULT:'):
                            result_json = line.replace('BATCH_RESULT:', '')
                            batch_result = json.loads(result_json)
                            batch_data.update(batch_result)
                            break
                    
                    batch_data["status"] = "completed"
                    self.logger.info(f"✅ Batch {batch_data['batch_id']} completed successfully")
                    
                except Exception as e:
                    self.logger.error(f"📊 Error parsing batch results: {e}")
                    batch_data["status"] = "error"
                    batch_data["error"] = str(e)
            else:
                self.logger.error(f"❌ Enhanced integration failed: {result.stderr}")
                batch_data["status"] = "failed"
                batch_data["error"] = result.stderr
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Batch {batch_data['batch_id']} timed out")
            batch_data["status"] = "timeout"
            batch_data["error"] = "Process timed out"
        except Exception as e:
            self.logger.error(f"❌ Batch {batch_data['batch_id']} failed: {e}")
            batch_data["status"] = "error"
            batch_data["error"] = str(e)
        
        # Finalize batch data
        batch_end = datetime.now()
        batch_data["end_time"] = batch_end.isoformat()
        batch_data["performance"]["total_time"] = (batch_end - batch_start).total_seconds()
        
        return batch_data
    
    def run_monitoring_loop(self):
        """Main monitoring loop"""
        self.logger.info("🎯 Starting Simple Continuous Firewall Monitoring System")
        self.logger.info(f"📊 Batch Duration: {self.batch_duration} seconds")
        self.logger.info(f"📁 Status File: {self.status_file}")
        self.logger.info(f"📁 Results File: {self.batches_file}")
        
        self.running = True
        self.start_time = time.time()
        
        # Initialize status
        self.update_status("connected", {
            "message": "Monitoring system started"
        })
        
        try:
            while self.running:
                self.batch_count += 1
                
                self.logger.info(f"📊 === BATCH {self.batch_count} CYCLE START ===")
                
                # Update status
                self.update_status("processing", {
                    "current_batch": self.batch_count,
                    "message": f"Processing batch {self.batch_count}"
                })
                
                # Run batch
                batch_result = self.run_enhanced_integration_batch()
                
                # Save results
                self.save_batch_result(batch_result)
                
                # Update status
                self.update_status("connected", {
                    "last_batch": self.batch_count,
                    "last_batch_status": batch_result["status"],
                    "message": f"Completed batch {self.batch_count}"
                })
                
                self.logger.info(f"📊 === BATCH {self.batch_count} CYCLE END ===")
                self.logger.info("")
                
                # Brief pause before next batch
                if self.running:
                    time.sleep(2)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Monitoring loop error: {e}")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.logger.info("🛑 Stopping continuous monitoring...")
        self.running = False
        
        # Update final status
        self.update_status("disconnected", {
            "message": "Monitoring stopped",
            "total_batches": self.batch_count
        })
        
        self.logger.info(f"📊 Monitoring stopped. Total batches processed: {self.batch_count}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Continuous Firewall Monitor')
    parser.add_argument('--batch-duration', type=int, default=10,
                       help='Duration of each batch in seconds (default: 10)')
    parser.add_argument('--step1-dir', type=str,
                       help='Path to Step1 directory')
    parser.add_argument('--frontend-dir', type=str,
                       help='Path to frontend directory')
    
    args = parser.parse_args()
    
    # Create and run monitor
    monitor = SimpleContinuousMonitor(
        batch_duration=args.batch_duration,
        step1_dir=args.step1_dir,
        frontend_dir=args.frontend_dir
    )
    
    monitor.run_monitoring_loop()

if __name__ == '__main__':
    main()