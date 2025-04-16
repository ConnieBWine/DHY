from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackPriority

class PushupState(Enum):
    """States for the pushup exercise"""
    IDLE = 0
    PUSHUP_START = 1
    PUSHUP_DOWN = 2
    PUSHUP_HOLD = 3
    PUSHUP_UP = 4
    COMPLETED = 5

class PushupAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the pushup exercise
    
    Tracks the pushup movement through its stages and provides feedback
    on form and technique.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the pushup analyzer
        
        Args:
            thresholds: Dictionary of threshold values for pushup analysis
        """
        super().__init__(thresholds)
        self.state = PushupState.IDLE
        self.prev_elbow_angle = 180
        
        # Thresholds for pushup
        self.pushup_start_threshold = 160   # Angle to detect start of pushup (arms extended)
        self.pushup_down_threshold = 120    # Angle to detect downward phase
        self.pushup_up_threshold = 150      # Angle to detect completion
        
        # Hip alignment tracking
        self.hip_heights = deque(maxlen=10)
        self.shoulder_heights = deque(maxlen=10)
        self.hip_alignment_buffer = deque(maxlen=5)
    
    def reset(self):
        """Reset the analyzer between reps"""
        super().reset()
        self.max_elbow_angle = 0
        self.min_elbow_angle = 180
        self.hip_heights.clear()
        self.shoulder_heights.clear()
        self.hip_alignment_buffer.clear()
    
    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for pushup analysis
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        
        # Calculate elbow angle for pushup (average of left and right if available)
        left_elbow_angle = right_elbow_angle = None
        if all(k in keypoints for k in ['left_shoulder', 'left_elbow', 'left_wrist']):
            left_elbow_angle = self.angle_calculator.angle_deg(
                keypoints['left_shoulder'], 
                keypoints['left_elbow'], 
                keypoints['left_wrist']
            )
            angles['left_elbow_angle'] = left_elbow_angle
            
        if all(k in keypoints for k in ['right_shoulder', 'right_elbow', 'right_wrist']):
            right_elbow_angle = self.angle_calculator.angle_deg(
                keypoints['right_shoulder'], 
                keypoints['right_elbow'], 
                keypoints['right_wrist']
            )
            angles['right_elbow_angle'] = right_elbow_angle
            
        # Average elbow angle
        if left_elbow_angle is not None and right_elbow_angle is not None:
            angles['elbow_angle'] = (left_elbow_angle + right_elbow_angle) / 2
        elif left_elbow_angle is not None:
            angles['elbow_angle'] = left_elbow_angle
        elif right_elbow_angle is not None:
            angles['elbow_angle'] = right_elbow_angle
        else:
            angles['elbow_angle'] = 180  # Default if not detected
            
        # Calculate spine/hip alignment
        # This checks if the hips are sagging or pike (raised too high)
        
        # Get hip and shoulder heights
        left_hip_y = keypoints.get('left_hip', [0, 0, 0, 0])[1]
        right_hip_y = keypoints.get('right_hip', [0, 0, 0, 0])[1]
        left_shoulder_y = keypoints.get('left_shoulder', [0, 0, 0, 0])[1]
        right_shoulder_y = keypoints.get('right_shoulder', [0, 0, 0, 0])[1]
        
        hip_y = (left_hip_y + right_hip_y) / 2 if left_hip_y and right_hip_y else (left_hip_y or right_hip_y)
        shoulder_y = (left_shoulder_y + right_shoulder_y) / 2 if left_shoulder_y and right_shoulder_y else (left_shoulder_y or right_shoulder_y)
        
        if hip_y and shoulder_y:
            # Add to height buffers
            self.hip_heights.append(hip_y)
            self.shoulder_heights.append(shoulder_y)
            
            # Calculate hip-shoulder alignment
            if len(self.hip_heights) > 5 and len(self.shoulder_heights) > 5:
                avg_hip_y = sum(self.hip_heights) / len(self.hip_heights)
                avg_shoulder_y = sum(self.shoulder_heights) / len(self.shoulder_heights)
                
                # Calculate hip alignment angle (in a side view, this would be the angle between the hip, shoulder, and a horizontal line)
                # Since we're using a front-facing camera, we approximate with Y-coordinate differences
                hip_alignment = avg_hip_y - avg_shoulder_y
                self.hip_alignment_buffer.append(hip_alignment)
                
                avg_hip_alignment = sum(self.hip_alignment_buffer) / len(self.hip_alignment_buffer)
                angles['hip_alignment'] = avg_hip_alignment
                
                # Positive values (hip_y > shoulder_y) mean hips are lower than shoulders (sagging)
                # Negative values (hip_y < shoulder_y) mean hips are higher than shoulders (piking)
        
        return angles
    
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze pushup form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new rep
            
        Returns:
            List of feedback strings about the pushup form
        """
        feedback = []
        
        # Calculate relevant angles
        angles = self.calculate_exercise_angles(keypoints)
        elbow_angle = angles.get('elbow_angle', 180)
        hip_alignment = angles.get('hip_alignment')
        
        if is_start:
            self.reset()
            return feedback
            
        # Update min/max angles
        self.max_elbow_angle = max(self.max_elbow_angle, elbow_angle)
        self.min_elbow_angle = min(self.min_elbow_angle, elbow_angle)
        
        # Only analyze form during the pushup (not in idle state)
        if self.state != PushupState.IDLE and elbow_angle < self.pushup_start_threshold:
            # Analyze depth
            if elbow_angle < self.thresholds.get('pushup_too_low', 70):
                feedback.append("You're going too low")
            elif elbow_angle >= self.thresholds.get('pushup_not_low_enough', 120):
                feedback.append("Lower your chest more")
                
            # Analyze hip alignment
            if hip_alignment is not None:
                if hip_alignment > self.thresholds.get('pushup_hip_sag', 15):
                    feedback.append("Keep your hips up, core engaged")
                elif hip_alignment < -self.thresholds.get('pushup_hip_pike', 25):
                    feedback.append("Lower your hips, maintain a straight line")
                    
            # If no issues found, give positive feedback
            if not feedback:
                feedback.append("Correct form")
                
        return feedback
    
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[PushupState, List[str]]:
        """
        Update the pushup state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        angles = self.calculate_exercise_angles(keypoints)
        elbow_angle = angles.get('elbow_angle', 180)
        
        feedback = []
        
        if self.state == PushupState.IDLE:
            # Detect the start of a pushup (arms extended)
            if elbow_angle < self.pushup_start_threshold:
                self.state = PushupState.PUSHUP_START
                self.feedback_manager.clear_feedback()
                self.reset()
        
        elif self.state == PushupState.PUSHUP_START:
            # Detect if we're going down
            if elbow_angle < self.pushup_down_threshold:
                self.state = PushupState.PUSHUP_DOWN
            # If the person went back up instead of continuing down
            elif elbow_angle > self.prev_elbow_angle:
                self.state = PushupState.IDLE
                self.feedback_manager.clear_feedback()
                
        elif self.state == PushupState.PUSHUP_DOWN:
            # Detect when we reach the bottom of the pushup
            if elbow_angle <= self.prev_elbow_angle:
                self.state = PushupState.PUSHUP_HOLD
                feedback = self.analyze_form(keypoints)
                
                for fb in feedback:
                    if "Correct form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                        self.rep_error = True
                    elif not self.rep_error:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                
        elif self.state == PushupState.PUSHUP_HOLD:
            # Starting to come back up
            if elbow_angle > self.prev_elbow_angle:
                self.state = PushupState.PUSHUP_UP
                
        elif self.state == PushupState.PUSHUP_UP:
            # Completed the pushup, back to starting position
            if elbow_angle >= self.pushup_up_threshold:
                self.state = PushupState.COMPLETED
                self.rep_count += 1
                feedback = self.analyze_form(keypoints)
                
                for fb in feedback:
                    if "Correct form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                    else:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                        
                # Reset to IDLE for next rep
                self.state = PushupState.IDLE
                
        # Update the previous angle for the next frame
        self.prev_elbow_angle = elbow_angle
        
        return self.state, self.feedback_manager.get_feedback()
        
    def get_state_name(self) -> str:
        """Get the name of the current pushup state"""
        return self.state.name