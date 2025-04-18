from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import time
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState # Assuming these imports are correct
from models.angle_calculator import AngleCalculator # Assuming these imports are correct
from utils.feedback_manager import FeedbackPriority # Assuming these imports are correct

class PlankState(Enum):
    """States for the plank exercise"""
    IDLE = 0             # Not in plank position or just finished
    PLANK_POSITION = 1   # Correct position detected, timer about to start/just started
    PLANK_HOLD = 2       # Actively holding the plank with timer running
    COMPLETED = 3        # Target duration reached (momentary state)

class PlankAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the plank exercise.

    Tracks plank position, provides form feedback, and manages hold time.
    This is a timed exercise, not rep-based by default, but tracks completions.
    """

    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the plank analyzer.

        Args:
            thresholds: Dictionary of threshold values for plank analysis.
        """
        # --- MOVED INITIALIZATIONS HERE ---
        # Initialize attributes used in reset() *before* calling super().__init__()
        self.start_time = None
        self.hold_time = 0.0 # Use float for time
        self.last_time_update = None
        self.hip_alignment_buffer = deque(maxlen=10) # Buffer for smoothing hip alignment values
        self.body_angle_buffer = deque(maxlen=10)    # Buffer for smoothing body angle values
        self.is_in_position_counter = 0              # Counter for consecutive frames in position
        # --- END MOVED INITIALIZATIONS ---

        # Now call the parent constructor, which will call our overridden reset()
        super().__init__(thresholds) # This calls reset() internally

        # Initialize remaining attributes
        self.state = PlankState.IDLE
        self.target_duration = 0.0 # Target hold duration in seconds (float)
        self.required_frames_in_position = thresholds.get('plank_required_frames', 5) # Frames to confirm start
        self.angle_calculator = AngleCalculator() # Instantiate angle calculator

        # Store thresholds locally for easier access
        self.hip_pike_threshold = self.thresholds.get('plank_hip_pike', 25) # Max deviation upwards (positive)
        self.hip_sag_threshold = self.thresholds.get('plank_hip_sag', 15)   # Max deviation downwards (negative)
        self.body_straightness_threshold = self.thresholds.get('plank_body_angle_threshold', 165) # Min angle for straightness (e.g., 165-180)


    def reset(self):
        """Reset the analyzer state, typically called before starting a new hold."""
        super().reset() # Call parent reset first if it has relevant logic
        self.start_time = None
        self.hold_time = 0.0
        self.last_time_update = None
        # Check if attributes exist before clearing (should be guaranteed now)
        if hasattr(self, 'hip_alignment_buffer'):
            self.hip_alignment_buffer.clear()
        if hasattr(self, 'body_angle_buffer'):
            self.body_angle_buffer.clear()
        self.is_in_position_counter = 0
        # Do not reset target_duration here, it's set externally
        # self.state = PlankState.IDLE # Reset state if needed, or handle in update_state

    def set_target_duration(self, seconds: float):
        """Set the target duration for the plank hold."""
        self.target_duration = max(0.0, float(seconds)) # Ensure it's a non-negative float

    def is_timed_exercise(self) -> bool:
        """This is a timed exercise."""
        return True

    def calculate_exercise_metrics(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate metrics relevant for plank analysis (angles, alignment).

        Args:
            keypoints: Dictionary of landmark keypoints [x, y, z, visibility].

        Returns:
            Dictionary of metric names and values.
        """
        metrics = {}
        default_kp = [0, 0, 0, 0] # Default for missing keypoints

        # --- Get Keypoints ---
        # Use .get() with default to avoid KeyErrors
        left_shoulder = keypoints.get('left_shoulder', default_kp)
        right_shoulder = keypoints.get('right_shoulder', default_kp)
        left_hip = keypoints.get('left_hip', default_kp)
        right_hip = keypoints.get('right_hip', default_kp)
        left_ankle = keypoints.get('left_ankle', default_kp)
        right_ankle = keypoints.get('right_ankle', default_kp)
        # Optional: Knees can help refine body line if ankles are obscured
        # left_knee = keypoints.get('left_knee', default_kp)
        # right_knee = keypoints.get('right_knee', default_kp)

        # --- Check Visibility (using index 3, assuming [x, y, z, visibility]) ---
        vis_threshold = 0.5 # Confidence threshold
        ls_vis = left_shoulder[3] > vis_threshold
        rs_vis = right_shoulder[3] > vis_threshold
        lh_vis = left_hip[3] > vis_threshold
        rh_vis = right_hip[3] > vis_threshold
        la_vis = left_ankle[3] > vis_threshold
        ra_vis = right_ankle[3] > vis_threshold

        # --- Calculate Average Positions (use only visible keypoints) ---
        # Shoulder Midpoint
        if ls_vis and rs_vis:
            shoulder_pos = [(left_shoulder[i] + right_shoulder[i]) / 2 for i in range(2)] # Use x, y
        elif ls_vis:
            shoulder_pos = left_shoulder[:2]
        elif rs_vis:
            shoulder_pos = right_shoulder[:2]
        else: shoulder_pos = None

        # Hip Midpoint
        if lh_vis and rh_vis:
            hip_pos = [(left_hip[i] + right_hip[i]) / 2 for i in range(2)] # Use x, y
        elif lh_vis:
            hip_pos = left_hip[:2]
        elif rh_vis:
            hip_pos = right_hip[:2]
        else: hip_pos = None

        # Ankle Midpoint
        if la_vis and ra_vis:
            ankle_pos = [(left_ankle[i] + right_ankle[i]) / 2 for i in range(2)] # Use x, y
        elif la_vis:
            ankle_pos = left_ankle[:2]
        elif ra_vis:
            ankle_pos = right_ankle[:2]
        else: ankle_pos = None


        # --- Calculate Metrics if all points are available ---
        if shoulder_pos and hip_pos and ankle_pos:
            # 1. Body Straightness Angle (Shoulder-Hip-Ankle)
            # Use the angle calculator for consistency
            # Note: angle_calculator expects full keypoint format or list of coordinates
            body_angle = self.angle_calculator.angle_deg(shoulder_pos, hip_pos, ankle_pos)
            self.body_angle_buffer.append(body_angle)
            if len(self.body_angle_buffer) > 0:
                 metrics['body_angle'] = sum(self.body_angle_buffer) / len(self.body_angle_buffer)

            # 2. Hip Alignment (deviation from shoulder-ankle line)
            # Calculate distance from hip_pos to the line segment defined by shoulder_pos and ankle_pos
            # Vector SA (Shoulder to Ankle)
            vec_sa = (ankle_pos[0] - shoulder_pos[0], ankle_pos[1] - shoulder_pos[1])
            # Vector SH (Shoulder to Hip)
            vec_sh = (hip_pos[0] - shoulder_pos[0], hip_pos[1] - shoulder_pos[1])

            len_sq_sa = vec_sa[0]**2 + vec_sa[1]**2

            if len_sq_sa > 1e-6: # Avoid division by zero if points overlap
                # Project SH onto SA
                dot_product = vec_sh[0] * vec_sa[0] + vec_sh[1] * vec_sa[1]
                projection_factor = dot_product / len_sq_sa

                # Find the closest point on the (infinite) line SA to H
                closest_point_on_line = (shoulder_pos[0] + projection_factor * vec_sa[0],
                                         shoulder_pos[1] + projection_factor * vec_sa[1])

                # Calculate the perpendicular distance (hip deviation)
                hip_deviation_dist = ((hip_pos[0] - closest_point_on_line[0])**2 +
                                      (hip_pos[1] - closest_point_on_line[1])**2)**0.5

                # Determine direction (sagging vs. piking) using cross product (z-component)
                # Cross product: vec_SA x vec_SH = SA.x * SH.y - SA.y * SH.x
                cross_product_z = vec_sa[0] * vec_sh[1] - vec_sa[1] * vec_sh[0]

                # Sign convention:
                # Assuming Y increases downwards (typical image coordinates):
                # Positive cross_product_z -> Hip is "above" the line SA (PIKING)
                # Negative cross_product_z -> Hip is "below" the line SA (SAGGING)
                # Adjust if Y increases upwards.
                signed_hip_deviation = hip_deviation_dist if cross_product_z >= 0 else -hip_deviation_dist

                # Normalize deviation (optional but recommended)
                # Normalize by the length of the shoulder-ankle segment for scale invariance
                len_sa = len_sq_sa**0.5
                normalized_deviation = signed_hip_deviation / len_sa if len_sa > 1 else signed_hip_deviation # Avoid amplifying noise for small segments

                self.hip_alignment_buffer.append(normalized_deviation) # Store normalized value
                if len(self.hip_alignment_buffer) > 0:
                    metrics['hip_alignment'] = sum(self.hip_alignment_buffer) / len(self.hip_alignment_buffer)
            else:
                 # Handle case where shoulder and ankle points are the same
                 metrics['hip_alignment'] = 0 # Or some indicator of invalid input
                 metrics['body_angle'] = 180 # Or indicator

        return metrics

    def is_in_plank_position(self, metrics: Dict[str, float]) -> bool:
        """
        Determine if the person is in a valid plank position based on calculated metrics.

        Args:
            metrics: Dictionary of calculated metric names and values.

        Returns:
            True if in valid plank position, False otherwise.
        """
        hip_alignment = metrics.get('hip_alignment')
        body_angle = metrics.get('body_angle')

        if hip_alignment is None or body_angle is None:
            return False # Not enough data

        # Check 1: Body Straightness
        # Body angle should be close to 180 degrees (e.g., > 165)
        if body_angle < self.body_straightness_threshold:
            return False

        # Check 2: Hip Alignment (using normalized deviation)
        # Thresholds for normalized deviation might be smaller (e.g., 0.1 means 10% deviation relative to body length)
        normalized_pike_threshold = self.thresholds.get('plank_norm_hip_pike', 0.15)
        normalized_sag_threshold = self.thresholds.get('plank_norm_hip_sag', 0.10)

        if hip_alignment > normalized_pike_threshold: # Piking too much
            return False
        if hip_alignment < -normalized_sag_threshold: # Sagging too much
            return False

        # Optional: Check if body is roughly horizontal (requires Z or comparing Y of shoulder/ankle)
        # ... add check if needed ...

        # If all checks pass
        return True

    def analyze_form(self, metrics: Dict[str, float]) -> List[str]:
        """
        Analyze plank form based on calculated metrics and provide feedback.

        Args:
            metrics: Dictionary of calculated metric names and values.

        Returns:
            List of feedback strings about the plank form for the current frame.
        """
        feedback = []
        hip_alignment = metrics.get('hip_alignment')
        body_angle = metrics.get('body_angle')

        if hip_alignment is None or body_angle is None:
            return ["Ensure shoulders, hips, and ankles are clearly visible."]

        # Analyze Body Straightness
        if body_angle < self.body_straightness_threshold:
            feedback.append(f"Straighten your body (Angle: {body_angle:.0f}°)")

        # Analyze Hip Alignment (using normalized thresholds)
        normalized_pike_threshold = self.thresholds.get('plank_norm_hip_pike', 0.15)
        normalized_sag_threshold = self.thresholds.get('plank_norm_hip_sag', 0.10)

        if hip_alignment > normalized_pike_threshold:
            feedback.append("Lower your hips, don't pike")
        elif hip_alignment < -normalized_sag_threshold:
            feedback.append("Raise your hips, don't sag")

        # If no specific issues found
        if not feedback:
            feedback.append("Good plank form!")

        return feedback

    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[PlankState, List[str]]:
        """
        Update the plank state based on keypoints, manage timer, and provide feedback.

        Args:
            keypoints: Dictionary of landmark keypoints.

        Returns:
            Tuple of (current state, persistent feedback list from manager).
        """
        now = time.time()
        metrics = self.calculate_exercise_metrics(keypoints)
        is_currently_in_position = self.is_in_plank_position(metrics)
        frame_feedback = [] # Feedback specific to this frame/transition

        # --- State Machine Logic ---
        if self.state == PlankState.IDLE:
            if is_currently_in_position:
                self.is_in_position_counter += 1
                if self.is_in_position_counter >= self.required_frames_in_position:
                    # Confirmed plank start
                    self.state = PlankState.PLANK_POSITION
                    self.feedback_manager.clear_feedback() # Clear old feedback
                    # Don't reset counters here, reset() handles that if needed
                    self.start_time = now
                    self.last_time_update = now
                    self.hold_time = 0.0 # Explicitly reset hold time
                    frame_feedback.append("Plank started!")
                    self.feedback_manager.add_feedback("Plank started!", FeedbackPriority.INFO)
            else:
                # Not in position or lost it before confirmation
                self.is_in_position_counter = 0

        elif self.state == PlankState.PLANK_POSITION:
            # This is a brief state after confirmation, immediately transition to HOLD
            if is_currently_in_position:
                self.state = PlankState.PLANK_HOLD
                # Update time immediately
                if self.last_time_update:
                    self.hold_time += now - self.last_time_update
                self.last_time_update = now
                # Analyze form on first hold frame
                form_feedback = self.analyze_form(metrics)
                frame_feedback.extend(form_feedback)
                for fb in form_feedback:
                     priority = FeedbackPriority.LOW if "Good" in fb else FeedbackPriority.HIGH
                     self.feedback_manager.add_feedback(fb, priority)
            else:
                # Lost position immediately after confirmation (false start)
                self.state = PlankState.IDLE
                self.is_in_position_counter = 0
                self.start_time = None # Reset timer info
                self.last_time_update = None
                self.hold_time = 0.0
                frame_feedback.append("Plank aborted.")
                self.feedback_manager.add_feedback("Plank aborted.", FeedbackPriority.WARN)


        elif self.state == PlankState.PLANK_HOLD:
            if is_currently_in_position:
                # Still holding, update time
                if self.last_time_update:
                    self.hold_time += now - self.last_time_update
                self.last_time_update = now

                # Analyze form periodically and provide feedback
                # (Could add logic to only analyze every N frames for performance)
                form_feedback = self.analyze_form(metrics)
                # Add feedback to manager (maybe only if it changes?)
                for fb in form_feedback:
                     priority = FeedbackPriority.LOW if "Good" in fb else FeedbackPriority.HIGH
                     # Add feedback, manager might handle duplicates/timing
                     self.feedback_manager.add_feedback(fb, priority)

                # Check if target duration reached
                if self.target_duration > 0 and self.hold_time >= self.target_duration:
                    self.state = PlankState.COMPLETED # Momentary state
                    self.rep_count += 1 # Count as one completed plank hold
                    completion_msg = f"Plank complete! ({self.hold_time:.1f}s)"
                    frame_feedback.append(completion_msg)
                    self.feedback_manager.add_feedback(completion_msg, FeedbackPriority.SUCCESS)
                    # Transition back to IDLE after completion
                    self.state = PlankState.IDLE
                    self.is_in_position_counter = 0 # Reset counter for next attempt
                    self.start_time = None
                    self.last_time_update = None
                    # Keep hold_time as the final time until reset() is called explicitly
            else:
                # Lost plank position during hold
                self.state = PlankState.IDLE
                self.is_in_position_counter = 0
                lost_msg = f"Plank stopped. Held for {self.hold_time:.1f}s."
                frame_feedback.append(lost_msg)
                self.feedback_manager.add_feedback(lost_msg, FeedbackPriority.WARN)
                # Decide if partially held plank counts (e.g., if held > 5 seconds)
                # if self.hold_time >= 5.0:
                #     self.rep_count += 1 # Optional: count partial holds

                # Reset timer info
                self.start_time = None
                self.last_time_update = None
                # Keep hold_time until explicit reset

        # elif self.state == PlankState.COMPLETED: # Handled in PLANK_HOLD transition
        #     self.state = PlankState.IDLE


        # Add frame-specific feedback to manager if needed (e.g., for debugging)
        # for fb in frame_feedback:
        #     self.feedback_manager.add_feedback(fb, FeedbackPriority.DEBUG)

        # Return current state and the persistent feedback list
        return self.state, self.feedback_manager.get_feedback()

    def get_hold_time(self) -> float:
        """Get the current accumulated plank hold time in seconds."""
        # If currently holding, update time since last update
        if self.state == PlankState.PLANK_HOLD and self.last_time_update:
             now = time.time()
             current_hold = self.hold_time + (now - self.last_time_update)
             return current_hold
        # Otherwise, return the last recorded hold time
        return self.hold_time

    def get_remaining_time(self) -> float:
        """Get the remaining time for the plank hold based on target duration."""
        if self.target_duration <= 0:
            return 0.0 # No target set or already passed
        current_hold = self.get_hold_time() # Get potentially updated hold time
        remaining = max(0.0, self.target_duration - current_hold)
        return remaining

    def get_state_name(self) -> str:
        """Get the name of the current plank state."""
        return self.state.name
