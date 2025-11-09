#!/bin/bash
# Quick test script - generates traffic and captures packets

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Quick Packet Capture Test                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    echo "Usage: sudo ./quick_test.sh"
    exit 1
fi

# Clean old CSV
rm -f summary_batch_1.csv

echo "[1/3] Generating network traffic in background..."
# Generate some traffic
(
    for i in {1..20}; do
        ping -c 1 -W 1 127.0.0.1 > /dev/null 2>&1 &
        sleep 0.1
    done
) &

sleep 1

echo "[2/3] Starting packet capture (10 packets)..."
./capture -i lo -n 10

echo ""
echo "[3/3] Results:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "summary_batch_1.csv" ]; then
    echo "✅ CSV Generated: summary_batch_1.csv"
    echo ""
    echo "Contents:"
    cat summary_batch_1.csv
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ SUCCESS! Packet capture is working!"
else
    echo "❌ ERROR: CSV file not created"
fi

echo ""
