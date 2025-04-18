from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState # Assuming these imports are correct
from models.angle_calculator import AngleCalculator # Assuming these imports are correct
from utils.feedback_manager import FeedbackPriority # Assuming these imports are correct

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
        # --- MOVED INITIALIZATIONS HERE ---
        # Initialize attributes used in reset() *before* calling super().__init__()
        self.hip_heights = deque(maxlen=10)
        self.shoulder_heights = deque(maxlen=10)
        self.hip_alignment_buffer = deque(maxlen=5)
        self.max_elbow_angle = 0 # Initialize attributes needed by reset()
        self.min_elbow_angle = 180 # Initialize attributes needed by reset()
        # --- END MOVED INITIALIZATIONS ---

        # Now call the parent constructor, which will call our overridden reset()
        super().__init__(thresholds)

        # Initialize remaining attributes
        self.state = PushupState.IDLE
        self.prev_elbow_angle = 180

        # Thresholds for pushup (consider loading from thresholds dict if applicable)
        self.pushup_start_threshold = 160   # Angle to detect start of pushup (arms extended)
        self.pushup_down_threshold = 120    # Angle to detect downward phase
        self.pushup_up_threshold = 150      # Angle to detect completion

        # Note: hip_heights, shoulder_heights, and hip_alignment_buffer
        # are already initialized above before super().__init__()

    def reset(self):
        """Reset the analyzer between reps"""
        super().reset() # Call parent reset first if it does anything important
        # Reset specific pushup attributes
        self.max_elbow_angle = 0
        self.min_elbow_angle = 180
        # Check if attributes exist before clearing, although they should now
        if hasattr(self, 'hip_heights'):
            self.hip_heights.clear()
        if hasattr(self, 'shoulder_heights'):
            self.shoulder_heights.clear()
        if hasattr(self, 'hip_alignment_buffer'):
            self.hip_alignment_buffer.clear()
        # Reset state to IDLE only if needed, or handle state transitions explicitly
        # self.state = PushupState.IDLE # Consider if reset should always go to IDLE

    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for pushup analysis

        Args:
            keypoints: Dictionary of landmark keypoints

        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        angle_calculator = AngleCalculator() # Instantiate if not already an instance variable

        # Calculate elbow angle for pushup (average of left and right if available)
        left_elbow_angle = right_elbow_angle = None
        if all(k in keypoints for k in ['left_shoulder', 'left_elbow', 'left_wrist']):
            left_elbow_angle = angle_calculator.angle_deg(
                keypoints['left_shoulder'],
                keypoints['left_elbow'],
                keypoints['left_wrist']
            )
            angles['left_elbow_angle'] = left_elbow_angle

        if all(k in keypoints for k in ['right_shoulder', 'right_elbow', 'right_wrist']):
            right_elbow_angle = angle_calculator.angle_deg(
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

        # Get hip and shoulder heights (assuming keypoints format [x, y, z, visibility] or similar)
        # Use a default value like [0, 0, 0, 0] if keypoint is missing
        default_kp = [0, 0, 0, 0]
        left_hip_y = keypoints.get('left_hip', default_kp)[1]
        right_hip_y = keypoints.get('right_hip', default_kp)[1]
        left_shoulder_y = keypoints.get('left_shoulder', default_kp)[1]
        right_shoulder_y = keypoints.get('right_shoulder', default_kp)[1]

        # Check if keypoints were actually found (y-coordinate > 0 assuming origin is top-left)
        # Adjust this logic based on your coordinate system and visibility scores if available
        left_hip_valid = left_hip_y > 0 and keypoints.get('left_hip', default_kp)[-1] > 0.5 # Example visibility check
        right_hip_valid = right_hip_y > 0 and keypoints.get('right_hip', default_kp)[-1] > 0.5
        left_shoulder_valid = left_shoulder_y > 0 and keypoints.get('left_shoulder', default_kp)[-1] > 0.5
        right_shoulder_valid = right_shoulder_y > 0 and keypoints.get('right_shoulder', default_kp)[-1] > 0.5

        hip_y = None
        if left_hip_valid and right_hip_valid:
            hip_y = (left_hip_y + right_hip_y) / 2
        elif left_hip_valid:
            hip_y = left_hip_y
        elif right_hip_valid:
            hip_y = right_hip_y

        shoulder_y = None
        if left_shoulder_valid and right_shoulder_valid:
            shoulder_y = (left_shoulder_y + right_shoulder_y) / 2
        elif left_shoulder_valid:
            shoulder_y = left_shoulder_y
        elif right_shoulder_valid:
            shoulder_y = right_shoulder_y


        if hip_y is not None and shoulder_y is not None:
            # Add to height buffers
            self.hip_heights.append(hip_y)
            self.shoulder_heights.append(shoulder_y)

            # Calculate hip-shoulder alignment (only if enough data points)
            if len(self.hip_heights) >= 5 and len(self.shoulder_heights) >= 5: # Use >= instead of >
                avg_hip_y = sum(self.hip_heights) / len(self.hip_heights)
                avg_shoulder_y = sum(self.shoulder_heights) / len(self.shoulder_heights)

                # Calculate hip alignment (difference in average Y coordinates)
                # Larger Y usually means lower on the screen (origin top-left)
                # Adjust sign if origin is bottom-left
                hip_alignment = avg_hip_y - avg_shoulder_y
                self.hip_alignment_buffer.append(hip_alignment)

                # Calculate average alignment over the buffer period
                if len(self.hip_alignment_buffer) > 0: # Check buffer is not empty
                    avg_hip_alignment = sum(self.hip_alignment_buffer) / len(self.hip_alignment_buffer)
                    angles['hip_alignment'] = avg_hip_alignment

                    # Positive values (hip_y > shoulder_y) mean hips are lower (sagging)
                    # Negative values (hip_y < shoulder_y) mean hips are higher (piking)

        return angles

    def analyze_form(self, keypoints: Dict[str, List[float]], is_start: bool = False) -> List[str]:
        """
        Analyze pushup form based on detected keypoints

        Args:
            keypoints: Dictionary of landmark keypoints
            is_start: Whether this is the start of a new rep (unused in current logic)

        Returns:
            List of feedback strings about the pushup form
        """
        feedback = []

        # Calculate relevant angles
        angles = self.calculate_exercise_angles(keypoints)
        elbow_angle = angles.get('elbow_angle', 180)
        hip_alignment = angles.get('hip_alignment') # Can be None if not enough data

        # Update min/max angles for the current rep attempt
        # Note: reset() should handle resetting these for a new rep
        self.max_elbow_angle = max(self.max_elbow_angle, elbow_angle)
        self.min_elbow_angle = min(self.min_elbow_angle, elbow_angle)

        # Only analyze form during the active pushup phases
        if self.state in [PushupState.PUSHUP_DOWN, PushupState.PUSHUP_HOLD, PushupState.PUSHUP_UP]:
            # Analyze depth (using thresholds from self.thresholds dictionary)
            # Use get() with default values to avoid KeyError if threshold isn't set
            too_low_threshold = self.thresholds.get('pushup_too_low', 70)
            not_low_enough_threshold = self.thresholds.get('pushup_not_low_enough', 120) # Check if this should be higher

            # Check depth primarily during the DOWN or HOLD phase
            if self.state in [PushupState.PUSHUP_DOWN, PushupState.PUSHUP_HOLD]:
                 if elbow_angle < too_low_threshold:
                    feedback.append("You're going too low")
                 # Check for not low enough only at the bottom (HOLD state or near min angle)
                 # This check might be better placed in update_state when transitioning UP
                 # elif elbow_angle > not_low_enough_threshold: # Re-evaluate this condition
                 #    feedback.append("Lower your chest more")


            # Analyze hip alignment (if calculated)
            if hip_alignment is not None:
                hip_sag_threshold = self.thresholds.get('pushup_hip_sag', 15) # Positive value = sag
                hip_pike_threshold = self.thresholds.get('pushup_hip_pike', 25) # Positive value for threshold, check against negative alignment

                if hip_alignment > hip_sag_threshold:
                    feedback.append("Keep your hips up, core engaged")
                elif hip_alignment < -hip_pike_threshold: # Check against negative value for piking
                    feedback.append("Lower your hips, maintain a straight line")

            # If no specific negative feedback, maybe add positive feedback (optional)
            # if not feedback and self.state == PushupState.PUSHUP_HOLD: # Example: Positive feedback at the hold point
            #     feedback.append("Good form at the bottom")

        return feedback

    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[PushupState, List[str]]:
        """
        Update the pushup state based on detected keypoints and provide feedback.

        Args:
            keypoints: Dictionary of landmark keypoints

        Returns:
            Tuple of (current state, feedback list)
        """
        current_feedback = [] # Feedback for this specific frame update
        angles = self.calculate_exercise_angles(keypoints)
        elbow_angle = angles.get('elbow_angle', 180)

        # --- State Machine Logic ---
        if self.state == PushupState.IDLE:
            # Detect the start of a pushup (arms extended but starting to bend)
            if self.pushup_down_threshold < elbow_angle < self.pushup_start_threshold:
                 # Check if angle is decreasing (moving down)
                 if elbow_angle < self.prev_elbow_angle - 1: # Small tolerance for noise
                    self.state = PushupState.PUSHUP_START
                    self.feedback_manager.clear_feedback() # Clear old feedback for new rep
                    self.reset() # Reset counters and angles for the new rep
                    current_feedback.append("Starting Pushup") # Optional feedback

        elif self.state == PushupState.PUSHUP_START:
            # Transition to DOWN phase once significant bending occurs
            if elbow_angle < self.pushup_down_threshold:
                self.state = PushupState.PUSHUP_DOWN
            # Abort if person goes back up immediately
            elif elbow_angle > self.prev_elbow_angle + 5: # Allow for some wiggle room
                 self.state = PushupState.IDLE
                 self.feedback_manager.clear_feedback()
                 current_feedback.append("Pushup aborted")

        elif self.state == PushupState.PUSHUP_DOWN:
            # Detect the bottom of the pushup (angle stops decreasing or starts increasing)
            # Use a small threshold to account for slight movements at the bottom
            if elbow_angle >= self.prev_elbow_angle - 1: # Angle stopped decreasing or started increasing
                self.state = PushupState.PUSHUP_HOLD
                # Analyze form at the bottom of the rep
                form_feedback = self.analyze_form(keypoints)
                current_feedback.extend(form_feedback)

                # Check depth specifically at the bottom
                not_low_enough_threshold = self.thresholds.get('pushup_not_low_enough', 95) # Threshold for minimum depth
                if elbow_angle > not_low_enough_threshold:
                     depth_feedback = "Lower your chest more"
                     if depth_feedback not in current_feedback: # Avoid duplicate messages
                         current_feedback.append(depth_feedback)
                     self.rep_error = True # Mark rep as having an error

                # Add feedback to manager
                for fb in current_feedback:
                    priority = FeedbackPriority.HIGH if "Correct form" not in fb else FeedbackPriority.LOW
                    self.feedback_manager.add_feedback(fb, priority)
                    if priority == FeedbackPriority.HIGH:
                        self.rep_error = True # Mark rep error if high priority feedback

            # Optional: Provide continuous form feedback during descent
            # form_feedback = self.analyze_form(keypoints)
            # current_feedback.extend(form_feedback) # Add to frame feedback

        elif self.state == PushupState.PUSHUP_HOLD:
            # Detect upward movement
            if elbow_angle > self.prev_elbow_angle + 1: # Start moving up
                self.state = PushupState.PUSHUP_UP

        elif self.state == PushupState.PUSHUP_UP:
            # Detect completion (reaching near full extension)
            if elbow_angle >= self.pushup_up_threshold:
                self.state = PushupState.COMPLETED
                # Final form check at the top (optional, usually less critical here)
                # form_feedback = self.analyze_form(keypoints)
                # current_feedback.extend(form_feedback)

                if not self.rep_error:
                    self.rep_count += 1
                    current_feedback.append(f"Rep {self.rep_count} Complete!")
                    self.feedback_manager.add_feedback(f"Rep {self.rep_count} Complete!", FeedbackPriority.INFO)
                else:
                    current_feedback.append("Rep incomplete due to form error.")
                    self.feedback_manager.add_feedback("Rep incomplete due to form error.", FeedbackPriority.HIGH)

                # Transition back to IDLE to wait for the next rep
                self.state = PushupState.IDLE
                # Don't reset() here, wait for the next PUSHUP_START

            # Optional: Provide continuous form feedback during ascent
            # form_feedback = self.analyze_form(keypoints)
            # current_feedback.extend(form_feedback) # Add to frame feedback

        # elif self.state == PushupState.COMPLETED: # Handled in PUSHUP_UP transition
        #     # This state is momentary, transition back to IDLE
        #     self.state = PushupState.IDLE


        # Update the previous angle for the next frame's comparison
        self.prev_elbow_angle = elbow_angle

        # Return the current state and the feedback collected *during this update*
        # The feedback manager holds the persistent feedback across frames
        return self.state, self.feedback_manager.get_feedback() # Return persistent feedback

    def get_state_name(self) -> str:
        """Get the name of the current pushup state"""
        return self.state.name

