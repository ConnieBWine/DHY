from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import time
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackPriority

class JumpingJackState(Enum):
    """States for the jumping jack exercise"""
    IDLE = 0
    STARTING = 1
    ARMS_UP = 2
    LEGS_APART = 3
    RETURNING = 4
    COMPLETED = 5

class JumpingJackAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the jumping jack exercise
    
    Tracks the jumping jack movement through its stages and provides feedback
    on form and technique. Can be used as a timed exercise or rep-based.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the jumping jack analyzer
        
        Args:
            thresholds: Dictionary of threshold values for jumping jack analysis
        """
        super().__init__(thresholds)
        self.state = JumpingJackState.IDLE
        
        # Thresholds for jumping jack
        self.arm_extension_threshold = self.thresholds.get('jumping_jack_arm_extension', 140)
        self.leg_spread_threshold = self.thresholds.get('jumping_jack_leg_spread', 35)
        
        # For timed mode
        self.is_timed_mode = False
        self.start_time = None
        self.elapsed_time = 0
        self.last_time_update = None
        self.target_duration = 0
        
        # Movement tracking
        self.arm_angle_buffer = deque(maxlen=5)
        self.leg_spread_buffer = deque(maxlen=5)
        self.cycle_time_buffer = deque(maxlen=10)
        self.last_rep_time = None
    
    def reset(self):
        """Reset the analyzer state"""
        super().reset()
        if not self.is_timed_mode:
            self.start_time = None
            self.elapsed_time = 0
            self.last_time_update = None
        
        self.arm_angle_buffer.clear()
        self.leg_spread_buffer.clear()
        self.last_rep_time = None
    
    def set_timed_mode(self, is_timed: bool, duration: int = 0):
        """
        Set whether this is a timed exercise or rep-based
        
        Args:
            is_timed: True for timed exercise, False for rep-based
            duration: Target duration in seconds for timed mode
        """
        self.is_timed_mode = is_timed
        self.target_duration = duration
        if is_timed:
            self.start_time = time.time()
            self.last_time_update = self.start_time
    
    def is_timed_exercise(self) -> bool:
        """Whether this is currently configured as a timed exercise"""
        return self.is_timed_mode
    
    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for jumping jack analysis
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        
        # Calculate arm angles (angle between shoulders and wrists)
        left_arm_angle = right_arm_angle = None
        if all(k in keypoints for k in ['left_shoulder', 'left_hip', 'left_wrist']):
            left_arm_angle = self.angle_calculator.angle_deg(
                keypoints['left_hip'], 
                keypoints['left_shoulder'], 
                keypoints['left_wrist']
            )
            angles['left_arm_angle'] = left_arm_angle
            
        if all(k in keypoints for k in ['right_shoulder', 'right_hip', 'right_wrist']):
            right_arm_angle = self.angle_calculator.angle_deg(
                keypoints['right_hip'], 
                keypoints['right_shoulder'], 
                keypoints['right_wrist']
            )
            angles['right_arm_angle'] = right_arm_angle
            
        # Average arm angle
        if left_arm_angle is not None and right_arm_angle is not None:
            angles['arm_angle'] = (left_arm_angle + right_arm_angle) / 2
        elif left_arm_angle is not None:
            angles['arm_angle'] = left_arm_angle
        elif right_arm_angle is not None:
            angles['arm_angle'] = right_arm_angle
            
        # Calculate leg spread (distance between ankles relative to hip width)
        if all(k in keypoints for k in ['left_hip', 'right_hip', 'left_ankle', 'right_ankle']):
            left_hip = keypoints['left_hip']
            right_hip = keypoints['right_hip']
            left_ankle = keypoints['left_ankle']
            right_ankle = keypoints['right_ankle']
            
            hip_width = ((right_hip[0] - left_hip[0])**2 + (right_hip[1] - left_hip[1])**2)**0.5
            ankle_spread = ((right_ankle[0] - left_ankle[0])**2 + (right_ankle[1] - left_ankle[1])**2)**0.5
            
            if hip_width > 0:  # Avoid division by zero
                leg_spread_ratio = ankle_spread / hip_width
                angles['leg_spread_ratio'] = leg_spread_ratio
                
                # Smooth the leg spread ratio
                self.leg_spread_buffer.append(leg_spread_ratio)
                angles['smoothed_leg_spread'] = sum(self.leg_spread_buffer) / len(self.leg_spread_buffer)
                
        # Store arm angle for smoothing
        if 'arm_angle' in angles:
            self.arm_angle_buffer.append(angles['arm_angle'])
            angles['smoothed_arm_angle'] = sum(self.arm_angle_buffer) / len(self.arm_angle_buffer)
                
        return angles
    
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze jumping jack form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new exercise
            
        Returns:
            List of feedback strings about the jumping jack form
        """
        feedback = []
        
        if is_start:
            self.reset()
            return feedback
            
        # Calculate relevant angles
        angles = self.calculate_exercise_angles(keypoints)
        arm_angle = angles.get('smoothed_arm_angle')
        leg_spread = angles.get('smoothed_leg_spread')
        
        if arm_angle is None or leg_spread is None:
            return ["Move into camera view"]
            
        # Check arm extension
        if self.state in [JumpingJackState.ARMS_UP, JumpingJackState.LEGS_APART] and arm_angle < self.arm_extension_threshold:
            feedback.append("Raise your arms higher")
            
        # Check leg spread
        if self.state in [JumpingJackState.LEGS_APART] and leg_spread < self.leg_spread_threshold:
            feedback.append("Spread your legs wider")
            
        # Check timing/rhythm if we have enough data
        if len(self.cycle_time_buffer) > 3:
            avg_cycle_time = sum(self.cycle_time_buffer) / len(self.cycle_time_buffer)
            if avg_cycle_time < 0.5:  # Too fast
                feedback.append("Slow down for better form")
            elif avg_cycle_time > 2.0:  # Too slow
                feedback.append("Try to keep a steady rhythm")
                
        # If no issues found, give positive feedback
        if not feedback and self.state in [JumpingJackState.ARMS_UP, JumpingJackState.LEGS_APART]:
            feedback.append("Good jumping jack form")
            
        return feedback
    
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[JumpingJackState, List[str]]:
        """
        Update the jumping jack state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        feedback = []
        now = time.time()
        
        # Update elapsed time if in timed mode
        if self.is_timed_mode:
            if self.last_time_update:
                self.elapsed_time += now - self.last_time_update
            self.last_time_update = now
            
            # Check if reached target duration
            if self.target_duration > 0 and self.elapsed_time >= self.target_duration:
                self.state = JumpingJackState.COMPLETED
                return self.state, ["Time complete!"]
        
        # Calculate angles
        angles = self.calculate_exercise_angles(keypoints)
        arm_angle = angles.get('smoothed_arm_angle')
        leg_spread = angles.get('smoothed_leg_spread')
        
        if arm_angle is None or leg_spread is None:
            return self.state, ["Move into camera view"]
        
        # State transitions for jumping jack
        if self.state == JumpingJackState.IDLE:
            # Detect the start of a jumping jack (arms starting to raise)
            if arm_angle > 90 and arm_angle < self.arm_extension_threshold:
                self.state = JumpingJackState.STARTING
                self.feedback_manager.clear_feedback()
                
                if self.last_rep_time is not None:
                    # Calculate cycle time for rhythm analysis
                    cycle_time = now - self.last_rep_time
                    if 0.5 < cycle_time < 5.0:  # Reasonable range for a cycle
                        self.cycle_time_buffer.append(cycle_time)
                
                self.last_rep_time = now
                
        elif self.state == JumpingJackState.STARTING:
            # Arms raised fully
            if arm_angle >= self.arm_extension_threshold:
                self.state = JumpingJackState.ARMS_UP
                form_feedback = self.analyze_form(keypoints)
                
                for fb in form_feedback:
                    if "Good jumping jack form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.MEDIUM)
                    else:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                        
        elif self.state == JumpingJackState.ARMS_UP:
            # Legs spread apart
            if leg_spread >= self.leg_spread_threshold:
                self.state = JumpingJackState.LEGS_APART
                form_feedback = self.analyze_form(keypoints)
                
                for fb in form_feedback:
                    if "Good jumping jack form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                    else:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                
        elif self.state == JumpingJackState.LEGS_APART:
            # Starting to return to standing position
            if arm_angle < self.arm_extension_threshold or leg_spread < self.leg_spread_threshold:
                self.state = JumpingJackState.RETURNING
                
        elif self.state == JumpingJackState.RETURNING:
            # Completed the jumping jack
            if arm_angle < 80 and leg_spread < 1.2:  # Arms down and legs together
                self.state = JumpingJackState.COMPLETED
                self.rep_count += 1
                
                # Reset to IDLE for next rep
                self.state = JumpingJackState.IDLE
                
        # Return feedback
        return self.state, self.feedback_manager.get_feedback()
    
    def get_elapsed_time(self) -> float:
        """Get the elapsed time for timed mode"""
        return self.elapsed_time
    
    def get_remaining_time(self) -> float:
        """Get the remaining time for timed mode"""
        if not self.is_timed_mode or self.target_duration <= 0:
            return 0
        remaining = max(0, self.target_duration - self.elapsed_time)
        return remaining
    
    def get_state_name(self) -> str:
        """Get the name of the current jumping jack state"""
        return self.state.name