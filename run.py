import os
import sys
import subprocess
import time
import threading

def run_backend():
    print("[SYSTEM] Starting FastAPI Backend on http://localhost:8000...")
    # Change cwd to root to run backend app
    # Run uvicorn src.backend.app:app --host 127.0.0.1 --port 8000 --reload
    try:
        subprocess.run(
            [sys.executable, "-m", "uvicorn", "src.backend.app:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            check=True
        )
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[ERROR] Failed to start backend: {e}")

def run_frontend():
    print("[SYSTEM] Starting React + Vite Frontend on http://localhost:5173...")
    frontend_dir = os.path.join(os.getcwd(), "src", "frontend")
    if not os.path.exists(frontend_dir):
        print(f"[ERROR] Frontend directory not found at: {frontend_dir}")
        return

    # Run npm run dev inside src/frontend
    try:
        # On Windows, we use shell=True to execute npm commands correctly
        subprocess.run("npm run dev", shell=True, cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[ERROR] Failed to start frontend. Make sure to run 'npm install' inside 'src/frontend' first. Details: {e}")

if __name__ == "__main__":
    print("="*60)
    print("      AI-POWERED AR VIRTUAL TRY-ON (PSCI) - STARTUP SCRIPT")
    print("="*60)

    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    # Wait a moment for backend to initialize
    time.sleep(1.5)

    # Start frontend in the main thread (keeps script alive)
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Shutting down servers. Goodbye!")
