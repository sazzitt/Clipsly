import asyncio
from pathlib import Path
import shutil
import subprocess
import sys
import time

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from httpx import ASGITransport, AsyncClient

from backend.app.core.config import settings
from backend.app.main import app


async def verify():
    print("--- Starting Phase 12 Real Video Ingestion Verification ---")
    temp_dir = Path("data/temp_verify")
    temp_dir.mkdir(parents=True, exist_ok=True)
    sample_video = temp_dir / "e2e_verify.mp4"

    cmd = [
        "ffmpeg", "-v", "error",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=640x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
        "-c:v", "libx264", "-c:a", "aac",
        "-y", str(sample_video)
    ]
    subprocess.run(cmd, check=True)
    file_size = sample_video.stat().st_size
    print(f"Created test video: {sample_video} ({file_size} bytes)")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # 1. Test real upload with duration check disabled
        settings.ENFORCE_DURATION_LIMITS = False
        t0 = time.perf_counter()
        with open(sample_video, "rb") as f:
            files = {"file": ("E2E_Test_Podcast.mp4", f, "video/mp4")}
            res = await client.post("/api/v1/videos/upload", files=files)
        elapsed = time.perf_counter() - t0

        assert res.status_code == 201, f"Upload failed: {res.text}"
        video_data = res.json()
        print(f"Upload succeeded in {elapsed*1000:.1f}ms!")
        print(f"Ingested Video ID: {video_data['id']}")
        print(f"Storage Filename: {video_data['filename']}")
        print(f"Extracted Specs: {video_data['width']}x{video_data['height']} @ {video_data['fps']}fps, {video_data['duration_seconds']}s, {video_data['video_codec']}/{video_data['audio_codec']}")

        # 2. Verify on SSD
        ssd_path = settings.UPLOAD_DIR / video_data["filename"]
        assert ssd_path.exists(), f"File missing on SSD: {ssd_path}"
        print(f"SSD file verified at {ssd_path} ({ssd_path.stat().st_size} bytes)")

        # 3. Verify in Video Library
        lib_res = await client.get("/api/v1/videos")
        assert lib_res.status_code == 200
        items = lib_res.json()["items"]
        found = any(item["id"] == video_data["id"] for item in items)
        assert found, "Uploaded video not found in library!"
        print("Video verified in Video Library list!")

        # 4. Verify in Video Details
        detail_res = await client.get(f"/api/v1/videos/{video_data['id']}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["file_exists"] is True
        print(f"Video Details verified! Child jobs count: {detail['processing_jobs_count']}, clips count: {detail['clips_count']}")

        # 5. Clean up uploaded video
        del_res = await client.delete(f"/api/v1/videos/{video_data['id']}?purge_files=true")
        assert del_res.status_code == 200
        assert not ssd_path.exists()
        print("Cleaned up test video from DB and SSD successfully.")

    shutil.rmtree(temp_dir)
    print("--- Verification Complete: All Ingestion Steps Verified! ---")


if __name__ == "__main__":
    asyncio.run(verify())
