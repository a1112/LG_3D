import asyncio
import sys
from pathlib import Path

from starlette.websockets import WebSocketDisconnect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = PROJECT_ROOT / "app" / "Server"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
if str(PROJECT_ROOT / "app") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "app"))

from app.Server.api import ApiDataServer


class DisconnectingWebSocket:
    def __init__(self):
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def receive_json(self):
        raise WebSocketDisconnect(1005)


def test_height_point_websocket_disconnect_is_clean():
    websocket = DisconnectingWebSocket()

    asyncio.run(ApiDataServer.ws_height_point(websocket))

    assert websocket.accepted
