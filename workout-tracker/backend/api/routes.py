from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List, Optional
import google.generativeai as genai
import logging
from pydantic import BaseModel

from utils.workout_extractor import WorkoutExtractor
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.MODEL_NAME)
    logger.info("Gemini AI initialized successfully in routes")
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI in routes: {e}")
    model = None

# Initialize workout extractor
workout_extractor = WorkoutExtractor(settings.GEMINI_API_KEY)

# Create API router
router = APIRouter()

# Define models
class SurveyData(BaseModel):
    weight: Optional[str] = "Not provided"
    height: Optional[str] = "Not provided"
    gender: Optional[str] = "Not provided"
    activity: Optional[str] = "Not provided"
    goal: Optional[str] = "Not provided"
    intensity: Optional[str] = "Not provided"

class WorkoutPrompt(BaseModel):
    prompt: str

class Exercise(BaseModel):
    name: str
    sets: int
    reps: int
    is_timed: bool

class DayPlan(BaseModel):
    day: str
    exercises: List[Exercise]

class WorkoutPlan(BaseModel):
    days: List[DayPlan]

class ExerciseData(BaseModel):
    exercise: str
    target_reps: Optional[int] = None
    target_sets: Optional[int] = None
    target_duration: Optional[int] = None  # In seconds for timed exercises

# Routes
@router.post("/workout-plan", response_model=WorkoutPlan)
async def generate_workout_plan(survey_data: SurveyData):
    """Generate a workout plan based on user survey data"""
    try:
        # Create the prompt for the AI model
        prompt = create_workout_prompt(survey_data)
        
        # Generate workout plan using AI
        if model:
            response = model.generate_content(prompt)
            workout_plan_text = response.text
            
            # Extract structured workout plan
            workout_plan = workout_extractor.extract_workout_plan(workout_plan_text)
            
            # Format response
            days = []
            for day_plan in workout_plan:
                exercises = []
                for exercise in day_plan["exercises"]:
                    exercises.append(Exercise(
                        name=exercise["name"],
                        sets=exercise["sets"],
                        reps=exercise["reps"],
                        is_timed=exercise["is_timed"]
                    ))
                days.append(DayPlan(
                    day=day_plan["day"],
                    exercises=exercises
                ))
            
            return WorkoutPlan(days=days)
        else:
            raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.error(f"Error generating workout plan: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate workout plan: {str(e)}")

@router.post("/workout-prompt", response_model=Dict)
async def custom_workout_prompt(data: WorkoutPrompt):
    """Generate a workout plan based on a custom prompt"""
    try:
        if model:
            response = model.generate_content(data.prompt)
            workout_plan_text = response.text
            
            # Extract structured workout plan
            workout_plan = workout_extractor.extract_workout_plan(workout_plan_text)
            
            return {"workout_plan": workout_plan, "raw_response": workout_plan_text}
        else:
            raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.error(f"Error with custom workout prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process workout prompt: {str(e)}")

@router.post("/start-exercise")
async def start_exercise(data: ExerciseData):
    """Start tracking a specific exercise"""
    try:
        return {"status": "success", "message": f"Started tracking {data.exercise}"}
    except Exception as e:
        logger.error(f"Error starting exercise: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start exercise: {str(e)}")

@router.post("/chat")
async def chat(message: dict = Body(...)):
    """Process a chat message"""
    try:
        if model:
            response = model.generate_content(message.get("message", ""))
            return {"message": response.text, "success": True}
        else:
            raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")

@router.get("/exercises")
async def get_available_exercises():
    """Get a list of all available exercises"""
    exercises = [
        {"name": "Squat", "type": "reps"},
        {"name": "Bicep Curl", "type": "reps"},
        {"name": "Pushup", "type": "reps"},
        {"name": "Lunge", "type": "reps"},
        {"name": "Shoulder Press", "type": "reps"},
        {"name": "Plank", "type": "timed"},
        {"name": "Jumping Jack", "type": "timed"}
    ]
    return {"exercises": exercises}

# this is for debug in the backend
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "api": "running"}
    
# Helper functions
def create_workout_prompt(survey_data: SurveyData) -> str:
    """Create AI prompt from survey data"""
    return f"""
    You are a specialized workout plan generator. Create a strict 7-day workout plan based on the following information:
    - Weight: {survey_data.weight}
    - Height: {survey_data.height}
    - Gender: {survey_data.gender}
    - Current activity level: {survey_data.activity}
    - Fitness goal: {survey_data.goal}
    - Desired Workout Intensity: {survey_data.intensity} (amount of time can spend per week to workout)

    Adhere to these rules strictly:
    1. Provide exactly 7 days of workouts, labeled Day 1 through Day 7.
    2. Each day must have 3-5 exercises.
    3. Use only the following exercises:
    Reps-based: curl, squat, lunge, pushup, shoulder press
    Duration-based: plank, jumping jack, jump rope, knee tap, mountain climber
    4. Format each exercise as follows:
    Reps-based: [Exercise Name]: [Sets] x [Reps]
    Duration-based: [Exercise Name]: [Duration] seconds
    5. Do not include any introductions, explanations, or dietary advice.
    6. Use the exact exercise names provided, with correct spelling.

    Example of correct formatting:
    Day 1:
    Jumping Jack: 30 seconds
    Pushup: 3 x 10
    Plank: 60 seconds
    Squat: 3 x 15
    Mountain Climber: 45 seconds

    Your response must follow this exact structure for all 7 days. DO NOT deviate from this format or include any additional information.

    Begin the 7-day workout plan NOW:
    """