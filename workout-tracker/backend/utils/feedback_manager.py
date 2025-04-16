from enum import Enum
from collections import deque
import heapq
from typing import List, Tuple, Dict, Any

class FeedbackPriority(Enum):
    """Enum for feedback priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class FeedbackManager:
    """
    Manages and prioritizes exercise feedback
    
    This class keeps track of recent feedback messages,
    prioritizes them, and provides the most important
    feedback to display to the user.
    """
    
    def __init__(self, window_size=5):
        """
        Initialize the feedback manager
        
        Args:
            window_size: Number of recent feedback items to track
        """
        self.feedback_window = deque(maxlen=window_size)
        self.current_feedback = []
        self.priority_queue = []
        self.all_feedback = {}  # For statistics tracking

    def add_feedback(self, feedback: str, priority: FeedbackPriority):
        """
        Add a new feedback item
        
        Args:
            feedback: Feedback message string
            priority: Priority level (LOW, MEDIUM, HIGH)
        """
        heapq.heappush(self.priority_queue, (-priority.value, feedback))
        self.feedback_window.append((feedback, priority))
        
        # Track all feedback for statistics
        if feedback in self.all_feedback:
            self.all_feedback[feedback] += 1
        else:
            self.all_feedback[feedback] = 1
            
        self._process_feedback()

    def _process_feedback(self):
        """Process recent feedback to determine current messages to display"""
        feedback_count = {}
        for feedback, priority in self.feedback_window:
            if feedback in feedback_count:
                feedback_count[feedback] += 1
            else:
                feedback_count[feedback] = 1

        # Only keep feedback that appears frequently enough
        threshold = len(self.feedback_window) // 2
        self.current_feedback = [fb for fb, count in feedback_count.items() if count > threshold]

    def get_feedback(self) -> List[str]:
        """
        Get the current highest priority feedback
        
        Returns:
            List of feedback messages to display
        """
        if self.priority_queue:
            _, top_feedback = self.priority_queue[0]
            return [top_feedback]
        return []

    def get_all_feedback(self) -> Dict[str, int]:
        """
        Get all feedback with occurrence count for statistics
        
        Returns:
            Dictionary with feedback messages as keys and counts as values
        """
        return self.all_feedback

    def clear_feedback(self):
        """Clear all current feedback"""
        self.feedback_window.clear()
        self.current_feedback = []
        self.priority_queue = []

class SessionFeedbackManager:
    """
    Manages feedback for an entire workout session
    
    Tracks feedback across multiple exercises and reps,
    and provides statistics for the session.
    """
    
    def __init__(self):
        """Initialize the session feedback manager"""
        self.exercise_feedback = {}  # Dict of exercise_name -> FeedbackManager
        self.session_stats = {}      # Overall session statistics

    def get_feedback_manager(self, exercise_name: str) -> FeedbackManager:
        """
        Get or create a feedback manager for a specific exercise
        
        Args:
            exercise_name: Name of the exercise
            
        Returns:
            FeedbackManager for the specified exercise
        """
        if exercise_name not in self.exercise_feedback:
            self.exercise_feedback[exercise_name] = FeedbackManager()
        return self.exercise_feedback[exercise_name]

    def add_feedback(self, exercise_name: str, feedback: str, priority: FeedbackPriority):
        """
        Add feedback for a specific exercise
        
        Args:
            exercise_name: Name of the exercise
            feedback: Feedback message
            priority: Feedback priority
        """
        manager = self.get_feedback_manager(exercise_name)
        manager.add_feedback(feedback, priority)
        
        # Update session stats
        if exercise_name not in self.session_stats:
            self.session_stats[exercise_name] = {}
        
        if feedback in self.session_stats[exercise_name]:
            self.session_stats[exercise_name][feedback] += 1
        else:
            self.session_stats[exercise_name][feedback] = 1

    def get_session_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics for the current session
        
        Returns:
            Dictionary with exercise names as keys and feedback stats as values
        """
        return self.session_stats

    def get_common_issues(self, exercise_name: str = None, limit: int = 3) -> List[Tuple[str, int]]:
        """
        Get the most common issues in the session
        
        Args:
            exercise_name: Optional exercise name to filter by
            limit: Maximum number of issues to return
            
        Returns:
            List of (feedback, count) tuples sorted by count
        """
        if exercise_name:
            if exercise_name not in self.session_stats:
                return []
            stats = self.session_stats[exercise_name]
        else:
            # Combine stats across all exercises
            stats = {}
            for exercise, feedback_dict in self.session_stats.items():
                for feedback, count in feedback_dict.items():
                    if feedback in stats:
                        stats[feedback] += count
                    else:
                        stats[feedback] = count
        
        # Sort by count (descending) and take top issues
        sorted_issues = sorted(
            [(feedback, count) for feedback, count in stats.items() if "Correct form" not in feedback],
            key=lambda x: x[1], 
            reverse=True
        )
        
        return sorted_issues[:limit]

    def clear_session(self):
        """Clear all session data"""
        self.exercise_feedback = {}
        self.session_stats = {}