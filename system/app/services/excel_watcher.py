from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any


class ExcelDashboardWatcher:
    def __init__(self, service: Any, poll_interval: float = 2.0) -> None:
        self.service = service
        self.poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._clients: set[Any] = set()
        self._snapshot: dict[str, Any] | None = None
        self._last_mtime: float | None = None
        self._last_signature: tuple[int, int] | None = None
        self._last_error: str | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        await self.refresh(force=True)
        self._task = asyncio.create_task(self._watch_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def current_snapshot(self) -> dict[str, Any] | None:
        async with self._lock:
            return self._snapshot

    async def current_status(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "ready": self._snapshot is not None,
                "last_error": self._last_error,
                "last_mtime": self._last_mtime,
                "connected_clients": len(self._clients),
                "source_file": str(self.service.excel_path),
            }

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        snapshot = await self.current_snapshot()
        if snapshot is not None:
            await websocket.send_json({"type": "dashboard.snapshot", "payload": snapshot})

    async def disconnect(self, websocket: Any) -> None:
        self._clients.discard(websocket)

    async def refresh(self, force: bool = False) -> None:
        excel_path = self.service.excel_path
        if excel_path.exists():
            stats = excel_path.stat()
            current_mtime = stats.st_mtime
            current_signature = (stats.st_mtime_ns, stats.st_size)
        else:
            current_mtime = None
            current_signature = None

        if not force and current_signature == self._last_signature:
            return

        try:
            snapshot = self.service.load_snapshot()
        except Exception as exc:  # pragma: no cover
            async with self._lock:
                self._last_error = str(exc)
            await self._broadcast(
                {
                    "type": "dashboard.error",
                    "payload": {
                        "message": str(exc),
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            )
            return

        async with self._lock:
            self._snapshot = snapshot
            self._last_error = None
            self._last_mtime = current_mtime
            self._last_signature = current_signature

        await self._broadcast({"type": "dashboard.updated", "payload": snapshot})

    async def _watch_loop(self) -> None:
        while True:
            await asyncio.sleep(self.poll_interval)
            await self.refresh()

    async def _broadcast(self, message: dict[str, Any]) -> None:
        stale_clients: list[Any] = []
        for client in list(self._clients):
            try:
                await client.send_json(message)
            except Exception:
                stale_clients.append(client)
        for client in stale_clients:
            self._clients.discard(client)