# fastapi_app.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import subprocess
import json
import time
import sys
import os
from typing import List
import signal

app = FastAPI(title="Nifty Option Chain Fetcher", version="1.0")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"New connection. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Connection closed. Total: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)
            
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

class ScriptRunner:
    def __init__(self):
        self.process = None
        self.running = False
        self.task = None
        
    async def start_script(self):
        """Start the Nifty script asynchronously"""
        if self.running:
            await manager.broadcast(json.dumps({
                "type": "error",
                "message": "Script is already running"
            }))
            return False
            
        try:
            await manager.broadcast(json.dumps({
                "type": "status",
                "message": "🚀 Starting Nifty Option Chain Fetcher..."
            }))
            
            # Command to run the script
            script_dir = "/home/niftyaic/niftyai"
            venv_python = "/home/niftyaic/virtualenv/niftyai/3.10/bin/python"
            
            cmd = [
                venv_python, 
                "-u",  # Unbuffered output
                "Nifty_Option_Chain_Fetcher_Part3.py"
            ]
            
            # Create subprocess with unbuffered output
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=script_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                bufsize=0,  # No buffering
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            self.running = True
            
            # Start output reading task
            self.task = asyncio.create_task(self._read_output())
            
            await manager.broadcast(json.dumps({
                "type": "status", 
                "message": "✅ Script started successfully"
            }))
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Failed to start script: {str(e)}"
            print(error_msg)
            await manager.broadcast(json.dumps({
                "type": "error",
                "message": error_msg
            }))
            return False
    
    async def _read_output(self):
        """Read output from the script in real-time"""
        try:
            while self.running and self.process and self.process.stdout:
                # Read line by line
                line = await self.process.stdout.readline()
                if line:
                    decoded = line.decode('utf-8').strip()
                    if decoded:
                        await manager.broadcast(json.dumps({
                            "type": "output",
                            "data": decoded,
                            "timestamp": time.time()
                        }))
                else:
                    # Process finished
                    if await self.process.wait() is not None:
                        break
        except Exception as e:
            print(f"Error reading output: {e}")
        
        self.running = False
        await manager.broadcast(json.dumps({
            "type": "status",
            "message": "🛑 Script stopped"
        }))
    
    async def stop_script(self):
        """Stop the running script"""
        if not self.running or not self.process:
            await manager.broadcast(json.dumps({
                "type": "error", 
                "message": "No script is running"
            }))
            return False
            
        try:
            await manager.broadcast(json.dumps({
                "type": "status",
                "message": "🛑 Stopping script..."
            }))
            
            # Terminate the process
            self.process.terminate()
            
            # Wait for process to end
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                # Force kill if not responding
                self.process.kill()
                await self.process.wait()
            
            self.running = False
            
            if self.task and not self.task.done():
                self.task.cancel()
                
            await manager.broadcast(json.dumps({
                "type": "status",
                "message": "✅ Script stopped successfully"
            }))
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Error stopping script: {str(e)}"
            print(error_msg)
            await manager.broadcast(json.dumps({
                "type": "error",
                "message": error_msg
            }))
            return False

# Global script runner
script_runner = ScriptRunner()

# WebSocket endpoint for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial status
        await manager.send_personal_message(json.dumps({
            "type": "status",
            "message": "🔌 Connected to server"
        }), websocket)
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle any incoming messages if needed
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# API endpoints
@app.post("/start")
async def start_script():
    """Start the Nifty script"""
    success = await script_runner.start_script()
    return {"status": "success" if success else "error", 
            "message": "Script started" if success else "Failed to start script"}

@app.post("/stop")  
async def stop_script():
    """Stop the Nifty script"""
    success = await script_runner.stop_script()
    return {"status": "success" if success else "error",
            "message": "Script stopped" if success else "Failed to stop script"}

@app.get("/status")
async def get_status():
    """Get current script status"""
    return {
        "running": script_runner.running,
        "status": "running" if script_runner.running else "stopped"
    }

# Main page
@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nifty Option Chain - RealTime</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
                color: #e0e0e0;
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto;
                background: #2d2d2d;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                overflow: hidden;
                border: 1px solid #404040;
            }
            .header {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-bottom: 1px solid #404040;
            }
            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                font-weight: 700;
            }
            .header p {
                font-size: 1.2em;
                opacity: 0.9;
            }
            .controls {
                background: #363636;
                padding: 25px;
                display: flex;
                justify-content: center;
                gap: 20px;
                border-bottom: 1px solid #404040;
                flex-wrap: wrap;
            }
            .btn {
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
                min-width: 140px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            }
            .btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            }
            .start-btn {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
            }
            .stop-btn {
                background: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%);
                color: white;
            }
            .btn:disabled {
                background: #6c757d;
                cursor: not-allowed;
                transform: none !important;
                box-shadow: none;
                opacity: 0.6;
            }
            .status-panel {
                background: #2d2d2d;
                padding: 25px;
                border-bottom: 1px solid #404040;
            }
            .status-card {
                background: #363636;
                padding: 25px;
                border-radius: 10px;
                text-align: center;
                border: 2px solid #404040;
                transition: all 0.3s ease;
            }
            .status-connected {
                border-color: #28a745;
                background: linear-gradient(135deg, #155724 0%, #1e7e34 100%);
            }
            .status-disconnected {
                border-color: #dc3545;
                background: linear-gradient(135deg, #721c24 0%, #c82333 100%);
            }
            .status-card h3 {
                font-size: 1.4em;
                margin-bottom: 10px;
            }
            .output-section {
                padding: 0;
            }
            .output-header {
                background: #363636;
                padding: 20px 25px;
                border-bottom: 1px solid #404040;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .output-header h3 {
                font-size: 1.3em;
                font-weight: 600;
            }
            .output-stats {
                font-size: 0.9em;
                color: #aaa;
            }
            .output-container {
                background: #1a1a1a;
                height: 600px;
                overflow-y: auto;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 20px;
            }
            .output-line {
                margin-bottom: 4px;
                padding: 4px 8px;
                border-radius: 4px;
                animation: slideIn 0.3s ease;
                word-wrap: break-word;
                border-left: 3px solid transparent;
            }
            .output-line:hover {
                background: #2d2d2d;
            }
            .output-line.info { border-left-color: #17a2b8; }
            .output-line.success { border-left-color: #28a745; }
            .output-line.warning { border-left-color: #ffc107; }
            .output-line.error { border-left-color: #dc3545; }
            
            @keyframes slideIn {
                from { opacity: 0; transform: translateX(-10px); }
                to { opacity: 1; transform: translateX(0); }
            }
            
            .line-number {
                color: #6c757d;
                margin-right: 15px;
                font-size: 0.9em;
                user-select: none;
                min-width: 50px;
                display: inline-block;
                text-align: right;
            }
            
            .output-container::-webkit-scrollbar {
                width: 12px;
            }
            .output-container::-webkit-scrollbar-track {
                background: #2d2d2d;
                border-radius: 6px;
            }
            .output-container::-webkit-scrollbar-thumb {
                background: #404040;
                border-radius: 6px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Nifty Option Chain Fetcher</h1>
                <p>Real-time Nifty, BankNifty, and Stock Options Analysis with AI</p>
            </div>
            
            <div class="controls">
                <button id="startBtn" class="btn start-btn" onclick="startScript()">
                    <span>▶</span> Start Script
                </button>
                <button id="stopBtn" class="btn stop-btn" onclick="stopScript()" disabled>
                    <span>⏹</span> Stop Script
                </button>
            </div>
            
            <div class="status-panel">
                <div id="statusCard" class="status-card status-disconnected">
                    <h3>🔌 Connection Status</h3>
                    <p id="statusText">Disconnected from server</p>
                </div>
            </div>
            
            <div class="output-section">
                <div class="output-header">
                    <h3>📊 Live Output</h3>
                    <div class="output-stats">
                        Lines: <span id="lineCount">0</span>
                    </div>
                </div>
                <div class="output-container" id="output">
                    <div class="output-line info">
                        <span class="line-number">1</span>🚀 Ready to connect...
                    </div>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let isConnected = false;
            let lineCount = 1;
            let reconnectTimeout = null;
            
            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws`;
                
                console.log('Connecting to:', wsUrl);
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    console.log('WebSocket connected');
                    isConnected = true;
                    updateStatus('✅ Connected to server', 'status-connected');
                    clearTimeout(reconnectTimeout);
                };
                
                ws.onmessage = function(event) {
                    try {
                        const data = JSON.parse(event.data);
                        handleWebSocketMessage(data);
                    } catch (error) {
                        console.error('Error parsing message:', error);
                    }
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket disconnected:', event.code, event.reason);
                    isConnected = false;
                    updateStatus('❌ Disconnected from server', 'status-disconnected');
                    
                    // Attempt reconnect after 2 seconds
                    if (!reconnectTimeout) {
                        reconnectTimeout = setTimeout(() => {
                            reconnectTimeout = null;
                            console.log('Attempting to reconnect...');
                            connectWebSocket();
                        }, 2000);
                    }
                };
                
                ws.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    updateStatus('❌ Connection error', 'status-disconnected');
                };
            }
            
            function handleWebSocketMessage(data) {
                switch(data.type) {
                    case 'output':
                        addOutputLine(data.data);
                        break;
                    case 'status':
                        addOutputLine(data.message, 'info');
                        break;
                    case 'error':
                        addOutputLine(data.message, 'error');
                        break;
                    default:
                        console.log('Unknown message type:', data);
                }
            }
            
            function addOutputLine(text, type = 'info') {
                lineCount++;
                const outputDiv = document.getElementById('output');
                const lineDiv = document.createElement('div');
                lineDiv.className = `output-line ${type}`;
                lineDiv.innerHTML = `<span class="line-number">${lineCount}</span>${escapeHtml(text)}`;
                outputDiv.appendChild(lineDiv);
                
                // Auto-scroll to bottom
                outputDiv.scrollTop = outputDiv.scrollHeight;
                
                // Update line count
                document.getElementById('lineCount').textContent = lineCount;
                
                // Limit lines to prevent memory issues
                const maxLines = 1000;
                const lines = outputDiv.querySelectorAll('.output-line');
                if (lines.length > maxLines) {
                    const toRemove = lines.length - maxLines;
                    for (let i = 0; i < toRemove; i++) {
                        lines[i].remove();
                    }
                }
            }
            
            function updateStatus(message, statusClass) {
                const statusCard = document.getElementById('statusCard');
                const statusText = document.getElementById('statusText');
                
                statusText.textContent = message;
                statusCard.className = `status-card ${statusClass}`;
            }
            
            async function startScript() {
                if (!isConnected) {
                    alert('Not connected to server');
                    return;
                }
                
                try {
                    const response = await fetch('/start', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const result = await response.json();
                    alert(result.message);
                } catch (error) {
                    console.error('Error starting script:', error);
                    alert('Error starting script: ' + error.message);
                }
            }
            
            async function stopScript() {
                if (!isConnected) {
                    alert('Not connected to server');
                    return;
                }
                
                try {
                    const response = await fetch('/stop', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const result = await response.json();
                    alert(result.message);
                } catch (error) {
                    console.error('Error stopping script:', error);
                    alert('Error stopping script: ' + error.message);
                }
            }
            
            function escapeHtml(unsafe) {
                return unsafe
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }
            
            // Update button states based on connection
            function updateButtonStates() {
                const startBtn = document.getElementById('startBtn');
                const stopBtn = document.getElementById('stopBtn');
                
                startBtn.disabled = !isConnected;
                stopBtn.disabled = !isConnected;
            }
            
            // Initialize
            connectWebSocket();
            
            // Periodically update button states
            setInterval(updateButtonStates, 1000);
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, access_log=True)