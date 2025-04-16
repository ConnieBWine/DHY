import mediapipe as mp
import cv2
import numpy as np
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class PoseDetector:
    """MediaPipe pose detection wrapper"""
    
    def __init__(self, 
                 static_image_mode=False, 
                 model_complexity=1, 
                 smooth_landmarks=True, 
                 min_detection_confidence=0.6, 
                 min_tracking_confidence=0.6):
        """Initialize pose detector with MediaPipe"""
        
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
    def find_pose(self, image):
        """Process an image and detect pose landmarks"""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.pose.process(image_rgb)
        return results
    
    def draw_landmarks(self, image, results, draw_connections=True):
        """Draw pose landmarks on an image"""
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(
                image, 
                results.pose_landmarks, 
                self.mp_pose.POSE_CONNECTIONS if draw_connections else None,
                self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)
            )
        return image
    
    def extract_landmarks(self, results, img_shape) -> Dict[str, List[float]]:
        """Extract normalized landmarks to dictionary with pixel coordinates"""
        landmarks = {}
        if not results.pose_landmarks:
            return landmarks
            
        h, w, _ = img_shape
        for idx, landmark in enumerate(results.pose_landmarks.landmark):
            # Get pose part name
            landmark_name = self.mp_pose.PoseLandmark(idx).name.lower()
            
            # Store landmarks with visibility
            landmarks[landmark_name] = [
                landmark.x * w,  # convert to pixel X
                landmark.y * h,  # convert to pixel Y
                landmark.z,      # depth
                landmark.visibility  # visibility
            ]
            
        return landmarks
    
    def get_pose_landmarks(self, results):
        """Get raw pose landmarks from results"""
        if not results.pose_landmarks:
            return None
        return results.pose_landmarks.landmark
    
    def get_keypoints_dict(self, landmarks, visibility_threshold=0.5):
        """Convert landmarks to dictionary with normalized coordinates"""
        keypoints = {}
        
        if landmarks:
            for idx, landmark in enumerate(landmarks):
                landmark_name = self.mp_pose.PoseLandmark(idx).name.lower()
                if landmark.visibility > visibility_threshold:
                    keypoints[landmark_name] = [landmark.x, landmark.y, landmark.z, landmark.visibility]
                    
        return keypoints