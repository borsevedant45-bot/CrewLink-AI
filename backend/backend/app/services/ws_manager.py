"""Doc #5 §3.1 — WebSocket connection manager for incident push.

Manages per-channel connections and broadcasts events to all subscribers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("crewlink.ws")


class ConnectionManager:
    """Bidirectional WS manager keyed on channel name.

    Thread-safe for single-process ASGI (uvicorn with one worker process).
    For multi-process deployments, replace with Redis pub/sub.
    """

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {}

    def connect(self, channel: str, websocket: WebSocket) -> None:
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        channel_ws = self._channels.get(channel)
        if channel_ws:
            channel_ws.discard(websocket)
            if not channel_ws:
                del self._channels[channel]

    async def broadcast(
        self,
        channel: str,
        event: str,
        data: dict[str, Any],
    ) -> None:
        from datetime import UTC, datetime
        payload = json.dumps({
            "event": event,
            "data": data,
            "emitted_at": datetime.now(UTC).isoformat(),
        })
        channel_ws = self._channels.get(channel, set())
        stale: list[WebSocket] = []
        for ws in channel_ws:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(channel, ws)


# Module-level singleton
manager = ConnectionManager()
