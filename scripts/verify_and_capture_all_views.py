"""
Harness to capture screenshots and perform automated visual/UX inspections of all primary views.
Inspired by Novyte AI's clean materials research SaaS layout.
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

VIEWS = [
    {
        "name": "dashboard",
        "hash": "#dashboard",
        "title": "Project Command Center",
        "check_table": True
    },
    {
        "name": "materials_designer",
        "hash": "#materials-designer",
        "title": "Materials Designer Studio",
        "check_table": False
    },
    {
        "name": "property_prediction",
        "hash": "#property-prediction",
        "title": "Property Prediction ML",
        "check_table": False
    },
    {
        "name": "research_discovery",
        "hash": "#research-discovery",
        "title": "Research Discovery Studio",
        "check_table": False
    },
    {
        "name": "literature_intelligence",
        "hash": "#literature-intelligence",
        "title": "Literature Extraction & Evidence Review",
        "check_table": True
    }
]

async def cdp_inspect_and_capture(ws_url: str, view_info: dict, out_path: Path):
    async with websockets.connect(ws_url, max_size=40 * 1024 * 1024) as ws:
        msg_id = 1
        
        async def send_cmd(method, params=None):
            nonlocal msg_id
            curr_id = msg_id
            msg_id += 1
            payload = {"id": curr_id, "method": method}
            if params:
                payload["params"] = params
            await ws.send(json.dumps(payload))
            while True:
                res = json.loads(await ws.recv())
                if res.get("id") == curr_id:
                    return res.get("result", {})

        await send_cmd("Page.enable")
        await send_cmd("Runtime.enable")

        # Desktop Viewport 1440x900
        await send_cmd("Emulation.setDeviceMetricsOverride", {
            "width": 1440,
            "height": 900,
            "deviceScaleFactor": 1,
            "mobile": False,
        })

        # Navigate
        nav_url = f"http://127.0.0.1:8008/{view_info['hash']}"
        await send_cmd("Page.navigate", {"url": nav_url})

        # Wait for React to render and API requests to settle
        print(f"      Waiting 5s for view '{view_info['name']}' to render...")
        await asyncio.sleep(5.0)

        # DOM inspection script
        eval_js = """
        (() => {
            const docWidth = document.documentElement.clientWidth;
            const docScroll = document.documentElement.scrollWidth;
            const tables = Array.from(document.querySelectorAll('.data-table, table'));
            const tableReports = tables.map((t, idx) => {
                const parent = t.parentElement;
                return {
                    tableIndex: idx,
                    clientWidth: t.clientWidth,
                    scrollWidth: t.scrollWidth,
                    parentClientWidth: parent ? parent.clientWidth : 0,
                    parentScrollWidth: parent ? parent.scrollWidth : 0,
                    hasHorizontalScroll: (t.scrollWidth > t.clientWidth + 2) || (parent && parent.scrollWidth > parent.clientWidth + 2)
                };
            });
            const bodyBg = window.getComputedStyle(document.body).backgroundColor;
            const textColors = Array.from(document.querySelectorAll('h1, h2, h3, h4, p, span, th, td'))
                .slice(0, 30)
                .map(el => window.getComputedStyle(el).color);

            return {
                docClientWidth: docWidth,
                docScrollWidth: docScroll,
                hasPageHorizontalScroll: docScroll > docWidth,
                tableCount: tables.length,
                tableReports: tableReports,
                bodyBg: bodyBg,
                sampleTextColors: textColors.slice(0, 10)
            };
        })()
        """
        eval_res = await send_cmd("Runtime.evaluate", {
            "expression": eval_js,
            "returnByValue": True
        })

        dom_data = eval_res.get("result", {}).get("value", {})
        print(f"      DOM Diagnostics for '{view_info['name']}':")
        print(f"         - Page Client vs Scroll Width: {dom_data.get('docClientWidth')}px vs {dom_data.get('docScrollWidth')}px (Scroll: {dom_data.get('hasPageHorizontalScroll')})")
        print(f"         - Tables detected: {dom_data.get('tableCount')}")
        for tr in dom_data.get('tableReports', []):
            print(f"           * Table #{tr['tableIndex']}: width {tr['clientWidth']}px, scroll {tr['scrollWidth']}px (Overflows: {tr['hasHorizontalScroll']})")

        # Capture screenshot
        cap_res = await send_cmd("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": False
        })
        b64_png = cap_res.get("data")
        if b64_png:
            png_bytes = base64.b64decode(b64_png)
            out_path.write_bytes(png_bytes)
            print(f"      [OK] Saved screenshot: {out_path.name} ({len(png_bytes):,} bytes)")
        
        return dom_data

def main():
    print("=" * 65)
    print("AUTOMATED VISUAL & UX INSPECTION (Novyte AI Polish Pass)")
    print("=" * 65)

    print("[1/4] Spawning FastAPI backend server on 127.0.0.1:8008...")
    server_log = tempfile.NamedTemporaryFile("w+", delete=False, suffix="_uvicorn.log")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8008"],
        cwd=str(PROJECT_ROOT),
        stdout=server_log,
        stderr=server_log,
    )

    edge_proc = None
    temp_dir = tempfile.mkdtemp(prefix="edge_audit_")

    try:
        # Wait for server
        ready = False
        for i in range(40):
            if backend_proc.poll() is not None:
                print(f"Backend exited early with code {backend_proc.returncode}!")
                server_log.seek(0)
                print(server_log.read())
                return 1
            try:
                with urllib.request.urlopen("http://127.0.0.1:8008/api/health", timeout=2) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(1)

        if not ready:
            print("ERROR: Backend server failed to start within 40 seconds.")
            server_log.seek(0)
            print("Server log output:")
            print(server_log.read())
            return 1
        print("   [OK] Backend server active and healthy on 127.0.0.1:8008.")

        # Start Edge
        print(f"[2/4] Starting Edge headless on port 9222...")
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
        for _ in range(15):
            try:
                with urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=2) as resp:
                    targets = json.loads(resp.read().decode("utf-8"))
                    if targets and "webSocketDebuggerUrl" in targets[0]:
                        ws_url = targets[0]["webSocketDebuggerUrl"]
                        break
            except Exception:
                time.sleep(1)

        if not ws_url:
            print("ERROR: Edge CDP websocket not available.")
            return 1
        print(f"   [OK] Connected to Edge CDP target.")

        # Run inspect & captures
        print("[3/4] Inspecting and capturing views...")
        all_reports = {}
        for v in VIEWS:
            img_path = SCREENSHOT_DIR / f"{v['name']}_desktop.png"
            report = asyncio.run(cdp_inspect_and_capture(ws_url, v, img_path))
            all_reports[v['name']] = report
            if ARTIFACT_DIR.exists() and img_path.exists():
                shutil.copy(img_path, ARTIFACT_DIR / img_path.name)

        print("[4/4] Verification Summary:")
        all_passed = True
        for name, rep in all_reports.items():
            scroll_ok = not rep.get("hasPageHorizontalScroll", False)
            table_scroll_ok = all(not t.get("hasHorizontalScroll", False) for t in rep.get("tableReports", []))
            print(f"   - {name}: Page No-Scroll={scroll_ok}, Tables No-Scroll={table_scroll_ok}")
            if not scroll_ok or not table_scroll_ok:
                all_passed = False

        print(f"\nAudit complete. All passed: {all_passed}")
        return 0

    finally:
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
        try:
            server_log.close()
            os.unlink(server_log.name)
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(main())
