#!/bin/bash
# Traffic Generator - Creates real network traffic for testing

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Network Traffic Generator                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "Generating different types of network traffic..."
echo ""

# 1. ICMP Traffic (Ping)
echo "[1/5] Generating ICMP traffic (ping)..."
ping -c 20 8.8.8.8 > /dev/null 2>&1 &
ping -c 20 1.1.1.1 > /dev/null 2>&1 &

# 2. DNS Traffic
echo "[2/5] Generating DNS queries..."
for domain in google.com facebook.com twitter.com github.com stackoverflow.com; do
    nslookup $domain > /dev/null 2>&1 &
done

# 3. HTTP Traffic
echo "[3/5] Generating HTTP traffic..."
curl -s http://example.com > /dev/null 2>&1 &
curl -s http://www.google.com > /dev/null 2>&1 &
curl -s http://httpbin.org/get > /dev/null 2>&1 &

# 4. HTTPS Traffic
echo "[4/5] Generating HTTPS traffic..."
curl -s https://www.google.com > /dev/null 2>&1 &
curl -s https://github.com > /dev/null 2>&1 &
curl -s https://api.github.com > /dev/null 2>&1 &

# 5. Local loopback traffic
echo "[5/5] Generating loopback traffic..."
for i in {1..30}; do
    ping -c 1 127.0.0.1 > /dev/null 2>&1 &
    sleep 0.1
done

echo ""
echo "✅ Traffic generation started!"
echo "   Multiple processes running in background"
echo "   This will generate traffic for ~20-30 seconds"
echo ""
echo "Now run your capture tool in another terminal:"
echo "   sudo ./capture -n 100"
echo ""
