#!/bin/bash
# Complete Test - Generates traffic and captures packets simultaneously

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Complete Packet Capture Test (with real traffic)        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ ERROR: Please run with sudo"
    echo "Usage: sudo ./run_complete_test.sh"
    exit 1
fi

# Clean old files
echo "[Cleanup] Removing old CSV files..."
rm -f summary_batch_1.csv

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 1: Starting Traffic Generation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start traffic generation in background
(
    # Generate various types of traffic
    echo "  → Generating ICMP traffic (ping)..."
    for i in {1..50}; do
        ping -c 1 -W 1 8.8.8.8 > /dev/null 2>&1 &
        ping -c 1 -W 1 127.0.0.1 > /dev/null 2>&1 &
        sleep 0.2
    done
) &

TRAFFIC_PID=$!

# Give traffic generation a head start
sleep 2

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 2: Starting Packet Capture (50 packets)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run capture
./capture -n 50

# Wait for traffic generation to complete
wait $TRAFFIC_PID 2>/dev/null

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 3: Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ -f "summary_batch_1.csv" ]; then
    echo "✅ SUCCESS! CSV file generated"
    echo ""
    
    # Count lines (excluding header)
    LINE_COUNT=$(($(wc -l < summary_batch_1.csv) - 1))
    
    echo "📊 Statistics:"
    echo "   - File: summary_batch_1.csv"
    echo "   - Size: $(du -h summary_batch_1.csv | cut -f1)"
    echo "   - Flows captured: $LINE_COUNT"
    echo ""
    
    echo "📄 First 5 flows:"
    head -6 summary_batch_1.csv | column -t -s,
    
    if [ $LINE_COUNT -gt 5 ]; then
        echo "   ... and $(($LINE_COUNT - 5)) more flows"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  STEP 4: Sending to RL Testing"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Copy CSV to RL_testing directory
    RL_DIR="../RL_testing"
    if [ -d "$RL_DIR" ]; then
        echo "📤 Copying CSV to RL_testing directory..."
        cp summary_batch_1.csv "$RL_DIR/network_traffic_data.csv"
        
        if [ -f "$RL_DIR/network_traffic_data.csv" ]; then
            echo "✅ CSV copied successfully to $RL_DIR/network_traffic_data.csv"
            echo ""
            echo "🧠 Running RL Testing..."
            echo ""
            
            # Run the RL testing script
            cd "$RL_DIR"
            python3 mdp_enhanced_reasoning.py
            
            # Return to Step1 directory
            cd -
            
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "  STEP 5: Cleanup"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            
            # Delete the CSV files after testing
            echo "🧹 Cleaning up temporary CSV files..."
            rm -f summary_batch_1.csv
            rm -f "$RL_DIR/network_traffic_data.csv"
            
            if [ ! -f "summary_batch_1.csv" ] && [ ! -f "$RL_DIR/network_traffic_data.csv" ]; then
                echo "✅ Cleanup completed - CSV files deleted"
            else
                echo "⚠️  Warning: Some files may not have been deleted"
            fi
        else
            echo "❌ Failed to copy CSV to RL_testing"
        fi
    else
        echo "⚠️  RL_testing directory not found at $RL_DIR"
        echo "   CSV file remains at: summary_batch_1.csv"
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ COMPLETE TEST FINISHED!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
else
    echo "❌ ERROR: CSV file was not created"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check if ./capture binary exists"
    echo "  2. Ensure network interfaces are up: ip link"
    echo "  3. Try running on loopback: sudo ./capture -i lo -n 50"
fi
