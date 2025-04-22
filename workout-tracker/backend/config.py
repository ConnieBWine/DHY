import os
from typing import Optional, Dict, ClassVar
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    APP_NAME: str = "WorkoutTracker"
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    MODEL_NAME: str = "gemini-2.0-flash"
    POSE_DETECTION_CONFIDENCE: float = 0.6
    POSE_TRACKING_CONFIDENCE: float = 0.6
    VIDEO_WIDTH: int = 640
    VIDEO_HEIGHT: int = 480
    FPS: int = 30
    
    # Exercise thresholds - using ClassVar to indicate it's not a model field
    THRESHOLDS: ClassVar[Dict[str, float]] = {
        # Squat thresholds
        'squat_too_deep': 68,
        'squat_not_deep_enough': 91,
        'squat_forward_bend_too_little': 19,
        'squat_forward_bend_too_much': 50,
        
        # Bicep curl thresholds
        'bicep_curl_not_low_enough': 160,
        'bicep_curl_not_high_enough': 90,
        'bicep_curl_elbow_movement': 5,
        'bicep_curl_body_swing': 10,
        
        # Pushup thresholds
        'pushup_not_low_enough': 120,
        'pushup_too_low': 70,
        'pushup_hip_sag': 15,
        'pushup_hip_pike': 25,
        
        # Lunge thresholds
        'lunge_front_knee_angle_min': 80,
        'lunge_front_knee_angle_max': 100,
        'lunge_back_knee_angle_min': 80,
        'lunge_back_knee_angle_max': 100,
        
        # Plank thresholds
        'plank_hip_sag': 15,
        'plank_hip_pike': 25,
        
        # Jumping jack thresholds
        'jumping_jack_arm_extension': 140,
        'jumping_jack_leg_spread': 35
    }

settings = Settings()
