from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import time
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackPriority

class PlankState(Enum):
    """States for the plank exercise"""
    IDLE = 0
    PLANK_POSITION = 1
    PLANK_HOLD = 2
    COMPLETED = 3

class PlankAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the plank exercise
    
    Tracks plank position and provides feedback on form and technique.
    This is a timed exercise, not rep-based.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the plank analyzer
        
        Args:
            thresholds: Dictionary of threshold values for plank analysis
        """
        super().__init__(thresholds)
        self.state = PlankState.IDLE
        
        # For timed exercise tracking
        self.start_time = None
        self.hold_time = 0
        self.last_time_update = None
        self.target_duration = 0  # Will be set by the user
        
        # Form analysis
        self.hip_alignment_buffer = deque(maxlen=10)
        self.body_angle_buffer = deque(maxlen=10)
        self.is_in_position_counter = 0
        self.required_frames_in_position = 5  # Number of consecutive frames to confirm plank position
    
    def reset(self):
        """Reset the analyzer state"""
        super().reset()
        self.start_time = None
        self.hold_time = 0
        self.last_time_update = None
        self.hip_alignment_buffer.clear()
        self.body_angle_buffer.clear()
        self.is_in_position_counter = 0
    
    def set_target_duration(self, seconds: int):
        """Set the target duration for the plank hold"""
        self.target_duration = seconds
    
    def is_timed_exercise(self) -> bool:
        """This is a timed exercise"""
        return True
    
    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for plank analysis
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        
        # Calculate body alignment (straight line from ankles through hips to shoulders)
        # For a plank, we need to determine if the body is in a straight line
        
        # Get keypoints
        left_shoulder = keypoints.get('left_shoulder')
        right_shoulder = keypoints.get('right_shoulder')
        left_hip = keypoints.get('left_hip')
        right_hip = keypoints.get('right_hip')
        left_ankle = keypoints.get('left_ankle')
        right_ankle = keypoints.get('right_ankle')
        
        # Calculate average positions for more stability
        shoulder_pos = None
        if left_shoulder is not None and right_shoulder is not None:
            shoulder_pos = [
                (left_shoulder[0] + right_shoulder[0]) / 2,
                (left_shoulder[1] + right_shoulder[1]) / 2
            ]
        elif left_shoulder is not None:
            shoulder_pos = left_shoulder[:2]
        elif right_shoulder is not None:
            shoulder_pos = right_shoulder[:2]
            
        hip_pos = None
        if left_hip is not None and right_hip is not None:
            hip_pos = [
                (left_hip[0] + right_hip[0]) / 2,
                (left_hip[1] + right_hip[1]) / 2
            ]
        elif left_hip is not None:
            hip_pos = left_hip[:2]
        elif right_hip is not None:
            hip_pos = right_hip[:2]
            
        ankle_pos = None
        if left_ankle is not None and right_ankle is not None:
            ankle_pos = [
                (left_ankle[0] + right_ankle[0]) / 2,
                (left_ankle[1] + right_ankle[1]) / 2
            ]
        elif left_ankle is not None:
            ankle_pos = left_ankle[:2]
        elif right_ankle is not None:
            ankle_pos = right_ankle[:2]
        
        # Calculate hip alignment (sagging or piking)
        if shoulder_pos and hip_pos and ankle_pos:
            # Calculate the angle between shoulder-hip line and hip-ankle line
            shoulder_hip_angle = np.arctan2(hip_pos[1] - shoulder_pos[1], hip_pos[0] - shoulder_pos[0])
            hip_ankle_angle = np.arctan2(ankle_pos[1] - hip_pos[1], ankle_pos[0] - hip_pos[0])
            
            # Calculate the difference between the angles
            angle_diff = np.abs(shoulder_hip_angle - hip_ankle_angle)
            body_angle = np.degrees(angle_diff)
            
            # Calculate hip height relative to the shoulder-ankle line
            # Project hip point onto the shoulder-ankle line
            shoulder_ankle_vector = [ankle_pos[0] - shoulder_pos[0], ankle_pos[1] - shoulder_pos[1]]
            shoulder_hip_vector = [hip_pos[0] - shoulder_pos[0], hip_pos[1] - shoulder_pos[1]]
            
            # Calculate the projection
            dot_product = (shoulder_hip_vector[0] * shoulder_ankle_vector[0] + 
                           shoulder_hip_vector[1] * shoulder_ankle_vector[1])
            squared_len = (shoulder_ankle_vector[0]**2 + shoulder_ankle_vector[1]**2)
            
            if squared_len > 0:
                projection_factor = dot_product / squared_len
                projected_point = [
                    shoulder_pos[0] + projection_factor * shoulder_ankle_vector[0],
                    shoulder_pos[1] + projection_factor * shoulder_ankle_vector[1]
                ]
                
                # Calculate distance from hip to the projected point
                hip_alignment = ((hip_pos[0] - projected_point[0])**2 + 
                                 (hip_pos[1] - projected_point[1])**2)**0.5
                
                # Determine if hips are sagging or piking
                # Cross product to determine direction
                cross_product = (shoulder_hip_vector[0] * shoulder_ankle_vector[1] - 
                                 shoulder_hip_vector[1] * shoulder_ankle_vector[0])
                
                # Positive means hip is above the line (piking), negative means below (sagging)
                if cross_product < 0:
                    hip_alignment = -hip_alignment
                    
                self.hip_alignment_buffer.append(hip_alignment)
                angles['hip_alignment'] = sum(self.hip_alignment_buffer) / len(self.hip_alignment_buffer)
                
                self.body_angle_buffer.append(body_angle)
                angles['body_angle'] = sum(self.body_angle_buffer) / len(self.body_angle_buffer)
        
        return angles
    
    def is_in_plank_position(self, keypoints: Dict[str, List[float]]) -> bool:
        """
        Determine if the person is in a plank position
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            True if in plank position, False otherwise
        """
        # For a plank, we need:
        # 1. Body in relatively straight line (shoulders, hips, ankles)
        # 2. Body relatively horizontal
        
        angles = self.calculate_exercise_angles(keypoints)
        hip_alignment = angles.get('hip_alignment')
        body_angle = angles.get('body_angle')
        
        if hip_alignment is None or body_angle is None:
            return False
            
        # Check if hips are properly aligned (not sagging or piking)
        if abs(hip_alignment) > self.thresholds.get('plank_hip_sag', 15):
            return False
            
        # Check if body is in a relatively straight line
        if body_angle > 30:  # Body should be relatively straight
            return False
            
        return True
    
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze plank form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new plank
            
        Returns:
            List of feedback strings about the plank form
        """
        feedback = []
        
        if is_start:
            self.reset()
            return feedback
            
        # Calculate relevant angles
        angles = self.calculate_exercise_angles(keypoints)
        hip_alignment = angles.get('hip_alignment')
        body_angle = angles.get('body_angle')
        
        if hip_alignment is None or body_angle is None:
            return ["Move into camera view"]
            
        # Analyze hip alignment
        if hip_alignment > self.thresholds.get('plank_hip_pike', 25):
            feedback.append("Lower your hips, don't pike")
        elif hip_alignment < -self.thresholds.get('plank_hip_sag', 15):
            feedback.append("Raise your hips, don't sag")
            
        # Analyze body alignment
        if body_angle > 30:
            feedback.append("Straighten your body")
            
        # If no issues found, give positive feedback
        if not feedback:
            feedback.append("Good plank form")
            
        return feedback
    
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[PlankState, List[str]]:
        """
        Update the plank state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        feedback = []
        now = time.time()
        
        # Check if person is in plank position
        is_in_position = self.is_in_plank_position(keypoints)
        
        if self.state == PlankState.IDLE:
            # Detect the start of a plank
            if is_in_position:
                self.is_in_position_counter += 1
                if self.is_in_position_counter >= self.required_frames_in_position:
                    # Plank position confirmed
                    self.state = PlankState.PLANK_POSITION
                    self.feedback_manager.clear_feedback()
                    self.reset()
                    self.start_time = now
                    self.last_time_update = now
            else:
                self.is_in_position_counter = 0
        
        elif self.state == PlankState.PLANK_POSITION:
            # Started holding the plank
            if is_in_position:
                self.state = PlankState.PLANK_HOLD
            else:
                # False start, go back to idle
                self.state = PlankState.IDLE
                self.is_in_position_counter = 0
                
        elif self.state == PlankState.PLANK_HOLD:
            # Check if still holding plank
            if is_in_position:
                # Update hold time
                if self.last_time_update:
                    self.hold_time += now - self.last_time_update
                self.last_time_update = now
                
                # Analyze form and provide feedback
                form_feedback = self.analyze_form(keypoints)
                for fb in form_feedback:
                    if "Good plank form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                    else:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                
                # Check if reached target duration
                if self.target_duration > 0 and self.hold_time >= self.target_duration:
                    self.state = PlankState.COMPLETED
                    self.rep_count += 1  # Count as one completed plank
                    
                    # Reset for next plank if needed
                    self.state = PlankState.IDLE
                    self.is_in_position_counter = 0
                    
            else:
                # Lost plank position
                self.state = PlankState.IDLE
                self.is_in_position_counter = 0
                
                # If held for a significant time, count as completed
                if self.hold_time >= 5:  # At least 5 seconds to count
                    self.rep_count += 1
                    
        # Return feedback
        return self.state, self.feedback_manager.get_feedback()
    
    def get_hold_time(self) -> float:
        """Get the current plank hold time in seconds"""
        return self.hold_time
    
    def get_remaining_time(self) -> float:
        """Get the remaining time for the plank hold"""
        if self.target_duration <= 0:
            return 0
        remaining = max(0, self.target_duration - self.hold_time)
        return remaining
    
    def get_state_name(self) -> str:
        """Get the name of the current plank state"""
        return self.state.name