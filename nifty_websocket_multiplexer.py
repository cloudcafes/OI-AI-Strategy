# nifty_websocket_multiplexer.py
import json
import time
from typing import List, Dict, Any, Optional
from fastapi import WebSocket

class WebSocketMultiplexer:
    """
    Handles multiplexing WebSocket messages to multiple clients
    with support for 4 parallel model output streams
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.model_channels = {
            "deepseek_r1": "model1",
            "cloud_deepseek": "model2", 
            "llama3": "model3",
            "mistral": "model4"
        }
        
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ New WebSocket connection. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 WebSocket disconnected. Total: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket client"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"❌ Error sending personal message: {e}")
            self.disconnect(websocket)
            
    async def broadcast_message(self, message_type: str, message: str):
        """Broadcast general message to all connected clients"""
        payload = {
            "type": "broadcast",
            "message_type": message_type,
            "message": message,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_model_status(self, model_name: str, status: str):
        """Broadcast model-specific status update"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "model_status",
            "channel": channel,
            "model_name": model_name,
            "status": status,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_model_output(self, model_name: str, output: str, output_type: str = "info"):
        """Broadcast model output to specific channel"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "model_output",
            "channel": channel,
            "model_name": model_name,
            "output": output,
            "output_type": output_type,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_model_result(self, model_name: str, result: Dict[str, Any]):
        """Broadcast complete model analysis result"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "model_result",
            "channel": channel,
            "model_name": model_name,
            "result": result,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_model_error(self, model_name: str, error: str):
        """Broadcast model error to specific channel"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "model_error",
            "channel": channel,
            "model_name": model_name,
            "error": error,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_execution_start(self, execution_id: str, models: List[str]):
        """Broadcast execution start with model list"""
        payload = {
            "type": "execution_start",
            "execution_id": execution_id,
            "models": models,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_execution_complete(self, execution_id: str, results: Dict[str, Any]):
        """Broadcast execution completion with results summary"""
        payload = {
            "type": "execution_complete",
            "execution_id": execution_id,
            "results_summary": {
                "total_models": len(results),
                "successful_models": len([r for r in results.values() if r.get("status") == "success"]),
                "failed_models": len([r for r in results.values() if r.get("status") == "error"])
            },
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def broadcast_model_progress(self, model_name: str, progress: float, message: str = ""):
        """Broadcast model execution progress"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "model_progress",
            "channel": channel,
            "model_name": model_name,
            "progress": progress,
            "message": message,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def clear_model_output(self, model_name: str):
        """Clear output for a specific model channel"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "clear_output",
            "channel": channel,
            "model_name": model_name,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def update_model_config(self, model_name: str, config: Dict[str, Any]):
        """Broadcast model configuration update"""
        channel = self.model_channels.get(model_name, "unknown")
        payload = {
            "type": "model_config_update",
            "channel": channel,
            "model_name": model_name,
            "config": config,
            "timestamp": time.time()
        }
        await self._broadcast(payload)
        
    async def _broadcast(self, message: Dict[str, Any]):
        """Internal method to broadcast message to all connected clients"""
        if not self.active_connections:
            return
            
        disconnected = []
        message_json = json.dumps(message)
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"❌ Error broadcasting to client: {e}")
                disconnected.append(connection)
                
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
            
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
        
    def get_model_channel(self, model_name: str) -> Optional[str]:
        """Get channel name for a model"""
        return self.model_channels.get(model_name)
        
    def get_connected_clients_info(self) -> List[Dict[str, Any]]:
        """Get information about connected clients"""
        return [
            {
                "id": id(conn),
                "connected_at": "unknown"  # Could be enhanced with connection tracking
            }
            for conn in self.active_connections
        ]
        
    async def send_system_message(self, message: str, message_type: str = "info"):
        """Send system-level message"""
        payload = {
            "type": "system_message",
            "message": message,
            "message_type": message_type,
            "timestamp": time.time()
        }
        await self._broadcast(payload)


# Global multiplexer instance
websocket_multiplexer = WebSocketMultiplexer()

async def test_websocket_multiplexer():
    """Test function for WebSocket multiplexer"""
    multiplexer = WebSocketMultiplexer()
    
    print("=== WebSocket Multiplexer Test ===")
    print(f"Model channels: {multiplexer.model_channels}")
    
    # Test message creation (without actual WebSocket connections)
    test_messages = [
        ("broadcast_message", ["status", "Test broadcast message"]),
        ("broadcast_model_status", ["deepseek_r1", "started"]),
        ("broadcast_model_output", ["deepseek_r1", "Model analysis in progress..."]),
        ("broadcast_model_error", ["llama3", "Model timeout error"]),
        ("broadcast_model_result", ["mistral", {"status": "success", "analysis": "Test analysis"}])
    ]
    
    for method_name, args in test_messages:
        method = getattr(multiplexer, method_name)
        print(f"Testing {method_name} with args {args}")
        
        # For testing without actual WebSocket connections
        print(f"  Would send: {method_name}({args})")
    
    print(f"Connection count: {multiplexer.get_connection_count()}")
    print("✅ WebSocket multiplexer test completed")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_websocket_multiplexer())