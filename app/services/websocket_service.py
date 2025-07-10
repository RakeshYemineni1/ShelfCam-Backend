# app/services/websocket_service.py
from typing import Dict, List, Optional
from fastapi import WebSocket
from app.models.alert import Alert
import json
import logging

logger = logging.getLogger(__name__)

class WebSocketService:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Connect user to WebSocket"""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected to WebSocket")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Disconnect user from WebSocket"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_alert_to_user(self, user_id: int, alert: Alert):
        """Send alert to specific user"""
        if user_id in self.active_connections:
            message = {
                "type": "new_alert",
                "data": {
                    "id": alert.id,
                    "alert_type": alert.alert_type.value,
                    "priority": alert.priority.value,
                    "title": alert.title,
                    "message": alert.message,
                    "shelf_name": alert.shelf_name,
                    "rack_name": alert.rack_name,
                    "product_name": alert.product_name,
                    "created_at": alert.created_at.isoformat()
                }
            }
            
            for websocket in self.active_connections[user_id][:]:  # Copy list to avoid modification during iteration
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending alert to user {user_id}: {e}")
                    self.active_connections[user_id].remove(websocket)
    
    async def send_alert_update(self, alert: Alert):
        """Send alert update to all connected users"""
        message = {
            "type": "alert_update",
            "data": {
                "id": alert.id,
                "status": alert.status.value,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None
            }
        }
        
        for user_id, websockets in self.active_connections.items():
            for websocket in websockets[:]:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending alert update to user {user_id}: {e}")
                    websockets.remove(websocket)
    
    async def broadcast_system_message(self, message: str):
        """Broadcast system message to all connected users"""
        broadcast_message = {
            "type": "system_message",
            "data": {
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        for user_id, websockets in self.active_connections.items():
            for websocket in websockets[:]:
                try:
                    await websocket.send_text(json.dumps(broadcast_message))
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    websockets.remove(websocket)