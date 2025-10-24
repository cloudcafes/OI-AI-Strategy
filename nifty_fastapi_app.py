# nifty_fastapi_app.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import subprocess
import json
import time
import sys
import os
from typing import List, Dict, Any
import signal
import logging

# Import our multi-model components
from nifty_websocket_multiplexer import WebSocketMultiplexer, websocket_multiplexer
from nifty_model_manager import ModelManager, model_manager
from nifty_model_registry import ModelRegistry, model_registry
from nifty_data_fetcher import fetch_option_chain, parse_option_chain, calculate_pcr_values, fetch_banknifty_data, fetch_all_stock_data
from nifty_core_config import initialize_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nifty Multi-Model Option Chain Analyzer", version="2.0")

# Mount templates directory
templates = Jinja2Templates(directory="templates")

# Initialize components
websocket_multiplexer = WebSocketMultiplexer()
model_manager = ModelManager(websocket_multiplexer=websocket_multiplexer)

class ScriptRunner:
    def __init__(self):
        self.process = None
        self.running = False
        self.task = None
        self.current_data = None
        
    async def start_multi_model_analysis(self):
        """Start multi-model analysis with current market data"""
        if self.running:
            await websocket_multiplexer.broadcast_message("error", "Analysis already in progress")
            return False
            
        try:
            await websocket_multiplexer.broadcast_message("status", "🚀 Starting multi-model analysis...")
            
            # Fetch fresh market data
            await websocket_multiplexer.broadcast_message("status", "📊 Fetching market data...")
            session = None
            try:
                session = initialize_session()
                data = fetch_option_chain(session)
                oi_data = parse_option_chain(data)
                oi_pcr, volume_pcr = calculate_pcr_values(oi_data)
                
                banknifty_data = fetch_banknifty_data()
                stock_data = fetch_all_stock_data()
                
                self.current_data = {
                    "oi_data": oi_data,
                    "oi_pcr": oi_pcr,
                    "volume_pcr": volume_pcr,
                    "current_nifty": oi_data[0]['nifty_value'] if oi_data else 0,
                    "expiry_date": oi_data[0]['expiry_date'] if oi_data else "N/A",
                    "stock_data": stock_data,
                    "banknifty_data": banknifty_data
                }
                
            except Exception as e:
                await websocket_multiplexer.broadcast_message("error", f"❌ Failed to fetch market data: {str(e)}")
                return False
            finally:
                if session:
                    session.close()
            
            await websocket_multiplexer.broadcast_message("status", "✅ Market data fetched successfully")
            
            # Start model execution
            self.running = True
            self.task = asyncio.create_task(self._execute_models())
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Failed to start analysis: {str(e)}"
            logger.error(error_msg)
            await websocket_multiplexer.broadcast_message("error", error_msg)
            return False
    
    async def _execute_models(self):
        """Execute models with current market data"""
        try:
            if not self.current_data:
                await websocket_multiplexer.broadcast_message("error", "No market data available")
                return
                
            # Get enabled models
            enabled_models = model_registry.get_enabled_models_in_order()
            if not enabled_models:
                await websocket_multiplexer.broadcast_message("error", "No models enabled for execution")
                return
                
            model_names = [model.name for model in enabled_models]
            await websocket_multiplexer.broadcast_execution_start("multi_exec", model_names)
            
            # Execute models sequentially
            results = await model_manager.execute_models_sequential(**self.current_data)
            
            await websocket_multiplexer.broadcast_execution_complete("multi_exec", results.get("results", {}))
            await websocket_multiplexer.broadcast_message("success", "🎉 Multi-model analysis completed!")
            
        except Exception as e:
            error_msg = f"❌ Model execution failed: {str(e)}"
            logger.error(error_msg)
            await websocket_multiplexer.broadcast_message("error", error_msg)
        finally:
            self.running = False
    
    async def stop_analysis(self):
        """Stop current analysis"""
        if not self.running:
            await websocket_multiplexer.broadcast_message("error", "No analysis is running")
            return False
            
        try:
            await websocket_multiplexer.broadcast_message("status", "🛑 Stopping analysis...")
            
            # Stop model execution
            if await model_manager.stop_execution():
                await websocket_multiplexer.broadcast_message("status", "✅ Analysis stopped successfully")
            else:
                await websocket_multiplexer.broadcast_message("status", "⚠️ No model execution to stop")
            
            # Cancel task
            if self.task and not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            
            self.running = False
            return True
            
        except Exception as e:
            error_msg = f"❌ Error stopping analysis: {str(e)}"
            logger.error(error_msg)
            await websocket_multiplexer.broadcast_message("error", error_msg)
            return False

# Global script runner
script_runner = ScriptRunner()

# WebSocket endpoint for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_multiplexer.connect(websocket)
    try:
        # Send initial status and model configuration
        await websocket_multiplexer.send_personal_message({
            "type": "system_message",
            "message": "🔌 Connected to multi-model analyzer",
            "message_type": "success"
        }, websocket)
        
        # Send current model status
        model_status = model_registry.get_model_status()
        await websocket_multiplexer.send_personal_message({
            "type": "model_config",
            "models": model_status
        }, websocket)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket_multiplexer.send_personal_message({
                        "type": "pong",
                        "timestamp": time.time()
                    }, websocket)
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        websocket_multiplexer.disconnect(websocket)

# API endpoints
@app.post("/start-models")
async def start_models():
    """Start multi-model analysis"""
    success = await script_runner.start_multi_model_analysis()
    return {
        "status": "success" if success else "error", 
        "message": "Multi-model analysis started" if success else "Failed to start analysis"
    }

@app.post("/stop-models")
async def stop_models():
    """Stop multi-model analysis"""
    success = await script_runner.stop_analysis()
    return {
        "status": "success" if success else "error",
        "message": "Analysis stopped" if success else "Failed to stop analysis"
    }

@app.post("/update-model")
async def update_model(model_data: Dict[str, Any]):
    """Update model configuration"""
    try:
        model_name = model_data.get("model_name")
        enabled = model_data.get("enabled")
        
        if not model_name:
            raise HTTPException(status_code=400, detail="Model name required")
            
        success = model_registry.set_model_enabled(model_name, enabled)
        
        if success:
            status = "enabled" if enabled else "disabled"
            await websocket_multiplexer.broadcast_message("success", f"Model {model_name} {status}")
            
            # Broadcast config update to all clients
            model_config = model_registry.get_model(model_name)
            if model_config:
                await websocket_multiplexer.update_model_config(model_name, model_config.to_dict())
            
            return {
                "status": "success",
                "message": f"Model {model_name} {status}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
            
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model-status")
async def get_model_status():
    """Get current model status and configuration"""
    return {
        "models": model_registry.get_model_status(),
        "analysis_running": script_runner.running,
        "connections": websocket_multiplexer.get_connection_count()
    }

@app.get("/model-config")
async def get_model_config():
    """Get complete model configuration"""
    return model_registry.to_dict()

@app.post("/model-config")
async def update_model_config(config: Dict[str, Any]):
    """Update model configuration from dictionary"""
    try:
        success = model_registry.from_dict(config)
        if success:
            # Broadcast config updates to all clients
            for model_name in model_registry.models.keys():
                model_config = model_registry.get_model(model_name)
                if model_config:
                    await websocket_multiplexer.update_model_config(model_name, model_config.to_dict())
            
            return {"status": "success", "message": "Configuration updated"}
        else:
            raise HTTPException(status_code=400, detail="Invalid configuration")
    except Exception as e:
        logger.error(f"Error updating model config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/execution-status")
async def get_execution_status():
    """Get current execution status"""
    return {
        "analysis_running": script_runner.running,
        "model_execution": model_manager.get_execution_status(),
        "connections": websocket_multiplexer.get_connection_count()
    }

@app.post("/clear-outputs")
async def clear_outputs():
    """Clear all model outputs"""
    try:
        for model_name in model_registry.models.keys():
            await websocket_multiplexer.clear_model_output(model_name)
        
        await websocket_multiplexer.broadcast_message("success", "All outputs cleared")
        return {"status": "success", "message": "Outputs cleared"}
    except Exception as e:
        logger.error(f"Error clearing outputs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Main page - serve the multi-model interface
@app.get("/", response_class=HTMLResponse)
async def get_root():
    """Serve the multi-model interface"""
    try:
        with open("templates/nifty_index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        # Fallback to embedded HTML if template file not found
        from nifty_frontend_components import get_multi_model_html
        return HTMLResponse(content=get_multi_model_html())

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "connections": websocket_multiplexer.get_connection_count(),
        "analysis_running": script_runner.running,
        "models_enabled": len(model_registry.get_enabled_models())
    }

@app.get("/system-info")
async def system_info():
    """Get system information"""
    return {
        "version": "2.0.0",
        "multi_model_enabled": True,
        "total_models": len(model_registry.get_all_models()),
        "enabled_models": len(model_registry.get_enabled_models()),
        "active_connections": websocket_multiplexer.get_connection_count(),
        "analysis_status": "running" if script_runner.running else "stopped"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 Nifty Multi-Model Analyzer starting up...")
    logger.info(f"📊 Total models: {len(model_registry.get_all_models())}")
    logger.info(f"✅ Enabled models: {len(model_registry.get_enabled_models())}")
    
    # Initialize model manager with WebSocket multiplexer
    model_manager.websocket_multiplexer = websocket_multiplexer

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Nifty Multi-Model Analyzer shutting down...")
    if script_runner.running:
        await script_runner.stop_analysis()

async def test_multi_model_system():
    """Test the multi-model system"""
    print("=== Testing Multi-Model System ===")
    
    # Test model registry
    enabled_models = model_registry.get_enabled_models_in_order()
    print(f"Enabled models: {[model.name for model in enabled_models]}")
    
    # Test WebSocket multiplexer
    print(f"WebSocket connections: {websocket_multiplexer.get_connection_count()}")
    
    # Test model manager
    status = model_manager.get_execution_status()
    print(f"Model manager status: {status}")
    
    print("✅ Multi-model system test completed")

if __name__ == "__main__":
    import uvicorn
    
    # Run test
    asyncio.run(test_multi_model_system())
    
    # Start the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5000, 
        access_log=True,
        log_level="info"
    )