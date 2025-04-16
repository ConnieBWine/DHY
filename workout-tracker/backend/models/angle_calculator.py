import numpy as np
import math
from typing import List, Tuple, Optional, Union

class AngleCalculator:
    """Utility class for calculating angles between body parts"""
    
    @staticmethod
    def calculate_angle(a: List[float], b: List[float], c: List[float]) -> float:
        """
        Calculate the angle between three points (in degrees)
        
        Args:
            a: First point [x, y]
            b: Middle point (vertex) [x, y]
            c: Third point [x, y]
            
        Returns:
            Angle in degrees between the three points
        """
        a = np.array(a[:2])  # Only use x,y coordinates
        b = np.array(b[:2])
        c = np.array(c[:2])
      
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
      
        return angle if angle <= 180.0 else 360 - angle

    @staticmethod
    def calculate_vertical_angle(point1: List[float], point2: List[float]) -> float:
        """
        Calculate the angle between a line and the vertical axis
        
        Args:
            point1: First point [x, y]
            point2: Second point [x, y]
            
        Returns:
            Angle in degrees from the vertical
        """
        x1, y1 = point1[:2]
        x2, y2 = point2[:2]
        dx = x2 - x1
        dy = y2 - y1
        angle = np.abs(np.arctan2(dx, -dy) * 180.0 / np.pi)
        return angle       
   
    @staticmethod
    def find_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calculate the Euclidean distance between two points
        
        Args:
            x1, y1: Coordinates of the first point
            x2, y2: Coordinates of the second point
            
        Returns:
            Euclidean distance
        """
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return dist

    @staticmethod
    def find_angle(x1: float, y1: float, x2: float, y2: float) -> float:
        """
        Calculate angle between a line and the vertical axis
        
        Args:
            x1, y1: Coordinates of the first point
            x2, y2: Coordinates of the second point
            
        Returns:
            Angle in degrees
        """
        if y1 == 0:  # Avoid division by zero
            return 0
            
        theta = math.acos((y2 - y1) * (-y1) / (math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) * y1))
        degree = int(180 / math.pi) * theta
        return degree
  
    @staticmethod
    def angle_deg(p1: List[float], pref: List[float], p2: List[float]) -> float:
        """
        Calculate the angle between three points in degrees
        
        Args:
            p1: First point [x, y, z, visibility]
            pref: Reference point (vertex) [x, y, z, visibility]
            p2: Third point [x, y, z, visibility]
            
        Returns:
            Angle in degrees
        """
        p1 = np.array(p1[:2])
        pref = np.array(pref[:2])
        p2 = np.array(p2[:2])
      
        p1ref = p1 - pref
        p2ref = p2 - pref
      
        dot_product = np.dot(p1ref, p2ref)
        magnitude_p1ref = np.linalg.norm(p1ref)
        magnitude_p2ref = np.linalg.norm(p2ref)
        
        # Avoid division by zero
        if magnitude_p1ref == 0 or magnitude_p2ref == 0:
            return 0
      
        cos_theta = dot_product / (magnitude_p1ref * magnitude_p2ref)
        angle_rad = np.arccos(np.clip(cos_theta, -1.0, 1.0))
        angle_deg = np.degrees(angle_rad)
      
        return angle_deg
  
    @staticmethod
    def calculate_elbow_torso_angle(
        left_hip: List[float], 
        left_shoulder: List[float], 
        left_elbow: List[float], 
        right_hip: List[float], 
        right_shoulder: List[float], 
        right_elbow: List[float], 
        visibility_threshold: float = 0.6
    ) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
        """
        Calculate angle between elbow and torso for both left and right sides
        
        Args:
            left_hip, left_shoulder, left_elbow: Left side landmarks [x, y, z, visibility]
            right_hip, right_shoulder, right_elbow: Right side landmarks [x, y, z, visibility]
            visibility_threshold: Minimum visibility score to consider a landmark
            
        Returns:
            Tuple containing:
            - Left elbow-torso angle (or None if not visible)
            - Right elbow-torso angle (or None if not visible)
            - Average angle (or single side if only one side is visible)
            - View type (front, left_side, right_side, or unclear)
        """
        def is_visible(points):
            return all(point[3] > visibility_threshold for point in points)

        left_visible = is_visible([left_hip, left_shoulder, left_elbow])
        right_visible = is_visible([right_hip, right_shoulder, right_elbow])

        if left_visible and right_visible:
            left_angle = AngleCalculator.angle_deg(left_hip, left_shoulder, left_elbow)
            right_angle = AngleCalculator.angle_deg(right_hip, right_shoulder, right_elbow)
            return left_angle, right_angle, (left_angle + right_angle) / 2, "front"
        elif left_visible:
            left_angle = AngleCalculator.angle_deg(left_hip, left_shoulder, left_elbow)
            return left_angle, None, left_angle, "left_side"
        elif right_visible:
            right_angle = AngleCalculator.angle_deg(right_hip, right_shoulder, right_elbow)
            return None, right_angle, right_angle, "right_side"
        else:
            return None, None, None, "unclear"
    
    @staticmethod
    def calculate_hip_shoulder_angle(
        hip: List[float], 
        shoulder: List[float], 
        visibility_threshold: float = 0.6
    ) -> Optional[float]:
        """
        Calculate angle between hip and shoulder relative to vertical
        
        Args:
            hip: Hip landmark [x, y, z, visibility]
            shoulder: Shoulder landmark [x, y, z, visibility]
            visibility_threshold: Minimum visibility score
            
        Returns:
            Angle in degrees or None if landmarks not visible
        """
        if hip[3] > visibility_threshold and shoulder[3] > visibility_threshold:
            return AngleCalculator.find_angle(hip[0], hip[1], shoulder[0], shoulder[1])
        else:
            return None