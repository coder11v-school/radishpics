import os
import time
import threading
import subprocess
from datetime import datetime
from picamera2 import Picamera2
from picamera2.outputs import WebServer

REPO_DIR = os.path.expanduser("~/radishpics")
INTERVAL_SECONDS = 600  # 10 minutes

# Initialize camera
picam = Picamera2()

def git_backup(filename):
    try:
        subprocess.run(["git", "add", filename], cwd=REPO_DIR, check=True)
        commit_msg = f"Automated capture: {filename}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print(f"[{datetime.now()}] Successfully pushed {filename} to GitHub!")
    except Exception as e:
        print(f"Git backup pipeline failed: {e}")

def timelapse_loop():
    print(f"Headless timelapse engine active. Tracking interval: {INTERVAL_SECONDS}s")
    while True:
        time.sleep(INTERVAL_SECONDS)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"radish_{timestamp}.jpg"
        output_path = os.path.join(REPO_DIR, filename)
        
        try:
            print(f"[{datetime.now()}] Capturing snapshot...")
            # Use dedicated still sensor channel configuration for high-res photo capture
            picam.capture_file(output_path, encoder="still")
            threading.Thread(target=git_backup, args=(filename,), daemon=True).start()
        except Exception as e:
            print(f"Camera frame capture failed: {e}")

# Build explicit configuration avoiding unallocated raw formats
config = picam.create_still_configuration(main={"size": (640, 480)}, still={"size": (3280, 2464)})
picam.configure(config)

# CRITICAL FOR HEADLESS SSH: Disables local display layout rendering pipelines
picam.start(preview=None)

# Initialize the official Raspberry Pi WebServer module on port 8000
server = WebServer(picam, port=8000)
print("Livestream server active at http://veerpiquick.local:8000")

# Start timelapse background worker thread loop
threading.Thread(target=timelapse_loop, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    server.stop()
    picam.stop()
