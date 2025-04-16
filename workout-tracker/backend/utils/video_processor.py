import cv2
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import time
import logging

from models.pose_detector import PoseDetector
from models.angle_calculator import AngleCalculator
from models.squat_analyzer import SquatAnalyzer
from models.bicep_curl_analyzer import BicepCurlAnalyzer
from models.pushup_analyzer import PushupAnalyzer
from models.lunge_analyzer import LungeAnalyzer
from models.plank_analyzer import PlankAnalyzer
from models.jump_analyzer import JumpingJackAnalyzer
from utils.feedback_manager import SessionFeedbackManager, FeedbackPriority

logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Process video frames for exercise detection and analysis
    
    This class handles the main video processing pipeline including pose detection,
    exercise analysis, and visualization.
    """
    
    def __init__(self, thresholds: Dict[str, float], visibility_threshold: float = 0.6):
        """
        Initialize the video processor
        
        Args:
            thresholds: Dictionary of threshold values for exercise analysis
            visibility_threshold: Minimum visibility score for landmarks
        """
        self.pose_detector = PoseDetector(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.angle_calculator = AngleCalculator()
        self.visibility_threshold = visibility_threshold
        self.thresholds = thresholds
        
        # Initialize exercise analyzers
        self.squat_analyzer = SquatAnalyzer(thresholds)
        self.bicep_curl_analyzer = BicepCurlAnalyzer(thresholds)
        self.pushup_analyzer = PushupAnalyzer(thresholds)
        self.lunge_analyzer = LungeAnalyzer(thresholds)
        self.plank_analyzer = PlankAnalyzer(thresholds)
        self.jumping_jack_analyzer = JumpingJackAnalyzer(thresholds)
        
        # Session feedback manager
        self.session_feedback_manager = SessionFeedbackManager()
        
        # Current exercise tracking
        self.current_exercise = None
        self.exercise_data = {
            'rep_count': 0,
            'state': '',
            'feedback': [],
            'target_reps': 0,
            'target_sets': 0,
            'current_set': 1,
            'is_timed': False,
            'elapsed_time': 0,
            'remaining_time': 0,
            'target_duration': 0
        }
        
        # For visualization
        self.colors = {
            'success': (0, 255, 0),    # Green
            'warning': (0, 255, 255),  # Yellow
            'error': (0, 0, 255),      # Red
            'info': (255, 255, 255),   # White
            'highlight': (255, 0, 255), # Magenta
            'blue': (255, 0, 0),        # Blue
            'black': (0, 0, 0)          # Black
        }
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.line_type = cv2.LINE_AA
        
    def set_current_exercise(self, exercise_name: str, target_reps: int = 0, 
                            target_sets: int = 0, target_duration: int = 0):
        """
        Set the current exercise to track
        
        Args:
            exercise_name: Name of the exercise
            target_reps: Target number of reps (for rep-based exercises)
            target_sets: Target number of sets
            target_duration: Target duration in seconds (for timed exercises)
        """
        # Clean up the exercise name
        cleaned_name = exercise_name.strip().lower()
        
        # Map common variations to standard names
        name_mapping = {
            'curl': 'bicep curl',
            'curls': 'bicep curl',
            'bicep': 'bicep curl',
            'biceps': 'bicep curl',
            'squats': 'squat',
            'push-up': 'pushup',
            'push up': 'pushup',
            'pushups': 'pushup',
            'lunges': 'lunge',
            'jumping jacks': 'jumping jack',
            'jumps': 'jumping jack',
            'jump': 'jumping jack'
        }
        
        if cleaned_name in name_mapping:
            cleaned_name = name_mapping[cleaned_name]
            
        self.current_exercise = cleaned_name
        
        # Reset exercise data
        self.exercise_data = {
            'name': cleaned_name,
            'rep_count': 0,
            'state': 'IDLE',
            'feedback': [],
            'target_reps': target_reps,
            'target_sets': target_sets,
            'current_set': 1,
            'is_timed': False,
            'elapsed_time': 0,
            'remaining_time': 0,
            'target_duration': target_duration
        }
        
        # Check if this is a timed exercise
        is_timed = False
        if cleaned_name == 'plank':
            is_timed = True
            self.plank_analyzer.set_target_duration(target_duration)
        elif cleaned_name == 'jumping jack' and target_duration > 0:
            is_timed = True
            self.jumping_jack_analyzer.set_timed_mode(True, target_duration)
        
        self.exercise_data['is_timed'] = is_timed
        
        logger.info(f"Set current exercise to: {self.current_exercise}")
        
    def get_analyzer_for_exercise(self, exercise_name: str):
        """
        Get the appropriate analyzer for the exercise
        
        Args:
            exercise_name: Name of the exercise
            
        Returns:
            Exercise analyzer instance
        """
        exercise_name = exercise_name.lower()
        
        if 'squat' in exercise_name:
            return self.squat_analyzer
        elif 'bicep' in exercise_name or 'curl' in exercise_name:
            return self.bicep_curl_analyzer
        elif 'push' in exercise_name:
            return self.pushup_analyzer
        elif 'lunge' in exercise_name:
            return self.lunge_analyzer
        elif 'plank' in exercise_name:
            return self.plank_analyzer
        elif 'jump' in exercise_name or 'jack' in exercise_name:
            return self.jumping_jack_analyzer
        else:
            # Default to squat if exercise not recognized
            logger.warning(f"Unrecognized exercise: {exercise_name}. Defaulting to squat analyzer.")
            return self.squat_analyzer
            
    def process_frame(self, frame):
        """
        Process a video frame
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple of (processed frame, exercise data)
        """
        if frame is None or frame.size == 0:
            logger.error("Empty frame received")
            return frame, self.exercise_data
            
        # Detect pose landmarks
        results = self.pose_detector.find_pose(frame)
        
        if results.pose_landmarks:
            # Extract keypoints
            landmarks = results.pose_landmarks.landmark
            h, w, _ = frame.shape
            keypoints = self.pose_detector.get_keypoints_dict(landmarks, self.visibility_threshold)
            
            # Draw the pose landmarks
            self.pose_detector.draw_landmarks(frame, results)
            
            # Process the current exercise if set
            if self.current_exercise:
                analyzer = self.get_analyzer_for_exercise(self.current_exercise)
                if analyzer:
                    # Update exercise state
                    state, feedback = analyzer.update_state(keypoints)
                    
                    # Update exercise data
                    self.exercise_data['rep_count'] = analyzer.get_rep_count()
                    self.exercise_data['state'] = analyzer.get_state_name()
                    self.exercise_data['feedback'] = feedback
                    
                    # Update time for timed exercises
                    if self.exercise_data['is_timed']:
                        if hasattr(analyzer, 'get_elapsed_time'):
                            self.exercise_data['elapsed_time'] = analyzer.get_elapsed_time()
                        if hasattr(analyzer, 'get_remaining_time'):
                            self.exercise_data['remaining_time'] = analyzer.get_remaining_time()
                    
                    # Add feedback to session tracking
                    for fb in feedback:
                        priority = FeedbackPriority.HIGH if "Correct form" not in fb else FeedbackPriority.LOW
                        self.session_feedback_manager.add_feedback(self.current_exercise, fb, priority)
            
            # Visualize exercise information
            self.visualize_exercise_info(frame)
            
        return frame, self.exercise_data
        
    def visualize_exercise_info(self, frame):
        """
        Add exercise information visualization to the frame
        
        Args:
            frame: Video frame to annotate
        """
        h, w, _ = frame.shape
        
        # Background rectangle for text
        cv2.rectangle(frame, (0, 0), (w, 80), (0, 0, 0), -1)
        
        # Exercise name and count
        exercise_text = f"{self.current_exercise.title() if self.current_exercise else 'No exercise selected'}"
        cv2.putText(frame, exercise_text, (10, 30), self.font, 0.8, self.colors['info'], 2, self.line_type)
        
        # Rep count or time
        if self.exercise_data['is_timed']:
            if self.exercise_data['target_duration'] > 0:
                progress = min(1.0, self.exercise_data['elapsed_time'] / self.exercise_data['target_duration'])
                time_text = f"Time: {int(self.exercise_data['elapsed_time'])}s / {self.exercise_data['target_duration']}s"
                remaining_text = f"Remaining: {int(self.exercise_data['remaining_time'])}s"
                
                cv2.putText(frame, time_text, (10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)
                
                # Progress bar
                bar_length = w - 40
                filled_length = int(bar_length * progress)
                cv2.rectangle(frame, (20, h - 30), (20 + bar_length, h - 20), self.colors['black'], -1)
                cv2.rectangle(frame, (20, h - 30), (20 + filled_length, h - 20), self.colors['success'], -1)
                cv2.putText(frame, remaining_text, (20, h - 40), self.font, 0.6, self.colors['info'], 2, self.line_type)
            else:
                time_text = f"Time: {int(self.exercise_data['elapsed_time'])}s"
                cv2.putText(frame, time_text, (10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)
        else:
            count_text = f"Reps: {self.exercise_data['rep_count']}"
            if self.exercise_data['target_reps'] > 0:
                count_text += f" / {self.exercise_data['target_reps']}"
                
            cv2.putText(frame, count_text, (10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)
            
            if self.exercise_data['target_sets'] > 1:
                set_text = f"Set: {self.exercise_data['current_set']} / {self.exercise_data['target_sets']}"
                cv2.putText(frame, set_text, (w - 150, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)
        
        # Exercise state
        state_text = f"State: {self.exercise_data['state']}"
        cv2.putText(frame, state_text, (w - 250, 30), self.font, 0.7, self.colors['info'], 2, self.line_type)
        
        # Feedback
        if self.exercise_data['feedback']:
            y_offset = 120
            
            # Background for feedback
            feedback_height = min(len(self.exercise_data['feedback']), 3) * 40
            cv2.rectangle(frame, (0, h - feedback_height - 40), (w, h), (0, 0, 0, 0.7), -1)
            
            for i, feedback in enumerate(self.exercise_data['feedback'][:3]):  # Limit to 3 feedback items
                color = self.colors['success'] if "Correct form" in feedback or "Good" in feedback else self.colors['warning']
                cv2.putText(frame, feedback, (20, h - y_offset + i * 40), 
                            self.font, 0.7, color, 2, self.line_type)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the current session
        
        Returns:
            Dictionary with session statistics
        """
        stats = {
            'common_issues': self.session_feedback_manager.get_common_issues(),
            'exercise_stats': {}
        }
        
        # Get stats for each exercise
        for exercise_name in self.session_feedback_manager.session_stats:
            exercise_stats = {
                'common_issues': self.session_feedback_manager.get_common_issues(exercise_name),
                'total_feedback': len(self.session_feedback_manager.session_stats[exercise_name])
            }
            stats['exercise_stats'][exercise_name] = exercise_stats
            
        return stats
    
    def reset_session(self):
        """Reset the session statistics"""
        self.session_feedback_manager.clear_session()