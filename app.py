from flask import Flask, render_template, jsonify, request
import os
import subprocess
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Global variables to track bot status
bot_process = None
bot_status = "stopped"
bot_output = []
max_output_lines = 100

def run_bot():
    global bot_process, bot_status, bot_output
    try:
        bot_process = subprocess.Popen(
            ["python", "stackexchange_bot.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        bot_status = "running"
        
        # Read output in real-time
        while True:
            output = bot_process.stdout.readline()
            if output == '' and bot_process.poll() is not None:
                break
            if output:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                bot_output.append(f"[{timestamp}] {output.strip()}")
                # Keep only last N lines
                if len(bot_output) > max_output_lines:
                    bot_output.pop(0)
        
        bot_status = "stopped"
        bot_process = None
        
    except Exception as e:
        bot_status = "error"
        bot_output.append(f"Error: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_process, bot_status
    if bot_status != "running":
        bot_output.clear()
        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already_running"})

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_process, bot_status
    if bot_process and bot_status == "running":
        bot_process.terminate()
        bot_status = "stopped"
        return jsonify({"status": "stopped"})
    return jsonify({"status": "not_running"})

@app.route('/status')
def get_status():
    return jsonify({
        "status": bot_status,
        "output": bot_output[-50:] # Return last 50 lines
    })

@app.route('/sites', methods=['GET', 'POST'])
def manage_sites():
    if request.method == 'POST':
        sites = request.form.get('sites', '').strip().split('\n')
        sites = [site.strip() for site in sites if site.strip()]
        with open('sites.txt', 'w') as f:
            f.write('\n'.join(sites))
        return jsonify({"status": "updated"})
    
    with open('sites.txt', 'r') as f:
        sites = f.read()
    return jsonify({"sites": sites})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 