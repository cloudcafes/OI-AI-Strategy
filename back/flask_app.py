from flask import Flask, render_template, request, jsonify
import threading
import queue
import sys
import io
import time
import signal
import os
import sqlite3
from datetime import datetime
from nifty_main import data_collection_loop, running, signal_handler, DB_FILE

app = Flask(__name__)

# Global variables
output_queue = queue.Queue()  # Store output lines
fetch_thread = None
stop_event = threading.Event()
original_stdout = sys.stdout
output_history = []  # Persist all output for history

# Custom stream to capture prints
class CapturingStream(io.StringIO):
    def write(self, text):
        text = text.strip()
        if text:
            output_queue.put(text)
            output_history.append((datetime.now().isoformat(), text))  # Store with timestamp
        original_stdout.write(text + '\n')

def run_fetcher():
    global running
    running = True
    sys.stdout = CapturingStream()
    try:
        data_collection_loop()
    except Exception as e:
        output_queue.put(f"Error: {str(e)}")
    finally:
        sys.stdout = original_stdout
        running = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    global fetch_thread
    if fetch_thread and fetch_thread.is_alive():
        return jsonify({'status': 'already_running'})
    
    stop_event.clear()
    running = True
    fetch_thread = threading.Thread(target=run_fetcher)
    fetch_thread.daemon = True
    fetch_thread.start()
    return jsonify({'status': 'started'})

@app.route('/stop', methods=['POST'])
def stop():
    global running
    if not fetch_thread or not fetch_thread.is_alive():
        return jsonify({'status': 'not_running'})
    
    running = False
    stop_event.set()
    os.kill(os.getpid(), signal.SIGINT)
    fetch_thread.join(timeout=10)
    output_history.append((datetime.now().isoformat(), "=== Fetcher Stopped ==="))
    return jsonify({'status': 'stopped'})

@app.route('/output')
def get_output():
    # Get latest from queue
    while not output_queue.empty():
        output_queue.get()  # Clear queue (history already stored)
    
    # Format history for HTML
    formatted_outputs = []
    current_block = []
    in_table = False
    for timestamp, line in output_history:
        if line.startswith("===="):  # Separator
            if current_block:
                formatted_outputs.append(format_block(current_block))
                current_block = []
            continue
        elif line.startswith("OI Data with Greeks"):
            in_table = True
            current_block.append(line)
        elif line.startswith("Note:") or line.startswith("PCR ANALYSIS") or line.startswith("FINAL INTERPRETATION") or line.startswith("🤖 DEEPSEEK AI INTRADAY ANALYSIS"):
            if current_block:
                formatted_outputs.append(format_block(current_block))
                current_block = [line]
            in_table = False
        else:
            current_block.append(line)
    
    if current_block:
        formatted_outputs.append(format_block(current_block))
    
    formatted_outputs.reverse()  # Latest on top
    return jsonify({'outputs': formatted_outputs})

def format_block(lines):
    """Format a block of output into HTML"""
    if not lines:
        return ""
    
    if lines[0].startswith("OI Data with Greeks"):
        return format_table(lines)
    elif lines[0].startswith("🤖 DEEPSEEK AI INTRADAY ANALYSIS"):
        return format_ai_analysis(lines)
    elif lines[0].startswith("PCR ANALYSIS") or lines[0].startswith("FINAL INTERPRETATION"):
        return format_analysis(lines)
    else:
        return "<div class='log-entry'>" + "<br>".join([f"<span>{line}</span>" for line in lines]) + "</div>"

def format_table(lines):
    """Format OI data table into HTML"""
    html = "<div class='table-container'><table class='table table-striped table-bordered'><thead>"
    for line in lines:
        if line.startswith("OI Data with Greeks"):
            html += f"<tr><th colspan='15' class='table-header'>{line}</th></tr>"
        elif line.startswith("CALL OPTION") or line.startswith("    Chg OI"):
            headers = line.split("|")
            html += "<tr>" + "".join([f"<th>{h.strip()}</th>" for h in headers if h.strip()]) + "</tr>"
        elif line.startswith("-" * 10):
            continue
        else:
            cells = [cell.strip() for cell in line.split("|") if cell.strip()]
            html += "<tr>" + "".join([f"<td>{c}</td>" for c in cells]) + "</tr>"
    html += "</thead></table></div>"
    return html

def format_ai_analysis(lines):
    """Format AI analysis into styled HTML"""
    html = "<div class='ai-analysis'><h4><i class='bi bi-robot'></i> AI Analysis</h4>"
    for line in lines:
        if line.startswith("SHORT SUMMARY"):
            html += f"<p><strong>{line}</strong></p>"
        elif line.startswith("- "):
            html += f"<p><em>{line}</em></p>"
        else:
            html += f"<p>{line}</p>"
    html += "</div>"
    return html

def format_analysis(lines):
    """Format PCR/Final analysis into styled HTML"""
    html = "<div class='analysis'><h5>{}</h5>".format(lines[0])
    for line in lines[1:]:
        if line.startswith(" "):
            key, value = line.split(":", 1)
            html += f"<p><strong>{key.strip()}:</strong> {value.strip()}</p>"
        else:
            html += f"<p>{line}</p>"
    html += "</div>"
    return html

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)