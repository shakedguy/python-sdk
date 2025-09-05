import asyncio
from typing import Annotated, Any, Optional, TypedDict, Union

from fastapi import Depends, WebSocket
from fastapi.websockets import WebSocketState
from loguru import logger
from pydantic import BaseModel

from ..utils import Crypto, memoize
from ..utils.decorators import singleton


class SocketRequest(TypedDict):
    req_id: str
    event: str
    data: Optional[Union[str, bytes, dict[str, Any]]]


@singleton
class ConnectionManager(object):
    def __init__(self) -> None:
        self.active_connections: dict[Union[str, int], WebSocket] = {}

        self.pending_requests: dict[Union[str, int], asyncio.Future[Any]] = {}
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(
            self, ws_client: WebSocket, client_id: Optional[Union[str, int]] = None
    ) -> None:
        await ws_client.accept()
        client_id = client_id or ws_client.client.host
        self.active_connections[client_id] = ws_client

    def disconnect(
            self, ws_client: WebSocket, client_id: Optional[Union[str, int]] = None
    ) -> None:
        client_id = client_id or ws_client.client.host
        self.active_connections.pop(client_id, None)

    @classmethod
    async def send_personal_message(
            cls,
            ws_client: WebSocket,
            message: Union[Union[str, bytes, dict[str, Any]], SocketRequest, BaseModel],
    ) -> None:

        message = message.model_dump() if isinstance(message, BaseModel) else message
        if isinstance(message, dict):
            await ws_client.send_json(data=message)
        elif isinstance(message, bytes):
            await ws_client.send_bytes(data=message)
        else:
            await ws_client.send_text(data=message)

    async def broadcast(self, message: Union[str, bytes, dict[str, Any], BaseModel]) -> None:
        if not self.active_connections:
            return
        message = message.model_dump() if isinstance(message, BaseModel) else message
        connections = [
            conn
            for conn in self.active_connections.values()
            if conn.state == WebSocketState.CONNECTED
        ]
        await asyncio.gather(
            *[
                self.send_personal_message(ws_client=conn, message=message)
                for conn in connections
            ]
        )

    def get_client_id(self, client: WebSocket) -> Optional[int | str]:
        return next(
            (
                client_id
                for client_id, connection in self.active_connections.items()
                if connection == client
            ),
            None,
        )

    async def join_room(self, room: str, client: WebSocket) -> None:
        if room not in self.rooms:
            self.rooms[room] = []
        self.rooms[room].append(client)
        await client.accept()

    async def leave_room(self, room: str, client: WebSocket) -> None:
        self.rooms[room].remove(client)
        await client.close()

    async def broadcast_to_room(self, room: str, message: str) -> None:
        if room not in self.rooms:
            return
        await asyncio.gather(
            *[client.send_text(message) for client in self.rooms[room]]
        )

    async def __request_handler(self, sid: Union[str, int], req: SocketRequest) -> Any:
        if sid not in self.active_connections:
            logger.error(f"Client {sid} not found in active connections")
            return None
        req_id = req["req_id"]
        client = self.active_connections[sid]
        self.pending_requests[req_id] = asyncio.Future()
        logger.debug(f"Sending request to client {sid}, message: {req}")
        await self.send_personal_message(ws_client=client, message=req)
        response = await self.pending_requests[req_id]
        logger.debug(f"Response from client {sid} to request {req_id}: {response}")
        await self.pending_requests.pop(req_id, None)
        return response.get("data", None) if "data" in response else response

    async def send_request(
            self,
            sid: Union[str, int],
            event: str,
            payload: Optional[Union[str, bytes, dict[str, Any]]] = None,
    ) -> Any:
        if sid not in self.active_connections:
            logger.error(f"Client {sid} not found in active connections")
            return None

        payload = payload or {}

        req: SocketRequest = {
            "event": event,
            "req_id": str(Crypto.uuidv7()),
            "data": payload,
        }
        return await self.__request_handler(sid=sid, req=req)

    async def broadcast_request(
            self, event: str, payload: Optional[Union[str, dict[str, Any]]] = None
    ) -> list[Any]:
        req_id: str = str(Crypto.uuidv7())
        self.pending_requests[req_id] = asyncio.Future()
        message: SocketRequest = {
            "event": event,
            "req_id": str(Crypto.uuidv7()),
            "data": payload,
        }

        return await asyncio.gather(
            *[self.__request_handler(sid, message) for sid in self.active_connections]
        )

    async def close(self) -> None:
        await asyncio.gather(
            *[connection.close() for connection in self.active_connections.values()]
        )


@memoize
def create_connection_manager() -> ConnectionManager:
    return ConnectionManager()


WSDep = Annotated[ConnectionManager, Depends(create_connection_manager)]
