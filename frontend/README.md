# 🔥 RL-Based Firewall Dashboard

A stunning, real-time web dashboard for monitoring your self-learning RL-based firewall. Watch packets flow through the system, see denylist filtering in action, and observe ML predictions in real-time!

## ✨ Features

### 🎨 Visual Design
- **Cyberpunk Tech Aesthetic** with animated backgrounds
- **Particle Animation** system for immersive experience
- **Gradient Effects** and glowing elements
- **Smooth Animations** for all state transitions
- **Responsive Design** works on all screen sizes

### 📊 Real-time Monitoring
- **Live Packet Flow** visualization through 3 stages:
  1. **Incoming Packets** - All captured network traffic
  2. **Denylist Filter** - Shows blocked malicious IPs/ports
  3. **ML Model** - AI predictions (ALLOW/DENY/INSPECT)
  
- **Interactive Stats Cards** showing:
  - Total packets processed
  - Allowed packets (with percentage)
  - Denied packets (with percentage)
  - Inspected packets (with percentage)
  - Blocked by denylist
  - ML analyzed packets

- **Live Activity Feed** with color-coded messages
- **Packet Rate** display (packets/second)
- **Uptime Counter** showing system runtime

### 🤖 AI Integration
- Real-time ML model predictions
- Risk score visualization
- Confidence levels for each decision
- Action recommendations (ALLOW/DENY/INSPECT)

### 🛡️ Denylist Monitoring
- Display of all blocked IPs
- Display of all blocked ports
- Live blocking events
- Reason tracking for blocks

### 🎮 Interactive Controls
- **START** - Begin packet capture
- **STOP** - Pause packet capture
- **RESET** - Clear all stats and buffers

### ⌨️ Keyboard Shortcuts
- `Ctrl+S` - Start capture
- `Ctrl+P` - Stop capture
- `Ctrl+Shift+R` - Reset stats

## 🚀 Quick Start

### Method 1: One-Command Launch (Recommended)

```bash
cd /home/aryan/Desktop/FireWall/frontend
./start_dashboard.sh
```

This script will:
- Create a virtual environment
- Install all dependencies
- Launch the dashboard
- Open at http://localhost:5000

### Method 2: Manual Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Launch Dashboard**
   ```bash
   python3 app.py
   ```

3. **Open Browser**
   Navigate to: http://localhost:5000

## 📁 Project Structure

```
frontend/
├── app.py                    # Flask backend with Socket.IO
├── start_dashboard.sh        # Launcher script
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Main dashboard HTML
└── static/
    ├── style.css            # Cyberpunk styling + animations
    └── script.js            # Real-time updates + Socket.IO
```

## 🔄 How It Works

### Packet Flow Pipeline

```
1. Network Traffic
   ↓
2. Capture.c (C Program)
   ↓
3. Incoming Buffer (Dashboard)
   ↓
4. Denylist Check
   ├─→ BLOCKED (if in denylist) → Stop
   └─→ PASS (if clean) → Continue
       ↓
5. ML Model Analysis
   ├─→ ALLOW (safe traffic)
   ├─→ DENY (malicious traffic)
   └─→ INSPECT (suspicious traffic)
```

### Backend Architecture

- **Flask** - Web server framework
- **Socket.IO** - Real-time bidirectional communication
- **Threading** - Concurrent packet processing
- **REST API** - Stats and control endpoints

### Frontend Architecture

- **HTML5 Canvas** - Particle animation system
- **CSS Animations** - Smooth transitions and effects
- **WebSocket** - Real-time packet updates
- **Vanilla JavaScript** - No heavy frameworks, pure performance

## 🎯 Dashboard Sections

### 1. Header
- Logo and branding
- System status indicator
- Uptime display
- Control buttons

### 2. Stats Overview
Six stat cards showing real-time metrics with percentages

### 3. Pipeline Visualization
Three-stage packet processing flow with live counters:
- Stage 1: Incoming packets
- Stage 2: Denylist filter
- Stage 3: ML model analysis

### 4. Live Activity Feed
Scrollable feed of all events with timestamps

### 5. Denylist Configuration
Shows currently blocked IPs and ports

### 6. Footer
System information and packet rate

## 🔧 Configuration

### Denylist Files

The dashboard reads from:
- `../Step1/IP.txt` - Blocked IP addresses
- `../Step1/Ports.txt` - Blocked ports

### ML Model

The backend can integrate with your trained models:
- Place `.pth` files in `../RL_testing/`
- Models are loaded automatically
- Predictions shown in real-time

## 🎨 Customization

### Colors (Edit `static/style.css`)

```css
:root {
    --primary: #00d9ff;      /* Cyan */
    --secondary: #ff006e;    /* Pink */
    --success: #00ff88;      /* Green */
    --warning: #ffaa00;      /* Orange */
    --danger: #ff3366;       /* Red */
}
```

### Packet Display Limit

Edit in `static/script.js`:
```javascript
// Limit displayed packets (currently 10)
while (list.children.length > 10) {
    list.removeChild(list.lastChild);
}
```

## 📊 API Endpoints

### GET Endpoints
- `/` - Dashboard homepage
- `/api/stats` - Current statistics
- `/api/denylist` - Denylist configuration
- `/api/recent_packets` - Recent packet history

### POST Endpoints
- `/api/start_capture` - Start packet capture
- `/api/stop_capture` - Stop packet capture
- `/api/reset` - Reset all statistics

### Socket.IO Events

**Client → Server:**
- `connect` - Client connected
- `disconnect` - Client disconnected

**Server → Client:**
- `new_packet` - New packet captured
- `packet_blocked` - Packet blocked by denylist
- `packet_to_ml` - Packet sent to ML model
- `ml_prediction` - ML model decision

## 🐛 Troubleshooting

### Port 5000 Already in Use
```bash
# Find and kill the process
sudo lsof -i :5000
sudo kill -9 <PID>

# Or use a different port in app.py
socketio.run(app, port=5001)
```

### Dependencies Won't Install
```bash
# Update pip
pip install --upgrade pip

# Install system dependencies
sudo apt-get install python3-dev

# Try installing packages individually
pip install flask flask-socketio python-socketio
```

### No Packets Showing
1. Check if capture is running in Step1
2. Verify CSV file exists: `../Step1/summary_batch_1.csv`
3. Check denylist files exist: `IP.txt` and `Ports.txt`
4. Look at browser console (F12) for errors

### Socket.IO Connection Failed
- Ensure Flask server is running
- Check firewall allows port 5000
- Try accessing via `127.0.0.1:5000` instead of `localhost`

## 🚀 Performance

- **Lightweight**: Pure vanilla JS, no heavy frameworks
- **Real-time**: Socket.IO for instant updates
- **Efficient**: Canvas-based particle system
- **Smooth**: CSS animations with GPU acceleration
- **Scalable**: Handles 100+ packets/second easily

## 🎓 Learning Resources

- **Flask**: https://flask.palletsprojects.com/
- **Socket.IO**: https://socket.io/docs/
- **CSS Animations**: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Animations
- **Canvas API**: https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API

## 📝 Future Enhancements

- [ ] Historical data charts (Chart.js)
- [ ] Export statistics to CSV/JSON
- [ ] Custom alert thresholds
- [ ] Dark/Light theme toggle
- [ ] Multi-user support with authentication
- [ ] Mobile app version
- [ ] Real-time model training visualization
- [ ] Network topology map

## 🤝 Integration

This dashboard integrates with:
- **Step1/capture.c** - Packet capture module
- **Step1/denylist.c** - IP/Port filtering
- **RL_testing/mdp_enhanced_reasoning.py** - ML predictions

## 📄 License

Part of the RL-Based Firewall project.

---

## 🎉 Ready to Roll!

Start the dashboard and watch your firewall in action:

```bash
./start_dashboard.sh
```

Then open your browser to **http://localhost:5000** and enjoy the show! 🔥

---

**Made with 🔥 and ❤️ for network security**
