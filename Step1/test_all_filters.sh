#!/bin/bash
# Test script to verify all filters are working

echo "═════════════════════════════════════════════════════════════════"
echo "           PACKET FILTER TEST - All Filters                      "
echo "═════════════════════════════════════════════════════════════════"
echo ""

echo "📋 This will test:"
echo "  1. Normal traffic (should pass)"
echo "  2. Denylist filter (add 8.8.8.8 to IP.txt to test)"
echo "  3. Rate limiter (rapid SYN floods)"
echo "  4. Malformed detection (currently no malformed packets generated)"
echo ""
echo "🚀 How to use:"
echo "  Terminal 1: Run this script"
echo "  Terminal 2: sudo ./capture -n 200"
echo ""

read -p "Press Enter to start generating test traffic..."

echo ""
echo "[1/4] Normal ping traffic..."
ping -c 10 8.8.8.8 &
ping -c 10 127.0.0.1 &
sleep 2

echo "[2/4] Rapid connection attempts (SYN flood simulation)..."
for i in {1..30}; do
    timeout 0.1 telnet 8.8.8.8 80 2>/dev/null &
    sleep 0.05
done
sleep 2

echo "[3/4] Multiple DNS queries..."
for domain in google.com facebook.com github.com twitter.com amazon.com; do
    nslookup $domain > /dev/null 2>&1 &
done
sleep 2

echo "[4/4] Various port connections..."
for port in 80 443 22 23 3306 3389; do
    timeout 0.1 nc -zv 127.0.0.1 $port 2>/dev/null &
done

wait

echo ""
echo "═════════════════════════════════════════════════════════════════"
echo "✅ Test traffic generation completed!"
echo ""
echo "Check capture output for:"
echo "  • [DENYLIST DROP] messages"
echo "  • [RATE-LIMIT DROP] messages (for SYN floods)"
echo "  • [MALFORMED DROP] messages"
echo "  • summary_batch_1.csv with enhanced features"
echo "═════════════════════════════════════════════════════════════════"
