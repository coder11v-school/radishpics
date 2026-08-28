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
            # Capture using the dedicated 'still' encoder channel configuration
            picam.capture_file(output_path, encoder="still")
            threading.Thread(target=git_backup, args=(filename,), daemon=True).start()
        except Exception as e:
            print(f"Camera frame capture failed: {e}")

# Configure dual streams: main video for the web, still for high-res photos
config = picam.create_still_configuration(main={"size": (1280, 720)}, still={"size": (3280, 2464)})
picam.configure(config)

# CRITICAL FOR HEADLESS: preview=None prevents the script from looking for a GUI display
picam.start(preview=None)

# Initialize the official built-in WebServer module on port 8000
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
