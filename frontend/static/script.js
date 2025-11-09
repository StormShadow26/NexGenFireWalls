// ================================================================
// 🔥 RL Firewall Dashboard - Real-time JavaScript
// ================================================================

// Socket.IO connection
const socket = io();

// State management
let feedPaused = false;
let packetCount = 0;
let lastPacketTime = Date.now();
let packetRate = 0;

// ================================================================
// Initialization
// ================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🔥 Firewall Dashboard Initialized');
    
    // Initialize particle animation
    initParticles();
    
    // Load initial data
    loadStats();
    loadDenylist();
    
    // Start update intervals
    setInterval(updateUptime, 1000);
    setInterval(loadStats, 2000);
    setInterval(calculatePacketRate, 1000);
    
    // Socket event listeners
    setupSocketListeners();
});

// ================================================================
// Socket.IO Event Handlers
// ================================================================

function setupSocketListeners() {
    socket.on('connect', () => {
        console.log('✅ Connected to server');
        updateStatus('online', 'System Online');
        addFeedMessage('System connected successfully', 'success');
    });
    
    socket.on('disconnect', () => {
        console.log('❌ Disconnected from server');
        updateStatus('offline', 'System Offline');
        addFeedMessage('Connection lost', 'error');
    });
    
    socket.on('new_packet', (data) => {
        handleIncomingPacket(data);
    });
    
    socket.on('packet_blocked_denylist', (data) => {
        handleBlockedPacket(data, 'denylist');
    });
    
    socket.on('packet_pass_denylist', (data) => {
        addFeedMessage(`✓ Packet #${data.id} passed denylist check`, 'info');
    });
    
    socket.on('packet_blocked_malformed', (data) => {
        handleBlockedPacket(data, 'malformed');
    });
    
    socket.on('packet_pass_malformed', (data) => {
        addFeedMessage(`✓ Packet #${data.id} passed malformed check`, 'info');
    });
    
    socket.on('packet_blocked_ratelimit', (data) => {
        handleBlockedPacket(data, 'ratelimit');
    });
    
    socket.on('packet_pass_ratelimit', (data) => {
        addFeedMessage(`✓ Packet #${data.id} passed rate limit check`, 'info');
    });
    
    socket.on('packet_to_ml', (data) => {
        handlePacketToML(data);
    });
    
    socket.on('ml_prediction', (data) => {
        handleMLPrediction(data);
    });
}

// ================================================================
// Packet Handlers
// ================================================================

function handleIncomingPacket(packet) {
    // Add to incoming packets list
    const list = document.getElementById('incomingList');
    
    // Remove empty state
    if (list.querySelector('.empty-state')) {
        list.innerHTML = '';
    }
    
    // Create packet element
    const packetEl = createPacketElement(packet, 'incoming');
    list.insertBefore(packetEl, list.firstChild);
    
    // Limit displayed packets
    while (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }
    
    // Update counter
    updateCounter('incomingCounter');
    
    // Add to feed
    addFeedMessage(`📦 Packet #${packet.id} from ${packet.src_ip}:${packet.src_port} → ${packet.dst_ip}:${packet.dst_port}`, 'info');
    
    // Highlight stage
    highlightStage('stage-incoming');
    
    packetCount++;
}

function handleBlockedPacket(packet, stage) {
    // Determine which list to add to
    let listId, counterId, stageName, emoji;
    
    if (stage === 'denylist') {
        listId = 'denylistList';
        counterId = 'denylistCounter';
        stageName = 'denylist';
        emoji = '🚫';
    } else if (stage === 'malformed') {
        listId = 'malformedList';
        counterId = 'malformedCounter';
        stageName = 'malformed filter';
        emoji = '⚠️';
    } else if (stage === 'ratelimit') {
        listId = 'ratelimitList';
        counterId = 'ratelimitCounter';
        stageName = 'rate limiter';
        emoji = '⏱️';
    }
    
    const list = document.getElementById(listId);
    
    if (list.querySelector('.empty-state')) {
        list.innerHTML = '';
    }
    
    const packetEl = createPacketElement(packet, 'blocked');
    list.insertBefore(packetEl, list.firstChild);
    
    while (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }
    
    updateCounter(counterId);
    
    addFeedMessage(`${emoji} Packet #${packet.id} BLOCKED by ${stageName}: ${packet.reason}`, 'blocked');
    
    highlightStage(`stage-${stage}`);
}

function handlePacketToML(packet) {
    addFeedMessage(`🤖 Packet #${packet.id} forwarded to ML model for analysis`, 'info');
}

function handleMLPrediction(packet) {
    // Add to ML predictions list
    const list = document.getElementById('mlList');
    
    if (list.querySelector('.empty-state')) {
        list.innerHTML = '';
    }
    
    const packetEl = createPacketElement(packet, packet.prediction.action.toLowerCase());
    list.insertBefore(packetEl, list.firstChild);
    
    while (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }
    
    updateCounter('mlCounter');
    
    const action = packet.prediction.action;
    const confidence = (packet.prediction.confidence * 100).toFixed(1);
    
    let emoji = '✅';
    let feedClass = 'allowed';
    if (action === 'DENY') {
        emoji = '🚫';
        feedClass = 'blocked';
    } else if (action === 'INSPECT') {
        emoji = '🔍';
        feedClass = 'info';
    }
    
    addFeedMessage(`${emoji} Packet #${packet.id} ${action} (confidence: ${confidence}%)`, feedClass);
    
    highlightStage('stage-ml');
}

// ================================================================
// Packet Element Creation
// ================================================================

function createPacketElement(packet, status) {
    const div = document.createElement('div');
    div.className = 'packet-item';
    
    let statusBadge = '';
    let predictionInfo = '';
    
    if (status === 'blocked') {
        statusBadge = `<span class="packet-status blocked">BLOCKED</span>`;
        predictionInfo = `<div class="packet-detail"><strong>Reason:</strong> ${packet.reason || 'Unknown'}</div>`;
    } else if (packet.prediction) {
        const pred = packet.prediction;
        const confidence = (pred.confidence * 100).toFixed(1);
        statusBadge = `<span class="packet-status ${pred.action.toLowerCase()}">${pred.action}</span>`;
        predictionInfo = `
            <div class="packet-detail"><strong>Risk:</strong> ${(pred.risk_score * 100).toFixed(1)}%</div>
            <div class="packet-detail"><strong>Confidence:</strong> ${confidence}%</div>
        `;
    } else {
        statusBadge = `<span class="packet-status incoming">INCOMING</span>`;
    }
    
    div.innerHTML = `
        <div class="packet-header">
            <span class="packet-id">#${packet.id}</span>
            <span class="packet-time">${packet.timestamp}</span>
        </div>
        <div class="packet-detail"><strong>From:</strong> ${packet.src_ip}:${packet.src_port}</div>
        <div class="packet-detail"><strong>To:</strong> ${packet.dst_ip}:${packet.dst_port}</div>
        <div class="packet-detail"><strong>Protocol:</strong> ${packet.protocol} | <strong>Size:</strong> ${packet.size} bytes</div>
        ${predictionInfo}
        ${statusBadge}
    `;
    
    return div;
}

// ================================================================
// Stats & Counters
// ================================================================

function loadStats() {
    fetch('/api/stats')
        .then(res => res.json())
        .then(stats => {
            document.getElementById('totalPackets').textContent = stats.total_packets;
            document.getElementById('allowedPackets').textContent = stats.allowed;
            document.getElementById('deniedPackets').textContent = stats.denied;
            document.getElementById('inspectedPackets').textContent = stats.inspected;
            document.getElementById('blockedPackets').textContent = stats.blocked_by_denylist;
            document.getElementById('malformedPackets').textContent = stats.blocked_by_malformed;
            document.getElementById('ratelimitPackets').textContent = stats.blocked_by_ratelimit;
            document.getElementById('mlPackets').textContent = stats.sent_to_ml;
            
            // Calculate percentages
            const total = stats.total_packets || 1;
            document.getElementById('allowedPercent').textContent = 
                `${((stats.allowed / total) * 100).toFixed(1)}%`;
            document.getElementById('deniedPercent').textContent = 
                `${((stats.denied / total) * 100).toFixed(1)}%`;
            document.getElementById('inspectedPercent').textContent = 
                `${((stats.inspected / total) * 100).toFixed(1)}%`;
            document.getElementById('blockedPercent').textContent = 
                `${((stats.blocked_by_denylist / total) * 100).toFixed(1)}%`;
            document.getElementById('malformedPercent').textContent = 
                `${((stats.blocked_by_malformed / total) * 100).toFixed(1)}%`;
            document.getElementById('ratelimitPercent').textContent = 
                `${((stats.blocked_by_ratelimit / total) * 100).toFixed(1)}%`;
            document.getElementById('mlPercent').textContent = 
                `${((stats.sent_to_ml / total) * 100).toFixed(1)}%`;
        })
        .catch(err => console.error('Error loading stats:', err));
}

function updateCounter(counterId) {
    const counter = document.getElementById(counterId);
    const current = parseInt(counter.textContent) || 0;
    counter.textContent = current + 1;
    
    // Animation
    counter.style.transform = 'scale(1.2)';
    setTimeout(() => {
        counter.style.transform = 'scale(1)';
    }, 200);
}

function calculatePacketRate() {
    const now = Date.now();
    const elapsed = (now - lastPacketTime) / 1000;
    
    if (elapsed > 0) {
        packetRate = packetCount / elapsed;
    }
    
    document.getElementById('packetRate').textContent = 
        `${packetRate.toFixed(1)} packets/sec`;
}

// ================================================================
// Denylist
// ================================================================

function loadDenylist() {
    fetch('/api/denylist')
        .then(res => res.json())
        .then(data => {
            // IPs
            const ipList = document.getElementById('deniedIpList');
            document.getElementById('deniedIpCount').textContent = data.ips.length;
            
            if (data.ips.length === 0) {
                ipList.innerHTML = '<div class="empty-state">No blocked IPs</div>';
            } else {
                ipList.innerHTML = data.ips
                    .map(ip => `<span class="denylist-item">${ip}</span>`)
                    .join('');
            }
            
            // Ports
            const portList = document.getElementById('deniedPortList');
            document.getElementById('deniedPortCount').textContent = data.ports.length;
            
            if (data.ports.length === 0) {
                portList.innerHTML = '<div class="empty-state">No blocked ports</div>';
            } else {
                portList.innerHTML = data.ports
                    .map(port => `<span class="denylist-item">${port}</span>`)
                    .join('');
            }
        })
        .catch(err => console.error('Error loading denylist:', err));
}

// ================================================================
// Control Functions
// ================================================================

function startCapture() {
    fetch('/api/start_capture', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log('Capture started:', data);
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            updateStatus('active', 'Capturing Packets');
            addFeedMessage('🚀 Packet capture started', 'success');
            lastPacketTime = Date.now();
            packetCount = 0;
        })
        .catch(err => {
            console.error('Error starting capture:', err);
            addFeedMessage('❌ Failed to start capture', 'error');
        });
}

function stopCapture() {
    fetch('/api/stop_capture', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log('Capture stopped:', data);
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            updateStatus('idle', 'System Idle');
            addFeedMessage('⏸️ Packet capture stopped', 'info');
        })
        .catch(err => console.error('Error stopping capture:', err));
}

function resetStats() {
    if (confirm('Reset all statistics and clear buffers?')) {
        fetch('/api/reset', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                console.log('Stats reset:', data);
                
                // Clear all lists
                document.getElementById('incomingList').innerHTML = '<div class="empty-state">Waiting for packets...</div>';
                document.getElementById('denylistList').innerHTML = '<div class="empty-state">No blocked packets</div>';
                document.getElementById('malformedList').innerHTML = '<div class="empty-state">No malformed packets</div>';
                document.getElementById('ratelimitList').innerHTML = '<div class="empty-state">No rate limit violations</div>';
                document.getElementById('mlList').innerHTML = '<div class="empty-state">Awaiting analysis...</div>';
                
                // Reset counters
                document.getElementById('incomingCounter').textContent = '0';
                document.getElementById('denylistCounter').textContent = '0';
                document.getElementById('malformedCounter').textContent = '0';
                document.getElementById('ratelimitCounter').textContent = '0';
                document.getElementById('mlCounter').textContent = '0';
                
                // Clear feed
                const feed = document.getElementById('liveFeed');
                feed.innerHTML = '<div class="feed-item welcome"><span class="feed-time">--:--:--</span><span class="feed-message">🔥 Dashboard reset - Ready to go</span></div>';
                
                packetCount = 0;
                lastPacketTime = Date.now();
                
                loadStats();
            })
            .catch(err => console.error('Error resetting:', err));
    }
}

// ================================================================
// UI Updates
// ================================================================

function updateStatus(status, text) {
    const statusDot = document.getElementById('systemStatus');
    const statusText = document.getElementById('statusText');
    
    statusDot.className = 'status-dot pulsing';
    
    if (status === 'online' || status === 'active') {
        statusDot.style.background = 'var(--success)';
    } else if (status === 'idle') {
        statusDot.style.background = 'var(--warning)';
    } else {
        statusDot.style.background = 'var(--danger)';
    }
    
    statusText.textContent = text;
}

function updateUptime() {
    const uptimeEl = document.getElementById('uptime');
    const current = uptimeEl.textContent.split(':');
    let hours = parseInt(current[0]) || 0;
    let minutes = parseInt(current[1]) || 0;
    let seconds = parseInt(current[2]) || 0;
    
    seconds++;
    if (seconds >= 60) {
        seconds = 0;
        minutes++;
    }
    if (minutes >= 60) {
        minutes = 0;
        hours++;
    }
    
    uptimeEl.textContent = 
        `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function highlightStage(stageId) {
    const stage = document.getElementById(stageId);
    stage.style.borderColor = 'var(--primary)';
    stage.style.boxShadow = 'var(--glow)';
    
    setTimeout(() => {
        stage.style.borderColor = 'var(--border-color)';
        stage.style.boxShadow = 'none';
    }, 500);
}

function addFeedMessage(message, type = 'info') {
    if (feedPaused) return;
    
    const feed = document.getElementById('liveFeed');
    const time = new Date().toLocaleTimeString('en-US', { hour12: false });
    
    const item = document.createElement('div');
    item.className = `feed-item ${type}`;
    item.innerHTML = `
        <span class="feed-time">${time}</span>
        <span class="feed-message">${message}</span>
    `;
    
    feed.insertBefore(item, feed.firstChild);
    
    // Limit feed items
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
}

function toggleFeed() {
    feedPaused = !feedPaused;
    const toggleText = document.getElementById('feedToggleText');
    toggleText.textContent = feedPaused ? 'Resume' : 'Pause';
}

// ================================================================
// Particle Animation
// ================================================================

function initParticles() {
    const canvas = document.getElementById('particleCanvas');
    const ctx = canvas.getContext('2d');
    
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    const particleCount = 50;
    
    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.vx = (Math.random() - 0.5) * 0.5;
            this.vy = (Math.random() - 0.5) * 0.5;
            this.radius = Math.random() * 2 + 1;
        }
        
        update() {
            this.x += this.vx;
            this.y += this.vy;
            
            if (this.x < 0 || this.x > canvas.width) this.vx *= -1;
            if (this.y < 0 || this.y > canvas.height) this.vy *= -1;
        }
        
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 217, 255, 0.5)';
            ctx.fill();
        }
    }
    
    // Create particles
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }
    
    // Animation loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        
        // Draw connections
        particles.forEach((p1, i) => {
            particles.slice(i + 1).forEach(p2 => {
                const dx = p1.x - p2.x;
                const dy = p1.y - p2.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 150) {
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(0, 217, 255, ${1 - distance / 150})`;
                    ctx.lineWidth = 0.5;
                    ctx.moveTo(p1.x, p1.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.stroke();
                }
            });
        });
        
        requestAnimationFrame(animate);
    }
    
    animate();
    
    // Handle resize
    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });
}

// ================================================================
// Keyboard Shortcuts
// ================================================================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S: Start
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        if (!document.getElementById('startBtn').disabled) {
            startCapture();
        }
    }
    
    // Ctrl/Cmd + P: Stop (Pause)
    if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
        e.preventDefault();
        if (!document.getElementById('stopBtn').disabled) {
            stopCapture();
        }
    }
    
    // Ctrl/Cmd + R: Reset (prevent default browser refresh)
    if ((e.ctrlKey || e.metaKey) && e.key === 'r' && e.shiftKey) {
        e.preventDefault();
        resetStats();
    }
});

console.log('🔥 Firewall Dashboard loaded successfully!');
console.log('💡 Keyboard shortcuts: Ctrl+S (Start) | Ctrl+P (Stop) | Ctrl+Shift+R (Reset)');
