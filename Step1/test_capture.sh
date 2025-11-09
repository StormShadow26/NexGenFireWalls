#!/bin/bash
# Test script for packet capture tool

echo "=== Packet Capture Tool Test ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo ./test_capture.sh"
    exit 1
fi

# Check if binary exists
if [ ! -f "./capture" ]; then
    echo "ERROR: ./capture binary not found"
    echo "Please compile first: gcc -Wall -Wextra -std=gnu11 capture.c preprocess.c denylist.c rate_limit.c malformed.c malformed_log.c -o capture -lpcap -lpthread"
    exit 1
fi

# Check config files
echo "Checking configuration files..."
if [ ! -f "IP.txt" ]; then
    echo "WARNING: IP.txt not found - no IPs will be blocked"
fi

if [ ! -f "Ports.txt" ]; then
    echo "WARNING: Ports.txt not found - no ports will be blocked"
fi

echo ""
echo "Starting capture for 10 packets..."
echo "Press Ctrl+C to stop early"
echo ""

# Run capture
./capture -n 10

echo ""
echo "=== Capture Complete ==="
echo ""
echo "Output files:"
ls -lh summary_batch_1.csv 2>/dev/null && echo "  ✓ summary_batch_1.csv created"

echo ""
echo "To view summary:"
echo "  cat summary_batch_1.csv"
