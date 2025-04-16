from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackPriority

class LungeState(Enum):
    """States for the lunge exercise"""
    IDLE = 0
    LUNGE_START = 1
    LUNGE_DOWN = 2
    LUNGE_HOLD = 3
    LUNGE_UP = 4
    COMPLETED = 5

class LungeAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the lunge exercise
    
    Tracks the lunge movement through its stages and provides feedback
    on form and technique.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the lunge analyzer
        
        Args:
            thresholds: Dictionary of threshold values for lunge analysis
        """
        super().__init__(thresholds)
        self.state = LungeState.IDLE
        self.prev_knee_angle = 180
        
        # Thresholds for lunge
        self.lunge_start_threshold = 160   # Angle to detect start of lunge (legs straight)
        self.lunge_down_threshold = 120    # Angle to detect downward phase
        self.lunge_up_threshold = 150      # Angle to detect completion
        
        # Tracking knee alignment (to detect if knees cave in)
        self.knee_alignment_buffer = deque(maxlen=5)
        self.front_knee_angles = deque(maxlen=10)
        self.back_knee_angles = deque(maxlen=10)
        
        # To track which leg is forward
        self.forward_leg = None  # 'left' or 'right'
    
    def reset(self):
        """Reset the analyzer between reps"""
        super().reset()
        self.max_knee_angle = 0
        self.min_knee_angle = 180
        self.knee_alignment_buffer.clear()
        self.front_knee_angles.clear()
        self.back_knee_angles.clear()
        self.forward_leg = None
    
    def _detect_forward_leg(self, keypoints: Dict[str, List[float]]) -> Optional[str]:
        """
        Detect which leg is forward in the lunge
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            'left', 'right', or None if can't determine
        """
        left_foot_x = keypoints.get('left_ankle', [0, 0, 0, 0])[0]
        right_foot_x = keypoints.get('right_ankle', [0, 0, 0, 0])[0]
        
        # If the legs aren't detected well, try using knees instead
        if not left_foot_x or not right_foot_x:
            left_foot_x = keypoints.get('left_knee', [0, 0, 0, 0])[0]
            right_foot_x = keypoints.get('right_knee', [0, 0, 0, 0])[0]
        
        if not left_foot_x or not right_foot_x:
            return None
            
        # Determine which foot is more forward (smaller x value is more to the left)
        # This assumes the person is facing the camera
        return 'left' if left_foot_x < right_foot_x else 'right'
    
    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for lunge analysis
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        
        # First, determine which leg is forward if not already determined
        if self.forward_leg is None:
            self.forward_leg = self._detect_forward_leg(keypoints)
        
        # Calculate knee angles
        left_knee_angle = right_knee_angle = None
        if all(k in keypoints for k in ['left_hip', 'left_knee', 'left_ankle']):
            left_knee_angle = self.angle_calculator.angle_deg(
                keypoints['left_hip'], 
                keypoints['left_knee'], 
                keypoints['left_ankle']
            )
            angles['left_knee_angle'] = left_knee_angle
            
        if all(k in keypoints for k in ['right_hip', 'right_knee', 'right_ankle']):
            right_knee_angle = self.angle_calculator.angle_deg(
                keypoints['right_hip'], 
                keypoints['right_knee'], 
                keypoints['right_ankle']
            )
            angles['right_knee_angle'] = right_knee_angle
        
        # Identify front and back legs
        if self.forward_leg == 'left':
            front_knee_angle = left_knee_angle
            back_knee_angle = right_knee_angle
            front_knee = 'left_knee'
            back_knee = 'right_knee'
        elif self.forward_leg == 'right':
            front_knee_angle = right_knee_angle
            back_knee_angle = left_knee_angle
            front_knee = 'right_knee'
            back_knee = 'left_knee'
        else:
            # Can't determine which leg is forward
            return angles
            
        angles['front_knee_angle'] = front_knee_angle
        angles['back_knee_angle'] = back_knee_angle
        
        # Track front knee position (for knee valgus/varus detection)
        if front_knee in keypoints and front_knee.replace('knee', 'ankle') in keypoints and front_knee.replace('knee', 'hip') in keypoints:
            knee = keypoints[front_knee]
            ankle = keypoints[front_knee.replace('knee', 'ankle')]
            hip = keypoints[front_knee.replace('knee', 'hip')]
            
            # Check if knee is aligned with hip and ankle
            # Calculate expected knee position if it were perfectly aligned
            hip_ankle_vector = [ankle[0] - hip[0], ankle[1] - hip[1]]
            hip_knee_distance = ((knee[0] - hip[0])**2 + (knee[1] - hip[1])**2)**0.5
            expected_knee_pos = [
                hip[0] + hip_ankle_vector[0] * hip_knee_distance / ((hip_ankle_vector[0]**2 + hip_ankle_vector[1]**2)**0.5),
                hip[1] + hip_ankle_vector[1] * hip_knee_distance / ((hip_ankle_vector[0]**2 + hip_ankle_vector[1]**2)**0.5)
            ]
            
            # Calculate lateral deviation of knee from expected position
            knee_deviation = ((knee[0] - expected_knee_pos[0])**2 + (knee[1] - expected_knee_pos[1])**2)**0.5
            self.knee_alignment_buffer.append(knee_deviation)
            angles['knee_deviation'] = sum(self.knee_alignment_buffer) / len(self.knee_alignment_buffer)
        
        # Store knee angles for tracking
        if front_knee_angle is not None:
            self.front_knee_angles.append(front_knee_angle)
        if back_knee_angle is not None:
            self.back_knee_angles.append(back_knee_angle)
            
        return angles
    
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze lunge form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new rep
            
        Returns:
            List of feedback strings about the lunge form
        """
        feedback = []
        
        # Calculate relevant angles
        angles = self.calculate_exercise_angles(keypoints)
        front_knee_angle = angles.get('front_knee_angle')
        back_knee_angle = angles.get('back_knee_angle')
        knee_deviation = angles.get('knee_deviation')
        
        if is_start:
            self.reset()
            return feedback
            
        # Skip analysis if key angles aren't available
        if front_knee_angle is None or back_knee_angle is None:
            return ["Move into camera view"]
        
        # Only analyze form during the lunge (not in idle state)
        if self.state != LungeState.IDLE and min(front_knee_angle, back_knee_angle) < self.lunge_start_threshold:
            # Check front knee angle
            if front_knee_angle < self.thresholds.get('lunge_front_knee_angle_min', 80):
                feedback.append("Front knee bent too much")
            elif front_knee_angle > self.thresholds.get('lunge_front_knee_angle_max', 100):
                feedback.append("Bend front knee more")
            
            # Check back knee angle
            if back_knee_angle < self.thresholds.get('lunge_back_knee_angle_min', 80):
                feedback.append("Back knee bent too much")
            elif back_knee_angle > self.thresholds.get('lunge_back_knee_angle_max', 100):
                feedback.append("Lower your back knee more")
            
            # Check knee alignment (possible knee valgus)
            if knee_deviation and knee_deviation > 20:
                feedback.append("Keep front knee aligned with foot")
            
            # If no issues found, give positive feedback
            if not feedback:
                feedback.append("Correct form")
        
        return feedback
    
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[LungeState, List[str]]:
        """
        Update the lunge state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        angles = self.calculate_exercise_angles(keypoints)
        front_knee_angle = angles.get('front_knee_angle')
        back_knee_angle = angles.get('back_knee_angle')
        
        # Use the minimum angle of both knees to track the lunge
        knee_angle = min(front_knee_angle, back_knee_angle) if front_knee_angle is not None and back_knee_angle is not None else None
        
        if knee_angle is None:
            return self.state, ["Move into camera view"]
        
        feedback = []
        
        if self.state == LungeState.IDLE:
            # Detect the start of a lunge
            if knee_angle < self.lunge_start_threshold:
                self.state = LungeState.LUNGE_START
                self.feedback_manager.clear_feedback()
                self.reset()
                # Detect forward leg again in case user switched legs
                self.forward_leg = self._detect_forward_leg(keypoints)
        
        elif self.state == LungeState.LUNGE_START:
            # Detect if we're going down
            if knee_angle < self.lunge_down_threshold:
                self.state = LungeState.LUNGE_DOWN
            # If the person went back up instead of continuing down
            elif knee_angle > self.prev_knee_angle:
                self.state = LungeState.IDLE
                self.feedback_manager.clear_feedback()
                
        elif self.state == LungeState.LUNGE_DOWN:
            # Detect when we reach the bottom of the lunge
            if knee_angle <= self.prev_knee_angle:
                self.state = LungeState.LUNGE_HOLD
                feedback = self.analyze_form(keypoints)
                
                for fb in feedback:
                    if "Correct form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                        self.rep_error = True
                    elif not self.rep_error:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                
        elif self.state == LungeState.LUNGE_HOLD:
            # Starting to come back up
            if knee_angle > self.prev_knee_angle:
                self.state = LungeState.LUNGE_UP
                
        elif self.state == LungeState.LUNGE_UP:
            # Completed the lunge
            if knee_angle >= self.lunge_up_threshold:
                self.state = LungeState.COMPLETED
                self.rep_count += 1
                feedback = self.analyze_form(keypoints)
                
                for fb in feedback:
                    if "Correct form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                    else:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                        
                # Reset to IDLE for next rep
                self.state = LungeState.IDLE
                
        # Update the previous angle for the next frame
        self.prev_knee_angle = knee_angle
        
        return self.state, self.feedback_manager.get_feedback()
        
    def get_state_name(self) -> str:
        """Get the name of the current lunge state"""
        return self.state.name