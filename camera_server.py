import os
import time
import io
import threading
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from picamera2 import Picamera2

# Setup paths and configurations
REPO_DIR = os.path.expanduser("~/radishpics")
INTERVAL_SECONDS = 600  # 10 minutes
PORT = 8000  # Web browser stream port

# Global frame buffer for the web stream
class StreamBuffer:
    def __init__(self):
        self.frame = b''
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

stream_buffer = StreamBuffer()
picam = Picamera2()

# Web server request handler for MJPEG streaming
class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = f"<html><head><title>RadishCam Live</title></head><body style='background:#111; text-align:center;'><h1 style='color:white;'>RadishCam Live Feed</h1><img src='/stream.mjpg' style='max-width:100%; border:2px solid #333;'/></body></html>"
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with stream_buffer.condition:
                        stream_buffer.condition.wait()
                        frame = stream_buffer.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(frame)))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                print(f"Client disconnected: {e}")
        else:
            self.send_error(404)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True

# Git automation deployment worker
def git_backup(filename):
    try:
        subprocess.run(["git", "add", filename], cwd=REPO_DIR, check=True)
        commit_msg = f"Automated capture: {filename.split('.')[0]}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print(f"[{datetime.now()}] Successfully pushed {filename} to GitHub!")
    except subprocess.CalledProcessError as e:
        print(f"Git push failed: {e}")

# Dedicated thread worker for the 10-minute snapshot loop
def timelapse_loop():
    print(f"Timelapse loop initialized. Interval: {INTERVAL_SECONDS}s")
    while True:
        start_time = time.time()
        
        # Format names safely
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"radish_{timestamp}.jpg"
        output_path = os.path.join(REPO_DIR, filename)
        
        print(f"[{datetime.now()}] Capturing high-res snapshot...")
        try:
            # Safely request a full-resolution capture mid-stream array
            picam.capture_file(output_path)
            # Offload GitHub sync to a background process so the camera feed never stutters
            threading.Thread(target=git_backup, args=(filename,), daemon=True).start()
        except Exception as capture_error:
            print(f"Snapshot execution failed: {capture_error}")

        # Sleep accurately between intervals
        elapsed = time.time() - start_time
        sleep_duration = max(0, INTERVAL_SECONDS - elapsed)
        time.sleep(sleep_duration)

def main():
    # Configure camera sensor profiling
    config = picam.create_video_configuration(main={"size": (1280, 720)})
    picam.configure(config)
    
    # Send video frames to our global stream buffer
    picam.start_recording(stream_buffer, format="mjpeg")
    print("Camera engine running.")

    # Start the background 10-minute timelapse tracker
    timelapse_thread = threading.Thread(target=timelapse_loop, daemon=True)
    timelapse_thread.start()

    # Launch the internal web server network hook
    server_address = ('', PORT)
    server = ThreadedHTTPServer(server_address, StreamingHandler)
    print(f"Livestream available at http://veerpiquick.local:{PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down camera server...")
    finally:
        picam.stop_recording()
        picam.close()

if __name__ == "__main__":
    main()
