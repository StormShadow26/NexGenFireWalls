#!/usr/bin/env python3

import requests
import json
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_rl_integration import EnhancedRLIntegration

def test_csv_frontend_display():
    """Test sending CSV data to the frontend dashboard"""
    
    integration = EnhancedRLIntegration()
    
    # Read the sample CSV data
    csv_data = integration.read_csv_data('test_dt_predictions_sample.csv')
    
    print("📊 Testing CSV data display on frontend...")
    print(f"📁 CSV file: {csv_data['file_name']}")
    print(f"📋 Headers: {csv_data['headers']}")
    print(f"📊 Total rows: {csv_data['total_rows']}")
    
    # Create mock batch completion data with CSV
    batch_data = {
        "batch_id": 999,
        "completion_time": "2025-11-09T08:01:30Z",
        "traffic": {
            "total_flows": 10,
            "external_flows": 7,
            "local_flows": 3,
            "external_ratio": 70.0
        },
        "predictions": {
            "allow": 6,
            "deny": 2,
            "inspect": 2,
            "avg_confidence": 0.895
        },
        "packet_details": [
            {
                "src_ip": "192.168.1.100",
                "dst_ip": "203.0.113.5",
                "src_port": 45678,
                "dst_port": 80,
                "protocol": "TCP",
                "packet_size": 2048,
                "service": "HTTP",
                "risk_level": "low",
                "flags": "SYN,ACK",
                "payload_size": 1024
            }
        ],
        "csv_data": csv_data  # Include the CSV data
    }
    
    try:
        # Send to frontend dashboard
        response = requests.post(
            'http://localhost:5000/api/batch_completed',
            json=batch_data,
            timeout=5
        )
        
        if response.status_code == 200:
            print("✅ Successfully sent CSV data to frontend!")
            print("🌐 Check the dashboard at http://localhost:5000 to see the CSV table")
            return True
        else:
            print(f"❌ Failed to send data. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to frontend dashboard at localhost:5000")
        print("💡 Make sure the frontend dashboard is running first")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_csv_frontend_display()