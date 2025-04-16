from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from models.angle_calculator import AngleCalculator
from utils.feedback_manager import FeedbackManager, FeedbackPriority

class ExerciseState(Enum):
    """Base exercise state enum. Each exercise should define its own states."""
    IDLE = 0
    PREPARING = 1
    EXECUTING = 2
    HOLDING = 3
    RETURNING = 4
    COMPLETED = 5

class ExerciseAnalyzer(ABC):
    """
    Base class for exercise analyzers
    
    This abstract class defines the interface and common functionality
    for all exercise analyzers. Specific exercises should subclass this.
    """
    
    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the exercise analyzer
        
        Args:
            thresholds: Dictionary of threshold values for the exercise
        """
        self.thresholds = thresholds
        self.angle_calculator = AngleCalculator()
        self.feedback_manager = FeedbackManager()
        self.rep_error = False
        self.rep_count = 0
        self.state = ExerciseState.IDLE
        self.reset()
        
    def reset(self):
        """Reset the analyzer state between reps"""
        self.start_positions = {}
        self.max_angles = {}
        self.min_angles = {}
        self.feedback = []
        self.rep_error = False
        
    @abstractmethod
    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze the exercise form based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new rep
            
        Returns:
            List of feedback strings about the exercise form
        """
        pass
    
    @abstractmethod
    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[Any, List[str]]:
        """
        Update the exercise state based on detected keypoints
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Tuple of (current state, feedback list)
        """
        pass
    
    def get_rep_count(self) -> int:
        """Get the current rep count"""
        return self.rep_count
    
    def get_state_name(self) -> str:
        """Get the name of the current state"""
        return self.state.name if hasattr(self.state, 'name') else str(self.state)
    
    def get_feedback(self) -> List[str]:
        """Get current feedback for the exercise"""
        return self.feedback_manager.get_feedback()
    
    def is_timed_exercise(self) -> bool:
        """Whether this is a timed exercise (vs. rep-based)"""
        return False
    
    def get_exercise_type(self) -> str:
        """Get the type of exercise (should match class name)"""
        return self.__class__.__name__.replace('Analyzer', '')

    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate relevant angles for the exercise
        
        Args:
            keypoints: Dictionary of landmark keypoints
            
        Returns:
            Dictionary of angle names and values
        """
        # Base implementation - should be overridden by subclasses
        return {}