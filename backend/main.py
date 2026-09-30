from pathlib import Path

from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import template_manager as tm
import scanner

app = FastAPI(title="Nuclei GUI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ---------- Template catalog ----------

@app.get("/api/templates")
def get_templates(search: str = "", severity: str = "", tag: str = "", source: str = ""):
    return {
        "templates": tm.list_templates(search=search, severity=severity, tag=tag, source=source),
        "tags": tm.all_tags(),
    }


@app.post("/api/templates/sync")
def sync_templates():
    """Clones/updates the official nuclei-templates repo from GitHub."""
    return tm.sync_official_templates()


@app.post("/api/templates/upload")
async def upload_template(file: UploadFile = File(...)):
    content = await file.read()
    return tm.save_custom_template(file.filename, content)


@app.get("/api/nuclei/status")
def nuclei_status():
    return {"nuclei_installed": scanner.nuclei_available()}


# ---------- Scanning ----------

@app.get("/api/scan/{scan_id}/results")
def get_scan_results(scan_id: str):
    return {"scan_id": scan_id, "findings": scanner.load_scan_results(scan_id)}


@app.websocket("/ws/scan")
async def ws_scan(websocket: WebSocket):
    """
    Client sends: {"target": "https://example.com", "template_ids": ["id1", "id2"]}
    Server streams: {"event": "started"|"finding"|"log"|"finished"|"error", ...}
    """
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        target = payload.get("target", "").strip()
        template_ids = payload.get("template_ids", [])

        if not target:
            await websocket.send_json({"event": "error", "message": "No target provided."})
            await websocket.close()
            return

        template_paths = tm.get_template_paths(template_ids)

        async for event in scanner.run_scan(target, template_paths):
            await websocket.send_json(event)

        await websocket.close()
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
