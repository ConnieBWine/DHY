from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import time
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState # Assuming these imports are correct
from models.angle_calculator import AngleCalculator # Assuming these imports are correct
from utils.feedback_manager import FeedbackPriority # Assuming these imports are correct

class JumpingJackState(Enum):
    """States for the jumping jack exercise"""
    IDLE = 0         # Starting position, arms down, legs together
    STARTING = 1     # Initial upward/outward movement detected
    ARMS_UP = 2      # Arms have reached the top position
    LEGS_APART = 3   # Legs have reached the 'apart' position (often simultaneous with ARMS_UP)
    RETURNING = 4    # Arms/legs moving back towards the start
    COMPLETED = 5    # Momentary state after returning to IDLE (for rep counting)

class JumpingJackAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the jumping jack exercise.

    Tracks the jumping jack movement, provides form feedback, and supports
    both rep-based and timed modes.
    """

    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the jumping jack analyzer.

        Args:
            thresholds: Dictionary of threshold values for analysis.
        """
        # --- MOVED INITIALIZATIONS HERE ---
        # Initialize attributes used in reset() *before* calling super().__init__()
        self.is_timed_mode = False # Default to rep-based
        self.start_time = None
        self.elapsed_time = 0.0 # Use float for time
        self.last_time_update = None
        self.arm_angle_buffer = deque(maxlen=5)
        self.leg_spread_buffer = deque(maxlen=5)
        self.cycle_time_buffer = deque(maxlen=10) # For rhythm analysis
        self.last_rep_time = None
        # --- END MOVED INITIALIZATIONS ---

        # Now call the parent constructor, which will call our overridden reset()
        super().__init__(thresholds) # This calls reset() internally

        # Initialize remaining attributes
        self.state = JumpingJackState.IDLE
        self.target_duration = 0.0 # Target duration in seconds (float)
        self.angle_calculator = AngleCalculator() # Instantiate angle calculator

        # Store thresholds locally for easier access
        # Arm angle: Angle between hip-shoulder and shoulder-wrist (higher means arms up)
        self.arm_up_threshold = self.thresholds.get('jumping_jack_arm_up', 140) # Angle when arms are considered 'up'
        self.arm_down_threshold = self.thresholds.get('jumping_jack_arm_down', 45) # Angle when arms are considered 'down'
        # Leg spread: Ratio of ankle distance to hip width (higher means legs apart)
        self.legs_apart_threshold = self.thresholds.get('jumping_jack_legs_apart', 1.8) # Ratio when legs are 'apart'
        self.legs_together_threshold = self.thresholds.get('jumping_jack_legs_together', 1.2) # Ratio when legs are 'together'


    def reset(self):
        """Reset the analyzer state, preparing for a new set or timed session."""
        super().reset() # Call parent reset

        # Reset time only if NOT currently in an active timed session
        # Or perhaps reset time always, depending on desired behavior when reset is called mid-session
        # Current logic: Resets timer info regardless of mode when reset() is called.
        self.start_time = None
        self.elapsed_time = 0.0
        self.last_time_update = None

        # Reset buffers and tracking variables
        if hasattr(self, 'arm_angle_buffer'):
            self.arm_angle_buffer.clear()
        if hasattr(self, 'leg_spread_buffer'):
            self.leg_spread_buffer.clear()
        if hasattr(self, 'cycle_time_buffer'):
             self.cycle_time_buffer.clear()
        self.last_rep_time = None
        # self.state = JumpingJackState.IDLE # Reset state if needed

    def set_timed_mode(self, is_timed: bool, duration: float = 0.0):
        """
        Configure the analyzer for timed or rep-based mode.

        Args:
            is_timed: True for timed exercise, False for rep-based.
            duration: Target duration in seconds for timed mode.
        """
        self.is_timed_mode = is_timed
        self.target_duration = max(0.0, float(duration))
        # Reset timer and state when mode is set/changed
        self.reset()
        self.state = JumpingJackState.IDLE
        # Start timer immediately if set to timed mode
        # if is_timed:
        #     self.start_time = time.time()
        #     self.last_time_update = self.start_time
        #     self.elapsed_time = 0.0
        # Consider starting timer only when the first movement is detected in update_state

    def is_timed_exercise(self) -> bool:
        """Returns True if currently configured for timed mode."""
        return self.is_timed_mode

    def calculate_exercise_metrics(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate metrics relevant for jumping jack analysis (arm angle, leg spread).

        Args:
            keypoints: Dictionary of landmark keypoints [x, y, z, visibility].

        Returns:
            Dictionary of metric names and smoothed values.
        """
        metrics = {}
        default_kp = [0, 0, 0, 0] # Default for missing keypoints
        vis_threshold = 0.5 # Confidence threshold

        # --- Keypoints ---
        left_shoulder = keypoints.get('left_shoulder', default_kp)
        right_shoulder = keypoints.get('right_shoulder', default_kp)
        left_hip = keypoints.get('left_hip', default_kp)
        right_hip = keypoints.get('right_hip', default_kp)
        left_wrist = keypoints.get('left_wrist', default_kp)
        right_wrist = keypoints.get('right_wrist', default_kp)
        left_ankle = keypoints.get('left_ankle', default_kp)
        right_ankle = keypoints.get('right_ankle', default_kp)

        # --- Visibility Checks ---
        ls_vis = left_shoulder[3] > vis_threshold
        rs_vis = right_shoulder[3] > vis_threshold
        lh_vis = left_hip[3] > vis_threshold
        rh_vis = right_hip[3] > vis_threshold
        lw_vis = left_wrist[3] > vis_threshold
        rw_vis = right_wrist[3] > vis_threshold
        la_vis = left_ankle[3] > vis_threshold
        ra_vis = right_ankle[3] > vis_threshold

        # --- Calculate Arm Angles ---
        left_arm_angle = right_arm_angle = None
        # Angle: Hip-Shoulder-Wrist
        if lh_vis and ls_vis and lw_vis:
            left_arm_angle = self.angle_calculator.angle_deg(left_hip, left_shoulder, left_wrist)
        if rh_vis and rs_vis and rw_vis:
            right_arm_angle = self.angle_calculator.angle_deg(right_hip, right_shoulder, right_wrist)

        # Average Arm Angle
        valid_arm_angles = [a for a in [left_arm_angle, right_arm_angle] if a is not None]
        if valid_arm_angles:
            avg_arm_angle = sum(valid_arm_angles) / len(valid_arm_angles)
            self.arm_angle_buffer.append(avg_arm_angle)
            if len(self.arm_angle_buffer) > 0:
                metrics['smoothed_arm_angle'] = sum(self.arm_angle_buffer) / len(self.arm_angle_buffer)

        # --- Calculate Leg Spread Ratio ---
        if lh_vis and rh_vis and la_vis and ra_vis:
            # Use X,Y coordinates for distance calculation
            hip_width = ((right_hip[0] - left_hip[0])**2 + (right_hip[1] - left_hip[1])**2)**0.5
            ankle_spread = ((right_ankle[0] - left_ankle[0])**2 + (right_ankle[1] - left_ankle[1])**2)**0.5

            if hip_width > 1e-6: # Avoid division by zero
                leg_spread_ratio = ankle_spread / hip_width
                self.leg_spread_buffer.append(leg_spread_ratio)
                if len(self.leg_spread_buffer) > 0:
                    metrics['smoothed_leg_spread'] = sum(self.leg_spread_buffer) / len(self.leg_spread_buffer)
            else:
                 metrics['smoothed_leg_spread'] = 0 # Or some indicator value

        return metrics

    def analyze_form(self, metrics: Dict[str, float]) -> List[str]:
        """
        Analyze jumping jack form based on calculated metrics.

        Args:
            metrics: Dictionary of calculated metric names and values.

        Returns:
            List of feedback strings for the current frame.
        """
        feedback = []
        arm_angle = metrics.get('smoothed_arm_angle')
        leg_spread = metrics.get('smoothed_leg_spread')

        if arm_angle is None or leg_spread is None:
            return ["Ensure arms and legs are clearly visible."]

        # Check form primarily during the 'up' phase
        if self.state in [JumpingJackState.ARMS_UP, JumpingJackState.LEGS_APART]:
            # Check Arm Height
            if arm_angle < self.arm_up_threshold * 0.9: # Allow some tolerance
                feedback.append("Raise arms higher")

            # Check Leg Width
            if leg_spread < self.legs_apart_threshold * 0.9: # Allow some tolerance
                feedback.append("Spread legs wider")

        # Check form during the 'down' phase (optional)
        # if self.state == JumpingJackState.RETURNING:
            # if arm_angle > self.arm_down_threshold * 1.1:
            #     feedback.append("Bring arms fully down")
            # if leg_spread > self.legs_together_threshold * 1.1:
            #     feedback.append("Bring legs fully together")


        # Check Rhythm (can be done in update_state when rep is counted)
        # if len(self.cycle_time_buffer) > 3:
        #     avg_cycle_time = sum(self.cycle_time_buffer) / len(self.cycle_time_buffer)
        #     std_dev_cycle_time = np.std(list(self.cycle_time_buffer)) if len(self.cycle_time_buffer) > 1 else 0
        #     # Check for consistency?
        #     # if std_dev_cycle_time > avg_cycle_time * 0.3: # Example: High variation
        #     #     feedback.append("Try to maintain a steady rhythm")


        # If no specific issues found during the active phase
        if not feedback and self.state in [JumpingJackState.ARMS_UP, JumpingJackState.LEGS_APART]:
            feedback.append("Good form!")

        return feedback

    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[JumpingJackState, List[str]]:
        """
        Update the jumping jack state machine based on keypoints and time.

        Args:
            keypoints: Dictionary of landmark keypoints.

        Returns:
            Tuple of (current state, persistent feedback list from manager).
        """
        now = time.time()
        metrics = self.calculate_exercise_metrics(keypoints)
        arm_angle = metrics.get('smoothed_arm_angle')
        leg_spread = metrics.get('smoothed_leg_spread')
        frame_feedback = [] # Specific feedback for this frame/transition

        # --- Handle Timed Mode ---
        if self.is_timed_mode:
            # Start timer on first valid pose detection if not already started
            if self.start_time is None and arm_angle is not None and leg_spread is not None:
                 self.start_time = now
                 self.last_time_update = now
                 self.elapsed_time = 0.0
                 self.feedback_manager.add_feedback("Timer started!", FeedbackPriority.INFO)


            if self.start_time and self.last_time_update:
                self.elapsed_time += now - self.last_time_update
            self.last_time_update = now

            # Check for completion
            if self.target_duration > 0 and self.elapsed_time >= self.target_duration:
                if self.state != JumpingJackState.COMPLETED: # Avoid multiple completions
                     self.state = JumpingJackState.COMPLETED
                     completion_msg = f"Time complete! ({self.elapsed_time:.1f}s)"
                     frame_feedback.append(completion_msg)
                     self.feedback_manager.add_feedback(completion_msg, FeedbackPriority.SUCCESS)
                     # Reset timer info? Or keep final time? Keep for now.
                     # self.start_time = None
                     # self.last_time_update = None
                # In timed mode, stay COMPLETED until reset or mode change
                return self.state, self.feedback_manager.get_feedback() # Early exit if time is up

        # --- State Machine Logic (Rep Mode or Timed Mode before completion) ---
        if arm_angle is None or leg_spread is None:
            # If key data is missing, potentially revert to IDLE or hold state
            # Reverting to IDLE might interrupt reps/timer if view is briefly lost
            # Holding state might be better, maybe add a timeout?
            # For now, just return current state and provide visibility feedback
             if self.state != JumpingJackState.IDLE: # Avoid spamming in idle
                  self.feedback_manager.add_feedback("Ensure arms and legs are visible.", FeedbackPriority.WARN)
             return self.state, self.feedback_manager.get_feedback()

        # Current state logic
        current_state = self.state

        if current_state == JumpingJackState.IDLE:
            # Detect start: Arms moving up OR legs moving apart significantly
            arms_moving_up = arm_angle > (self.arm_down_threshold + 20) # Hysteresis
            legs_moving_apart = leg_spread > (self.legs_together_threshold + 0.2) # Hysteresis

            if arms_moving_up or legs_moving_apart:
                self.state = JumpingJackState.STARTING
                self.feedback_manager.clear_feedback() # Clear feedback for new rep

                # Calculate cycle time if previous rep time exists
                if self.last_rep_time is not None:
                    cycle_time = now - self.last_rep_time
                    if 0.3 < cycle_time < 4.0: # Filter unreasonable times
                        self.cycle_time_buffer.append(cycle_time)
                        # Analyze rhythm here or in analyze_form
                        if len(self.cycle_time_buffer) > 3:
                             avg_cycle = np.mean(list(self.cycle_time_buffer))
                             # Add rhythm feedback based on avg_cycle if needed
                             # e.g., if avg_cycle < 0.6: self.feedback_manager.add_feedback("Slow down", ...)

                self.last_rep_time = now # Record time at the start of the upward movement


        elif current_state == JumpingJackState.STARTING:
            # Transition to ARMS_UP when arms reach threshold
            if arm_angle >= self.arm_up_threshold:
                self.state = JumpingJackState.ARMS_UP
                # Analyze form at the peak (arms up)
                form_feedback = self.analyze_form(metrics)
                frame_feedback.extend(form_feedback)
                for fb in form_feedback:
                     priority = FeedbackPriority.LOW if "Good" in fb else FeedbackPriority.MEDIUM
                     self.feedback_manager.add_feedback(fb, priority)

            # If arms go back down before reaching the top, reset to IDLE
            elif arm_angle < self.arm_down_threshold + 10: # Hysteresis
                 self.state = JumpingJackState.IDLE


        elif current_state == JumpingJackState.ARMS_UP:
             # Transition to LEGS_APART when legs reach threshold
             # This might happen almost simultaneously with ARMS_UP
             if leg_spread >= self.legs_apart_threshold:
                  self.state = JumpingJackState.LEGS_APART
                  # Analyze form again now that legs are also apart
                  form_feedback = self.analyze_form(metrics)
                  frame_feedback.extend(form_feedback)
                  for fb in form_feedback:
                     priority = FeedbackPriority.LOW if "Good" in fb else FeedbackPriority.HIGH # Higher priority at peak
                     self.feedback_manager.add_feedback(fb, priority)

             # If arms start returning before legs are apart, move to RETURNING
             elif arm_angle < self.arm_up_threshold * 0.95: # Hysteresis
                  self.state = JumpingJackState.RETURNING


        elif current_state == JumpingJackState.LEGS_APART:
             # Detect start of return movement (arms OR legs start coming in)
             arms_returning = arm_angle < self.arm_up_threshold * 0.95 # Hysteresis
             legs_returning = leg_spread < self.legs_apart_threshold * 0.95 # Hysteresis

             if arms_returning or legs_returning:
                  self.state = JumpingJackState.RETURNING


        elif current_state == JumpingJackState.RETURNING:
             # Detect return to starting position (arms down AND legs together)
             arms_down = arm_angle < self.arm_down_threshold
             legs_together = leg_spread < self.legs_together_threshold

             if arms_down and legs_together:
                  # --- Rep Completed ---
                  # Don't count reps if in timed mode and time already completed
                  if not (self.is_timed_mode and self.state == JumpingJackState.COMPLETED):
                       self.rep_count += 1
                       completion_msg = f"Rep {self.rep_count}"
                       # Don't spam rep count in timed mode
                       if not self.is_timed_mode:
                            frame_feedback.append(completion_msg)
                            self.feedback_manager.add_feedback(completion_msg, FeedbackPriority.INFO)

                  # Transition back to IDLE to wait for the next rep
                  self.state = JumpingJackState.IDLE


        # Add any frame-specific feedback to manager (optional)
        # for fb in frame_feedback:
        #     self.feedback_manager.add_feedback(fb, FeedbackPriority.DEBUG)

        return self.state, self.feedback_manager.get_feedback()

    def get_elapsed_time(self) -> float:
        """Get the elapsed time in seconds for timed mode."""
        if not self.is_timed_mode:
             return 0.0
        # Update elapsed time based on last known update time if timer is running
        if self.state != JumpingJackState.COMPLETED and self.last_time_update:
             now = time.time()
             current_elapsed = self.elapsed_time + (now - self.last_time_update)
             return current_elapsed
        return self.elapsed_time # Return last calculated time if stopped or not started

    def get_remaining_time(self) -> float:
        """Get the remaining time in seconds for timed mode."""
        if not self.is_timed_mode or self.target_duration <= 0:
            return 0.0
        current_elapsed = self.get_elapsed_time() # Get potentially updated elapsed time
        remaining = max(0.0, self.target_duration - current_elapsed)
        return remaining

    def get_state_name(self) -> str:
        """Get the name of the current jumping jack state."""
        return self.state.name
