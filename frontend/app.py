#!/usr/bin/env python3
"""
Flask Backend for RL-Based Firewall Dashboard
Monitors packet capture, denylist filtering, and ML predictions in real-time
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import subprocess
import threading
import time
import csv
import os
import sys
import json
import random
from datetime import datetime
from collections import deque, defaultdict
import pandas as pd
import numpy as np

# Add RL_testing to path for model imports
# sys.path.append(os.path.join(os.path.dirname(__file__), '../RL_testing'))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'firewall-secret-2025'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global state
packet_buffer = deque(maxlen=100)
denylist_buffer = deque(maxlen=50)
malformed_buffer = deque(maxlen=50)
ratelimit_buffer = deque(maxlen=50)
ml_predictions = deque(maxlen=50)
stats = {
    'total_packets': 0,
    'allowed': 0,
    'denied': 0,
    'inspected': 0,
    'blocked_by_denylist': 0,
    'blocked_by_malformed': 0,
    'blocked_by_ratelimit': 0,
    'sent_to_ml': 0,
    'uptime': 0
}
start_time = time.time()
capture_process = None
is_capturing = False

# Denylist cache
denylist_ips = set()
denylist_ports = set()

def load_denylist():
    """Load IPs and ports from denylist files"""
    global denylist_ips, denylist_ports
    
    # Load IPs
    ip_file = os.path.join(os.path.dirname(__file__), '../Step1/IP.txt')
    if os.path.exists(ip_file):
        with open(ip_file, 'r') as f:
            denylist_ips = {line.strip() for line in f if line.strip()}
    
    # Load Ports
    port_file = os.path.join(os.path.dirname(__file__), '../Step1/Ports.txt')
    if os.path.exists(port_file):
        with open(port_file, 'r') as f:
            denylist_ports = {int(line.strip()) for line in f if line.strip().isdigit()}
    
    print(f"[Denylist] Loaded {len(denylist_ips)} IPs and {len(denylist_ports)} ports")

def check_denylist(packet):
    """Check if packet matches denylist"""
    src_ip = packet.get('src_ip', '')
    dst_ip = packet.get('dst_ip', '')
    src_port = packet.get('src_port', 0)
    dst_port = packet.get('dst_port', 0)
    
    if src_ip in denylist_ips or dst_ip in denylist_ips:
        return True, 'IP in denylist'
    
    if src_port in denylist_ports or dst_port in denylist_ports:
        return True, 'Port in denylist'
    
    return False, None

def check_malformed(packet):
    """Check if packet is malformed (simulated)"""
    # Simulate malformed packet detection
    protocol = packet.get('protocol', 'TCP')
    size = packet.get('size', 0)
    
    # Very small packets might be malformed
    if size < 20:
        return True, 'Packet too small'
    
    # Very large packets might be suspicious
    if size > 9000:
        return True, 'Packet too large (possible jumbo frame attack)'
    
    # ICMP packets larger than typical ping
    if protocol == 'ICMP' and size > 1500:
        return True, 'Suspicious ICMP size'
    
    # Random chance for demo purposes
    if random.random() < 0.05:  # 5% chance
        return True, 'Invalid checksum detected'
    
    return False, None

def check_ratelimit(packet):
    """Check if packet violates rate limiting (simulated)"""
    src_ip = packet.get('src_ip', '')
    protocol = packet.get('protocol', 'TCP')
    
    # Simulate SYN flood detection
    if protocol == 'TCP' and random.random() < 0.03:  # 3% chance
        return True, f'SYN flood detected from {src_ip}'
    
    # Simulate too many connections
    if random.random() < 0.02:  # 2% chance
        return True, f'Rate limit exceeded from {src_ip}'
    
    return False, None

def simulate_ml_prediction(packet):
    """Simulate ML model prediction (you can replace with actual model)"""
    # Simple rule-based simulation for now
    risk_score = random.uniform(0, 1)
    
    # Higher risk for certain patterns
    if packet.get('protocol') == 'ICMP':
        risk_score += 0.2
    if packet.get('dst_port') in [23, 445, 3389]:  # Telnet, SMB, RDP
        risk_score += 0.3
    
    risk_score = min(risk_score, 1.0)
    
    if risk_score < 0.4:
        action = 'ALLOW'
    elif risk_score < 0.7:
        action = 'INSPECT'
    else:
        action = 'DENY'
    
    return {
        'action': action,
        'confidence': risk_score,
        'risk_score': risk_score,
        'reason': f"ML Analysis: Risk={risk_score:.2f}"
    }

def process_packet(packet_data):
    """Process incoming packet through the complete pipeline"""
    global stats
    
    stats['total_packets'] += 1
    
    # Add timestamp and ID
    packet_data['id'] = stats['total_packets']
    packet_data['timestamp'] = datetime.now().strftime('%H:%M:%S.%f')[:-3]
    packet_data['status'] = 'incoming'
    
    # Stage 1: Add to incoming buffer
    packet_buffer.append(packet_data.copy())
    socketio.emit('new_packet', packet_data)
    time.sleep(0.1)
    
    # Stage 2: Check denylist
    is_denied, reason = check_denylist(packet_data)
    
    if is_denied:
        stats['blocked_by_denylist'] += 1
        stats['denied'] += 1
        packet_data['status'] = 'blocked'
        packet_data['reason'] = reason
        packet_data['blocked_stage'] = 'denylist'
        denylist_buffer.append(packet_data.copy())
        socketio.emit('packet_blocked_denylist', packet_data)
        return
    
    # Stage 3: Check malformed
    socketio.emit('packet_pass_denylist', packet_data)
    time.sleep(0.1)
    
    is_malformed, reason = check_malformed(packet_data)
    
    if is_malformed:
        stats['blocked_by_malformed'] += 1
        stats['denied'] += 1
        packet_data['status'] = 'blocked'
        packet_data['reason'] = reason
        packet_data['blocked_stage'] = 'malformed'
        malformed_buffer.append(packet_data.copy())
        socketio.emit('packet_blocked_malformed', packet_data)
        return
    
    # Stage 4: Check rate limit
    socketio.emit('packet_pass_malformed', packet_data)
    time.sleep(0.1)
    
    is_ratelimited, reason = check_ratelimit(packet_data)
    
    if is_ratelimited:
        stats['blocked_by_ratelimit'] += 1
        stats['denied'] += 1
        packet_data['status'] = 'blocked'
        packet_data['reason'] = reason
        packet_data['blocked_stage'] = 'ratelimit'
        ratelimit_buffer.append(packet_data.copy())
        socketio.emit('packet_blocked_ratelimit', packet_data)
        return
    
    # Stage 5: Send to ML model
    socketio.emit('packet_pass_ratelimit', packet_data)
    time.sleep(0.1)
    
    stats['sent_to_ml'] += 1
    packet_data['status'] = 'processing'
    socketio.emit('packet_to_ml', packet_data)
    time.sleep(0.15)
    
    # Get ML prediction
    prediction = simulate_ml_prediction(packet_data)
    packet_data['prediction'] = prediction
    packet_data['status'] = prediction['action'].lower()
    
    if prediction['action'] == 'ALLOW':
        stats['allowed'] += 1
    elif prediction['action'] == 'DENY':
        stats['denied'] += 1
    elif prediction['action'] == 'INSPECT':
        stats['inspected'] += 1
    
    ml_predictions.append(packet_data.copy())
    socketio.emit('ml_prediction', packet_data)

def generate_sample_packet():
    """Generate a realistic sample packet for testing"""
    protocols = ['TCP', 'UDP', 'ICMP']
    src_ips = ['192.168.1.' + str(random.randint(1, 254)), 
               '10.0.0.' + str(random.randint(1, 254)),
               '172.16.0.' + str(random.randint(1, 254))]
    dst_ips = ['8.8.8.8', '1.1.1.1', '192.168.1.1', '10.0.0.1']
    
    protocol = random.choice(protocols)
    
    packet = {
        'src_ip': random.choice(src_ips),
        'dst_ip': random.choice(dst_ips),
        'protocol': protocol,
        'size': random.randint(64, 1500)
    }
    
    if protocol in ['TCP', 'UDP']:
        packet['src_port'] = random.randint(1024, 65535)
        packet['dst_port'] = random.choice([80, 443, 22, 53, 8080, 3306, 23, 445])
    else:
        packet['src_port'] = 0
        packet['dst_port'] = 0
    
    return packet

def packet_simulator():
    """Simulate incoming packets for demo"""
    while is_capturing:
        packet = generate_sample_packet()
        process_packet(packet)
        time.sleep(random.uniform(0.3, 1.0))

def read_csv_packets():
    """Read packets from CSV file (summary_batch_1.csv)"""
    csv_path = os.path.join(os.path.dirname(__file__), '../Step1/summary_batch_1.csv')
    
    if not os.path.exists(csv_path):
        return []
    
    packets = []
    try:
        df = pd.read_csv(csv_path)
        for _, row in df.iterrows():
            packet = {
                'src_ip': str(row.get('src_ip', 'N/A')),
                'dst_ip': str(row.get('dst_ip', 'N/A')),
                'src_port': int(row.get('src_port', 0)),
                'dst_port': int(row.get('dst_port', 0)),
                'protocol': str(row.get('protocol', 'TCP')),
                'size': int(row.get('bytes_sent', 0) + row.get('bytes_received', 0))
            }
            packets.append(packet)
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    return packets

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    stats['uptime'] = int(time.time() - start_time)
    return jsonify(stats)

@app.route('/api/denylist')
def get_denylist():
    """Get denylist info"""
    return jsonify({
        'ips': list(denylist_ips),
        'ports': list(denylist_ports)
    })

@app.route('/api/recent_packets')
def get_recent_packets():
    """Get recent packets"""
    return jsonify({
        'incoming': list(packet_buffer)[-20:],
        'denylist_blocked': list(denylist_buffer)[-20:],
        'malformed_blocked': list(malformed_buffer)[-20:],
        'ratelimit_blocked': list(ratelimit_buffer)[-20:],
        'predictions': list(ml_predictions)[-20:]
    })

@app.route('/api/start_capture', methods=['POST'])
def start_capture():
    """Start packet capture"""
    global is_capturing, capture_thread
    
    if not is_capturing:
        is_capturing = True
        capture_thread = threading.Thread(target=packet_simulator, daemon=True)
        capture_thread.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/api/stop_capture', methods=['POST'])
def stop_capture():
    """Stop packet capture"""
    global is_capturing
    is_capturing = False
    return jsonify({'status': 'stopped'})

@app.route('/api/reset', methods=['POST'])
def reset_stats():
    """Reset all statistics"""
    global stats, packet_buffer, denylist_buffer, malformed_buffer, ratelimit_buffer, ml_predictions, start_time
    
    stats = {
        'total_packets': 0,
        'allowed': 0,
        'denied': 0,
        'inspected': 0,
        'blocked_by_denylist': 0,
        'blocked_by_malformed': 0,
        'blocked_by_ratelimit': 0,
        'sent_to_ml': 0,
        'uptime': 0
    }
    start_time = time.time()
    packet_buffer.clear()
    denylist_buffer.clear()
    malformed_buffer.clear()
    ratelimit_buffer.clear()
    ml_predictions.clear()
    
    return jsonify({'status': 'reset'})

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connection_response', {'data': 'Connected to Firewall Dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')

if __name__ == '__main__':
    print("=" * 60)
    print("🔥 RL-Based Firewall Dashboard Starting...")
    print("=" * 60)
    
    # Load denylist
    load_denylist()
    
    # Start server
    print("\n🌐 Dashboard available at: http://localhost:5000")
    print("📊 Real-time packet monitoring enabled")
    print("🤖 ML predictions active")
    print("\nPress Ctrl+C to stop\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
