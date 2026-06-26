import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/events", tags=["Enterprise Gateway"])

class EventSubscriptionManager:
    """
    Manages WebSocket subscriptions to Domain Events.
    Avoids streaming the firehose to every client.
    """
    def __init__(self):
        self.active_connections: list[dict] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append({
            "ws": websocket,
            "subscriptions": []
        })

    def subscribe(self, websocket: WebSocket, events: list[str]):
        for conn in self.active_connections:
            if conn["ws"] == websocket:
                conn["subscriptions"].extend(events)

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [c for c in self.active_connections if c["ws"] != websocket]

    async def broadcast(self, event_type: str, payload: dict):
        for connection in self.active_connections:
            if event_type in connection["subscriptions"]:
                await connection["ws"].send_json({"type": event_type, "payload": payload})

manager = EventSubscriptionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("action") == "subscribe":
                events = message.get("events", [])
                manager.subscribe(websocket, events)
                await websocket.send_json({"status": "subscribed", "events": events})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
