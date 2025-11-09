#!/usr/bin/env python3
"""
Test script to verify packet filtering and detection
Generates various types of legitimate test traffic
"""

import socket
import time
import sys

def test_normal_traffic():
    """Generate normal traffic"""
    print("[TEST 1] Generating normal traffic...")
    try:
        # Normal DNS query
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(b'test', ('8.8.8.8', 53))
        s.close()
        print("  ✓ Normal UDP traffic sent")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def test_ping_flood():
    """Simulate high-rate ping (not malicious, just high volume)"""
    print("\n[TEST 2] Generating rapid ICMP traffic (ping flood simulation)...")
    import subprocess
    try:
        # Send 50 pings rapidly
        subprocess.run(['ping', '-c', '50', '-i', '0.01', '8.8.8.8'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL,
                      timeout=5)
        print("  ✓ Rapid ICMP traffic generated")
    except Exception as e:
        print(f"  ✗ Error: {e}")

def test_syn_pattern():
    """Generate SYN-like connection attempts (rate limit test)"""
    print("\n[TEST 3] Generating rapid connection attempts (SYN rate test)...")
    for i in range(20):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            try:
                s.connect(('8.8.8.8', 80))
            except:
                pass
            s.close()
            time.sleep(0.05)  # 20 connections per second
        except:
            pass
    print("  ✓ Rapid connection attempts generated")

def test_denylist():
    """Test denylist filtering"""
    print("\n[TEST 4] Testing denylist (configure IP.txt first)...")
    print("  ℹ  To test: Add '8.8.8.8' to IP.txt, then run capture")
    print("  ℹ  You should see [DENYLIST DROP] messages")

def test_different_ports():
    """Generate traffic to various ports"""
    print("\n[TEST 5] Generating traffic to various ports...")
    ports = [80, 443, 22, 23, 3389, 3306, 1433]
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            try:
                s.connect(('127.0.0.1', port))
            except:
                pass
            s.close()
        except:
            pass
    print("  ✓ Multi-port traffic generated")

def main():
    print("═" * 70)
    print("  Packet Filter Testing Script")
    print("  Testing: Denylist, Rate Limit, Malformed Detection")
    print("═" * 70)
    
    print("\n📌 INSTRUCTIONS:")
    print("  1. Run this script in one terminal")
    print("  2. Run 'sudo ./capture -n 100' in another terminal")
    print("  3. Watch for drop messages in the capture output")
    print("\n")
    
    input("Press Enter to start generating test traffic...")
    
    test_normal_traffic()
    time.sleep(1)
    
    test_syn_pattern()
    time.sleep(1)
    
    test_ping_flood()
    time.sleep(1)
    
    test_different_ports()
    
    test_denylist()
    
    print("\n" + "═" * 70)
    print("✅ Test traffic generation completed!")
    print("\nCheck your capture output for:")
    print("  • [DENYLIST DROP] - if IPs/ports are in denylist")
    print("  • [RATE-LIMIT DROP] - for rapid SYN packets")
    print("  • [MALFORMED DROP] - for invalid packets")
    print("  • CSV file with all captured traffic statistics")
    print("═" * 70)

if __name__ == "__main__":
    main()
