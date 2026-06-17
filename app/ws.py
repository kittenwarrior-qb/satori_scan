"""WebSocket manager — push kết quả quét realtime lên UI."""
import logging

from fastapi import WebSocket

log = logging.getLogger("satori.ws")


class WSManager:
    def __init__(self):
        self.conns: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.conns.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.conns:
            self.conns.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = WSManager()
