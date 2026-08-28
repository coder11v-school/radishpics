import os
import time
import threading
import subprocess
from datetime import datetime
from picamera2 import Picamera2
from picamera2.outputs import WebServer

REPO_DIR = os.path.expanduser("~/radishpics")
INTERVAL_SECONDS = 600  # 10 minutes

picam = Picamera2()

def git_backup(filename):
    try:
        subprocess.run(["git", "add", filename], cwd=REPO_DIR, check=True)
        commit_msg = f"Automated capture: {filename}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print(f"[{datetime.now()}] Pushed {filename} to GitHub!")
    except Exception as e:
        print(f"Git push failed: {e}")

def timelapse_loop():
    print(f"Timelapse loop running. Interval: {INTERVAL_SECONDS} seconds.")
    while True:
        time.sleep(INTERVAL_SECONDS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"radish_{timestamp}.jpg"
        output_path = os.path.join(REPO_DIR, filename)
        
        try:
            print(f"[{datetime.now()}] Capturing image...")
            # Capture file mid-stream without breaking the active web feed
            picam.capture_file(output_path)
            # Offload Git changes to a background task so video feed stays fluid
            threading.Thread(target=git_backup, args=(filename,), daemon=True).start()
        except Exception as e:
            print(f"Capture failed: {e}")

# Create standard 720p stream configuration settings
config = picam.create_video_configuration(main={"size": (1280, 720)})
picam.configure(config)
picam.start()

# Use Picamera2's official native web server suite
server = WebServer(picam, port=8000)
print("Livestream server active at http://veerpiquick.local:8000")

# Spin up the background 10-minute snapshot timer loop thread
threading.Thread(target=timelapse_loop, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    picam.stop()
