from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import EXCEL_FILE, STATIC_DIR
from app.services.dashboard_service import DashboardService
from app.services.excel_watcher import ExcelDashboardWatcher


dashboard_service = DashboardService(EXCEL_FILE)
dashboard_watcher = ExcelDashboardWatcher(dashboard_service)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await dashboard_watcher.start()
    yield
    await dashboard_watcher.stop()


app = FastAPI(
    title="Dashboard Bangchak",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
async def health() -> dict[str, object]:
    return await dashboard_watcher.current_status()


@app.get("/api/dashboard")
async def dashboard() -> dict[str, object]:
    snapshot = await dashboard_watcher.current_snapshot()
    if snapshot is None:
        snapshot = dashboard_service.load_snapshot()
    return snapshot


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket) -> None:
    await dashboard_watcher.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await dashboard_watcher.disconnect(websocket)
