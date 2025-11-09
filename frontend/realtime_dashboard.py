#!/usr/bin/env python3

"""
Real-time Firewall Monitoring Dashboard

Flask application with Socket.IO for displaying continuous firewall monitoring results:
- Real-time batch processing visualization
- Traffic analysis charts and statistics
- Decision Tree prediction results and confidence scores
- System monitoring and status updates
- Responsive web interface with live updates
"""

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

class FirewallDashboard:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'firewall-monitoring-secret-key'
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True
        )
        
        # Data storage
        self.monitor_status = {
            "status": "disconnected",
            "batch_count": 0,
            "uptime": 0,
            "last_update": None
        }
        
        self.batch_history = []  # Store last 50 batches
        self.current_batch = None
        
        # Setup routes and socket handlers
        self.setup_routes()
        self.setup_socket_handlers()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('Dashboard')
    
    def setup_routes(self):
        """Setup Flask routes"""
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')
        
        @self.app.route('/api/status')
        def api_status():
            return json.dumps({
                "monitor_status": self.monitor_status,
                "batch_count": len(self.batch_history),
                "last_batch": self.batch_history[-1] if self.batch_history else None
            })
        
        @self.app.route('/api/history')
        def api_history():
            return json.dumps({
                "batches": self.batch_history[-20:],  # Last 20 batches
                "total_count": len(self.batch_history)
            })
        
        @self.app.route('/api/monitor_status', methods=['POST'])
        def api_monitor_status():
            data = request.get_json()
            self.monitor_status.update(data)
            self.monitor_status['last_update'] = datetime.now().isoformat()
            
            self.logger.info(f"📊 Monitor status updated: {data.get('status', 'unknown')}")
            
            # Broadcast to all WebSocket clients
            self.socketio.emit('monitor_status', self.monitor_status)
            return {'status': 'success'}
        
        @self.app.route('/api/batch_start', methods=['POST'])
        def api_batch_start():
            data = request.get_json()
            self.current_batch = data
            
            self.logger.info(f"🚀 Batch {data.get('batch_id', 'unknown')} started")
            
            # Broadcast to all WebSocket clients
            self.socketio.emit('batch_start', data)
            return {'status': 'success'}
        
        @self.app.route('/api/batch_completed', methods=['POST'])
        def api_batch_completed():
            data = request.get_json()
            
            # Process and store batch data
            processed_batch = self.process_batch_completion(data)
            self.batch_history.append(processed_batch)
            
            # Keep only last 50 batches
            if len(self.batch_history) > 50:
                self.batch_history.pop(0)
            
            batch_id = data.get('batch_id', 'unknown')
            self.logger.info(f"✅ Batch {batch_id} completed")
            
            # Broadcast to all WebSocket clients
            self.socketio.emit('batch_completed', processed_batch)
            self.socketio.emit('batch_history_update', {
                'latest_batch': processed_batch,
                'total_batches': len(self.batch_history)
            })
            
            return {'status': 'success'}
    
    def setup_socket_handlers(self):
        """Setup Socket.IO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info(f"🔌 Client connected: {request.sid}")
            # Send current status to newly connected client
            emit('monitor_status', self.monitor_status)
            emit('batch_history', {
                'batches': self.batch_history[-10:],
                'total_count': len(self.batch_history)
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info(f"🔌 Client disconnected: {request.sid}")
        
        @self.socketio.on('monitor_status')
        def handle_monitor_status(data):
            """Receive monitoring status updates"""
            self.monitor_status.update(data)
            self.monitor_status['last_update'] = datetime.now().isoformat()
            
            self.logger.info(f"📊 Monitor status: {data['status']} - Batch {data.get('batch_count', 0)}")
            
            # Broadcast to all clients
            self.socketio.emit('monitor_status', self.monitor_status)
        
        @self.socketio.on('batch_start')
        def handle_batch_start(data):
            """Receive batch start notifications"""
            self.current_batch = data
            self.logger.info(f"🚀 Batch {data['batch_id']} started")
            
            # Broadcast to all clients
            self.socketio.emit('batch_start', data)
        
        @self.socketio.on('batch_results')
        def handle_batch_results(data):
            """Receive and process batch results"""
            batch_id = data['batch_id']
            results = data['results']
            
            # Process and store batch data
            processed_batch = self.process_batch_results(data)
            self.batch_history.append(processed_batch)
            
            # Keep only last 50 batches
            if len(self.batch_history) > 50:
                self.batch_history.pop(0)
            
            self.logger.info(f"✅ Batch {batch_id} completed - {results.get('traffic_analysis', {}).get('total_flows', 0)} flows")
            
            # Broadcast to all clients
            self.socketio.emit('batch_completed', processed_batch)
            self.socketio.emit('batch_history_update', {
                'latest_batch': processed_batch,
                'total_batches': len(self.batch_history)
            })
        
        @self.socketio.on('request_dashboard_data')
        def handle_dashboard_request():
            """Send comprehensive dashboard data to client"""
            dashboard_data = {
                'monitor_status': self.monitor_status,
                'batch_history': self.batch_history[-20:],
                'statistics': self.calculate_statistics(),
                'current_batch': self.current_batch
            }
            emit('dashboard_data', dashboard_data)
    
    def process_batch_completion(self, data):
        """Process batch completion data from HTTP API"""
        batch_id = data.get('batch_id', 0)
        completion_time = data.get('completion_time', datetime.now().isoformat())
        
        # Extract key metrics directly from API data
        traffic_analysis = data.get('traffic', {})
        dt_predictions = data.get('predictions', {})
        batch_metadata = data.get('batch_metadata', {})
        packet_details = data.get('packet_details', [])
        csv_data = data.get('csv_data', {})
        
        processed = {
            'batch_id': batch_id,
            'completion_time': completion_time,
            'start_time': batch_metadata.get('start_time', completion_time),
            'duration': batch_metadata.get('duration', 10),
            
            # Traffic metrics
            'traffic': {
                'total_flows': traffic_analysis.get('total_flows', 0),
                'local_flows': traffic_analysis.get('local_flows', 0),
                'external_flows': traffic_analysis.get('external_flows', 0),
                'external_ratio': traffic_analysis.get('external_ratio', 0)
            },
            
            # Decision Tree prediction metrics
            'predictions': {
                'allow': dt_predictions.get('allow_count', 0),
                'deny': dt_predictions.get('deny_count', 0),
                'inspect': dt_predictions.get('inspect_count', 0),
                'avg_confidence': dt_predictions.get('avg_confidence', 0),
                'avg_risk': dt_predictions.get('avg_risk', 0),
                'agreement_rate': dt_predictions.get('agreement_rate', 0)
            },
            
            # Detailed packet information
            'packet_details': packet_details,
            
            # CSV data from decision tree
            'csv_data': csv_data,
            
            # Metadata
            'batch_metadata': batch_metadata
        }
        
        return processed

    def process_batch_results(self, data):
        """Process raw batch results into dashboard format"""
        batch_id = data['batch_id']
        completion_time = data['completion_time']
        results = data['results']
        
        # Extract key metrics
        traffic_analysis = results.get('traffic_analysis', {})
        dt_predictions = results.get('dt_predictions', {})
        batch_metadata = results.get('batch_metadata', {})
        
        processed = {
            'batch_id': batch_id,
            'completion_time': completion_time,
            'start_time': batch_metadata.get('start_time', completion_time),
            'duration': batch_metadata.get('duration', 10),
            
            # Traffic metrics
            'traffic': {
                'total_flows': traffic_analysis.get('total_flows', 0),
                'local_flows': traffic_analysis.get('local_flows', 0),
                'external_flows': traffic_analysis.get('external_flows', 0),
                'external_ratio': traffic_analysis.get('external_ratio', 0)
            },
            
            # RL prediction metrics
            'predictions': {
                'allow': dt_predictions.get('allow_count', 0),
                'deny': dt_predictions.get('deny_count', 0),
                'inspect': dt_predictions.get('inspect_count', 0),
                'avg_confidence': dt_predictions.get('avg_confidence', 0),
                'avg_risk': dt_predictions.get('avg_risk', 0),
                'agreement_rate': dt_predictions.get('agreement_rate', 0)
            },
            
            # Files generated
            'files': results.get('files_generated', {}),
            
            # Sample data for detailed view
            'sample_data': results.get('csv_data', {}),
            
            # Raw results for debugging
            'raw_results': results
        }
        
        return processed
    
    def calculate_statistics(self):
        """Calculate aggregate statistics from batch history"""
        if not self.batch_history:
            return {}
        
        recent_batches = self.batch_history[-20:]  # Last 20 batches
        
        # Traffic statistics
        total_flows = sum(b['traffic']['total_flows'] for b in recent_batches)
        total_external = sum(b['traffic']['external_flows'] for b in recent_batches)
        total_local = sum(b['traffic']['local_flows'] for b in recent_batches)
        
        avg_external_ratio = sum(b['traffic']['external_ratio'] for b in recent_batches) / len(recent_batches)
        
        # Decision Tree prediction statistics
        total_allows = sum(b['predictions']['allow'] for b in recent_batches)
        total_denies = sum(b['predictions']['deny'] for b in recent_batches)
        total_inspects = sum(b['predictions']['inspect'] for b in recent_batches)
        
        avg_confidence = sum(b['predictions']['avg_confidence'] for b in recent_batches) / len(recent_batches)
        avg_risk = sum(b['predictions']['avg_risk'] for b in recent_batches) / len(recent_batches)
        avg_agreement = sum(b['predictions']['agreement_rate'] for b in recent_batches) / len(recent_batches)
        
        return {
            'traffic': {
                'total_flows': total_flows,
                'external_flows': total_external,
                'local_flows': total_local,
                'avg_external_ratio': avg_external_ratio
            },
            'predictions': {
                'total_allows': total_allows,
                'total_denies': total_denies,
                'total_inspects': total_inspects,
                'avg_confidence': avg_confidence,
                'avg_risk': avg_risk,
                'avg_agreement': avg_agreement
            },
            'timespan': {
                'batches_analyzed': len(recent_batches),
                'first_batch_time': recent_batches[0]['start_time'] if recent_batches else None,
                'last_batch_time': recent_batches[-1]['completion_time'] if recent_batches else None
            }
        }
    
    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Start the dashboard server"""
        self.logger.info(f"🚀 Starting Firewall Monitoring Dashboard on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Firewall Monitoring Dashboard')
    parser.add_argument('--host', default='0.0.0.0',
                       help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Create and run dashboard
    dashboard = FirewallDashboard()
    
    try:
        dashboard.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        dashboard.logger.info("👋 Dashboard shutting down...")
    except Exception as e:
        dashboard.logger.error(f"💥 Dashboard error: {e}")

if __name__ == "__main__":
    main()