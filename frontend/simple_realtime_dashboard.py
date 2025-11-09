#!/usr/bin/env python3
"""
Simple Real-time Dashboard
File-based communication with continuous monitor
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('SimpleFirewallDashboard')

class SimpleFirewallDashboard:
    def __init__(self):
        self.app = Flask(__name__, template_folder='templates')
        self.app.config['SECRET_KEY'] = 'firewall-monitoring-secret-key'
        
        # Setup SocketIO with less verbose logging
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            logger=False,
            engineio_logger=False
        )
        
        # Data directories
        self.shared_data_dir = Path(__file__).parent / "shared_data"
        self.shared_data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.status_file = self.shared_data_dir / "monitor_status.json"
        self.batches_file = self.shared_data_dir / "batch_results.json"
        
        # Initialize files if they don't exist
        self._initialize_files()
        
        # Setup routes and WebSocket handlers
        self._setup_routes()
        self._setup_websocket_handlers()
        
        logger.info("🚀 Simple Firewall Dashboard initialized")
    
    def _initialize_files(self):
        """Initialize shared data files"""
        if not self.status_file.exists():
            initial_status = {
                "status": "disconnected",
                "batch_count": 0,
                "uptime": 0,
                "last_update": None,
                "batch_duration": 10
            }
            with open(self.status_file, 'w') as f:
                json.dump(initial_status, f)
        
        if not self.batches_file.exists():
            initial_batches = {
                "batches": [],
                "total_count": 0,
                "last_update": None
            }
            with open(self.batches_file, 'w') as f:
                json.dump(initial_batches, f)
    
    def _setup_routes(self):
        """Setup Flask routes"""
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def get_status():
            try:
                if self.status_file.exists():
                    with open(self.status_file, 'r') as f:
                        return jsonify(json.load(f))
                else:
                    return jsonify({
                        "status": "disconnected",
                        "batch_count": 0,
                        "uptime": 0,
                        "last_update": None
                    })
            except Exception as e:
                logger.error(f"Error reading status: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/batches')
        def get_batches():
            try:
                if self.batches_file.exists():
                    with open(self.batches_file, 'r') as f:
                        return jsonify(json.load(f))
                else:
                    return jsonify({
                        "batches": [],
                        "total_count": 0,
                        "last_update": None
                    })
            except Exception as e:
                logger.error(f"Error reading batches: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _setup_websocket_handlers(self):
        """Setup WebSocket event handlers"""
        @self.socketio.on('connect')
        def handle_connect():
            from flask import request
            logger.info(f"🔌 Client connected: {request.sid}")
            # Send current status and batches
            self.emit_current_status()
            self.emit_current_batches()
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            from flask import request
            logger.info(f"🔌 Client disconnected: {request.sid}")
    
    def emit_current_status(self):
        """Emit current status to all clients"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    status = json.load(f)
                self.socketio.emit('monitor_status', status)
        except Exception as e:
            logger.error(f"Error emitting status: {e}")
    
    def emit_current_batches(self):
        """Emit current batch history to all clients"""
        try:
            if self.batches_file.exists():
                with open(self.batches_file, 'r') as f:
                    batches = json.load(f)
                self.socketio.emit('batch_history', batches)
        except Exception as e:
            logger.error(f"Error emitting batches: {e}")
    
    def start_file_monitor(self):
        """Start monitoring files for changes"""
        def monitor_files():
            last_status_mtime = 0
            last_batches_mtime = 0
            
            while True:
                try:
                    # Check status file
                    if self.status_file.exists():
                        status_mtime = self.status_file.stat().st_mtime
                        if status_mtime > last_status_mtime:
                            last_status_mtime = status_mtime
                            self.emit_current_status()
                    
                    # Check batches file
                    if self.batches_file.exists():
                        batches_mtime = self.batches_file.stat().st_mtime
                        if batches_mtime > last_batches_mtime:
                            last_batches_mtime = batches_mtime
                            self.emit_current_batches()
                    
                    time.sleep(1)  # Check every second
                    
                except Exception as e:
                    logger.error(f"File monitor error: {e}")
                    time.sleep(5)
        
        # Start file monitor in background thread
        import threading
        monitor_thread = threading.Thread(target=monitor_files, daemon=True)
        monitor_thread.start()
        logger.info("📁 File monitor started")
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Run the dashboard"""
        logger.info(f"🚀 Starting Simple Firewall Dashboard on {host}:{port}")
        
        # Start file monitor
        self.start_file_monitor()
        
        # Run the app
        self.socketio.run(
            self.app, 
            host=host, 
            port=port, 
            debug=debug,
            use_reloader=False
        )

def main():
    """Main entry point"""
    dashboard = SimpleFirewallDashboard()
    
    try:
        dashboard.run()
    except KeyboardInterrupt:
        logger.info("🛑 Dashboard stopped by user")
    except Exception as e:
        logger.error(f"❌ Dashboard error: {e}")

if __name__ == '__main__':
    main()