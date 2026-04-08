"""MedGuard-IDS Launcher — starts the unified dashboard.

Usage:
    python launcher.py          # Start the app
    python launcher.py --stop   # Kill running instance
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = 8501


def _python() -> str:
    return sys.executable


def start() -> None:
    print("=" * 50)
    print("  MedGuard-IDS  |  Unified Platform")
    print("=" * 50)
    print()
    print(f"  http://localhost:{PORT}")
    print()
    print("  Pages:")
    print("    - Hospital IoMT       (sidebar)")
    print("    - Intrusion Detection  (sidebar)")
    print("    - Attack Lab           (sidebar)")
    print()
    print("-" * 50)
    print("  Press Ctrl+C to stop.")
    print("-" * 50)
    print()

    cmd = [
        _python(), "-m", "streamlit", "run",
        str(ROOT / "app.py"),
        "--server.port", str(PORT),
        "--server.headless", "true",
    ]

    try:
        proc = subprocess.Popen(cmd, cwd=str(ROOT))
        proc.wait()
    except KeyboardInterrupt:
        print()
        print("  Shutting down...")
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        print("  Stopped. Goodbye.")


def stop() -> None:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(("localhost", PORT))
        s.close()
        if result == 0:
            print(f"  Port {PORT} is in use — attempting to free...")
            if sys.platform == "win32":
                os.system(f'for /f "tokens=5" %a in (\'netstat -ano ^| findstr :{PORT} ^| findstr LISTEN\') do taskkill /F /PID %a 2>nul')
            else:
                os.system(f"lsof -ti:{PORT} | xargs kill -9 2>/dev/null")
    except Exception:
        pass
    print("  Done.")


if __name__ == "__main__":
    if "--stop" in sys.argv:
        stop()
    else:
        start()
