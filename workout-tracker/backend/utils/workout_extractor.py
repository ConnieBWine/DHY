import google.generativeai as genai
from typing import List, Dict, Any, Union, Optional
import re
import logging
import json

logger = logging.getLogger(__name__)

class WorkoutExtractor:
    """
    Extracts structured workout plans from AI-generated text responses
    
    Uses Gemini API to process raw text into a structured format for the app
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the workout extractor
        
        Args:
            api_key: Google Gemini API key
        """
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API initialized for workout extraction")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {str(e)}")
            self.model = None

    def extract_workout_plan(self, ai_response: str) -> List[Dict[str, Any]]:
        """
        Extract a structured workout plan from AI response text
        
        Args:
            ai_response: Raw text from the AI containing workout plan
            
        Returns:
            List of day plan dictionaries with exercises
        """
        prompt = f"""
        You are a precise workout plan formatter. Your task is to take the following 7-day workout plan and reformat it into a strictly structured JSON format. Follow these rules exactly:

        1. The output must be a valid JSON array containing exactly 7 objects, one for each day.
        2. Each day object must have a "day" key (e.g., "Day 1") and an "exercises" array.
        3. Each exercise in the "exercises" array must have these exact keys: "name", "sets", "reps", and "is_timed".
        4. For timed exercises, "reps" represents duration in seconds, and "is_timed" must be true.
        5. For non-timed exercises, "is_timed" must be false.
        6. All numerical values (sets, reps) must be integers, not strings.
        7. Do not include any explanations or additional text outside the JSON structure.

        Here's the workout plan to format:

        {ai_response}

        Expected output format:
        [
            {{
                "day": "Day 1",
                "exercises": [
                    {{"name": "Pushup", "sets": 3, "reps": 10, "is_timed": false}},
                    {{"name": "Plank", "sets": 1, "reps": 60, "is_timed": true}},
                    {{"name": "Squat", "sets": 3, "reps": 15, "is_timed": false}}
                ]
            }},
            {{
                "day": "Day 2",
                "exercises": [
                    {{"name": "Jumping Jack", "sets": 1, "reps": 30, "is_timed": true}},
                    {{"name": "Lunge", "sets": 3, "reps": 12, "is_timed": false}},
                    {{"name": "Mountain Climber", "sets": 1, "reps": 45, "is_timed": true}}
                ]
            }},
            // ... (Days 3-6 would be listed here in the same format)
            {{
                "day": "Day 7",
                "exercises": [
                    {{"name": "Rest Day", "sets": 1, "reps": 1, "is_timed": false}}
                ]
            }}
        ]

        Format the provided workout plan strictly according to these instructions and example.
        """

        try:
            if self.model:
                response = self.model.generate_content(prompt)
                response_text = response.text
                
                # Remove code block markers if present
                response_text = response_text.replace('```json', '').replace('```', '').strip()
                
                logger.debug(f"Raw AI extraction response:\n{response_text}")

                try:
                    workout_plan = json.loads(response_text)
                    if isinstance(workout_plan, list):
                        # Validate the workout plan structure
                        if self._validate_workout_plan(workout_plan):
                            return workout_plan
                        else:
                            logger.warning("AI returned invalid workout plan structure")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON: {str(e)}")
            
            # If we reached here, either model is None or parsing failed
            return self._manual_extraction(ai_response)
                
        except Exception as e:
            logger.error(f"Error in extract_workout_plan: {str(e)}")
            return self._manual_extraction(ai_response)

    def _validate_workout_plan(self, workout_plan: List[Dict[str, Any]]) -> bool:
        """
        Validate the structure of the extracted workout plan
        
        Args:
            workout_plan: List of day plan dictionaries
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(workout_plan, list):
            return False
            
        for day_plan in workout_plan:
            if not isinstance(day_plan, dict) or 'day' not in day_plan or 'exercises' not in day_plan:
                return False
                
            if not isinstance(day_plan['exercises'], list):
                return False
                
            for exercise in day_plan['exercises']:
                required_keys = ['name', 'sets', 'reps', 'is_timed']
                if not all(key in exercise for key in required_keys):
                    return False
                    
                if not isinstance(exercise['name'], str):
                    return False
                    
                if not isinstance(exercise['sets'], int) or not isinstance(exercise['reps'], int):
                    return False
                    
                if not isinstance(exercise['is_timed'], bool):
                    return False
                    
        return True

    def _manual_extraction(self, text: str) -> List[Dict[str, Any]]:
        """
        Manually extract workout plan when AI parsing fails
        
        Args:
            text: Raw workout plan text
            
        Returns:
            List of day plan dictionaries with exercises
        """
        logger.info("Falling back to manual workout plan extraction")
        workout_plan = []
        
        # Extract day blocks
        day_matches = re.findall(r'Day\s+(\d+)[:\s]+(.*?)(?=Day\s+\d+[:\s]+|$)', text, re.DOTALL)
        
        # If no day matches found, try another pattern
        if not day_matches:
            day_matches = re.findall(r'(?:^|\n)(?:Day|DAY)\s*(\d+)\s*:?\s*(.*?)(?=(?:^|\n)(?:Day|DAY)\s*\d+|$)', text, re.DOTALL)
        
        # If still no matches, create default plan
        if not day_matches:
            logger.warning("No day patterns found in response, creating default plan")
            return self._generate_default_plan()

        for day_num, day_content in day_matches:
            exercises = []
            
            # Extract exercises
            exercise_matches = re.findall(r'([\w\s-]+):\s*(?:(\d+)\s*x\s*(\d+)|(\d+)\s*(?:seconds|sec|s))', day_content, re.IGNORECASE)
            
            for match in exercise_matches:
                exercise_name = match[0].strip()
                
                # Check if it's a timed exercise or reps-based
                if match[3]:  # Duration in seconds
                    sets = 1
                    reps = int(match[3])
                    is_timed = True
                else:  # Sets x Reps
                    sets = int(match[1]) if match[1] else 1
                    reps = int(match[2]) if match[2] else 10
                    is_timed = False
                
                exercises.append({
                    "name": exercise_name,
                    "sets": sets,
                    "reps": reps,
                    "is_timed": is_timed
                })
            
            # If no exercises found, try another pattern
            if not exercises:
                # Try alternative format: Exercise name followed by reps or time
                alt_matches = re.findall(r'([\w\s-]+)[\s-]+(?:(\d+)\s*x\s*(\d+)|(\d+)\s*(?:seconds|sec|s))', day_content, re.IGNORECASE)
                
                for match in alt_matches:
                    exercise_name = match[0].strip()
                    
                    if match[3]:  # Duration in seconds
                        sets = 1
                        reps = int(match[3])
                        is_timed = True
                    else:  # Sets x Reps
                        sets = int(match[1]) if match[1] else 1
                        reps = int(match[2]) if match[2] else 10
                        is_timed = False
                    
                    exercises.append({
                        "name": exercise_name,
                        "sets": sets,
                        "reps": reps,
                        "is_timed": is_timed
                    })
            
            # Add the day to the workout plan
            if exercises:
                workout_plan.append({
                    "day": f"Day {day_num.strip()}",
                    "exercises": exercises
                })
        
        # If we couldn't extract any days with exercises, return default plan
        if not workout_plan or any(len(day['exercises']) == 0 for day in workout_plan):
            logger.warning("Failed to extract exercises, using default plan")
            return self._generate_default_plan()
        
        return workout_plan

    def _generate_default_plan(self) -> List[Dict[str, Any]]:
        """
        Generate a default workout plan as fallback
        
        Returns:
            List with 7 days of default exercises
        """
        logger.info("Generating default workout plan")
        default_plan = []
        
        # Day 1: Full body basics
        default_plan.append({
            "day": "Day 1",
            "exercises": [
                {"name": "Jumping Jack", "sets": 1, "reps": 60, "is_timed": True},
                {"name": "Pushup", "sets": 3, "reps": 10, "is_timed": False},
                {"name": "Squat", "sets": 3, "reps": 15, "is_timed": False},
                {"name": "Plank", "sets": 1, "reps": 30, "is_timed": True}
            ]
        })
        
        # Day 2: Lower body focus
        default_plan.append({
            "day": "Day 2",
            "exercises": [
                {"name": "Jumping Jack", "sets": 1, "reps": 45, "is_timed": True},
                {"name": "Squat", "sets": 3, "reps": 20, "is_timed": False},
                {"name": "Lunge", "sets": 3, "reps": 12, "is_timed": False},
                {"name": "Plank", "sets": 1, "reps": 45, "is_timed": True}
            ]
        })
        
        # Day 3: Upper body focus
        default_plan.append({
            "day": "Day 3",
            "exercises": [
                {"name": "Jumping Jack", "sets": 1, "reps": 60, "is_timed": True},
                {"name": "Pushup", "sets": 3, "reps": 12, "is_timed": False},
                {"name": "Bicep Curl", "sets": 3, "reps": 15, "is_timed": False},
                {"name": "Shoulder Press", "sets": 3, "reps": 10, "is_timed": False}
            ]
        })
        
        # Day 4: Core focus
        default_plan.append({
            "day": "Day 4",
            "exercises": [
                {"name": "Jumping Jack", "sets": 1, "reps": 30, "is_timed": True},
                {"name": "Plank", "sets": 3, "reps": 30, "is_timed": True},
                {"name": "Mountain Climber", "sets": 1, "reps": 60, "is_timed": True},
                {"name": "Knee Tap", "sets": 1, "reps": 45, "is_timed": True}
            ]
        })
        
        # Day 5: Full body challenge
        default_plan.append({
            "day": "Day 5",
            "exercises": [
                {"name": "Jumping Jack", "sets": 1, "reps": 60, "is_timed": True},
                {"name": "Pushup", "sets": 3, "reps": 15, "is_timed": False},
                {"name": "Squat", "sets": 3, "reps": 20, "is_timed": False},
                {"name": "Lunge", "sets": 3, "reps": 15, "is_timed": False},
                {"name": "Plank", "sets": 1, "reps": 60, "is_timed": True}
            ]
        })
        
        # Day 6: Upper body strength
        default_plan.append({
            "day": "Day 6",
            "exercises": [
                {"name": "Pushup", "sets": 4, "reps": 10, "is_timed": False},
                {"name": "Bicep Curl", "sets": 3, "reps": 12, "is_timed": False},
                {"name": "Shoulder Press", "sets": 3, "reps": 10, "is_timed": False},
                {"name": "Plank", "sets": 1, "reps": 45, "is_timed": True}
            ]
        })
        
        # Day 7: Active recovery
        default_plan.append({
            "day": "Day 7",
            "exercises": [
                {"name": "Jumping Jack", "sets": 1, "reps": 30, "is_timed": True},
                {"name": "Squat", "sets": 2, "reps": 10, "is_timed": False},
                {"name": "Plank", "sets": 1, "reps": 30, "is_timed": True}
            ]
        })
        
        return default_plan