from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import cv2
import numpy as np
import json
import base64
from typing import Dict, List, Optional
import logging
import google.generativeai as genai

from api.routes import router as api_router
from api.websocket import WebSocketManager
from utils.workout_extractor import WorkoutExtractor
from utils.video_processor import VideoProcessor
from config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title=settings.APP_NAME)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
try:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.MODEL_NAME)
    logger.info("Gemini AI initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}")
    model = None

# Initialize workout extractor
workout_extractor = WorkoutExtractor(settings.GEMINI_API_KEY)

# Initialize WebSocket manager
websocket_manager = WebSocketManager()

# Initialize video processor
video_processor = VideoProcessor(settings.THRESHOLDS, settings.POSE_DETECTION_CONFIDENCE)

# Include API routes
app.include_router(api_router, prefix="/api")

# WebSocket endpoint for video streaming
@app.websocket("/ws/video")
async def video_websocket(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Process received frame data
            try:
                frame_data = json.loads(data)
                if "image" in frame_data:
                    # Decode base64 image
                    img_data = base64.b64decode(frame_data["image"].split(',')[1])
                    nparr = np.frombuffer(img_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    # Set current exercise if provided
                    if "exercise" in frame_data:
                        video_processor.set_current_exercise(frame_data["exercise"])
                    
                    # Process the frame
                    processed_frame, exercise_data = video_processor.process_frame(frame)
                    
                    # Encode the processed frame
                    _, buffer = cv2.imencode('.jpg', processed_frame)
                    encoded_frame = base64.b64encode(buffer).decode('utf-8')
                    
                    # Send back the processed frame and exercise data
                    await websocket.send_json({
                        "image": f"data:image/jpeg;base64,{encoded_frame}",
                        "exerciseData": exercise_data
                    })
            except Exception as e:
                logger.error(f"Error processing video frame: {e}")
                await websocket.send_json({"error": str(e)})
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

# Serve static files for React frontend
app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)