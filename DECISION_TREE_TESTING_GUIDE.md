# 🌳 Decision Tree Firewall Testing Guide

## 🚀 Quick Tests

### 1. **Single Batch Test**
```bash
cd /home/aryan/Desktop/FireWall/Step1
sudo /home/aryan/Desktop/FireWall/venv/bin/python enhanced_rl_integration.py --api-mode -n 50 -d 8
```
**Expected Output:**
- ✅ "🌳 Enhanced Decision Tree Predictions: enhanced_dt_predictions_*.csv"
- ✅ File contains DecisionTree_Classifier model predictions
- ✅ High confidence scores (0.9-1.0 typical)

### 2. **Start Complete System**
```bash
# Terminal 1: Start Frontend
cd /home/aryan/Desktop/FireWall/frontend
source ../venv/bin/activate
python3 realtime_dashboard.py --host 0.0.0.0 --port 5000

# Terminal 2: Start Monitor (needs sudo)
cd /home/aryan/Desktop/FireWall/Step1
sudo /home/aryan/Desktop/FireWall/venv/bin/python simplified_continuous_monitor.py
```

### 3. **Check Live Dashboard**
- **URL**: http://localhost:5000
- **Check For**:
  - 🌳 "Decision Tree Predictions" section (not "RL Predictions")
  - Batch counter incrementing every 10 seconds
  - Traffic analysis showing external flows
  - Decision tree confidence scores updating

## 📊 What to Verify

### ✅ **Naming Updates**
- Frontend shows "🌳 Decision Tree Predictions"
- CSV files named `enhanced_dt_predictions_*.csv`
- Logs show "🌳 Processing Decision Tree analysis..."
- Model_Used field shows "DecisionTree_Classifier"

### ✅ **Decision Tree Functionality**
- Model loading from `/RL_testing/DecisionTreeClassifier.pkl`
- Real ML predictions (not mock data)
- Confidence scores from trained model
- Feature engineering for network data

### ✅ **System Integration**
- 10-second batch processing cycles
- HTTP communication between monitor and frontend
- WebSocket streaming to dashboard
- Traffic type classification (EXTERNAL, LOCAL_LOOPBACK, LOCAL_NETWORK)

## 🧪 Advanced Tests

### 4. **Generate External Traffic**
```bash
# Create realistic external traffic to test decision tree
curl -s google.com &
ping -c 3 8.8.8.8 &
dig @1.1.1.1 github.com &
```

### 5. **Check Decision Tree Model**
```bash
cd /home/aryan/Desktop/FireWall/RL_testing
/home/aryan/Desktop/FireWall/venv/bin/python test_decision_tree.py summary_batch_1.csv
```

### 6. **Validate CSV Output**
```bash
cd /home/aryan/Desktop/FireWall/Step1
# Check latest decision tree predictions
ls -la enhanced_dt_predictions_*.csv | tail -1
# View content
tail -5 $(ls enhanced_dt_predictions_*.csv | tail -1)
```

### 7. **Monitor System Performance**
```bash
# Check processes
ps aux | grep -E "(simplified_continuous_monitor|realtime_dashboard)"

# Monitor logs (if created)
tail -f /tmp/firewall_monitor.log

# Check system resources
htop | grep python
```

## 🎯 Expected Results

### **Single Batch Test:**
- **File Generation**: `enhanced_dt_predictions_YYYYMMDD_HHMMSS.csv`
- **Model Type**: Shows "DecisionTree" in CSV
- **Confidence**: Usually 1.0 (100%) from trained model
- **Actions**: Typically shows INSPECT (action 2) for security

### **Live System Test:**
- **Dashboard**: Updates every 10 seconds with new batches
- **Traffic**: Shows external ratio (percentage of external traffic)
- **Predictions**: Decision tree classifications with confidence scores
- **Timeline**: Batch history with completion status

### **Performance Metrics:**
- **Batch Processing**: ~10-15 seconds per cycle (includes capture + analysis)
- **Memory Usage**: ~50-100MB per Python process
- **CPU Usage**: Low (~5-10%) except during batch processing
- **Network**: Real external traffic detection and classification

## 🔧 Troubleshooting

### **Common Issues:**
1. **"No module named 'joblib'"** → Run: `pip install joblib pandas numpy scikit-learn`
2. **"Permission denied for packet capture"** → Use `sudo` for continuous monitor
3. **"DecisionTreeClassifier.pkl not found"** → Check `/RL_testing/` folder has the model
4. **Frontend shows "disconnected"** → Restart both frontend and monitor processes

### **Debug Commands:**
```bash
# Check Python environment
/home/aryan/Desktop/FireWall/venv/bin/python -c "import joblib, pandas, numpy; print('All imports OK')"

# Verify model file exists
ls -la /home/aryan/Desktop/FireWall/RL_testing/DecisionTreeClassifier.pkl

# Test model loading
cd /home/aryan/Desktop/FireWall/RL_testing
/home/aryan/Desktop/FireWall/venv/bin/python -c "import joblib; model = joblib.load('DecisionTreeClassifier.pkl'); print(f'Model loaded: {type(model)}')"
```

## 🏆 Success Criteria

**✅ System is working correctly when:**
1. Frontend shows "Decision Tree Predictions" (not "RL")
2. CSV files are named `enhanced_dt_predictions_*.csv`
3. Model_Used field shows "DecisionTree_Classifier"
4. Confidence scores are realistic (0.7-1.0 range)
5. Batch processing completes every 10 seconds
6. Dashboard updates in real-time
7. External traffic is detected and classified

**🎉 Your Decision Tree Firewall System is Live!** 🌳🛡️