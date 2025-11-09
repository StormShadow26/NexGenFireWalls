import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import os
import glob
from datetime import datetime
import matplotlib.pyplot as plt
from collections import defaultdict, deque
from typing import Tuple, Dict, List

# Set device for GPU acceleration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Using device: {device}")

class RegularizedDQN(nn.Module):
    def __init__(self, state_size, action_size, dropout_rate=0.3):
        super(RegularizedDQN, self).__init__()
        self.fc1 = nn.Linear(state_size, 128)
        self.dropout1 = nn.Dropout(dropout_rate)
        self.fc2 = nn.Linear(128, 64)
        self.dropout2 = nn.Dropout(dropout_rate) 
        self.fc3 = nn.Linear(64, 32)
        self.fc4 = nn.Linear(32, action_size)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        x = F.relu(self.fc3(x))
        return self.fc4(x)

class MDPFirewallReasoning:
    """
    Enhanced decision reasoning using Markov Decision Process
    Considers sequential states and transitions for better firewall decisions
    """
    
    def __init__(self, history_length=10, learning_rate=0.1, discount_factor=0.9):
        self.history_length = history_length
        self.learning_rate = learning_rate  # α
        self.discount_factor = discount_factor  # γ
        
        # State tracking
        self.session_history = defaultdict(lambda: deque(maxlen=history_length))
        self.state_transitions = defaultdict(lambda: defaultdict(int))
        self.state_rewards = defaultdict(lambda: defaultdict(float))
        self.action_values = defaultdict(lambda: defaultdict(float))
        
        # Reward structure for different outcomes
        self.rewards = {
            'ALLOW': {'correct_allow': 1.0, 'false_negative': -5.0},
            'DENY': {'correct_deny': 2.0, 'false_positive': -1.0},
            'INSPECT': {'detailed_analysis': 0.5, 'resolved_threat': 3.0, 'wasted_resources': -0.5}
        }
    
    def discretize_state(self, continuous_state: np.array, session_id: str = None) -> Tuple[int, int, int, int, int]:
        """Convert continuous 12-feature state to discrete MDP state"""
        src_port_type, dest_port_type, protocol_type, bytes_sent, bytes_received, \
        pkts_sent, pkts_received, duration, time_of_day, hist_success, geo_risk, service_freq = continuous_state
        
        # 1. Risk Level (based on geographic risk and historical success)
        risk_score = geo_risk - hist_success + 0.5
        if risk_score < 0.2:
            risk_level = 0  # Low risk
        elif risk_score < 0.7:
            risk_level = 1  # Medium risk
        else:
            risk_level = 2  # High risk
        
        # 2. Port Pattern Analysis
        port_pattern = self._analyze_port_pattern(src_port_type, dest_port_type, protocol_type)
        
        # 3. Traffic Volume Analysis
        traffic_volume = self._analyze_traffic_volume(bytes_sent, bytes_received, pkts_sent, pkts_received)
        
        # 4. Protocol Anomaly
        protocol_anom = self._analyze_protocol_anomaly(protocol_type, dest_port_type, duration)
        
        # 5. Time Context
        time_context = self._analyze_time_context(time_of_day)
        
        return (risk_level, port_pattern, traffic_volume, protocol_anom, time_context)
    
    def _analyze_port_pattern(self, src_type: int, dest_type: int, protocol: int) -> int:
        """Analyze port usage patterns for anomalies"""
        if (src_type == 2 and dest_type == 0 and protocol == 0):  # Client to server TCP
            return 0  # Normal
        elif (src_type == 0 and dest_type == 0):  # Server to server
            return 1  # Suspicious - needs verification
        elif (src_type == 0 and dest_type == 2):  # Server to client on high port
            return 2  # Potentially malicious - reverse shell pattern
        else:
            return 1  # Unusual pattern
    
    def _analyze_traffic_volume(self, bytes_sent: float, bytes_received: float, 
                               pkts_sent: float, pkts_received: float) -> int:
        """Analyze traffic volume for anomalies"""
        total_bytes = bytes_sent + bytes_received
        total_pkts = pkts_sent + pkts_received
        
        if total_pkts > 0:
            bpp_ratio = total_bytes / total_pkts
        else:
            bpp_ratio = 0
        
        if total_bytes < 1000 and total_pkts < 10:
            return 0  # Low volume
        elif total_bytes < 100000 and bpp_ratio < 1500:
            return 1  # Normal volume
        else:
            return 2  # High volume or large packets
    
    def _analyze_protocol_anomaly(self, protocol: int, dest_port: int, duration: float) -> int:
        """Detect protocol-specific anomalies"""
        if protocol == 0:  # TCP
            if duration < 0.001:
                return 2  # Anomalous - port scan pattern
            elif duration > 0.5:
                return 0  # Normal
            else:
                return 1  # Unusual but not clearly malicious
        elif protocol == 1:  # UDP
            if dest_port == 53:  # DNS
                return 0  # Normal
            else:
                return 1  # Unusual UDP traffic
        elif protocol == 2:  # ICMP
            return 1  # Always inspect ICMP
        
        return 1  # Default to unusual
    
    def _analyze_time_context(self, time_of_day: float) -> int:
        """Analyze temporal context"""
        if 0.25 <= time_of_day <= 0.75:  # 6 AM to 6 PM
            return 0  # Business hours
        elif 0.75 < time_of_day <= 1.0 or 0.0 <= time_of_day < 0.25:  # 6 PM to 6 AM
            return 1  # After hours
        else:
            return 2  # Weekend/holiday
    
    def get_mdp_recommendation(self, current_state: Tuple, session_id: str, 
                              dqn_prediction: int, q_values: np.array) -> Dict:
        """Get MDP-enhanced recommendation considering state transitions"""
        history = self.session_history[session_id]
        
        # Calculate expected future rewards for each action
        action_expectations = {}
        for action in [0, 1, 2]:  # ALLOW, DENY, INSPECT
            expected_reward = self._calculate_expected_reward(current_state, action, q_values)
            action_expectations[action] = expected_reward
        
        # Get MDP optimal action
        mdp_optimal_action = max(action_expectations.items(), key=lambda x: x[1])[0]
        
        # Compare with DQN prediction
        agreement = (mdp_optimal_action == dqn_prediction)
        confidence_adjustment = self._calculate_confidence_adjustment(agreement, action_expectations)
        
        # Generate reasoning
        reasoning = self._generate_mdp_reasoning(current_state, history, action_expectations, mdp_optimal_action)
        
        return {
            'mdp_recommendation': mdp_optimal_action,
            'dqn_prediction': dqn_prediction,
            'agreement': agreement,
            'confidence_adjustment': confidence_adjustment,
            'expected_rewards': action_expectations,
            'reasoning': reasoning,
            'state_context': self._describe_state(current_state),
            'historical_pattern': self._analyze_historical_pattern(history)
        }
    
    def _calculate_expected_reward(self, state: Tuple, action: int, q_values: np.array) -> float:
        """Calculate expected future reward for taking an action"""
        immediate_reward = q_values[action]  # Q-value as immediate reward proxy
        
        risk_level, port_pattern, traffic_volume, protocol_anom, time_context = state
        future_reward = 0.0
        
        if action == 0:  # ALLOW
            if risk_level == 2 or port_pattern == 2:  # High risk
                future_reward -= 3.0  # Penalty for allowing risky traffic
            elif risk_level == 0 and port_pattern == 0:  # Low risk, normal pattern
                future_reward += 1.0  # Reward for allowing safe traffic
        elif action == 1:  # DENY
            if risk_level == 2 or port_pattern == 2:  # High risk
                future_reward += 2.0  # Reward for blocking risky traffic
            elif risk_level == 0 and port_pattern == 0:  # Low risk
                future_reward -= 1.0  # Penalty for blocking safe traffic
        elif action == 2:  # INSPECT
            if risk_level == 1 or port_pattern == 1:  # Medium risk/suspicious
                future_reward += 0.5  # Reward for appropriate inspection
            else:
                future_reward -= 0.2  # Small penalty for unnecessary inspection
        
        return immediate_reward + self.discount_factor * future_reward
    
    def _calculate_confidence_adjustment(self, agreement: bool, action_expectations: Dict) -> float:
        """Adjust confidence based on MDP-DQN agreement"""
        if agreement:
            return 0.1  # Boost confidence when both agree
        else:
            expectation_diff = max(action_expectations.values()) - min(action_expectations.values())
            if expectation_diff < 0.5:
                return -0.05  # Small confidence penalty
            else:
                return -0.15  # Larger penalty for strong disagreement
    
    def _generate_mdp_reasoning(self, state: Tuple, history: deque, 
                              action_expectations: Dict, optimal_action: int) -> List[str]:
        """Generate human-readable reasoning based on MDP analysis"""
        risk_level, port_pattern, traffic_volume, protocol_anom, time_context = state
        
        reasoning = []
        
        # State-based reasoning
        risk_names = ["Low", "Medium", "High"]
        pattern_names = ["Normal", "Suspicious", "Malicious"]
        volume_names = ["Low", "Normal", "High"]
        anom_names = ["Normal", "Unusual", "Anomalous"]
        time_names = ["Business hours", "After hours", "Weekend"]
        
        reasoning.append(f"🎯 Risk assessment: {risk_names[risk_level]} risk level")
        reasoning.append(f"🔌 Port pattern: {pattern_names[port_pattern]} usage pattern")
        reasoning.append(f"📊 Traffic volume: {volume_names[traffic_volume]} volume detected")
        reasoning.append(f"🔍 Protocol behavior: {anom_names[protocol_anom]} protocol usage")
        reasoning.append(f"⏰ Temporal context: {time_names[time_context]} activity")
        
        # Historical pattern reasoning
        if len(history) >= 3:
            recent_actions = [h['action'] for h in list(history)[-3:]]
            if all(a == 0 for a in recent_actions):
                reasoning.append("✅ Recent session history shows consistent safe behavior")
            elif any(a == 1 for a in recent_actions):
                reasoning.append("⚠️ Recent session shows suspicious activity - increased caution")
            elif all(a == 2 for a in recent_actions):
                reasoning.append("🔍 Ongoing investigation of this session")
        
        # Action expectation reasoning
        action_names = {0: "ALLOW", 1: "DENY", 2: "INSPECT"}
        best_action = max(action_expectations.items(), key=lambda x: x[1])
        reasoning.append(f"🤖 MDP recommends {action_names[best_action[0]]} (expected value: {best_action[1]:.2f})")
        
        return reasoning
    
    def _describe_state(self, state: Tuple) -> str:
        """Provide human-readable state description"""
        risk_level, port_pattern, traffic_volume, protocol_anom, time_context = state
        
        risk_names = ["low-risk", "medium-risk", "high-risk"]
        pattern_names = ["normal-pattern", "suspicious-pattern", "malicious-pattern"]
        volume_names = ["low-volume", "normal-volume", "high-volume"]
        
        return f"{risk_names[risk_level]} {pattern_names[port_pattern]} {volume_names[traffic_volume]} connection"
    
    def _analyze_historical_pattern(self, history: deque) -> str:
        """Analyze historical patterns for this session"""
        if len(history) < 2:
            return "New session - no history available"
        
        actions = [h['action'] for h in history]
        
        allow_count = actions.count(0)
        deny_count = actions.count(1)
        inspect_count = actions.count(2)
        
        if deny_count > 0:
            return f"⚠️ Problematic session: {deny_count} denies, {inspect_count} inspections"
        elif inspect_count > len(history) / 2:
            return f"🔍 Under investigation: {inspect_count} inspections in {len(history)} packets"
        elif allow_count == len(history):
            return f"✅ Clean session: {allow_count} consecutive allows"
        else:
            return f"📊 Mixed pattern: {allow_count} allows, {inspect_count} inspections"
    
    def update_session_history(self, session_id: str, state: Tuple, action: int, reward: float = None):
        """Update session history with new state-action pair"""
        self.session_history[session_id].append({
            'state': state,
            'action': action,
            'reward': reward,
            'timestamp': pd.Timestamp.now()
        })
    
    def get_session_risk_score(self, session_id: str) -> float:
        """Calculate overall risk score for a session"""
        history = self.session_history[session_id]
        if not history:
            return 0.5  # Neutral risk for new sessions
        
        weights = [0.5, 0.3, 0.2]  # More weight on recent actions
        risk_score = 0.0
        
        for i, entry in enumerate(list(history)[-3:]):  # Last 3 actions
            action = entry['action']
            weight = weights[i] if i < len(weights) else 0.1
            
            if action == 0:  # ALLOW
                risk_score += 0.0 * weight
            elif action == 1:  # DENY
                risk_score += 1.0 * weight
            elif action == 2:  # INSPECT
                risk_score += 0.5 * weight
        
        return min(1.0, risk_score)

class SingleModelFirewallPredictor:
    def __init__(self):
        self.device = device
        self.model = None
        self.model_info = {}
        self.mdp_reasoner = MDPFirewallReasoning()  # Initialize MDP reasoning
        
    def load_model(self, model_path):
        """Load a single model from .pth file"""
        try:
            print(f"📂 Loading model: {os.path.basename(model_path)}")
            model_data = torch.load(model_path, map_location=device)
            
            # Create model instance
            self.model = RegularizedDQN(
                state_size=model_data['state_size'],
                action_size=model_data['action_size']
            )
            self.model.load_state_dict(model_data['policy_net_state_dict'])
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            # Store model info
            self.model_info = {
                'name': os.path.basename(model_path),
                'state_size': model_data['state_size'],
                'action_size': model_data['action_size'],
                'timestamp': model_data.get('timestamp', 'Unknown'),
                'epsilon': model_data.get('epsilon', 'Unknown'),
                'memory_size': model_data.get('memory_size', 'Unknown')
            }
            
            print("✅ Model loaded successfully!")
            print(f"   📊 State size: {self.model_info['state_size']}")
            print(f"   🎯 Action size: {self.model_info['action_size']}")
            print(f"   🕐 Trained: {self.model_info['timestamp']}")
            print(f"   ε: {self.model_info['epsilon']}")
            print(f"   💾 Memory: {self.model_info['memory_size']} experiences")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
    
    def preprocess_single_row(self, row):
        """Preprocess a single row of CSV data"""
        try:
            # Extract and map features according to your training format
            state = self._extract_features(row)
            return state
            
        except Exception as e:
            print(f"❌ Error processing row: {e}")
            return np.zeros(12, dtype=np.float32)  # Fallback state
    
    def preprocess_batch(self, csv_data):
        """Preprocess entire CSV batch"""
        print("🔄 Preprocessing data...")
        processed_data = []
        
        for idx, row in csv_data.iterrows():
            state = self.preprocess_single_row(row)
            processed_data.append(state)
        
        return np.array(processed_data)
    
    def _extract_features(self, row):
        """Extract 12 features from CSV row (same as before)"""
        # 1. Source Port Type (0-2)
        src_port = row.get('src_port', 0)
        src_port_type = self._get_port_type(src_port)
        
        # 2. Destination Port Type (0-2)
        dst_port = row.get('dst_port', 0)
        dst_port_type = self._get_port_type(dst_port)
        
        # 3. Protocol Inference (0-2)
        protocol = str(row.get('protocol', '')).upper()
        protocol_type = self._infer_protocol(protocol, dst_port)
        
        # 4-7. Traffic Volume Metrics
        bytes_sent = max(float(row.get('bytes_sent', 0)), 0)
        bytes_received = max(float(row.get('bytes_received', 0)), 0)
        pkts_sent = max(float(row.get('pkts_sent', 0)), 0)
        pkts_received = max(float(row.get('pkts_received', 0)), 0)
        
        # 8. Temporal Features
        duration_sec = max(float(row.get('duration_sec', 0)), 0)
        
        # 9-12. Context Features (using defaults for new data)
        time_of_day = 0.5
        historical_success = 0.7
        geographic_risk = 0.3
        service_frequency = 0.5
        
        # Normalize values
        normalized_bytes_sent = self._normalize_bytes(bytes_sent)
        normalized_bytes_received = self._normalize_bytes(bytes_received)
        normalized_duration = self._normalize_duration(duration_sec)
        
        state = [
            src_port_type, dst_port_type, protocol_type,
            normalized_bytes_sent, normalized_bytes_received,
            pkts_sent, pkts_received, normalized_duration,
            time_of_day, historical_success, geographic_risk, service_frequency
        ]
        
        return np.array(state, dtype=np.float32)
    
    def _get_port_type(self, port):
        port = int(port)
        if port <= 1023: return 0
        elif port <= 49151: return 1
        else: return 2
    
    def _infer_protocol(self, protocol, dst_port):
        protocol = str(protocol).upper()
        
        if protocol == 'TCP': return 0
        elif protocol == 'UDP': return 1
        elif protocol == 'ICMP': return 2
        else:
            tcp_ports = [80, 443, 22, 23, 25, 53, 110, 143, 993, 995, 3389]
            udp_ports = [53, 67, 68, 69, 123, 161, 162, 514]
            
            if dst_port in tcp_ports: return 0
            elif dst_port in udp_ports: return 1
            else: return 2
    
    def _normalize_bytes(self, bytes_value):
        return np.log1p(bytes_value) / 10.0
    
    def _normalize_duration(self, duration):
        return min(duration / 3600.0, 1.0)
    
    def predict_single(self, state):
        """Make prediction for single state"""
        if self.model is None:
            print("❌ No model loaded!")
            return None, None, None
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.model(state_tensor)
            q_values_np = q_values.cpu().numpy()[0]
            
            predicted_action = np.argmax(q_values_np)
            confidence = self._calculate_confidence(q_values_np)
            
            return predicted_action, confidence, q_values_np
    
    def predict_batch(self, processed_states):
        """Make predictions on batch of states"""
        if self.model is None:
            print("❌ No model loaded!")
            return None
        
        predictions = []
        confidences = []
        q_values_list = []
        
        for state in processed_states:
            pred, conf, q_vals = self.predict_single(state)
            predictions.append(pred)
            confidences.append(conf)
            q_values_list.append(q_vals)
        
        return predictions, confidences, q_values_list
    
    def _calculate_confidence(self, q_values):
        max_q = np.max(q_values)
        min_q = np.min(q_values)
        q_range = max_q - min_q
        
        if q_range > 1e-6:
            return min(1.0, q_range / 10.0)
        else:
            return 0.1
    
    def interactive_test(self, csv_file_path):
        """Interactive testing mode - test one row at a time"""
        print(f"\n🎯 INTERACTIVE TESTING MODE")
        print(f"📊 Loading CSV: {csv_file_path}")
        
        try:
            data = pd.read_csv(csv_file_path)
            print(f"✅ Loaded {len(data)} records")
            
            while True:
                print(f"\n{'='*50}")
                print("Choose an option:")
                print("1. Test specific row by index")
                print("2. Test random row") 
                print("3. Test all rows and save results")
                print("4. Load different model")
                print("5. Exit")
                
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == '1':
                    self._test_specific_row(data)
                elif choice == '2':
                    self._test_random_row(data)
                elif choice == '3':
                    self._test_all_rows(data, csv_file_path)
                elif choice == '4':
                    return True  # Signal to load new model
                elif choice == '5':
                    return False  # Signal to exit
                else:
                    print("❌ Invalid choice!")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def _test_specific_row(self, data):
        """Test a specific row by index"""
        try:
            row_idx = int(input(f"Enter row index (0-{len(data)-1}): "))
            if 0 <= row_idx < len(data):
                self._analyze_single_row(data, row_idx)
            else:
                print("❌ Invalid index!")
        except ValueError:
            print("❌ Please enter a valid number!")
    
    def _test_random_row(self, data):
        """Test a random row"""
        row_idx = np.random.randint(0, len(data))
        print(f"🎲 Testing random row {row_idx}...")
        self._analyze_single_row(data, row_idx)
    
    def _analyze_single_row(self, data, row_idx):
        """Analyze and display single row prediction with MDP enhancement"""
        row = data.iloc[row_idx]
        state = self.preprocess_single_row(row)
        
        action, confidence, q_values = self.predict_single(state)
        
        if action is not None:
            # Create session ID from source and destination
            session_id = f"{row.get('src_ip', 'unknown')}:{row.get('src_port', '0')}->{row.get('dst_ip', 'unknown')}:{row.get('dst_port', '0')}"
            
            # Get MDP enhancement
            discrete_state = self.mdp_reasoner.discretize_state(state, session_id)
            mdp_result = self.mdp_reasoner.get_mdp_recommendation(
                discrete_state, session_id, action, q_values
            )
            
            # Update session history
            self.mdp_reasoner.update_session_history(session_id, discrete_state, action)
            
            action_names = {0: "ALLOW 🟢", 1: "DENY 🔴", 2: "INSPECT 🔍"}
            
            print(f"\n{'='*60}")
            print(f"📊 ROW {row_idx} ANALYSIS")
            print(f"{'='*60}")
            print(f"📋 Connection: {row.get('src_ip', 'N/A')}:{row.get('src_port', 'N/A')} → {row.get('dst_ip', 'N/A')}:{row.get('dst_port', 'N/A')}")
            print(f"📋 Protocol: {row.get('protocol', 'N/A')}")
            print(f"📊 Traffic: {row.get('bytes_sent', 'N/A')} bytes sent, {row.get('bytes_received', 'N/A')} bytes received")
            print(f"⏱️  Duration: {row.get('duration_sec', 'N/A')} seconds")
            
            # DQN Prediction
            print(f"\n🤖 DQN PREDICTION: {action_names[action]}")
            print(f"💪 DQN Confidence: {confidence:.3f}")
            print(f"📈 Q-values: ALLOW={q_values[0]:.2f}, DENY={q_values[1]:.2f}, INSPECT={q_values[2]:.2f}")
            
            # MDP Enhancement
            print(f"\n🧠 MDP ENHANCEMENT:")
            print(f"🎯 MDP Recommendation: {action_names[mdp_result['mdp_recommendation']]}")
            print(f"🤝 DQN-MDP Agreement: {'✅ YES' if mdp_result['agreement'] else '❌ NO'}")
            
            # Adjusted confidence
            adjusted_confidence = confidence + mdp_result['confidence_adjustment']
            adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))  # Clamp to [0,1]
            print(f"💪 Adjusted Confidence: {adjusted_confidence:.3f} (change: {mdp_result['confidence_adjustment']:+.3f})")
            
            # State context
            print(f"📊 State Context: {mdp_result['state_context']}")
            
            # Session analysis
            session_risk = self.mdp_reasoner.get_session_risk_score(session_id)
            print(f"🎭 Session Risk Score: {session_risk:.3f}")
            print(f"📈 {mdp_result['historical_pattern']}")
            
            # Detailed reasoning
            print(f"\n🔍 DETAILED REASONING:")
            for i, reason in enumerate(mdp_result['reasoning'], 1):
                print(f"   {i}. {reason}")
            
            # Expected rewards breakdown
            print(f"\n💰 EXPECTED REWARDS:")
            for action_idx, reward in mdp_result['expected_rewards'].items():
                print(f"   {action_names[action_idx]}: {reward:.3f}")
            
            # Final recommendation
            final_action = mdp_result['mdp_recommendation']
            if mdp_result['agreement']:
                print(f"\n✅ FINAL RECOMMENDATION: {action_names[final_action]} (Both systems agree)")
            else:
                print(f"\n⚠️  FINAL RECOMMENDATION: {action_names[final_action]} (MDP override - investigate discrepancy)")
            
            print(f"{'='*60}")
    

    
    def _test_all_rows(self, data, csv_file_path):
        """Test all rows and save to CSV with MDP enhancement"""
        print("🧪 Testing all rows with MDP enhancement...")
        
        processed_states = self.preprocess_batch(data)
        predictions, confidences, q_values_list = self.predict_batch(processed_states)
        
        # Create results DataFrame
        results = data.copy()
        results['DQN_Predicted_Action'] = predictions
        results['DQN_Confidence'] = confidences
        results['Q_ALLOW'] = [q[0] for q in q_values_list]
        results['Q_DENY'] = [q[1] for q in q_values_list] 
        results['Q_INSPECT'] = [q[2] for q in q_values_list]
        
        # Add MDP analysis for each row
        print("🧠 Adding MDP analysis...")
        mdp_recommendations = []
        mdp_agreements = []
        adjusted_confidences = []
        session_risks = []
        state_contexts = []
        
        for idx, (state, dqn_pred, q_vals) in enumerate(zip(processed_states, predictions, q_values_list)):
            # Create session ID
            row = data.iloc[idx]
            session_id = f"{row.get('src_ip', 'unknown')}:{row.get('src_port', '0')}->{row.get('dst_ip', 'unknown')}:{row.get('dst_port', '0')}"
            
            # Get MDP analysis
            discrete_state = self.mdp_reasoner.discretize_state(state, session_id)
            mdp_result = self.mdp_reasoner.get_mdp_recommendation(
                discrete_state, session_id, dqn_pred, q_vals
            )
            
            # Update session history
            self.mdp_reasoner.update_session_history(session_id, discrete_state, dqn_pred)
            
            # Store MDP results
            mdp_recommendations.append(mdp_result['mdp_recommendation'])
            mdp_agreements.append(mdp_result['agreement'])
            
            # Calculate adjusted confidence
            adj_conf = confidences[idx] + mdp_result['confidence_adjustment']
            adjusted_confidences.append(max(0.0, min(1.0, adj_conf)))
            
            session_risks.append(self.mdp_reasoner.get_session_risk_score(session_id))
            state_contexts.append(mdp_result['state_context'])
        
        # Add MDP columns to results
        results['MDP_Recommendation'] = mdp_recommendations
        results['DQN_MDP_Agreement'] = mdp_agreements
        results['Adjusted_Confidence'] = adjusted_confidences
        results['Session_Risk_Score'] = session_risks
        results['State_Context'] = state_contexts
        
        # Map action numbers to names
        action_map = {0: 'ALLOW', 1: 'DENY', 2: 'INSPECT'}
        results['DQN_Action_Name'] = results['DQN_Predicted_Action'].map(action_map)
        results['MDP_Action_Name'] = results['MDP_Recommendation'].map(action_map)
        
        # Final recommendation (MDP takes precedence in disagreements)
        results['Final_Recommendation'] = results['MDP_Recommendation']
        results['Final_Action_Name'] = results['Final_Recommendation'].map(action_map)
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = self.model_info['name'].replace('.pth', '')
        output_file = f"mdp_enhanced_predictions_{model_name}_{timestamp}.csv"
        
        # Save results
        results.to_csv(output_file, index=False)
        print(f"💾 Enhanced results saved to: {output_file}")
        
        # Show enhanced summary
        self._show_enhanced_prediction_summary(results)
    
    def _show_enhanced_prediction_summary(self, results):
        """Show enhanced prediction summary with MDP analysis"""
        total = len(results)
        
        print(f"\n{'='*60}")
        print(f"📈 ENHANCED PREDICTION SUMMARY")
        print(f"{'='*60}")
        print(f"📊 Total records processed: {total}")
        print(f"🤖 Model: {self.model_info['name']}")
        
        # DQN vs MDP comparison
        dqn_counts = results['DQN_Action_Name'].value_counts()
        mdp_counts = results['MDP_Action_Name'].value_counts()
        final_counts = results['Final_Action_Name'].value_counts()
        
        print(f"\n🤖 DQN PREDICTIONS:")
        for action in ['ALLOW', 'DENY', 'INSPECT']:
            count = dqn_counts.get(action, 0)
            percentage = (count / total) * 100
            icon = "🟢" if action == 'ALLOW' else "🔴" if action == 'DENY' else "🔍"
            print(f"   {icon} {action}: {count} ({percentage:.1f}%)")
        
        print(f"\n🧠 MDP RECOMMENDATIONS:")
        for action in ['ALLOW', 'DENY', 'INSPECT']:
            count = mdp_counts.get(action, 0)
            percentage = (count / total) * 100
            icon = "🟢" if action == 'ALLOW' else "🔴" if action == 'DENY' else "🔍"
            print(f"   {icon} {action}: {count} ({percentage:.1f}%)")
        
        print(f"\n🎯 FINAL RECOMMENDATIONS:")
        for action in ['ALLOW', 'DENY', 'INSPECT']:
            count = final_counts.get(action, 0)
            percentage = (count / total) * 100
            icon = "🟢" if action == 'ALLOW' else "🔴" if action == 'DENY' else "🔍"
            print(f"   {icon} {action}: {count} ({percentage:.1f}%)")
        
        # Agreement analysis
        agreements = results['DQN_MDP_Agreement'].sum()
        disagreements = total - agreements
        agreement_rate = (agreements / total) * 100
        
        print(f"\n🤝 SYSTEM AGREEMENT:")
        print(f"   ✅ Agreements: {agreements} ({agreement_rate:.1f}%)")
        print(f"   ❌ Disagreements: {disagreements} ({100-agreement_rate:.1f}%)")
        
        # Confidence analysis
        avg_dqn_confidence = results['DQN_Confidence'].mean()
        avg_adjusted_confidence = results['Adjusted_Confidence'].mean()
        confidence_improvement = avg_adjusted_confidence - avg_dqn_confidence
        
        print(f"\n💪 CONFIDENCE ANALYSIS:")
        print(f"   🤖 DQN Average: {avg_dqn_confidence:.3f}")
        print(f"   🧠 MDP Adjusted: {avg_adjusted_confidence:.3f}")
        print(f"   📈 Improvement: {confidence_improvement:+.3f}")
        
        # Risk analysis
        avg_session_risk = results['Session_Risk_Score'].mean()
        high_risk_sessions = (results['Session_Risk_Score'] > 0.7).sum()
        
        print(f"\n🎭 RISK ANALYSIS:")
        print(f"   📊 Average Session Risk: {avg_session_risk:.3f}")
        print(f"   ⚠️  High Risk Sessions: {high_risk_sessions} ({(high_risk_sessions/total)*100:.1f}%)")
        
        # Security recommendations
        allow_count = final_counts.get('ALLOW', 0)
        deny_count = final_counts.get('DENY', 0)
        inspect_count = final_counts.get('INSPECT', 0)
        
        print(f"\n🛡️  SECURITY RECOMMENDATIONS:")
        if deny_count > 0:
            print(f"   🔴 BLOCK {deny_count} connections immediately")
        if inspect_count > 0:
            print(f"   🔍 INSPECT {inspect_count} connections for deeper analysis")
        if allow_count > 0:
            print(f"   🟢 ALLOW {allow_count} connections (verified safe)")
        
        print(f"{'='*60}")

def find_model_files(directory="."):
    """Find all .pth model files"""
    pattern = os.path.join(directory, "*.pth")
    model_files = glob.glob(pattern)
    
    # Also check common directories
    if not model_files:
        common_dirs = ["/kaggle/working/trained_models", "./trained_models", "."]
        for dir_path in common_dirs:
            pattern = os.path.join(dir_path, "*.pth")
            model_files.extend(glob.glob(pattern))
    
    return list(set(model_files))

def main():
    """Main function for VS Code interactive testing with MDP enhancement"""
    print("=== VS CODE FIREWALL AI TESTER (MDP ENHANCED) ===")
    print("🤖 Single Model Testing Mode with Markov Decision Process Reasoning")
    print("🧠 Features: Sequential decision making, session awareness, adaptive confidence")
    print("🎯 Enhanced prediction accuracy through contextual analysis")
    
    # Find available models
    model_files = find_model_files()
    
    if not model_files:
        print("❌ No .pth model files found!")
        print("💡 Please place your .pth model files in the current directory")
        return
    
    print(f"\n📂 Found {len(model_files)} model files:")
    for i, path in enumerate(model_files, 1):
        print(f"   {i}. {os.path.basename(path)}")
    
    # CSV file path - CHANGE THIS TO YOUR CSV PATH
    csv_file_path = "network_traffic_data.csv"  
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        csv_file_path = input("📁 Enter path to your CSV file: ").strip()
    
    # Main loop
    predictor = SingleModelFirewallPredictor()
    
    while True:
        print(f"\n{'='*60}")
        print("🎯 MAIN MENU")
        print("="*60)
        
        # Show model selection
        print("\nSelect a model to load:")
        for i, path in enumerate(model_files, 1):
            print(f"   {i}. {os.path.basename(path)}")
        print(f"   {len(model_files) + 1}. Exit")
        
        try:
            choice = int(input(f"\nEnter choice (1-{len(model_files) + 1}): "))
            
            if 1 <= choice <= len(model_files):
                # Load selected model
                model_path = model_files[choice - 1]
                success = predictor.load_model(model_path)
                
                if success:
                    # Enter interactive testing with this model
                    should_continue = predictor.interactive_test(csv_file_path)
                    if not should_continue:
                        break
                else:
                    print("❌ Failed to load model, please try another.")
            
            elif choice == len(model_files) + 1:
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice!")
                
        except ValueError:
            print("❌ Please enter a valid number!")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()