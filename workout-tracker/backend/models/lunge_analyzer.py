from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import deque
from models.exercise_base import ExerciseAnalyzer, ExerciseState # Assuming these imports are correct
from models.angle_calculator import AngleCalculator # Assuming these imports are correct
from utils.feedback_manager import FeedbackPriority # Assuming these imports are correct

class LungeState(Enum):
    """States for the lunge exercise"""
    IDLE = 0
    LUNGE_START = 1
    LUNGE_DOWN = 2
    LUNGE_HOLD = 3
    LUNGE_UP = 4
    COMPLETED = 5

class LungeAnalyzer(ExerciseAnalyzer):
    """
    Analyzer for the lunge exercise

    Tracks the lunge movement through its stages and provides feedback
    on form and technique.
    """

    def __init__(self, thresholds: Dict[str, float]):
        """
        Initialize the lunge analyzer

        Args:
            thresholds: Dictionary of threshold values for lunge analysis
        """
        # --- MOVED INITIALIZATIONS HERE ---
        # Initialize attributes used in reset() *before* calling super().__init__()
        self.knee_alignment_buffer = deque(maxlen=5)
        self.front_knee_angles = deque(maxlen=10)
        self.back_knee_angles = deque(maxlen=10)
        self.forward_leg = None  # 'left' or 'right'
        self.max_knee_angle = 0  # Initialize attributes needed by reset()
        self.min_knee_angle = 180 # Initialize attributes needed by reset()
        # --- END MOVED INITIALIZATIONS ---

        # Now call the parent constructor, which will call our overridden reset()
        super().__init__(thresholds)

        # Initialize remaining attributes
        self.state = LungeState.IDLE
        self.prev_knee_angle = 180 # Use this to track the primary angle for state changes
        self.angle_calculator = AngleCalculator() # Instantiate angle calculator

        # Thresholds for lunge (consider loading from thresholds dict if applicable)
        self.lunge_start_threshold = thresholds.get('lunge_start_threshold', 160)
        self.lunge_down_threshold = thresholds.get('lunge_down_threshold', 120)
        self.lunge_up_threshold = thresholds.get('lunge_up_threshold', 150)

        # Note: Attributes used in reset() are already initialized above

    def reset(self):
        """Reset the analyzer between reps"""
        super().reset() # Call parent reset first
        # Reset specific lunge attributes
        self.max_knee_angle = 0
        self.min_knee_angle = 180
        self.prev_knee_angle = 180 # Reset previous angle as well
        # Check if attributes exist before clearing (should be guaranteed now)
        if hasattr(self, 'knee_alignment_buffer'):
            self.knee_alignment_buffer.clear()
        if hasattr(self, 'front_knee_angles'):
            self.front_knee_angles.clear()
        if hasattr(self, 'back_knee_angles'):
            self.back_knee_angles.clear()
        self.forward_leg = None # Reset forward leg detection
        # Reset state if necessary, or handle in update_state
        # self.state = LungeState.IDLE

    def _detect_forward_leg(self, keypoints: Dict[str, List[float]]) -> Optional[str]:
        """
        Detect which leg is forward in the lunge based on ankle Z-coordinate (depth).
        Assumes Z increases away from the camera. Adjust if coordinate system differs.

        Args:
            keypoints: Dictionary of landmark keypoints [x, y, z, visibility]

        Returns:
            'left', 'right', or None if can't determine
        """
        default_kp = [0, 0, 0, 0]
        left_ankle = keypoints.get('left_ankle', default_kp)
        right_ankle = keypoints.get('right_ankle', default_kp)

        # Check visibility or confidence score if available
        left_visible = left_ankle[3] > 0.5 # Example threshold
        right_visible = right_ankle[3] > 0.5

        if left_visible and right_visible:
            # Compare Z-coordinates (depth)
            # Smaller Z is closer to the camera (usually the back leg in a lunge)
            # Larger Z is further away (usually the front leg)
            # Adjust comparison if Z decreases away from camera
            if left_ankle[2] > right_ankle[2]:
                return 'left' # Left leg is further away (forward)
            elif right_ankle[2] > left_ankle[2]:
                return 'right' # Right leg is further away (forward)
            else:
                # If Z is very similar, try X coordinate as a fallback (less reliable for depth)
                if left_ankle[0] < right_ankle[0]: # Assuming facing camera, left foot has smaller X
                    return 'left' # Tentative guess
                else:
                    return 'right' # Tentative guess
        elif left_visible:
            return 'left' # Only left is visible, assume it's the one moving
        elif right_visible:
            return 'right' # Only right is visible
        else:
            return None # Cannot determine

    def calculate_exercise_angles(self, keypoints: Dict[str, List[float]]) -> Dict[str, float]:
        """
        Calculate angles relevant for lunge analysis

        Args:
            keypoints: Dictionary of landmark keypoints

        Returns:
            Dictionary of angle names and values
        """
        angles = {}
        default_kp = [0, 0, 0, 0] # Default for missing keypoints

        # --- Calculate raw angles first ---
        left_knee_angle = right_knee_angle = None
        left_hip_angle = right_hip_angle = None # For torso lean check

        # Left Knee Angle
        if all(k in keypoints for k in ['left_hip', 'left_knee', 'left_ankle']):
            left_knee_angle = self.angle_calculator.angle_deg(
                keypoints['left_hip'], keypoints['left_knee'], keypoints['left_ankle']
            )
            angles['left_knee_angle'] = left_knee_angle

        # Right Knee Angle
        if all(k in keypoints for k in ['right_hip', 'right_knee', 'right_ankle']):
            right_knee_angle = self.angle_calculator.angle_deg(
                keypoints['right_hip'], keypoints['right_knee'], keypoints['right_ankle']
            )
            angles['right_knee_angle'] = right_knee_angle

        # Left Hip Angle (Torso relative to thigh)
        if all(k in keypoints for k in ['left_shoulder', 'left_hip', 'left_knee']):
             # Use midpoint of shoulders if available for better torso line
            left_shoulder = keypoints.get('left_shoulder', default_kp)
            right_shoulder = keypoints.get('right_shoulder', default_kp)
            if left_shoulder[3] > 0.5 and right_shoulder[3] > 0.5:
                 mid_shoulder = [(ls+rs)/2 for ls, rs in zip(left_shoulder[:3], right_shoulder[:3])]
            elif left_shoulder[3] > 0.5:
                 mid_shoulder = left_shoulder[:3]
            else:
                 mid_shoulder = None

            if mid_shoulder:
                 left_hip_angle = self.angle_calculator.angle_deg(
                    mid_shoulder, keypoints['left_hip'], keypoints['left_knee']
                 )
                 angles['left_hip_angle'] = left_hip_angle


        # Right Hip Angle (Torso relative to thigh)
        if all(k in keypoints for k in ['right_shoulder', 'right_hip', 'right_knee']):
            left_shoulder = keypoints.get('left_shoulder', default_kp)
            right_shoulder = keypoints.get('right_shoulder', default_kp)
            if left_shoulder[3] > 0.5 and right_shoulder[3] > 0.5:
                 mid_shoulder = [(ls+rs)/2 for ls, rs in zip(left_shoulder[:3], right_shoulder[:3])]
            elif right_shoulder[3] > 0.5:
                 mid_shoulder = right_shoulder[:3]
            else:
                 mid_shoulder = None

            if mid_shoulder:
                right_hip_angle = self.angle_calculator.angle_deg(
                    mid_shoulder, keypoints['right_hip'], keypoints['right_knee']
                )
                angles['right_hip_angle'] = right_hip_angle

        # --- Determine forward leg and assign front/back angles ---
        # Detect forward leg only if needed (e.g., at the start or if it becomes None)
        if self.forward_leg is None and self.state in [LungeState.IDLE, LungeState.LUNGE_START]:
             self.forward_leg = self._detect_forward_leg(keypoints)

        front_knee_angle = back_knee_angle = None
        front_hip_angle = back_hip_angle = None
        front_knee_kp_name = back_knee_kp_name = None
        front_ankle_kp_name = back_ankle_kp_name = None
        front_hip_kp_name = back_hip_kp_name = None


        if self.forward_leg == 'left':
            front_knee_angle = left_knee_angle
            back_knee_angle = right_knee_angle
            front_hip_angle = left_hip_angle
            back_hip_angle = right_hip_angle
            front_knee_kp_name = 'left_knee'
            back_knee_kp_name = 'right_knee'
            front_ankle_kp_name = 'left_ankle'
            back_ankle_kp_name = 'right_ankle'
            front_hip_kp_name = 'left_hip'
            back_hip_kp_name = 'right_hip'
        elif self.forward_leg == 'right':
            front_knee_angle = right_knee_angle
            back_knee_angle = left_knee_angle
            front_hip_angle = right_hip_angle
            back_hip_angle = left_hip_angle
            front_knee_kp_name = 'right_knee'
            back_knee_kp_name = 'left_knee'
            front_ankle_kp_name = 'right_ankle'
            back_ankle_kp_name = 'left_ankle'
            front_hip_kp_name = 'right_hip'
            back_hip_kp_name = 'left_hip'
        # else: # If forward leg couldn't be determined, don't calculate front/back specific metrics
        #     return angles # Return only raw angles if needed

        # Store front/back angles if determined
        if front_knee_angle is not None:
            angles['front_knee_angle'] = front_knee_angle
            self.front_knee_angles.append(front_knee_angle) # Add to buffer
        if back_knee_angle is not None:
            angles['back_knee_angle'] = back_knee_angle
            self.back_knee_angles.append(back_knee_angle) # Add to buffer
        if front_hip_angle is not None:
             angles['front_hip_angle'] = front_hip_angle
        if back_hip_angle is not None:
             angles['back_hip_angle'] = back_hip_angle


        # --- Calculate Knee Alignment / Deviation (Front Leg) ---
        if front_knee_kp_name and front_ankle_kp_name and front_hip_kp_name:
            if all(k in keypoints for k in [front_knee_kp_name, front_ankle_kp_name, front_hip_kp_name]):
                knee = keypoints[front_knee_kp_name]
                ankle = keypoints[front_ankle_kp_name]
                hip = keypoints[front_hip_kp_name]

                # Calculate the horizontal distance (X-coordinate) between knee and ankle
                # This helps detect if the knee is collapsing inwards (valgus) or outwards (varus)
                # relative to the ankle. Assumes a mostly frontal view.
                knee_ankle_x_diff = knee[0] - ankle[0]

                # Normalize by hip-ankle distance or another metric if needed for scale invariance
                # hip_ankle_dist = ((hip[0] - ankle[0])**2 + (hip[1] - ankle[1])**2)**0.5
                # normalized_deviation = knee_ankle_x_diff / hip_ankle_dist if hip_ankle_dist > 0 else 0

                # Use the raw difference for now, thresholding will handle scale somewhat
                self.knee_alignment_buffer.append(knee_ankle_x_diff)

                if len(self.knee_alignment_buffer) > 0:
                    avg_knee_deviation = sum(self.knee_alignment_buffer) / len(self.knee_alignment_buffer)
                    angles['knee_deviation'] = avg_knee_deviation
                    # Positive value: Knee is to the right of the ankle
                    # Negative value: Knee is to the left of the ankle
                    # Interpretation depends on which leg is forward and camera view

        return angles

    def analyze_form(self, keypoints: Dict[str, List[float]]) -> List[str]:
        """
        Analyze lunge form based on detected keypoints. Called primarily at LUNGE_HOLD state.

        Args:
            keypoints: Dictionary of landmark keypoints

        Returns:
            List of feedback strings about the lunge form for the current frame/state.
        """
        feedback = []
        angles = self.calculate_exercise_angles(keypoints) # Recalculate for current frame if needed

        front_knee_angle = angles.get('front_knee_angle')
        back_knee_angle = angles.get('back_knee_angle')
        knee_deviation = angles.get('knee_deviation') # Average deviation from buffer
        front_hip_angle = angles.get('front_hip_angle') # Torso lean relative to front thigh

        # --- Basic Checks ---
        if front_knee_angle is None or back_knee_angle is None:
            return ["Ensure both legs are clearly visible."] # Early exit if angles missing

        # --- Depth Checks (at LUNGE_HOLD) ---
        # Front Knee Depth
        min_front_knee = self.thresholds.get('lunge_front_knee_angle_min', 80)
        max_front_knee = self.thresholds.get('lunge_front_knee_angle_max', 100) # Should be around 90 ideally
        if front_knee_angle < min_front_knee:
            feedback.append("Front knee bent too much (too deep)")
        elif front_knee_angle > max_front_knee:
            feedback.append("Bend front knee more (not deep enough)")

        # Back Knee Depth
        min_back_knee = self.thresholds.get('lunge_back_knee_angle_min', 80)
        max_back_knee = self.thresholds.get('lunge_back_knee_angle_max', 110) # Back knee can be > 90
        # Check if back knee is close to the ground (optional, needs Y coordinate analysis)
        # back_knee_y = keypoints.get(back_knee_kp_name, [0,0,0,0])[1]
        # back_ankle_y = keypoints.get(back_ankle_kp_name, [0,0,0,0])[1]
        # if back_knee_y > back_ankle_y - threshold: # Example check
        #      feedback.append("Lower back knee closer to the ground")
        if back_knee_angle < min_back_knee:
             feedback.append("Back knee bent too much") # Less common issue
        elif back_knee_angle > max_back_knee:
             feedback.append("Lower your back knee more")


        # --- Knee Alignment Check (Front Leg) ---
        if knee_deviation is not None:
            deviation_threshold = self.thresholds.get('lunge_knee_deviation_threshold', 20) # Pixels/normalized value
            if self.forward_leg == 'left':
                # Left leg forward: positive deviation = knee right of ankle (VARUS/outward)
                #                  negative deviation = knee left of ankle (VALGUS/inward)
                if knee_deviation < -deviation_threshold:
                    feedback.append("Keep front (left) knee aligned with foot (don't let it collapse inward)")
                elif knee_deviation > deviation_threshold:
                     feedback.append("Keep front (left) knee aligned with foot (don't let it push outward)")
            elif self.forward_leg == 'right':
                # Right leg forward: positive deviation = knee right of ankle (VALGUS/inward)
                #                   negative deviation = knee left of ankle (VARUS/outward)
                if knee_deviation > deviation_threshold:
                    feedback.append("Keep front (right) knee aligned with foot (don't let it collapse inward)")
                elif knee_deviation < -deviation_threshold:
                    feedback.append("Keep front (right) knee aligned with foot (don't let it push outward)")


        # --- Torso Lean Check ---
        if front_hip_angle is not None:
            min_torso_angle = self.thresholds.get('lunge_torso_angle_min', 160) # Angle between torso and front thigh
            if front_hip_angle < min_torso_angle:
                feedback.append("Keep your torso more upright")

        # --- Positive Feedback ---
        if not feedback:
            feedback.append("Good lunge form!")

        return feedback

    def update_state(self, keypoints: Dict[str, List[float]]) -> Tuple[LungeState, List[str]]:
        """
        Update the lunge state based on detected keypoints and provide feedback.

        Args:
            keypoints: Dictionary of landmark keypoints

        Returns:
            Tuple of (current state, persistent feedback list from manager)
        """
        angles = self.calculate_exercise_angles(keypoints)
        front_knee_angle = angles.get('front_knee_angle')
        back_knee_angle = angles.get('back_knee_angle')
        frame_feedback = [] # Specific feedback for this frame transition/analysis

        # Use the minimum angle of both knees as the primary driver for state transitions
        # Ensure angles are valid before taking min
        valid_angles = [a for a in [front_knee_angle, back_knee_angle] if a is not None]
        if not valid_angles:
             # If no valid angles, maintain state or reset to IDLE, provide feedback
             if self.state != LungeState.IDLE:
                 # Maybe add a timeout or counter before resetting?
                 pass # Maintain state for now
             return self.state, ["Ensure legs are visible to track lunge."]

        # Use the minimum valid angle found
        current_min_knee_angle = min(valid_angles)

        # --- State Machine Logic ---
        if self.state == LungeState.IDLE:
            # Detect start: legs relatively straight, then start bending
            if self.lunge_down_threshold < current_min_knee_angle < self.lunge_start_threshold:
                # Check if angle is decreasing
                if current_min_knee_angle < self.prev_knee_angle - 2: # Threshold for movement
                    self.state = LungeState.LUNGE_START
                    self.feedback_manager.clear_feedback() # Clear old feedback
                    self.reset() # Reset counters, angles, buffers for the new rep
                    # Re-detect forward leg at the start of the rep
                    self.forward_leg = self._detect_forward_leg(keypoints)
                    if not self.forward_leg:
                         frame_feedback.append("Could not determine forward leg.")
                         self.state = LungeState.IDLE # Go back to idle if detection fails
                    else:
                         frame_feedback.append(f"Starting Lunge ({self.forward_leg} leg forward)")


        elif self.state == LungeState.LUNGE_START:
            # Transition to DOWN once significant bending occurs
            if current_min_knee_angle < self.lunge_down_threshold:
                self.state = LungeState.LUNGE_DOWN
            # Abort if person goes back up immediately
            elif current_min_knee_angle > self.prev_knee_angle + 5:
                 self.state = LungeState.IDLE
                 self.feedback_manager.clear_feedback()
                 frame_feedback.append("Lunge aborted")

        elif self.state == LungeState.LUNGE_DOWN:
            # Detect bottom: angle stops decreasing or starts increasing
            if current_min_knee_angle >= self.prev_knee_angle - 1:
                self.state = LungeState.LUNGE_HOLD
                # --- Analyze form comprehensively at the bottom ---
                form_feedback = self.analyze_form(keypoints)
                frame_feedback.extend(form_feedback) # Add form feedback for this frame

                # Add feedback to manager and track errors
                self.rep_error = False # Assume no error for this rep initially
                for fb in form_feedback:
                    is_positive = "Good" in fb or "Correct" in fb # Simple check for positive feedback
                    priority = FeedbackPriority.LOW if is_positive else FeedbackPriority.HIGH
                    # Only add feedback if it's new or important
                    self.feedback_manager.add_feedback(fb, priority)
                    if priority == FeedbackPriority.HIGH:
                        self.rep_error = True # Mark rep as having an error

        elif self.state == LungeState.LUNGE_HOLD:
            # Detect upward movement
            if current_min_knee_angle > self.prev_knee_angle + 1:
                self.state = LungeState.LUNGE_UP

        elif self.state == LungeState.LUNGE_UP:
            # Detect completion (reaching near starting extension)
            if current_min_knee_angle >= self.lunge_up_threshold:
                self.state = LungeState.COMPLETED # Momentary state

                # --- Final actions for the completed rep ---
                if not self.rep_error:
                    self.rep_count += 1
                    completion_msg = f"Rep {self.rep_count} Complete!"
                    frame_feedback.append(completion_msg)
                    self.feedback_manager.add_feedback(completion_msg, FeedbackPriority.INFO)
                else:
                    error_msg = "Rep incomplete due to form error."
                    frame_feedback.append(error_msg)
                    # Ensure the specific errors are already in the manager from LUNGE_HOLD
                    self.feedback_manager.add_feedback(error_msg, FeedbackPriority.HIGH)

                # Transition back to IDLE for the next rep
                self.state = LungeState.IDLE
                # Do not reset here, reset happens at the start of the next rep (LUNGE_START)

        # elif self.state == LungeState.COMPLETED: # Handled in LUNGE_UP transition
        #     self.state = LungeState.IDLE


        # Update the primary tracking angle for the next frame's comparison
        self.prev_knee_angle = current_min_knee_angle

        # Add any frame-specific feedback to the manager if needed (optional)
        # for fb in frame_feedback:
        #     self.feedback_manager.add_feedback(fb, FeedbackPriority.DEBUG) # Example

        # Return the current state and the persistent feedback list from the manager
        return self.state, self.feedback_manager.get_feedback()

    def get_state_name(self) -> str:
        """Get the name of the current lunge state"""
        return self.state.name
