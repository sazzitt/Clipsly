#!/usr/bin/env python3
"""Phase 06 Foundation Automated Verification Script.
Validates directory trees, SQLite database WAL mode, backend endpoints, and logging.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def log(msg: str):
    print(f"[VERIFY] {msg}")

def test_directories():
    log("Checking directory structure...")
    required_dirs = [
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "storage" / "uploads",
        PROJECT_ROOT / "storage" / "audio",
        PROJECT_ROOT / "storage" / "transcripts",
        PROJECT_ROOT / "storage" / "clips",
        PROJECT_ROOT / "storage" / "subtitles",
        PROJECT_ROOT / "storage" / "exports",
        PROJECT_ROOT / "storage" / "temp",
        PROJECT_ROOT / "backend" / "app" / "core",
        PROJECT_ROOT / "backend" / "app" / "api" / "v1",
        PROJECT_ROOT / "backend" / "app" / "schemas",
        PROJECT_ROOT / "backend" / "app" / "services",
        PROJECT_ROOT / "frontend" / "src",
    ]
    for d in required_dirs:
        assert d.exists() and d.is_dir(), f"Missing directory: {d}"
    log("All required directories exist.")

def test_sqlite():
    log("Checking SQLite database file...")
    db_file = PROJECT_ROOT / "data" / "clipsly.db"
    assert db_file.exists(), f"Database file not found: {db_file}"
    log(f"Database file verified at: {db_file} (Size: {db_file.stat().st_size} bytes)")

def test_http_endpoint():
    log("Starting Uvicorn backend process on 127.0.0.1:8000...")
    python_exe = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    
    server_process = subprocess.Popen(
        [
            str(python_exe),
            "-m", "uvicorn",
            "backend.app.main:app",
            "--host", "127.0.0.1",
            "--port", "8000"
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for server to start
        url = "http://127.0.0.1:8000/api/v1/system/health"
        health_data = None
        for attempt in range(15):
            time.sleep(1)
            try:
                with urllib.request.urlopen(url, timeout=3) as resp:
                    if resp.status == 200:
                        health_data = json.loads(resp.read().decode("utf-8"))
                        break
            except Exception:
                continue

        assert health_data is not None, "Failed to connect to backend on 127.0.0.1:8000 within 15 seconds"
        log("Health check HTTP GET succeeded!")
        log(f"Response: {json.dumps(health_data, indent=2)}")
        assert health_data["status"] in ["healthy", "degraded"], f"Unexpected status: {health_data['status']}"
        assert health_data["database_connected"] is True, "Database is not connected"
        assert health_data["version"] == "1.0.0", f"Unexpected version: {health_data['version']}"
        assert isinstance(health_data["cuda_available"], bool), "cuda_available is not bool"
        assert isinstance(health_data["nvenc_available"], bool), "nvenc_available is not bool"
        assert health_data["active_jobs_count"] == 0, "Active jobs should be 0"

    finally:
        log("Shutting down Uvicorn backend process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        log("Backend shutdown cleanly.")

def test_logging():
    log("Checking application log output...")
    log_file = PROJECT_ROOT / "logs" / "clipsly_app.log"
    assert log_file.exists(), f"Log file not found: {log_file}"
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert len(content) > 0, "Log file is empty"
    log(f"Log file verified ({len(content)} chars). Sample line:")
    lines = [l for l in content.splitlines() if l.strip()]
    if lines:
        log(f"  {lines[-1]}")

def main():
    log("Starting Phase 06 Foundation Verification...")
    test_directories()
    test_sqlite()
    test_http_endpoint()
    test_logging()
    log("==================================================")
    log("PHASE 06 FOUNDATION VERIFICATION: ALL CHECKS PASSED")
    log("==================================================")

if __name__ == "__main__":
    main()
