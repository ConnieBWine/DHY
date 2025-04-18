import cv2
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import time
import logging
import traceback # Import traceback for detailed error logging

# Assuming these imports are correct relative to your project structure
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
# You might want to set the level to DEBUG to see all messages
# logging.basicConfig(level=logging.DEBUG) # Uncomment this in main.py if needed

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
        logger.info("Initializing VideoProcessor...")
        try:
            self.visibility_threshold = visibility_threshold
            self.thresholds = thresholds
            logger.debug(f"Using visibility threshold: {self.visibility_threshold}")
            logger.debug(f"Using exercise thresholds: {self.thresholds}")

            # Initialize PoseDetector
            try:
                self.pose_detector = PoseDetector(
                    static_image_mode=False,
                    model_complexity=1,
                    smooth_landmarks=True,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6
                )
                logger.info("PoseDetector initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PoseDetector: {str(e)}\n{traceback.format_exc()}")
                raise # Reraise the exception to stop initialization

            self.angle_calculator = AngleCalculator() # Assuming this doesn't fail easily

            # Initialize exercise analyzers
            logger.info("Initializing exercise analyzers...")
            self.analyzers = {}
            analyzer_classes = {
                'squat': SquatAnalyzer,
                'bicep curl': BicepCurlAnalyzer,
                'pushup': PushupAnalyzer,
                'lunge': LungeAnalyzer,
                'plank': PlankAnalyzer,
                'jumping jack': JumpingJackAnalyzer
            }
            for name, AnalyzerClass in analyzer_classes.items():
                 try:
                      self.analyzers[name] = AnalyzerClass(thresholds)
                      logger.info(f"{AnalyzerClass.__name__} initialized successfully for '{name}'")
                 except Exception as e:
                      logger.error(f"Failed to initialize {AnalyzerClass.__name__} for '{name}': {str(e)}\n{traceback.format_exc()}")
                      # Decide if you want to continue without this analyzer or raise error
                      # For now, we log and continue, it might default later if needed
            logger.info("Finished initializing exercise analyzers.")

            # Session feedback manager
            self.session_feedback_manager = SessionFeedbackManager()

            # Current exercise tracking
            self.current_exercise = None
            self.exercise_data = self._reset_exercise_data() # Use helper method

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

            logger.info("VideoProcessor initialization complete")
        except Exception as e:
            logger.critical(f"CRITICAL Error during VideoProcessor initialization: {str(e)}\n{traceback.format_exc()}")
            # Depending on the desired behavior, you might want to raise the exception
            # raise e
            # Or handle it gracefully, e.g., set a flag indicating an error state
            self.initialization_failed = True


    def _reset_exercise_data(self, exercise_name: Optional[str] = None, target_reps: int = 0,
                            target_sets: int = 0, target_duration: int = 0, is_timed: bool = False):
        """Helper to reset exercise data dictionary."""
        return {
            'name': exercise_name,
            'rep_count': 0,
            'state': 'IDLE',
            'feedback': [],
            'target_reps': target_reps,
            'target_sets': target_sets,
            'current_set': 1,
            'is_timed': is_timed,
            'elapsed_time': 0,
            'remaining_time': target_duration if is_timed else 0,
            'target_duration': target_duration
        }

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
        logger.info(f"Setting current exercise. Received: name='{exercise_name}', reps={target_reps}, sets={target_sets}, duration={target_duration}")

        # Clean up the exercise name
        cleaned_name = exercise_name.strip().lower() if isinstance(exercise_name, str) else "unknown"
        logger.debug(f"Cleaned exercise name (lowercase, stripped): '{cleaned_name}'")

        # Import ExerciseConfig here to avoid circular imports
        from config import ExerciseConfig
        
        # Find the closest matching exercise in our configuration
        standard_name = None
        for name in ExerciseConfig.AVAILABLE_EXERCISES:
            if name.lower() == cleaned_name:
                standard_name = name
                break
        
        # If no exact match, try common variations
        if not standard_name:
            name_mapping = {
                'curl': 'Bicep Curl',
                'curls': 'Bicep Curl',
                'bicep': 'Bicep Curl',
                'biceps': 'Bicep Curl',
                'squats': 'Squat',
                'push-up': 'Pushup',
                'push up': 'Pushup',
                'pushups': 'Pushup',
                'lunges': 'Lunge',
                'jumping jacks': 'Jumping Jack',
                'jumps': 'Jumping Jack',
                'jump': 'Jumping Jack',
                'shoulder': 'Shoulder Press'
            }
            standard_name = name_mapping.get(cleaned_name)
        
        # If still no match, try partial matching
        if not standard_name:
            for name in ExerciseConfig.AVAILABLE_EXERCISES:
                if cleaned_name in name.lower() or name.lower() in cleaned_name:
                    standard_name = name
                    break
        
        # If no match found, use a default or log an error
        if not standard_name:
            logger.warning(f"No matching exercise found for '{cleaned_name}'. Using default 'Squat'.")
            standard_name = "Squat"  # Default to squat if nothing matches
        
        logger.debug(f"Standardized exercise name: '{standard_name}'")

        if standard_name.lower() not in [analyzer.lower() for analyzer in self.analyzers]:
            logger.warning(f"No specific analyzer found for exercise '{standard_name}'. Analysis might be limited or inaccurate.")
        
        self.current_exercise = standard_name.lower()  # Store lowercase for analyzer lookup

        # Check if this is a timed exercise based on name or duration param
        is_timed = False
        exercise_type = ExerciseConfig.get_exercise_type(standard_name)
        
        if exercise_type == "timed":
            is_timed = True
            analyzer = self.get_analyzer_for_exercise(self.current_exercise)
            
            if analyzer:
                if self.current_exercise == "plank" and hasattr(analyzer, 'set_target_duration'):
                    analyzer.set_target_duration(target_duration)
                    logger.info(f"Plank detected as timed. Set target duration to {target_duration}s.")
                elif self.current_exercise == "jumping jack" and hasattr(analyzer, 'set_timed_mode'):
                    analyzer.set_timed_mode(True, target_duration)
                    logger.info(f"Jumping Jack detected as timed. Set target duration to {target_duration}s.")
        
        # Reset exercise data using helper
        self.exercise_data = self._reset_exercise_data(
            exercise_name=standard_name,
            target_reps=target_reps,
            target_sets=target_sets,
            target_duration=target_duration,
            is_timed=is_timed
        )
        logger.info(f"Current exercise set to: '{self.current_exercise}'. Timed: {is_timed}. Data reset.")
        logger.debug(f"Initial exercise data: {self.exercise_data}")


    def get_analyzer_for_exercise(self, exercise_name: str):
        """
        Get the appropriate analyzer for the exercise

        Args:
            exercise_name: Standardized name of the exercise

        Returns:
            Exercise analyzer instance or None
        """
        logger.debug(f"Attempting to get analyzer for: '{exercise_name}'")
        analyzer = self.analyzers.get(exercise_name)
        if analyzer:
             logger.debug(f"Found analyzer: {type(analyzer).__name__}")
             return analyzer
        else:
             # Handle case where analyzer might not have been initialized or name doesn't match
             logger.warning(f"No analyzer found for '{exercise_name}'. Returning None.")
             # Alternative: Default to a specific analyzer?
             # default_analyzer_name = 'squat'
             # logger.warning(f"No analyzer found for '{exercise_name}'. Defaulting to '{default_analyzer_name}'.")
             # return self.analyzers.get(default_analyzer_name)
             return None


    def process_frame(self, frame):
        """
        Process a video frame

        Args:
            frame: Input video frame (numpy array)

        Returns:
            Tuple of (processed frame, exercise data dictionary)
        """
        start_time = time.time()
        logger.debug(f"--- Processing Frame Start (Exercise: {self.current_exercise}) ---")

        # Basic frame check
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            logger.error("Empty or invalid frame received in process_frame.")
            # Return a default frame or indicator? For now, return input and current data.
            return frame, self.exercise_data

        logger.debug(f"Input frame shape: {frame.shape}")
        original_frame = frame.copy() # Keep original if needed, processing happens on 'frame'
        processed_frame = frame # Alias for clarity, drawing happens on this

        try:
            # 1. Detect Pose Landmarks
            results = None
            landmarks = None
            keypoints = None
            try:
                logger.debug("Running pose detection...")
                results = self.pose_detector.find_pose(processed_frame)
                logger.debug(f"Pose detection completed. Results valid: {bool(results and results.pose_landmarks)}")
            except Exception as e:
                logger.error(f"Error during pose detection: {str(e)}\n{traceback.format_exc()}")
                # Continue without landmarks, maybe return original frame?
                return original_frame, self.exercise_data # Return original frame on pose detection error

            # 2. Process if landmarks are found
            if results and results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                h, w, _ = processed_frame.shape
                logger.debug(f"Landmarks detected. Frame dimensions: H={h}, W={w}")

                # 2a. Extract Keypoints
                try:
                    logger.debug("Extracting keypoints...")
                    keypoints = self.pose_detector.get_keypoints_dict(landmarks, self.visibility_threshold)
                    keypoints_count = len([k for k, v in keypoints.items() if v is not None])
                    logger.debug(f"Keypoints extracted successfully. Count: {keypoints_count}")
                    # Optional: Log specific keypoint presence/values if needed for deep debugging
                    # logger.debug(f"Keypoints data (sample): { {k: v for i, (k, v) in enumerate(keypoints.items()) if i < 3} }")
                except Exception as e:
                    logger.error(f"Error extracting keypoints: {str(e)}\n{traceback.format_exc()}")
                    # Decide how to proceed - maybe skip analysis?
                    keypoints = None # Ensure keypoints is None if extraction failed

                # 2b. Draw Landmarks
                try:
                    logger.debug("Drawing landmarks...")
                    # Pass 'processed_frame' to draw on, not 'original_frame'
                    self.pose_detector.draw_landmarks(processed_frame, results)
                    logger.debug("Landmarks drawn successfully.")
                except Exception as e:
                    logger.error(f"Error drawing landmarks: {str(e)}\n{traceback.format_exc()}")
                    # Continue, drawing is not critical for analysis

                # 2c. Analyze Current Exercise (if set and keypoints available)
                if self.current_exercise and keypoints:
                    logger.debug(f"Analyzing current exercise: {self.current_exercise}")
                    analyzer = self.get_analyzer_for_exercise(self.current_exercise)
                    if analyzer:
                        try:
                            logger.debug(f"Calling update_state for {type(analyzer).__name__}")
                            # Update exercise state using the analyzer
                            state, feedback = analyzer.update_state(keypoints)
                            logger.debug(f"Analyzer returned state: '{state}', feedback: {feedback}")

                            # Update exercise data based on analyzer results
                            self.exercise_data['rep_count'] = analyzer.get_rep_count()
                            self.exercise_data['state'] = analyzer.get_state_name()
                            self.exercise_data['feedback'] = feedback
                            logger.debug(f"Updated rep_count: {self.exercise_data['rep_count']}, state: {self.exercise_data['state']}")

                            # Update time for timed exercises
                            if self.exercise_data['is_timed']:
                                elapsed_time = analyzer.get_elapsed_time() if hasattr(analyzer, 'get_elapsed_time') else 0
                                remaining_time = analyzer.get_remaining_time() if hasattr(analyzer, 'get_remaining_time') else 0
                                self.exercise_data['elapsed_time'] = elapsed_time
                                self.exercise_data['remaining_time'] = remaining_time
                                logger.debug(f"Updated timed exercise: elapsed={elapsed_time:.2f}s, remaining={remaining_time:.2f}s")

                            # Add feedback to session tracking
                            for fb in feedback:
                                priority = FeedbackPriority.HIGH if "Correct form" not in fb else FeedbackPriority.LOW
                                self.session_feedback_manager.add_feedback(self.current_exercise, fb, priority)

                        except Exception as e:
                            logger.error(f"Error during exercise analysis ({type(analyzer).__name__}): {str(e)}\n{traceback.format_exc()}")
                            # Reset feedback for this frame?
                            self.exercise_data['feedback'] = ["Error during analysis"]
                    else:
                        logger.warning(f"No analyzer available for '{self.current_exercise}', skipping analysis.")
                        self.exercise_data['feedback'] = ["Exercise analyzer not available"]
                elif not self.current_exercise:
                     logger.debug("No current exercise selected, skipping analysis.")
                     self.exercise_data['feedback'] = [] # Clear feedback if no exercise
                elif not keypoints:
                     logger.warning("Keypoints not available, skipping analysis.")
                     self.exercise_data['feedback'] = ["Could not detect pose clearly"]

            else:
                # No landmarks detected in this frame
                logger.info("No landmarks detected in this frame.")
                self.exercise_data['state'] = 'NO POSE DETECTED'
                self.exercise_data['feedback'] = ["Ensure you are fully visible to the camera"]

            # 3. Visualize Exercise Information
            try:
                logger.debug("Visualizing exercise info...")
                # Pass 'processed_frame' to draw on
                self.visualize_exercise_info(processed_frame)
                logger.debug("Visualization complete.")
            except Exception as e:
                logger.error(f"Error during visualization: {str(e)}\n{traceback.format_exc()}")
                # Visualization error shouldn't stop returning the frame

            # 4. Calculate processing time and finalize
            end_time = time.time()
            processing_time = end_time - start_time
            logger.debug(f"--- Processing Frame End. Time: {processing_time:.4f}s ---")

            # Return the frame that has been drawn on
            return processed_frame, self.exercise_data

        except Exception as e:
            # Catch-all for any unexpected error during processing
            logger.critical(f"CRITICAL UNHANDLED error processing frame: {str(e)}\n{traceback.format_exc()}")
            # Return the original frame and indicate error in data
            error_data = self.exercise_data.copy()
            error_data['feedback'] = ["Critical processing error"]
            return original_frame, error_data


    def visualize_exercise_info(self, frame):
        """
        Add exercise information visualization to the frame.
        Now includes basic error checking for data access.

        Args:
            frame: Video frame to annotate
        """
        try:
            h, w, _ = frame.shape
            logger.debug(f"Visualizing on frame H={h}, W={w}")

            # Use get() with defaults for safety
            current_exercise_name = self.exercise_data.get('name', 'No Exercise')
            rep_count = self.exercise_data.get('rep_count', 0)
            target_reps = self.exercise_data.get('target_reps', 0)
            target_sets = self.exercise_data.get('target_sets', 0)
            current_set = self.exercise_data.get('current_set', 1)
            state = self.exercise_data.get('state', 'UNKNOWN')
            feedback_list = self.exercise_data.get('feedback', [])
            is_timed = self.exercise_data.get('is_timed', False)
            elapsed_time = self.exercise_data.get('elapsed_time', 0)
            remaining_time = self.exercise_data.get('remaining_time', 0)
            target_duration = self.exercise_data.get('target_duration', 0)

            # Background rectangle for top text
            cv2.rectangle(frame, (0, 0), (w, 80), (50, 50, 50, 0.8), -1) # Semi-transparent dark grey

            # Exercise name
            exercise_text = f"{current_exercise_name.title() if current_exercise_name else 'No Exercise'}"
            cv2.putText(frame, exercise_text, (10, 30), self.font, 0.8, self.colors['info'], 2, self.line_type)

            # Rep count or time display
            if is_timed:
                if target_duration > 0:
                    progress = min(1.0, elapsed_time / target_duration) if target_duration > 0 else 0
                    time_text = f"Time: {int(elapsed_time)}s / {target_duration}s"
                    remaining_text = f"Remaining: {int(remaining_time)}s"
                    logger.debug(f"Visualizing timed exercise: {time_text}, Progress: {progress:.2f}")

                    cv2.putText(frame, time_text, (10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)

                    # Progress bar at bottom
                    bar_y = h - 35
                    bar_height = 15
                    bar_length = w - 40
                    filled_length = int(bar_length * progress)
                    # Draw background bar
                    cv2.rectangle(frame, (20, bar_y), (20 + bar_length, bar_y + bar_height), self.colors['black'], -1)
                    # Draw progress fill
                    cv2.rectangle(frame, (20, bar_y), (20 + filled_length, bar_y + bar_height), self.colors['success'], -1)
                    # Draw remaining time above bar
                    cv2.putText(frame, remaining_text, (20, bar_y - 5), self.font, 0.6, self.colors['info'], 2, self.line_type)
                else:
                    # Just show elapsed time if no target duration
                    time_text = f"Time: {int(elapsed_time)}s"
                    logger.debug(f"Visualizing timed exercise (no target): {time_text}")
                    cv2.putText(frame, time_text, (10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)
            else:
                # Rep-based exercise display
                count_text = f"Reps: {rep_count}"
                if target_reps > 0:
                    count_text += f" / {target_reps}"
                logger.debug(f"Visualizing rep exercise: {count_text}")
                cv2.putText(frame, count_text, (10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)

                if target_sets > 1:
                    set_text = f"Set: {current_set} / {target_sets}"
                    logger.debug(f"Visualizing set info: {set_text}")
                    (set_w, set_h), _ = cv2.getTextSize(set_text, self.font, 0.7, 2)
                    cv2.putText(frame, set_text, (w - set_w - 10, 60), self.font, 0.7, self.colors['info'], 2, self.line_type)

            # Exercise state display
            state_text = f"State: {state}"
            (state_w, state_h), _ = cv2.getTextSize(state_text, self.font, 0.7, 2)
            cv2.putText(frame, state_text, (w - state_w - 10, 30), self.font, 0.7, self.colors['info'], 2, self.line_type)
            logger.debug(f"Visualizing state: {state_text}")

            # Feedback display at bottom
            if feedback_list:
                 max_feedback_items = 3
                 feedback_start_y = h - 20 # Start slightly higher from bottom
                 feedback_line_height = 30 # Spacing between feedback lines

                 # Calculate dynamic background height
                 num_items_to_show = min(len(feedback_list), max_feedback_items)
                 feedback_bg_height = num_items_to_show * feedback_line_height + 10 # Add padding

                 # Draw feedback background
                 cv2.rectangle(frame, (0, h - feedback_bg_height), (w, h), (0, 0, 0, 0.7), -1) # Semi-transparent black

                 logger.debug(f"Visualizing feedback (showing {num_items_to_show}/{len(feedback_list)}): {feedback_list[:num_items_to_show]}")
                 for i, feedback in enumerate(feedback_list[:num_items_to_show]):
                     y_pos = feedback_start_y - (num_items_to_show - 1 - i) * feedback_line_height
                     # Determine color based on content
                     color = self.colors['success']
                     if "Correct" not in feedback and "Good" not in feedback and "Keep" not in feedback:
                          color = self.colors['warning']
                     if "Error" in feedback or "Could not" in feedback:
                          color = self.colors['error']

                     cv2.putText(frame, feedback, (20, y_pos),
                                 self.font, 0.6, color, 1, self.line_type) # Slightly smaller font
            else:
                 logger.debug("No feedback to visualize.")

        except Exception as e:
            logger.error(f"Error during visualization drawing: {str(e)}\n{traceback.format_exc()}")
            # Optionally draw an error message onto the frame itself
            cv2.putText(frame, "Vis Error", (w // 2 - 50, h // 2), self.font, 1, self.colors['error'], 2, self.line_type)

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the current session

        Returns:
            Dictionary with session statistics
        """
        logger.info("Retrieving session statistics...")
        try:
            stats = {
                'common_issues': self.session_feedback_manager.get_common_issues(),
                'exercise_stats': {}
            }

            # Get stats for each exercise
            session_data = self.session_feedback_manager.session_stats # Get the raw data
            logger.debug(f"Raw session data: {session_data}")

            for exercise_name in session_data:
                common_issues = self.session_feedback_manager.get_common_issues(exercise_name)
                total_feedback_count = len(session_data.get(exercise_name, []))
                exercise_stats = {
                    'common_issues': common_issues,
                    'total_feedback_count': total_feedback_count
                }
                stats['exercise_stats'][exercise_name] = exercise_stats
                logger.debug(f"Stats for '{exercise_name}': Issues={common_issues}, Count={total_feedback_count}")

            logger.info("Session statistics retrieved successfully.")
            return stats
        except Exception as e:
             logger.error(f"Error retrieving session stats: {str(e)}\n{traceback.format_exc()}")
             return {"error": "Could not retrieve session stats", "common_issues": [], "exercise_stats": {}}


    def reset_session(self):
        """Reset the session statistics"""
        logger.info("Resetting session statistics.")
        try:
            self.session_feedback_manager.clear_session()
            logger.info("Session statistics cleared.")
        except Exception as e:
            logger.error(f"Error resetting session stats: {str(e)}\n{traceback.format_exc()}")