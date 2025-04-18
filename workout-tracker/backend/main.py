# --- (Keep previous imports and logging setup) ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response # Added Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import uvicorn
import cv2
import numpy as np
import json
import base64
from typing import Dict, List, Optional
import logging
import google.generativeai as genai

# Assuming these imports are correct relative to main.py
from api.routes import router as api_router
from api.websocket import WebSocketManager
from utils.workout_extractor import WorkoutExtractor
from utils.video_processor import VideoProcessor
from config import settings

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialize Services (Centralized) ---
gemini_model = None
video_processor_instance = None
workout_extractor_instance = None

try:
    # Initialize Gemini
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(settings.MODEL_NAME)
    logger.info(f"Gemini AI initialized successfully with model: {settings.MODEL_NAME}")

    # Initialize Workout Extractor
    # --- FIX: Reverted this line ---
    # Remove the 'model_name' argument as WorkoutExtractor.__init__ doesn't accept it.
    # Assuming it expects only the API key, or uses the globally configured model.
    workout_extractor_instance = WorkoutExtractor(settings.GEMINI_API_KEY)
    # --- End Fix ---
    logger.info("WorkoutExtractor initialized successfully")


    # Initialize Video Processor
    video_processor_instance = VideoProcessor(settings.THRESHOLDS, settings.POSE_DETECTION_CONFIDENCE)
    logger.info("VideoProcessor initialized successfully")

except TypeError as e:
     # Catching TypeError specifically for the init issue
     logger.exception(f"TypeError during service initialization (check constructor arguments): {e}")
     # Handle specific error, maybe exit or set instances to None
     workout_extractor_instance = None # Ensure it's None if init fails
     # Potentially stop the app if a critical service fails:
     # raise SystemExit("Failed to initialize critical services.") from e
except Exception as e:
    logger.exception(f"Fatal error during service initialization: {e}")
    # Decide if the app should exit or run with limited functionality
    # For now, we log the error, instances might remain None

# --- (Keep Dependency Provider Functions: get_gemini_model, get_video_processor, get_workout_extractor) ---
def get_gemini_model() -> Optional[genai.GenerativeModel]:
    if gemini_model is None:
         logger.error("Gemini model dependency requested but not initialized.")
    return gemini_model

def get_video_processor() -> Optional[VideoProcessor]:
    if video_processor_instance is None:
        logger.error("VideoProcessor dependency requested but not initialized.")
    return video_processor_instance

def get_workout_extractor() -> Optional[WorkoutExtractor]:
    if workout_extractor_instance is None:
        logger.error("WorkoutExtractor dependency requested but not initialized.")
    return workout_extractor_instance

# --- (Keep FastAPI app initialization, CORS, WebSocket Manager, Router Inclusion) ---
app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Adjust if your frontend runs elsewhere
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

websocket_manager = WebSocketManager()
app.include_router(api_router, prefix="/api")


# --- (Keep WebSocket endpoint /ws/video) ---
@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    if video_processor_instance is None:
        logger.error("WebSocket connection attempt failed: VideoProcessor not initialized.")
        await websocket.close(code=1011, reason="Server configuration error")
        return

    logger.info("New WebSocket connection attempt")
    try:
        await websocket_manager.connect(websocket)
        logger.info("WebSocket connected successfully")
        
        # Send initial connection success message
        await websocket.send_json({
            "status": "connected",
            "message": "WebSocket connected successfully"
        })
        
        while True:
            data = await websocket.receive_text()
            try:
                frame_data = json.loads(data)
                
                # Check if image data exists and is valid
                if "image" not in frame_data or not frame_data["image"]:
                    logger.warning("Missing image data in WebSocket message")
                    await websocket.send_json({"error": "Missing image data", "status": "error"})
                    continue
                
                # Extract image data
                try:
                    img_parts = frame_data["image"].split(',')
                    if len(img_parts) != 2:
                        raise ValueError("Invalid image format")
                    
                    img_data = base64.b64decode(img_parts[1])
                    nparr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except Exception as e:
                    logger.error(f"Failed to decode image: {e}")
                    await websocket.send_json({"error": "Failed to decode image data", "status": "error"})
                    continue

                if frame is None:
                    logger.warning("Failed to decode image received via WebSocket.")
                    await websocket.send_json({"error": "Failed to decode image.", "status": "error"})
                    continue

                if "exercise" in frame_data:
                    video_processor_instance.set_current_exercise(frame_data["exercise"])

                processed_frame, exercise_data = video_processor_instance.process_frame(frame)

                is_success, buffer = cv2.imencode('.jpg', processed_frame)
                if not is_success:
                    logger.warning("Failed to encode processed frame to JPG.")
                    await websocket.send_json({"error": "Failed to encode processed frame.", "status": "error"})
                    continue

                encoded_frame = base64.b64encode(buffer).decode('utf-8')

                await websocket.send_json({
                    "image": f"data:image/jpeg;base64,{encoded_frame}",
                    "exerciseData": exercise_data,
                    "status": "success"
                })
            except json.JSONDecodeError as e:
                logger.error(f"WebSocket JSON decode error: {str(e)}")
                await websocket.send_json({"error": f"Invalid JSON received: {str(e)}", "status": "error"})
            except cv2.error as e:
                logger.error(f"OpenCV error processing frame: {e}")
                await websocket.send_json({"error": "Server error processing video frame.", "status": "error"})
            except Exception as e:
                logger.exception(f"Error processing video frame or sending WebSocket message: {e}")
                try:
                    await websocket.send_json({"error": f"An unexpected server error occurred: {str(e)}", "status": "error"})
                except Exception:
                    pass
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.exception(f"Unexpected WebSocket error: {str(e)}")
        websocket_manager.disconnect(websocket)


# --- (Keep Static Files and SPA Fallback) ---
app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")

@app.get("/{full_path:path}")
async def serve_react_app(request: Request, full_path: str):
    build_dir = os.path.abspath("../frontend/build")
    index_path = os.path.join(build_dir, 'index.html')
    requested_path = os.path.abspath(os.path.join(build_dir, full_path))

    if not requested_path.startswith(build_dir):
        logger.warning(f"Attempted directory traversal: {full_path}")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        else:
             return Response(content="Not Found", status_code=404)

    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        logger.error(f"index.html not found at {index_path}")
        return Response(content="Frontend build not found.", status_code=404)

# --- (Keep Main Execution block) ---
if __name__ == "__main__":
    logger.info("Starting Uvicorn server...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)