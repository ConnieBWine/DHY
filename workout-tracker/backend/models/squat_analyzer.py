from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from models.exercise_base import ExerciseAnalyzer, ExerciseState
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackPriority

class SquatState(Enum):
    """States for the squat exercise"""
    IDLE = 0
    SQUAT_START = 1
    SQUAT_DOWN = 2
    SQUAT_HOLD = 3
    SQUAT_UP = 4
    COMPLETED = 5

class SquatAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the squat exercise
    
    Tracks the squat movement through its stages and provides feedback
    on form and technique.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the squat analyzer
        
        Args:
            thresholds: Dictionary of threshold values for squat analysis
        """
        super().__init__(thresholds)
        self.state = SquatState.IDLE
        self.prev_knee_angle = 180
        self.squat_threshold = self.thresholds.get('squat_not_deep_enough', 91)
        self.start_threshold = 160
        self.back_angles = []  # Store back angles for analysis
        
    def reset(self):
        """Reset the analyzer between reps"""
        super().reset()
        self.max_knee_angle = 0
        self.min_knee_angle = 180
        self.max_back_angle = 0
        self.min_back_angle = 90
        self.back_angles = []
        
    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for squat analysis
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        
        # Calculate knee angle (average of left and right if available)
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
            
        # Average knee angle
        if left_knee_angle is not None and right_knee_angle is not None:
            angles['knee_angle'] = (left_knee_angle + right_knee_angle) / 2
        elif left_knee_angle is not None:
            angles['knee_angle'] = left_knee_angle
        elif right_knee_angle is not None:
            angles['knee_angle'] = right_knee_angle
        else:
            angles['knee_angle'] = 180  # Default if not detected
            
        # Calculate back angle (how much forward lean)
        back_angle = None
        if all(k in keypoints for k in ['left_hip', 'left_shoulder']):
            left_back = self.angle_calculator.angle_deg(
                keypoints['left_hip'],
                keypoints['left_shoulder'],
                [keypoints['left_shoulder'][0], keypoints['left_hip'][1]]  # Vertical reference
            )
            angles['left_back_angle'] = left_back
            back_angle = left_back
            
        if all(k in keypoints for k in ['right_hip', 'right_shoulder']):
            right_back = self.angle_calculator.angle_deg(
                keypoints['right_hip'],
                keypoints['right_shoulder'],
                [keypoints['right_shoulder'][0], keypoints['right_hip'][1]]  # Vertical reference
            )
            angles['right_back_angle'] = right_back
            
            if back_angle is not None:
                back_angle = (back_angle + right_back) / 2
            else:
                back_angle = right_back
                
        if back_angle is not None:
            angles['back_angle'] = back_angle
            self.back_angles.append(back_angle)  # Track back angle over time
            
        return angles
    
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze squat form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new rep
            
        Returns:
            List of feedback strings about the squat form
        """
        feedback = []
        
        # Calculate relevant angles
        angles = self.calculate_exercise_angles(keypoints)
        knee_angle = angles.get('knee_angle', 180)
        back_angle = angles.get('back_angle')
        
        if is_start:
            self.reset()
            return feedback
            
        # Update min/max angles
        self.max_knee_angle = max(self.max_knee_angle, knee_angle)
        self.min_knee_angle = min(self.min_knee_angle, knee_angle)
        
        if back_angle is not None:
            self.max_back_angle = max(self.max_back_angle, back_angle)
            self.min_back_angle = min(self.min_back_angle, back_angle)
        
        # Only analyze form during the squat (not in idle state)
        if self.state != SquatState.IDLE and knee_angle < self.start_threshold:
            # Analyze depth
            if knee_angle < self.thresholds.get('squat_too_deep', 68):
                feedback.append("Don't squat too deep")
            elif knee_angle >= self.thresholds.get('squat_not_deep_enough', 91):
                feedback.append("Lower your hips")
                
            # Analyze back angle
            if back_angle is not None:
                if back_angle < self.thresholds.get('squat_forward_bend_too_little', 19):
                    feedback.append("Bend forward more")
                elif back_angle > self.thresholds.get('squat_forward_bend_too_much', 50):
                    feedback.append("Forward bending too much")
                    
            # Check if knees are caving in (knee valgus)
            # This requires comparing knee positions to ankle and hip positions
            # More complex analysis would go here
            
            # If no issues found, give positive feedback
            if not feedback:
                feedback.append("Correct form")
                
        return feedback
    
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[SquatState, List[str]]:
        """
        Update the squat state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        angles = self.calculate_exercise_angles(keypoints)
        knee_angle = angles.get('knee_angle', 180)
        back_angle = angles.get('back_angle')
        
        feedback = []
        
        if self.state == SquatState.IDLE:
            # Detect the start of a squat
            if knee_angle < self.start_threshold:
                self.state = SquatState.SQUAT_START
                self.feedback_manager.clear_feedback()
                self.reset()
        
        elif self.state == SquatState.SQUAT_START:
            # Detect if we're squatting down
            if knee_angle < self.squat_threshold:
                self.state = SquatState.SQUAT_DOWN
            # If the person stood back up instead of continuing the squat
            elif knee_angle > self.prev_knee_angle:
                self.state = SquatState.IDLE
                self.feedback_manager.clear_feedback()
                
        elif self.state == SquatState.SQUAT_DOWN:
            # Detect when we reach the bottom of the squat
            if knee_angle <= self.prev_knee_angle:
                self.state = SquatState.SQUAT_HOLD
                feedback = self.analyze_form(keypoints)
                
                for fb in feedback:
                    if "Correct form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                        self.rep_error = True
                    elif not self.rep_error:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                
        elif self.state == SquatState.SQUAT_HOLD:
            # Starting to come back up
            if knee_angle > self.prev_knee_angle:
                self.state = SquatState.SQUAT_UP
                
        elif self.state == SquatState.SQUAT_UP:
            # Completed the squat
            if knee_angle >= self.start_threshold:
                self.state = SquatState.COMPLETED
                self.rep_count += 1
                feedback = self.analyze_form(keypoints)
                
                for fb in feedback:
                    if "Correct form" not in fb:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.HIGH)
                    else:
                        self.feedback_manager.add_feedback(fb, FeedbackPriority.LOW)
                        
                # Reset to IDLE for next rep
                self.state = SquatState.IDLE
                
        # Update the previous angle for the next frame
        self.prev_knee_angle = knee_angle
        
        return self.state, self.feedback_manager.get_feedback()
        
    def get_state_name(self) -> str:
        """Get the name of the current squat state"""
        return self.state.name