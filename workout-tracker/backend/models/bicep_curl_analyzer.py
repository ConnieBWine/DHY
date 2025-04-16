from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackPriority

class BicepCurlState(Enum):
    """States for the bicep curl exercise"""
    IDLE = 0
    CURL_START = 1
    CURL_UP = 2
    CURL_HOLD = 3
    CURL_DOWN = 4
    COMPLETED = 5

class BicepCurlAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the bicep curl exercise
    
    Tracks the bicep curl movement through its stages and provides feedback
    on form and technique.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the bicep curl analyzer
        
        Args:
            thresholds: Dictionary of threshold values for curl analysis
        """
        super().__init__(thresholds)
        self.state = BicepCurlState.IDLE
        self.last_angle = None
        
        # Thresholds for bicep curl
        self.curl_start_threshold = 160  # Angle to detect start of curl (arm extended)
        self.curl_up_threshold = 90      # Angle to detect upward curl phase
        self.curl_down_threshold = 150   # Angle to detect completion of downward phase
        
        # For detecting body swing
        self.body_swing_angle_threshold = 18
        self.max_swing_angle = 0
        self.start_hip_shoulder_angle = None
        
        # For tracking elbow movement
        self.elbow_angle_buffer = deque(maxlen=5)
        self.elbow_detection_confidence = 1.0
        self.confidence_threshold = 0.7
        self.low_confidence_count = 0
        self.max_low_confidence_frames = 8
        self.max_elbow_angle = 0
    
    def reset(self):
        """Reset the analyzer between reps"""
        super().reset()
        self.start_shoulder_pos = None
        self.start_hip_pos = None
        self.start_elbow_pos = None
        self.max_angle = 0
        self.min_angle = 180
        self.fully_extended = False
        self.curled_high_enough = False
        self.max_elbow_angle = 0
        self.start_hip_shoulder_angle = None
        self.max_swing_angle = 0
        self.elbow_angle_buffer.clear()
    
    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for bicep curl analysis
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        
        # Calculate bicep curl angles (both arms if visible)
        if all(k in keypoints for k in ['left_shoulder', 'left_elbow', 'left_wrist']):
            left_bicep_angle = self.angle_calculator.angle_deg(
                keypoints['left_shoulder'],
                keypoints['left_elbow'],
                keypoints['left_wrist']
            )
            angles['left_bicep_angle'] = left_bicep_angle
            
        if all(k in keypoints for k in ['right_shoulder', 'right_elbow', 'right_wrist']):
            right_bicep_angle = self.angle_calculator.angle_deg(
                keypoints['right_shoulder'],
                keypoints['right_elbow'],
                keypoints['right_wrist']
            )
            angles['right_bicep_angle'] = right_bicep_angle
            
        # Calculate elbow-torso angles to detect excessive movement
        if all(k in keypoints for k in ['left_hip', 'left_shoulder', 'left_elbow']):
            left_elbow_torso_angle = self.angle_calculator.angle_deg(
                keypoints['left_hip'],
                keypoints['left_shoulder'],
                keypoints['left_elbow']
            )
            angles['left_elbow_torso_angle'] = left_elbow_torso_angle
            
        if all(k in keypoints for k in ['right_hip', 'right_shoulder', 'right_elbow']):
            right_elbow_torso_angle = self.angle_calculator.angle_deg(
                keypoints['right_hip'],
                keypoints['right_shoulder'],
                keypoints['right_elbow']
            )
            angles['right_elbow_torso_angle'] = right_elbow_torso_angle
            
        # Calculate hip-shoulder angle to detect body swing
        if all(k in keypoints for k in ['left_hip', 'left_shoulder']):
            left_hip_shoulder_angle = self.angle_calculator.find_angle(
                keypoints['left_hip'][0], 
                keypoints['left_hip'][1], 
                keypoints['left_shoulder'][0], 
                keypoints['left_shoulder'][1]
            )
            angles['left_hip_shoulder_angle'] = left_hip_shoulder_angle
            
        if all(k in keypoints for k in ['right_hip', 'right_shoulder']):
            right_hip_shoulder_angle = self.angle_calculator.find_angle(
                keypoints['right_hip'][0], 
                keypoints['right_hip'][1], 
                keypoints['right_shoulder'][0], 
                keypoints['right_shoulder'][1]
            )
            angles['right_hip_shoulder_angle'] = right_hip_shoulder_angle
            
        return angles
        
    def detect_body_swing(self, angles: Dict[str, float]) -> bool:
        """
        Detect if there's excessive body swing during the curl
        
        Args:
            angles: Dictionary of calculated angles
            
        Returns:
            True if body swing detected, False otherwise
        """
        # Use either the left or right hip-shoulder angle
        hip_shoulder_angle = angles.get('left_hip_shoulder_angle', angles.get('right_hip_shoulder_angle'))
        
        if self.start_hip_shoulder_angle is None or hip_shoulder_angle is None:
            # Set the starting angle if not set yet
            if hip_shoulder_angle is not None:
                self.start_hip_shoulder_angle = hip_shoulder_angle
            return False
        
        angle_diff = abs(hip_shoulder_angle - self.start_hip_shoulder_angle)
        self.max_swing_angle = max(self.max_swing_angle, angle_diff)
        
        return angle_diff > self.body_swing_angle_threshold
    
    def update_elbow_angle(self, elbow_torso_angle: Optional[float]) -> Optional[float]:
        """
        Smooth elbow angle readings using a rolling average
        
        Args:
            elbow_torso_angle: Current elbow-torso angle
            
        Returns:
            Smoothed elbow angle
        """
        if elbow_torso_angle is None:
            return None
            
        self.elbow_angle_buffer.append(elbow_torso_angle)
        
        if not self.elbow_angle_buffer:
            return elbow_torso_angle
            
        return sum(self.elbow_angle_buffer) / len(self.elbow_angle_buffer)
    
    def is_curl_completed(self) -> bool:
        """
        Check if a curl rep is complete based on angle changes
        
        Returns:
            True if curl is complete, False otherwise
        """
        return self.max_angle - self.min_angle > self.thresholds.get('bicep_curl_not_high_enough', 65)
    
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze bicep curl form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new rep
            
        Returns:
            List of feedback strings about the curl form
        """
        feedback = []
        
        # Calculate angles
        angles = self.calculate_exercise_angles(keypoints)
        
        # Determine which arm is doing the curl (use the one with the smallest angle)
        left_bicep_angle = angles.get('left_bicep_angle')
        right_bicep_angle = angles.get('right_bicep_angle')
        
        # Choose the arm that is most bent (smaller angle)
        if left_bicep_angle is not None and right_bicep_angle is not None:
            bicep_angle = min(left_bicep_angle, right_bicep_angle)
            primary_side = 'left' if left_bicep_angle < right_bicep_angle else 'right'
        elif left_bicep_angle is not None:
            bicep_angle = left_bicep_angle
            primary_side = 'left'
        elif right_bicep_angle is not None:
            bicep_angle = right_bicep_angle
            primary_side = 'right'
        else:
            # Can't analyze without visible arm
            return ["Can't detect arm position"]
        
        # Get the elbow and shoulder positions
        shoulder = keypoints.get(f'{primary_side}_shoulder')
        elbow = keypoints.get(f'{primary_side}_elbow')
        wrist = keypoints.get(f'{primary_side}_wrist')
        hip = keypoints.get(f'{primary_side}_hip')
        
        if is_start or (self.start_shoulder_pos is None and shoulder is not None):
            self.reset()
            self.start_shoulder_pos = shoulder
            self.start_hip_pos = hip
            self.start_elbow_pos = elbow
            self.start_hip_shoulder_angle = angles.get(f'{primary_side}_hip_shoulder_angle')
            self.last_angle = bicep_angle
            return []
        
        # Skip analysis if key body parts aren't visible
        if shoulder is None or elbow is None or wrist is None or hip is None:
            return ["Move into camera view"]
        
        has_issues = False
        
        # Check if arm is fully extended at the bottom
        if bicep_angle > self.thresholds.get('bicep_curl_not_low_enough', 160):
            feedback.append("Extend your arm fully at the bottom")
            has_issues = True
        
        # Check if arm is curled high enough
        if bicep_angle > self.thresholds.get('bicep_curl_not_high_enough', 90) and self.state == BicepCurlState.CURL_UP:
            feedback.append("Curl the weight higher")
            has_issues = True
        
        # Check for elbow movement
        elbow_movement = ((elbow[0] - self.start_elbow_pos[0])**2 + 
                        (elbow[1] - self.start_elbow_pos[1])**2)**0.5
        if elbow_movement > self.thresholds.get('bicep_curl_elbow_movement', 5):
            feedback.append("Keep your elbow still")
            has_issues = True
        
        # Check for body swing
        if self.detect_body_swing(angles):
            swing_severity = "slightly" if self.max_swing_angle <= self.thresholds.get('bicep_curl_body_swing', 10) else "excessively"
            feedback.append(f"Your body is {swing_severity} swinging. Keep your body stable.")
            has_issues = True
        
        # Check elbow-torso angle for excessive movement
        elbow_torso_angle = angles.get(f'{primary_side}_elbow_torso_angle')
        if elbow_torso_angle is not None:
            smoothed_elbow_angle = self.update_elbow_angle(elbow_torso_angle)
            if smoothed_elbow_angle is not None:
                self.max_elbow_angle = max(self.max_elbow_angle, smoothed_elbow_angle)
                if self.max_elbow_angle > 35 and self.elbow_detection_confidence > self.confidence_threshold:
                    feedback.append("Keep your upper arm still, excessive elbow movement")
                    has_issues = True
                self.low_confidence_count = 0
        else:
            self.low_confidence_count += 1
            if self.low_confidence_count >= self.max_low_confidence_frames:
                feedback.append("Unable to detect elbow movement accurately")
                self.low_confidence_count = 0
        
        # Update min/max angles
        self.max_angle = max(self.max_angle, bicep_angle)
        self.min_angle = min(self.min_angle, bicep_angle)
        
        # Detect if the arm has reset between reps
        if self.last_angle < 90 and bicep_angle > 160:
            self.max_angle = bicep_angle
            self.min_angle = bicep_angle
            self.fully_extended = False
            self.curled_high_enough = False
        
        self.last_angle = bicep_angle
        
        # If no issues and a complete curl is detected, provide positive feedback
        if not has_issues and self.is_curl_completed():
            feedback.append("Correct form, keep it up")
        
        return feedback
    
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[BicepCurlState, List[str]]:
        """
        Update the bicep curl state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        # Calculate angles
        angles = self.calculate_exercise_angles(keypoints)
        
        # Determine which arm is doing the curl (use the one with the smallest angle)
        left_bicep_angle = angles.get('left_bicep_angle')
        right_bicep_angle = angles.get('right_bicep_angle')
        
        if left_bicep_angle is not None and right_bicep_angle is not None:
            bicep_angle = min(left_bicep_angle, right_bicep_angle)
            primary_side = 'left' if left_bicep_angle < right_bicep_angle else 'right'
        elif left_bicep_angle is not None:
            bicep_angle = left_bicep_angle
            primary_side = 'left'
        elif right_bicep_angle is not None:
            bicep_angle = right_bicep_angle
            primary_side = 'right'
        else:
            # Can't update state without visible arm
            return self.state, ["Can't detect arm position"]
        
        # Get relevant positions for the primary arm
        shoulder = keypoints.get(f'{primary_side}_shoulder')
        elbow = keypoints.get(f'{primary_side}_elbow')
        wrist = keypoints.get(f'{primary_side}_wrist')
        hip = keypoints.get(f'{primary_side}_hip')
        elbow_torso_angle = angles.get(f'{primary_side}_elbow_torso_angle')
        hip_shoulder_angle = angles.get(f'{primary_side}_hip_shoulder_angle')
        
        feedback = []
        is_start = False
        
        if self.state == BicepCurlState.IDLE:
            # Detect the start of a curl
            if bicep_angle < self.curl_start_threshold:
                self.state = BicepCurlState.CURL_START
                is_start = True
                self.feedback_manager.clear_feedback()
                self.rep_error = False
                
                # Initialize starting positions
                if shoulder is not None and elbow is not None and hip is not None:
                    self.reset()
                    self.start_shoulder_pos = shoulder
                    self.start_hip_pos = hip
                    self.start_elbow_pos = elbow
                    self.start_hip_shoulder_angle = hip_shoulder_angle
        
        elif self.state == BicepCurlState.CURL_START:
            # Detect if we're curling up
            if bicep_angle < self.curl_up_threshold:
                self.state = BicepCurlState.CURL_UP
            # If the person extended back instead of continuing the curl
            elif bicep_angle > self.last_angle:
                self.state = BicepCurlState.IDLE
        
        elif self.state == BicepCurlState.CURL_UP:
            # Detect when we reach the top of the curl
            if bicep_angle <= self.last_angle:
                self.state = BicepCurlState.CURL_HOLD
        
        elif self.state == BicepCurlState.CURL_HOLD:
            # Starting to lower the arm
            if bicep_angle > self.last_angle:
                self.state = BicepCurlState.CURL_DOWN
        
        elif self.state == BicepCurlState.CURL_DOWN:
            # Completed lowering the arm
            if bicep_angle >= self.curl_down_threshold:
                self.state = BicepCurlState.COMPLETED
                self.rep_count += 1
                
                # Reset to IDLE for next rep
                self.state = BicepCurlState.IDLE
        
        # Analyze form and gather feedback
        if not is_start and shoulder is not None and elbow is not None and wrist is not None and hip is not None:
            form_feedback = self.analyze_form(keypoints)
            
            for fb in form_feedback:
                if "Correct form" not in fb:
                    self.rep_error = True
                    self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                elif not self.rep_error:
                    self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
        
        # Update the previous angle for the next frame
        self.last_angle = bicep_angle
        
        return self.state, self.feedback_manager.get_feedback()
    
    def get_state_name(self) -> str:
        """Get the name of the current bicep curl state"""
        return self.state.name