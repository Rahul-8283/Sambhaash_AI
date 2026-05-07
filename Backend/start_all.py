import subprocess
import sys
import time
import os

print("[START] Booting up Sambhaash AI services...")

# Start background worker process
print("[START] Starting Background Worker Process...")
worker_process = subprocess.Popen([sys.executable, "run_worker.py"])

# Get port from environment or default to 10000
port = os.environ.get("PORT", "10000")

# Start FastAPI web server
print(f"[START] Starting FastAPI Server on port {port}...")
api_process = subprocess.Popen([
    sys.executable, "-m", "uvicorn", "main:app", 
    "--host", "0.0.0.0", 
    "--port", port
])

# Keep container alive and monitor processes
try:
    while True:
        # Check if either process has died
        if worker_process.poll() is not None:
            print("[ERROR] Background worker process terminated! Exiting container...", file=sys.stderr)
            api_process.terminate()
            sys.exit(1)
            
        if api_process.poll() is not None:
            print("[ERROR] FastAPI server process terminated! Exiting container...", file=sys.stderr)
            worker_process.terminate()
            sys.exit(1)
            
        time.sleep(2)
except KeyboardInterrupt:
    print("[STOP] Stopping all services...")
    worker_process.terminate()
    api_process.terminate()
