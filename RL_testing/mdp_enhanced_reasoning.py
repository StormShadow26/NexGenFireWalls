import numpy as np
import pandas as pd
from collections import defaultdict, deque
from typing import Tuple, Dict, List

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
        
        # Define state space
        self.state_features = [
            'risk_level',      # 0: low, 1: medium, 2: high
            'port_pattern',    # 0: normal, 1: suspicious, 2: malicious
            'traffic_volume',  # 0: low, 1: normal, 2: high
            'protocol_anom',   # 0: normal, 1: unusual, 2: anomalous
            'time_context'     # 0: business, 1: after-hours, 2: weekend
        ]
        
        # Reward structure for different outcomes
        self.rewards = {
            'ALLOW': {
                'correct_allow': 1.0,     # Correctly allowed legitimate traffic
                'false_positive': -2.0,   # Incorrectly blocked legitimate traffic
                'false_negative': -5.0    # Incorrectly allowed malicious traffic
            },
            'DENY': {
                'correct_deny': 2.0,      # Correctly blocked malicious traffic
                'false_positive': -1.0,   # Incorrectly blocked legitimate traffic
                'correct_block': 1.5      # Prevented potential attack
            },
            'INSPECT': {
                'detailed_analysis': 0.5,  # Gained information from inspection
                'resolved_threat': 3.0,    # Found and resolved threat through inspection
                'wasted_resources': -0.5   # Unnecessary inspection of benign traffic
            }
        }
    
    def discretize_state(self, continuous_state: np.array, session_id: str = None) -> Tuple[int, int, int, int, int]:
        """
        Convert continuous 12-feature state to discrete MDP state
        """
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
        # Normal patterns
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
        
        # Calculate bytes per packet ratio
        if total_pkts > 0:
            bpp_ratio = total_bytes / total_pkts
        else:
            bpp_ratio = 0
        
        # Volume thresholds (can be learned from data)
        if total_bytes < 1000 and total_pkts < 10:
            return 0  # Low volume
        elif total_bytes < 100000 and bpp_ratio < 1500:  # Normal packet sizes
            return 1  # Normal volume
        else:
            return 2  # High volume or large packets (potential exfiltration)
    
    def _analyze_protocol_anomaly(self, protocol: int, dest_port: int, duration: float) -> int:
        """Detect protocol-specific anomalies"""
        # TCP connections
        if protocol == 0:
            if duration < 0.001:  # Very short TCP connection
                return 2  # Anomalous - port scan pattern
            elif duration > 0.5:  # Long-lived connection
                return 0  # Normal
            else:
                return 1  # Unusual but not clearly malicious
        
        # UDP traffic
        elif protocol == 1:
            if dest_port == 53:  # DNS
                return 0  # Normal
            else:
                return 1  # Unusual UDP traffic
        
        # ICMP
        elif protocol == 2:
            return 1  # Always inspect ICMP
        
        return 1  # Default to unusual
    
    def _analyze_time_context(self, time_of_day: float) -> int:
        """Analyze temporal context"""
        # Assuming time_of_day is normalized 0-1 (0=midnight, 0.5=noon)
        if 0.25 <= time_of_day <= 0.75:  # 6 AM to 6 PM
            return 0  # Business hours
        elif 0.75 < time_of_day <= 1.0 or 0.0 <= time_of_day < 0.25:  # 6 PM to 6 AM
            return 1  # After hours
        else:
            return 2  # Weekend/holiday (would need additional logic)
    
    def get_mdp_recommendation(self, current_state: Tuple, session_id: str, 
                              dqn_prediction: int, q_values: np.array) -> Dict:
        """
        Get MDP-enhanced recommendation considering state transitions
        """
        # Get state history for this session
        history = self.session_history[session_id]
        
        # Calculate state transition probabilities
        transition_probs = self._calculate_transition_probabilities(current_state, history)
        
        # Calculate expected future rewards for each action
        action_expectations = {}
        for action in [0, 1, 2]:  # ALLOW, DENY, INSPECT
            expected_reward = self._calculate_expected_reward(
                current_state, action, transition_probs, q_values
            )
            action_expectations[action] = expected_reward
        
        # Get MDP optimal action
        mdp_optimal_action = max(action_expectations.items(), key=lambda x: x[1])[0]
        
        # Compare with DQN prediction
        agreement = (mdp_optimal_action == dqn_prediction)
        confidence_adjustment = self._calculate_confidence_adjustment(
            agreement, action_expectations, q_values
        )
        
        # Generate reasoning
        reasoning = self._generate_mdp_reasoning(
            current_state, history, action_expectations, mdp_optimal_action
        )
        
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
    
    def _calculate_transition_probabilities(self, current_state: Tuple, 
                                         history: deque) -> Dict:
        """Calculate probabilities of transitioning to different states"""
        if len(history) < 2:
            return {}  # Not enough history
        
        transitions = defaultdict(float)
        total_transitions = 0
        
        # Analyze historical transitions
        for i in range(len(history) - 1):
            prev_state = history[i]['state']
            next_state = history[i + 1]['state']
            
            transition_key = f"{prev_state}->{next_state}"
            transitions[transition_key] += 1
            total_transitions += 1
        
        # Normalize to probabilities
        if total_transitions > 0:
            for key in transitions:
                transitions[key] /= total_transitions
        
        return dict(transitions)
    
    def _calculate_expected_reward(self, state: Tuple, action: int, 
                                 transition_probs: Dict, q_values: np.array) -> float:
        """Calculate expected future reward for taking an action"""
        immediate_reward = q_values[action]  # Q-value as immediate reward proxy
        
        # Estimate future reward based on state transitions
        future_reward = 0.0
        
        # Risk-based reward adjustments
        risk_level, port_pattern, traffic_volume, protocol_anom, time_context = state
        
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
    
    def _calculate_confidence_adjustment(self, agreement: bool, 
                                       action_expectations: Dict, q_values: np.array) -> float:
        """Adjust confidence based on MDP-DQN agreement"""
        if agreement:
            return 0.1  # Boost confidence when both agree
        else:
            # Check how close the expectations are
            expectation_diff = max(action_expectations.values()) - min(action_expectations.values())
            if expectation_diff < 0.5:  # Close expectations
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
        
        reasoning.append(f"Risk assessment: {risk_names[risk_level]} risk level")
        reasoning.append(f"Port pattern: {pattern_names[port_pattern]} usage pattern")
        reasoning.append(f"Traffic volume: {volume_names[traffic_volume]} volume detected")
        reasoning.append(f"Protocol behavior: {anom_names[protocol_anom]} protocol usage")
        reasoning.append(f"Temporal context: {time_names[time_context]} activity")
        
        # Historical pattern reasoning
        if len(history) >= 3:
            recent_actions = [h['action'] for h in list(history)[-3:]]
            if all(a == 0 for a in recent_actions):  # All recent allows
                reasoning.append("Recent session history shows consistent safe behavior")
            elif any(a == 1 for a in recent_actions):  # Recent denies
                reasoning.append("Recent session shows suspicious activity - increased caution")
            elif all(a == 2 for a in recent_actions):  # All inspections
                reasoning.append("Ongoing investigation of this session")
        
        # Action expectation reasoning
        action_names = {0: "ALLOW", 1: "DENY", 2: "INSPECT"}
        best_action = max(action_expectations.items(), key=lambda x: x[1])
        reasoning.append(f"MDP recommends {action_names[best_action[0]]} (expected value: {best_action[1]:.2f})")
        
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
            return "Insufficient history"
        
        actions = [h['action'] for h in history]
        states = [h['state'] for h in history]
        
        # Analyze action patterns
        allow_count = actions.count(0)
        deny_count = actions.count(1)
        inspect_count = actions.count(2)
        
        if deny_count > 0:
            return f"Problematic session: {deny_count} denies, {inspect_count} inspections"
        elif inspect_count > len(history) / 2:
            return f"Under investigation: {inspect_count} inspections in {len(history)} packets"
        elif allow_count == len(history):
            return f"Clean session: {allow_count} consecutive allows"
        else:
            return f"Mixed pattern: {allow_count} allows, {inspect_count} inspections"
    
    def update_session_history(self, session_id: str, state: Tuple, action: int, 
                              reward: float = None):
        """Update session history with new state-action pair"""
        self.session_history[session_id].append({
            'state': state,
            'action': action,
            'reward': reward,
            'timestamp': pd.Timestamp.now()
        })
        
        # Update transition counts for learning
        if len(self.session_history[session_id]) >= 2:
            prev_entry = list(self.session_history[session_id])[-2]
            prev_state = prev_entry['state']
            
            transition_key = f"{prev_state}->{state}"
            self.state_transitions[session_id][transition_key] += 1
    
    def get_session_risk_score(self, session_id: str) -> float:
        """Calculate overall risk score for a session"""
        history = self.session_history[session_id]
        if not history:
            return 0.5  # Neutral risk for new sessions
        
        # Weighted risk calculation based on recent actions
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


# Example usage integration with your existing system
def enhance_prediction_with_mdp(predictor_instance, state, session_id, 
                               dqn_prediction, q_values, mdp_reasoner):
    """
    Enhance existing prediction with MDP reasoning
    """
    # Convert to discrete MDP state
    discrete_state = mdp_reasoner.discretize_state(state, session_id)
    
    # Get MDP recommendation
    mdp_result = mdp_reasoner.get_mdp_recommendation(
        discrete_state, session_id, dqn_prediction, q_values
    )
    
    # Update session history
    mdp_reasoner.update_session_history(session_id, discrete_state, dqn_prediction)
    
    # Combine results
    enhanced_result = {
        'original_prediction': dqn_prediction,
        'original_confidence': predictor_instance._calculate_confidence(q_values),
        'mdp_enhanced': mdp_result,
        'final_recommendation': mdp_result['mdp_recommendation'],
        'confidence_adjusted': predictor_instance._calculate_confidence(q_values) + mdp_result['confidence_adjustment'],
        'reasoning': mdp_result['reasoning'],
        'session_risk_score': mdp_reasoner.get_session_risk_score(session_id)
    }
    
    return enhanced_result


if __name__ == "__main__":
    # Example of how to use MDP reasoning
    mdp_reasoner = MDPFirewallReasoning()
    
    # Example state (12 features from your system)
    example_state = np.array([
        2, 0, 0,  # Ephemeral source, well-known dest, TCP
        0.5, 0.1, 10, 5, 0.1,  # Traffic metrics
        0.5, 0.7, 0.8, 0.4  # Context features (high geo risk!)
    ])
    
    # Example DQN prediction
    dqn_pred = 2  # INSPECT
    q_vals = np.array([0.2, 0.3, 0.5])  # Q-values for ALLOW, DENY, INSPECT
    
    # Get MDP enhancement
    session_id = "192.168.1.100:12345->10.0.0.1:80"
    
    # This would be integrated into your existing predictor
    # enhanced = enhance_prediction_with_mdp(predictor, example_state, session_id, dqn_pred, q_vals, mdp_reasoner)
    
    print("MDP Enhanced Firewall Reasoning System Ready!")
    print("Benefits:")
    print("- Sequential decision making")
    print("- Session-aware predictions") 
    print("- Adaptive confidence adjustment")
    print("- Rich contextual reasoning")