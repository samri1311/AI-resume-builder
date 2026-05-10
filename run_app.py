import subprocess
import sys


def run_backend():
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--reload"
        ]
    )


def run_frontend():
    return subprocess.Popen(
        [
            "streamlit",
            "run",
            "frontend/app.py"
        ]
    )


if __name__ == "__main__":

    print("🚀 Starting Backend...")
    backend_process = run_backend()

    print("🎨 Starting Frontend...")
    frontend_process = run_frontend()

    try:
        backend_process.wait()
        frontend_process.wait()

    except KeyboardInterrupt:

        print("\n🛑 Shutting down...")

        backend_process.kill()
        frontend_process.kill()

        print("✅ App stopped.")

        #How to run:
        #python run_app.py
