#!/bin/bash
# Demonstration script showing all filter statistics with emoji indicators

echo "=========================================="
echo "🔍 PACKET CAPTURE STATISTICS DEMO"
echo "=========================================="
echo ""
echo "This demo will:"
echo "  ✓ Capture packets on all interfaces"
echo "  ✓ Show real-time drop messages with emoji indicators:"
echo "    🚫 DENYLIST - Blocked IPs/Ports"
echo "    ⚡ RATE-LIMIT - SYN flood prevention"
echo "    ❌ MALFORMED - RFC compliance issues"
echo "  ✓ Display comprehensive statistics at the end"
echo ""

# Generate traffic in background to trigger filters
generate_traffic() {
    sleep 2
    echo "📡 Generating test traffic..."
    
    # Normal traffic
    ping -c 3 8.8.8.8 >/dev/null 2>&1 &
    
    # Try to hit denylist (192.168.1.100 is in IP.txt)
    ping -c 5 192.168.1.100 >/dev/null 2>&1 &
    
    # Try rate limiting with fast pings
    for i in {1..20}; do
        ping -c 1 -W 0.1 127.0.0.1 >/dev/null 2>&1 &
    done
    
    # Generate some TCP traffic
    curl -s --max-time 2 http://example.com >/dev/null 2>&1 &
    
    echo "✅ Traffic generation started"
}

# Start traffic generator in background
generate_traffic &

echo "🚀 Starting packet capture (15 seconds)..."
echo "=========================================="
echo ""

# Run capture with 15 second timeout
timeout 15 sudo ./capture 100 || true

echo ""
echo "=========================================="
echo "✅ Demo complete!"
echo "=========================================="
echo ""
echo "📄 Check summary_batch_1.csv for detailed packet statistics"
echo "   (23 features for ML/DDoS detection)"
