# 🔥 Firewall AI Project - Quick Start Guide

## One-Command Complete Test

To run the entire firewall project (capture → AI analysis → cleanup):

```bash
sudo ./run_firewall_project.sh
```

That's it! This single command will:

## What It Does

### 1. **Compiles Packet Capture Tool** ⚙️
- Compiles C code if needed
- Includes all filtering modules

### 2. **Generates Network Traffic** 🌐
- Creates test traffic (ICMP pings)
- Runs in background

### 3. **Captures Packets** 📡
- Captures 50 network packets
- Creates CSV with flow statistics

### 4. **Runs AI Analysis** 🤖
- Loads trained DQN models
- Performs MDP-enhanced reasoning
- Analyzes each packet for threats

### 5. **Displays Results** 📊
- Shows predictions (ALLOW/DENY/INSPECT)
- Confidence scores
- Risk assessments

### 6. **Cleans Up** 🧹
- Removes temporary CSV files
- Keeps only final results

## Output

The script displays:
- ✅ Success indicators (green)
- ❌ Error messages (red)
- ⚠️  Warnings (yellow)
- ℹ️  Information (blue/magenta)

## Results Location

Final AI predictions saved to:
```
RL_testing/mdp_enhanced_predictions_*.csv
```

## Requirements

- **Root access**: `sudo` required for packet capture
- **Network interfaces**: At least one active interface
- **Python 3**: For AI/ML testing
- **Trained models**: `.pth` files in `RL_testing/` directory

## Troubleshooting

### "Permission Denied"
```bash
sudo ./run_firewall_project.sh
```

### "No models found"
Ensure `.pth` model files are in `RL_testing/` directory

### "Compilation failed"
Install required libraries:
```bash
sudo apt-get install libpcap-dev gcc make
```

### "Python3 not found"
Install Python:
```bash
sudo apt-get install python3 python3-pip
```

## Manual Steps (if needed)

If you prefer to run components separately:

### 1. Packet Capture Only
```bash
cd Step1
sudo ./run_complete_test.sh
```

### 2. AI Testing Only
```bash
cd RL_testing
python3 mdp_enhanced_reasoning.py
```

### 3. Compilation Only
```bash
cd Step1
make
```

## Project Structure

```
FireWall/
├── run_firewall_project.sh     # 👈 Main script (run this!)
├── Step1/                       # Packet capture & filtering
│   ├── capture.c               # Main capture code
│   ├── Makefile                # Build configuration
│   └── run_complete_test.sh    # Capture-only test
└── RL_testing/                  # AI/ML analysis
    ├── mdp_enhanced_reasoning.py  # Main AI script
    ├── *.pth                    # Trained models
    └── network_traffic_data.csv # Input (auto-created)
```

## What Each Module Does

### Step1 - Packet Capture
- **capture.c**: Captures packets from network interfaces
- **preprocess.c**: Aggregates flow statistics
- **denylist.c**: IP/Port blacklist filtering
- **rate_limit.c**: SYN flood detection
- **malformed.c**: RFC compliance checking

### RL_testing - AI Analysis
- **DQN Models**: Deep Q-Network for decision making
- **MDP Enhancement**: Markov Decision Process reasoning
- **Session Analysis**: Tracks connection patterns
- **Risk Scoring**: Calculates threat levels

## Example Output

```
╔══════════════════════════════════════════════════════════════╗
║     🔥 FIREWALL AI PROJECT - COMPLETE TEST SUITE 🔥        ║
╚══════════════════════════════════════════════════════════════╝

STEP 1: Compiling Packet Capture Tool
✅ Compilation successful!

STEP 2: Cleanup Old Files
✅ Old files cleaned up

STEP 3: Traffic Generation & Packet Capture
✅ Traffic generation started
✅ Captured 50 packets

STEP 4: Verify Capture Results
✅ CSV file generated successfully!
ℹ️  Flows captured: 42

STEP 5: Prepare for RL/AI Testing
✅ CSV copied to RL_testing

STEP 6: Running RL/AI Testing
🤖 DQN PREDICTIONS:
   🟢 ALLOW: 35 (83.3%)
   🔴 DENY: 5 (11.9%)
   🔍 INSPECT: 2 (4.8%)

STEP 7: Results Summary
✅ Enhanced prediction results saved

STEP 8: Cleanup
✅ Temporary files cleaned up

🎉 FIREWALL AI PROJECT TEST COMPLETED! 🎉
```

## Need Help?

Check the detailed documentation:
- `Step1/README.md` - Packet capture details
- `Step1/USAGE_GUIDE.md` - Capture tool usage
- `RL_testing/README.md` - AI/ML details

---

**Ready?** Just run:
```bash
sudo ./run_firewall_project.sh
```

🚀 **Let's secure some networks!**
