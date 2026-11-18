"""
UI Visual Verification Script using Chrome DevTools Protocol (CDP) via Edge Headless.
Captures real, rendered screenshots of the React application at desktop and mobile widths.
"""
import os
import sys
import time
import json
import base64
import shutil
import asyncio
import tempfile
import subprocess
import urllib.request
from pathlib import Path
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = PROJECT_ROOT / "docs" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_EXE):
    EDGE_EXE = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

ARTIFACT_DIR = Path(r"C:\Users\priya\.gemini\antigravity\brain\8770fdf4-a7cd-478a-b39a-2899ca7cf43e")

async def cdp_capture(ws_url: str, url: str, width: int, height: int, mobile: bool, out_path: Path):
    async with websockets.connect(ws_url, max_size=30 * 1024 * 1024) as ws:
        # Enable Page & Runtime
        await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
        await ws.recv()
        await ws.send(json.dumps({"id": 2, "method": "Runtime.enable"}))
        await ws.recv()

        # Set viewport
        await ws.send(json.dumps({
            "id": 3,
            "method": "Emulation.setDeviceMetricsOverride",
            "params": {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": mobile,
            }
        }))
        await ws.recv()

        # Navigate
        await ws.send(json.dumps({
            "id": 4,
            "method": "Page.navigate",
            "params": {"url": url}
        }))
        await ws.recv()

        # Wait for React to mount, fetch initial data, and render
        print(f"      Waiting 7s for DOM rendering at {width}x{height}...")
        await asyncio.sleep(7.0)

        # Capture screenshot
        await ws.send(json.dumps({
            "id": 5,
            "method": "Page.captureScreenshot",
            "params": {"format": "png", "captureBeyondViewport": False}
        }))

        # Wait for screenshot response
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data.get("id") == 5:
                b64_png = data["result"]["data"]
                png_bytes = base64.b64decode(b64_png)
                out_path.write_bytes(png_bytes)
                print(f"   [OK] Captured screenshot: {out_path.name} ({len(png_bytes):,} bytes)")
                break

def main():
    print("=" * 60)
    print("STARTING CDP-BASED UI VISUAL VERIFICATION")
    print("=" * 60)

    # 1. Start backend server
    print("[1/5] Starting FastAPI + SPA server on port 8000...")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", "8000"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    edge_proc = None
    temp_dir = tempfile.mkdtemp(prefix="edge_cdp_")
    try:
        # 2. Wait for server readiness
        print("[2/5] Waiting for server on http://localhost:8000...")
        ready = False
        for i in range(25):
            try:
                with urllib.request.urlopen("http://localhost:8000/api/health", timeout=2) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(1)

        if not ready:
            print("ERROR: Backend server failed to start within 25s.")
            return 1
        print("   [OK] Backend server is active and healthy.")

        # 3. Start Edge with CDP and dedicated user-data-dir
        print(f"[3/5] Starting headless Edge with CDP on port 9222 (profile: {temp_dir})...")
        cmd_edge = [
            EDGE_EXE,
            "--headless=new",
            "--disable-gpu",
            "--remote-debugging-port=9222",
            f"--user-data-dir={temp_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
        edge_proc = subprocess.Popen(cmd_edge, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        ws_url = None
        for i in range(15):
            try:
                with urllib.request.urlopen("http://localhost:9222/json", timeout=2) as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                    if targets and "webSocketDebuggerUrl" in targets[0]:
                        ws_url = targets[0]["webSocketDebuggerUrl"]
                        break
            except Exception:
                time.sleep(1)

        if not ws_url:
            print("ERROR: Failed to obtain Edge CDP websocket URL.")
            return 1
        print(f"   [OK] Connected to Edge CDP target: {ws_url}")

        # 4. Capture Desktop & Mobile Screenshots
        desktop_img = SCREENSHOT_DIR / "discovery_desktop.png"
        mobile_img = SCREENSHOT_DIR / "discovery_mobile.png"

        print("[4/5] Capturing Desktop view (1440x900)...")
        asyncio.run(cdp_capture(ws_url, "http://localhost:8000/#research-discovery", 1440, 900, False, desktop_img))

        print("[4/5] Capturing Mobile view (390x844)...")
        asyncio.run(cdp_capture(ws_url, "http://localhost:8000/#research-discovery", 390, 844, True, mobile_img))

        # 5. Check & copy to artifact dir
        if desktop_img.exists() and mobile_img.exists() and desktop_img.stat().st_size > 15000:
            print(f"[5/5] Visual verification successful:")
            print(f"   - Desktop: {desktop_img.name} ({desktop_img.stat().st_size:,} bytes)")
            print(f"   - Mobile:  {mobile_img.name} ({mobile_img.stat().st_size:,} bytes)")
            
            if ARTIFACT_DIR.exists():
                shutil.copy(desktop_img, ARTIFACT_DIR / "discovery_desktop.png")
                shutil.copy(mobile_img, ARTIFACT_DIR / "discovery_mobile.png")
                print("   - Copied screenshots to brain artifact directory.")
            return 0
        else:
            print(f"ERROR: Screenshot size unexpected: desktop={desktop_img.stat().st_size if desktop_img.exists() else 0}b, mobile={mobile_img.stat().st_size if mobile_img.exists() else 0}b")
            return 1

    finally:
        print("Cleaning up Edge and backend processes...")
        if edge_proc:
            edge_proc.terminate()
            try:
                edge_proc.wait(timeout=3)
            except Exception:
                edge_proc.kill()
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=3)
        except Exception:
            backend_proc.kill()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        print("Harness finished.")

if __name__ == "__main__":
    sys.exit(main())
