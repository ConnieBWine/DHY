from fastapi import WebSocket
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Connect a WebSocket client"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            "current_exercise": None,
            "target_reps": 0,
            "target_sets": 0,
            "is_timed": False,
            "target_duration": 0
        }
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_data:
            del self.connection_data[websocket]
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                await self.disconnect(connection)
    
    def set_exercise_data(self, websocket: WebSocket, exercise_data: dict):
        """Set exercise data for a specific connection"""
        if websocket in self.connection_data:
            self.connection_data[websocket].update(exercise_data)
    
    def get_exercise_data(self, websocket: WebSocket) -> Dict[str, Any]:
        """Get exercise data for a specific connection"""
        return self.connection_data.get(websocket, {})