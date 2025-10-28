# fastapi_app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import subprocess
import json
import time
import os
import glob
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nifty Option Chain Fetcher", version="1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScriptRunner:
    def __init__(self):
        self.running = False
        
    def find_latest_text_file(self):
        """Find the most recently created text file in ai-query-logs directory"""
        try:
            logs_dir = os.path.join(os.getcwd(), "ai-query-logs")
            if not os.path.exists(logs_dir):
                return None
                
            text_files = glob.glob(os.path.join(logs_dir, "*.txt"))
            if not text_files:
                return None
                
            # Get the most recently created file
            latest_file = max(text_files, key=os.path.getctime)
            return latest_file
            
        except Exception as e:
            logger.error(f"Error finding text files: {e}")
            return None
    
    def read_text_file_content(self, filepath: str) -> str:
        """Read the content of a text file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error reading file {filepath}: {str(e)}"
    
    async def run_script_and_get_file_content(self):
        """Run nifty_main.py and return the content of the created text file"""
        if self.running:
            return None, "Script is already running"
            
        try:
            logger.info("Starting nifty_main.py...")
            
            # Run nifty_main.py as a subprocess
            cmd = ["python", "nifty_main.py"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                bufsize=0,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}
            )
            
            self.running = True
            
            # Wait for the process to complete
            await process.wait()
            self.running = False
            
            logger.info("nifty_main.py completed")
            
            # Find and read the latest text file
            latest_file = self.find_latest_text_file()
            if latest_file:
                content = self.read_text_file_content(latest_file)
                logger.info(f"Found text file: {os.path.basename(latest_file)}")
                return content, f"Script completed successfully. File: {os.path.basename(latest_file)}"
            else:
                logger.warning("No text file found after script completion")
                return None, "Script completed but no text file was found"
                
        except Exception as e:
            self.running = False
            logger.error(f"Error running script: {e}")
            return None, f"Error running script: {str(e)}"

# Global script runner
script_runner = ScriptRunner()

# API endpoints
@app.post("/run")
async def run_script():
    """Run the Nifty script and return the text file content"""
    if script_runner.running:
        raise HTTPException(status_code=400, detail="Script is already running")
    
    try:
        logger.info("Run endpoint called")
        
        # Run script and get file content
        content, status_message = await script_runner.run_script_and_get_file_content()
        
        if content:
            return {
                "status": "success", 
                "message": status_message,
                "content": content
            }
        else:
            return {"status": "error", "message": status_message}
            
    except Exception as e:
        error_msg = f"Error running script: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/status")
async def get_status():
    """Get current script status"""
    return {
        "running": script_runner.running,
        "status": "running" if script_runner.running else "stopped"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

# Serve the main page
@app.get("/")
async def get_main_page():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Nifty Option Chain - AI Analysis</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: #333;
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1400px; 
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .header h1 {
                font-size: 2.2em;
                margin-bottom: 10px;
                font-weight: 700;
            }
            .header p {
                font-size: 1.1em;
                opacity: 0.9;
            }
            .controls {
                background: #f8f9fa;
                padding: 25px;
                display: flex;
                justify-content: center;
                gap: 20px;
                border-bottom: 2px solid #e9ecef;
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
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }
            .btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            }
            .run-btn {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
            }
            .copy-btn {
                background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
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
                background: #f8f9fa;
                padding: 20px;
                border-bottom: 2px solid #e9ecef;
            }
            .status-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                border: 2px solid #dee2e6;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .status-connected {
                border-color: #28a745;
                background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
            }
            .status-running {
                border-color: #ffc107;
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            }
            .status-card h3 {
                font-size: 1.2em;
                margin-bottom: 10px;
                color: #495057;
            }
            .output-section {
                padding: 0;
            }
            .output-header {
                background: #343a40;
                color: white;
                padding: 20px 25px;
                border-bottom: 2px solid #495057;
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
                color: #adb5bd;
            }
            .output-container {
                background: #1a1a1a;
                color: #e9ecef;
                height: 70vh;
                min-height: 500px;
                overflow-y: auto;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                padding: 20px;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .output-line {
                margin-bottom: 2px;
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            /* Mobile Responsive */
            @media (max-width: 768px) {
                body { padding: 10px; }
                .header { padding: 20px; }
                .header h1 { font-size: 1.8em; }
                .controls { padding: 15px; gap: 10px; }
                .btn { 
                    padding: 12px 20px; 
                    min-width: 120px;
                    font-size: 14px;
                }
                .output-container {
                    height: 60vh;
                    font-size: 11px;
                    padding: 15px;
                }
                .output-header {
                    padding: 15px 20px;
                    flex-direction: column;
                    gap: 10px;
                    text-align: center;
                }
            }
            
            @media (max-width: 480px) {
                .controls { flex-direction: column; }
                .btn { width: 100%; }
                .output-container {
                    height: 50vh;
                    font-size: 10px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Nifty AI Analysis Console</h1>
                <p>Complete AI Query + Option Chain Data</p>
            </div>
            
            <div class="controls">
                <button id="runBtn" class="btn run-btn" onclick="runScript()">
                    <span>▶</span> RUN ANALYSIS
                </button>
                <button id="copyBtn" class="btn copy-btn" onclick="copyOutput()">
                    <span>📋</span> COPY OUTPUT
                </button>
            </div>
            
            <div class="status-panel">
                <div id="statusCard" class="status-card status-connected">
                    <h3>🔌 Server Status</h3>
                    <p id="statusText">Ready to run analysis</p>
                </div>
            </div>
            
            <div class="output-section">
                <div class="output-header">
                    <h3>📊 AI Analysis Output</h3>
                    <div class="output-stats">
                        <span id="fileInfo">No file loaded</span>
                    </div>
                </div>
                <div class="output-container" id="output">
                    <div class="output-line">🚀 Ready to run analysis...</div>
                    <div class="output-line">Click RUN ANALYSIS to generate AI query data</div>
                </div>
            </div>
        </div>

        <script>
            let currentContent = "";
            let isRunning = false;
            
            async function runScript() {
                if (isRunning) {
                    alert('Script is already running. Please wait...');
                    return;
                }
                
                try {
                    // Clear console first
                    clearOutput();
                    addOutputLine('🚀 Starting analysis...');
                    updateFileInfo('Running analysis...');
                    updateStatus('🔄 Running analysis...', 'status-running');
                    document.getElementById('runBtn').disabled = true;
                    isRunning = true;
                    
                    const response = await fetch('/run', { 
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        // Display the file content
                        displayFileContent(result.content);
                        updateFileInfo(result.message);
                        updateStatus('✅ Analysis completed', 'status-connected');
                        addOutputLine('✅ ' + result.message);
                    } else {
                        addOutputLine('❌ ' + result.message, 'error');
                        updateFileInfo('Error: ' + result.message);
                        updateStatus('❌ Analysis failed', 'status-connected');
                    }
                    
                } catch (error) {
                    console.error('Error running script:', error);
                    addOutputLine('❌ Error: ' + error.message, 'error');
                    updateFileInfo('Error running analysis');
                    updateStatus('❌ Analysis failed', 'status-connected');
                } finally {
                    document.getElementById('runBtn').disabled = false;
                    isRunning = false;
                }
            }
            
            async function copyOutput() {
                if (!currentContent) {
                    alert('No content to copy. Please run analysis first.');
                    return;
                }
                
                try {
                    await navigator.clipboard.writeText(currentContent);
                    addOutputLine('✅ Content copied to clipboard!', 'success');
                } catch (error) {
                    console.error('Error copying to clipboard:', error);
                    
                    // Fallback method
                    const textArea = document.createElement('textarea');
                    textArea.value = currentContent;
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {
                        document.execCommand('copy');
                        addOutputLine('✅ Content copied to clipboard!', 'success');
                    } catch (fallbackError) {
                        addOutputLine('❌ Failed to copy content', 'error');
                    }
                    document.body.removeChild(textArea);
                }
            }
            
            function clearOutput() {
                const outputDiv = document.getElementById('output');
                outputDiv.innerHTML = '';
                currentContent = "";
            }
            
            function displayFileContent(content) {
                const outputDiv = document.getElementById('output');
                currentContent = content;
                
                // Split content by lines and display
                const lines = content.split('\n');
                lines.forEach((line, index) => {
                    const lineDiv = document.createElement('div');
                    lineDiv.className = 'output-line';
                    lineDiv.textContent = line;
                    outputDiv.appendChild(lineDiv);
                });
                
                // Auto-scroll to bottom
                outputDiv.scrollTop = outputDiv.scrollHeight;
            }
            
            function addOutputLine(text, type = 'info') {
                const outputDiv = document.getElementById('output');
                const lineDiv = document.createElement('div');
                lineDiv.className = 'output-line';
                lineDiv.textContent = text;
                outputDiv.appendChild(lineDiv);
                
                // Auto-scroll to bottom
                outputDiv.scrollTop = outputDiv.scrollHeight;
            }
            
            function updateStatus(message, statusClass) {
                const statusCard = document.getElementById('statusCard');
                const statusText = document.getElementById('statusText');
                
                statusText.textContent = message;
                statusCard.className = `status-card ${statusClass}`;
            }
            
            function updateFileInfo(info) {
                document.getElementById('fileInfo').textContent = info;
            }
            
            // Check server status on load
            async function checkServerStatus() {
                try {
                    const response = await fetch('/health');
                    const result = await response.json();
                    updateStatus('✅ Server connected', 'status-connected');
                } catch (error) {
                    updateStatus('❌ Server unavailable', 'status-connected');
                }
            }
            
            // Initialize when page loads
            document.addEventListener('DOMContentLoaded', function() {
                checkServerStatus();
            });
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5001, 
        access_log=True
    )