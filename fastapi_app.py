# fastapi_app.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

# Serve static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="."), name="static")

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
            
            # Use python3 instead of python
            cmd = ["python3", "nifty_main.py"]
            
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
    # Serve the HTML file directly
    return FileResponse('index.html')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=5001, 
        access_log=True
    )