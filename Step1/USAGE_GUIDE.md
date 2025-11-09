# HOW TO RUN - Packet Capture Tool

## 🚀 Quick Start (Easiest Method)

### Option 1: Complete Automated Test
```bash
sudo ./run_complete_test.sh
```
**What it does:**
- Automatically generates network traffic
- Captures 50 packets
- Shows results with statistics
- Creates `summary_batch_1.csv`

---

## 📖 Detailed Usage Guide

### Method 1: Two Terminal Method (Recommended for learning)

**Terminal 1** - Generate Traffic:
```bash
./generate_traffic.sh
```

**Terminal 2** - Capture Packets:
```bash
sudo ./capture -n 50
```

This gives you full visibility of both processes.

---

### Method 2: Capture with Real Internet Traffic

**Start capture first:**
```bash
sudo ./capture -n 100
```

**Then in another terminal, generate traffic:**
```bash
# Web browsing
curl https://www.google.com
curl https://github.com
curl https://api.github.com

# DNS queries
nslookup google.com
nslookup facebook.com

# Ping
ping -c 10 8.8.8.8
```

The capture will automatically stop after 100 packets.

---

### Method 3: Capture from Specific Interface

**Find your interfaces:**
```bash
ip link show
```

**Capture from specific interface:**
```bash
# Ethernet
sudo ./capture -i eth0 -n 50

# WiFi
sudo ./capture -i wlan0 -n 50

# Loopback (always has traffic)
sudo ./capture -i lo -n 50
```

---

### Method 4: Capture While Using Internet

1. **Start capture:**
```bash
sudo ./capture -n 100 &
```

2. **Use internet normally:**
   - Open browser and visit websites
   - Download a file: `wget http://example.com`
   - Stream video or music
   - Use any online application

3. **Wait for completion** - It will auto-stop after 100 packets

---

## 🎯 How to Generate Real Traffic

### Quick Traffic Generation

**Simple ping test:**
```bash
ping -c 20 8.8.8.8
```

**Web requests:**
```bash
curl http://example.com
curl https://www.google.com
wget http://httpbin.org/get
```

**DNS lookups:**
```bash
nslookup google.com
nslookup github.com
dig facebook.com
```

**Multiple connections:**
```bash
for i in {1..20}; do curl -s http://example.com > /dev/null & done
```

---

### Continuous Traffic (for testing)

**Keep generating traffic:**
```bash
while true; do 
    ping -c 5 8.8.8.8
    curl -s https://www.google.com > /dev/null
    sleep 2
done
```

Stop with `Ctrl+C` when done.

---

## 📊 Understanding the Output

### Console Output
You'll see:
- Number of interfaces being monitored
- Packet limit setting
- Any dropped packets (denylist, rate-limit, malformed)
- Final statistics

Example:
```
Starting capture on 7 interface(s). Packet limit=50
[DENYLIST DROP] ... (if any blocked IPs/ports detected)
[RATE-LIMIT DROP] ... (if SYN flood detected)
[MALFORMED DROP] ... (if invalid packets found)
Finished capture. Processed packets: 50
```

### CSV Output (summary_batch_1.csv)
Contains per-flow statistics:
```csv
src_ip,dst_ip,src_port,dst_port,protocol,bytes_sent,bytes_received,pkts_sent,pkts_received,elapsed_seconds
192.168.1.10,8.8.8.8,54321,443,TCP,1500,3000,10,15,2.456789
```

**To view nicely formatted:**
```bash
column -t -s, < summary_batch_1.csv
```

---

## ⚙️ Command Line Options

```bash
sudo ./capture [OPTIONS]

Options:
  -i <interface>   Capture from specific interface (e.g., eth0, lo)
  -n <number>      Number of packets to capture (default: 50)
  -h               Show help message

Examples:
  sudo ./capture                    # Capture 50 packets from all interfaces
  sudo ./capture -n 100             # Capture 100 packets
  sudo ./capture -i eth0 -n 200     # Capture 200 packets from eth0
  sudo ./capture -i lo -n 10        # Quick test on loopback
```

---

## 🧪 Testing Scenarios

### Test 1: Basic Functionality
```bash
sudo ./run_complete_test.sh
```

### Test 2: Denylist Testing
1. Add IPs to `IP.txt`:
```bash
echo "8.8.8.8" >> IP.txt
```

2. Run capture while pinging that IP:
```bash
ping -c 10 8.8.8.8 &
sudo ./capture -n 20
```

You should see `[DENYLIST DROP]` messages.

### Test 3: High Traffic
```bash
# Generate lots of traffic
./generate_traffic.sh &

# Capture more packets
sudo ./capture -n 500
```

### Test 4: Specific Protocol
```bash
# Only capture while doing HTTP
curl http://example.com &
sudo ./capture -i lo -n 10
```

---

## 🐛 Troubleshooting

### Problem: "No packets captured"
**Solution:**
- Generate traffic: `ping -c 10 8.8.8.8`
- Or use loopback: `sudo ./capture -i lo -n 10`
- Make sure you're connected to internet

### Problem: "Permission denied"
**Solution:**
```bash
sudo ./capture -n 50
```

### Problem: "CSV file empty"
**Solution:**
- Code might still be running, wait for completion
- Make sure packets reached the limit or press Ctrl+C
- Check: `ls -lh summary_batch_1.csv`

### Problem: "Code hangs"
**Solution:**
- Press `Ctrl+C` to stop
- This is normal if there's no traffic
- Generate traffic in another terminal

---

## 💡 Pro Tips

1. **Monitor live:** Use `tail -f` to watch drops in real-time:
```bash
sudo ./capture -n 1000 2>&1 | tee capture.log
```

2. **Analyze CSV in Excel/LibreOffice:**
   - The CSV can be opened directly in spreadsheet software

3. **Filter by protocol:**
```bash
grep "TCP" summary_batch_1.csv
grep "UDP" summary_batch_1.csv
grep "ICMP" summary_batch_1.csv
```

4. **Count flows by protocol:**
```bash
tail -n +2 summary_batch_1.csv | cut -d, -f5 | sort | uniq -c
```

5. **Find top talkers (by bytes):**
```bash
tail -n +2 summary_batch_1.csv | sort -t, -k6 -nr | head -5
```

---

## 🎓 Example Session

```bash
# Terminal 1: Start traffic generation
./generate_traffic.sh

# Terminal 2: Capture packets
sudo ./capture -n 100

# View results
cat summary_batch_1.csv

# Or view formatted
column -t -s, < summary_batch_1.csv

# Check statistics
wc -l summary_batch_1.csv  # Count flows
```

---

## 📁 Files Created

- `summary_batch_1.csv` - Main output (traffic statistics)
- Console output - Real-time drop notifications

That's it! Your packet capture tool is ready to use! 🎉
