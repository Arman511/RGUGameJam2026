from __future__ import annotations

import asyncio
import logging
import os
import secrets
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

PROTOCOL_VERSION = 1
ROOM_CODE_CHARACTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ELEMENTS = {"AIR", "EARTH", "FIRE", "ICE", "LIGHTNING", "WATER"}
MATCH_ACTIONS = {
    "extra_enemies",
    "tougher_enemies",
    "elemental_chance",
    "change_weather",
}
DEFAULT_MATCH_LIMIT = 100
DEFAULT_JOIN_TIMEOUT_SECONDS = 120.0

router = APIRouter()
logger = logging.getLogger(__name__)


@dataclass
class MatchRoom:
    code: str
    players: dict[str, WebSocket] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)
    started: bool = False
    expiry_task: asyncio.Task[None] | None = None


@dataclass
class QueuedHost:
    socket: WebSocket
    name: str
    promoted: asyncio.Event = field(default_factory=asyncio.Event)
    room: MatchRoom | None = None


class MatchManager:
    def __init__(
        self,
        room_limit: int | None = None,
        join_timeout_seconds: float | None = None,
    ) -> None:
        self.room_limit = (
            int(os.environ.get("ELEMENTAL_MATCH_LIMIT", DEFAULT_MATCH_LIMIT))
            if room_limit is None
            else room_limit
        )
        self.join_timeout_seconds = (
            float(
                os.environ.get(
                    "ELEMENTAL_MATCH_JOIN_TIMEOUT_SECONDS",
                    DEFAULT_JOIN_TIMEOUT_SECONDS,
                )
            )
            if join_timeout_seconds is None
            else join_timeout_seconds
        )
        if self.room_limit < 1:
            raise ValueError("ELEMENTAL_MATCH_LIMIT must be at least 1.")
        if self.join_timeout_seconds <= 0:
            raise ValueError("ELEMENTAL_MATCH_JOIN_TIMEOUT_SECONDS must be positive.")
        self.rooms: dict[str, MatchRoom] = {}
        self.queue: deque[QueuedHost] = deque()

    def _create_room(self, socket: WebSocket, name: str) -> MatchRoom:
        code = self._new_code()
        room = MatchRoom(
            code=code, players={"player1": socket}, names={"player1": name}
        )
        self.rooms[code] = room
        room.expiry_task = asyncio.create_task(self._expire_room(room))
        return room

    async def host_or_queue(
        self, socket: WebSocket, name: str
    ) -> MatchRoom | QueuedHost:
        if len(self.rooms) < self.room_limit:
            return self._create_room(socket, name)
        queued_host = QueuedHost(socket, name)
        self.queue.append(queued_host)
        await socket.send_json(
            {
                "version": PROTOCOL_VERSION,
                "type": "queued",
                "payload": {"position": len(self.queue)},
            }
        )
        return queued_host

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(ROOM_CODE_CHARACTERS) for _ in range(6))
            if code not in self.rooms:
                return code

    async def join_room(self, socket: WebSocket, code: str, name: str) -> MatchRoom:
        room = self.rooms.get(code)
        if room is None:
            raise ValueError("Room code not found.")
        if room.started or len(room.players) >= 2:
            raise ValueError("That room is already full.")

        room.players["player2"] = socket
        room.names["player2"] = name
        room.started = True
        if room.expiry_task is not None:
            room.expiry_task.cancel()
            room.expiry_task = None
        for player_id, player_socket in room.players.items():
            opponent_id = "player2" if player_id == "player1" else "player1"
            await player_socket.send_json(
                {
                    "version": PROTOCOL_VERSION,
                    "type": "match_started",
                    "payload": {
                        "room_code": room.code,
                        "player_id": player_id,
                        "opponent_name": room.names[opponent_id],
                    },
                }
            )
        return room

    async def wait_for_room(
        self, socket: WebSocket, queued_host: QueuedHost
    ) -> tuple[MatchRoom | None, Any | None]:
        while True:
            receive_task = asyncio.create_task(socket.receive_json())
            promoted_task = asyncio.create_task(queued_host.promoted.wait())
            done, _ = await asyncio.wait(
                (receive_task, promoted_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if promoted_task in done:
                if receive_task in done:
                    message = receive_task.result()
                    if isinstance(message, dict) and message.get("type") == "leave":
                        if queued_host.room is not None:
                            await self.disconnect(queued_host.room, "player1")
                        return None, None
                    return queued_host.room, message
                receive_task.cancel()
                with suppress(asyncio.CancelledError):
                    await receive_task
                return queued_host.room, None

            promoted_task.cancel()
            with suppress(asyncio.CancelledError):
                await promoted_task
            message = receive_task.result()
            if isinstance(message, dict) and message.get("type") == "leave":
                await self.cancel_queue(queued_host)
                return None, None
            await self._error(socket, "Please wait until a match slot is available.")

    async def cancel_queue(self, queued_host: QueuedHost) -> None:
        with suppress(ValueError):
            self.queue.remove(queued_host)
        for position, queued in enumerate(self.queue, start=1):
            try:
                await queued.socket.send_json(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "queue_status",
                        "payload": {"position": position},
                    }
                )
            except RuntimeError as error:
                logger.info("Could not update a queued host's position: %s", error)
                continue

    async def _expire_room(self, room: MatchRoom) -> None:
        await asyncio.sleep(self.join_timeout_seconds)
        if room.started or self.rooms.get(room.code) is not room:
            return
        host = room.players["player1"]
        try:
            await host.send_json(
                {
                    "version": PROTOCOL_VERSION,
                    "type": "room_expired",
                    "payload": {"message": "Room expired. No player joined."},
                }
            )
        except RuntimeError as error:
            logger.info(
                "Could not notify host for expired room %s: %s", room.code, error
            )
        self.rooms.pop(room.code, None)
        try:
            await host.close(code=1000)
        except RuntimeError as error:
            logger.info("Could not close expired room %s cleanly: %s", room.code, error)
        await self._promote_queued()

    async def _promote_queued(self) -> None:
        while self.queue and len(self.rooms) < self.room_limit:
            queued_host = self.queue.popleft()
            room = self._create_room(queued_host.socket, queued_host.name)
            try:
                await queued_host.socket.send_json(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "room_created",
                        "payload": {"room_code": room.code, "player_id": "player1"},
                    }
                )
            except RuntimeError as error:
                logger.info("Queued host disconnected during room promotion: %s", error)
                self.rooms.pop(room.code, None)
                if room.expiry_task is not None:
                    room.expiry_task.cancel()
                continue
            queued_host.room = room
            queued_host.promoted.set()
        for position, queued_host in enumerate(self.queue, start=1):
            try:
                await queued_host.socket.send_json(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "queue_status",
                        "payload": {"position": position},
                    }
                )
            except RuntimeError as error:
                logger.info("Could not update a queued host's position: %s", error)
                continue

    async def _remove_room(self, room: MatchRoom) -> None:
        if self.rooms.pop(room.code, None) is None:
            return
        if (
            room.expiry_task is not None
            and room.expiry_task is not asyncio.current_task()
        ):
            room.expiry_task.cancel()
        await self._promote_queued()

    async def handle_message(
        self, room: MatchRoom, player_id: str, message: Any
    ) -> bool:
        if (
            not isinstance(message, dict)
            or message.get("version") != PROTOCOL_VERSION
            or not isinstance(message.get("type"), str)
        ):
            await self._error(room.players[player_id], "Invalid protocol message.")
            return True

        message_type = message["type"]
        payload = message.get("payload", {})
        if not isinstance(payload, dict):
            await self._error(
                room.players[player_id], "Message payload must be an object."
            )
            return True

        if message_type == "action":
            action = payload.get("action")
            element = payload.get("element")
            if not isinstance(action, str) or action not in MATCH_ACTIONS:
                await self._error(
                    room.players[player_id], "Unknown multiplayer action."
                )
                return True
            if action in {"elemental_chance", "change_weather"} and (
                not isinstance(element, str) or element not in ELEMENTS
            ):
                await self._error(
                    room.players[player_id], "A valid element is required."
                )
                return True
            if action in {"extra_enemies", "tougher_enemies"} and element is not None:
                await self._error(
                    room.players[player_id], "This action does not use an element."
                )
                return True
            opponent_id = "player2" if player_id == "player1" else "player1"
            opponent = room.players.get(opponent_id)
            if opponent is None:
                await self._error(
                    room.players[player_id], "Your opponent is not connected."
                )
                return True
            await opponent.send_json(
                {
                    "version": PROTOCOL_VERSION,
                    "type": "opponent_action",
                    "payload": {"action": action, "element": element},
                }
            )
            await room.players[player_id].send_json(
                {
                    "version": PROTOCOL_VERSION,
                    "type": "action_accepted",
                    "payload": {"action": action},
                }
            )
        elif message_type == "state_update":
            wave = payload.get("wave")
            if not isinstance(wave, int) or wave < 0:
                await self._error(
                    room.players[player_id], "Wave must be a non-negative integer."
                )
                return True
            opponent_id = "player2" if player_id == "player1" else "player1"
            opponent = room.players.get(opponent_id)
            if opponent is not None:
                await opponent.send_json(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "opponent_state",
                        "payload": {"wave": wave},
                    }
                )
        elif message_type == "match_ended":
            if payload.get("result") != "defeat":
                await self._error(room.players[player_id], "Invalid match result.")
                return True
            opponent_id = "player2" if player_id == "player1" else "player1"
            for result_player, result in (
                (player_id, "defeat"),
                (opponent_id, "victory"),
            ):
                result_socket = room.players.get(result_player)
                if result_socket is not None:
                    await result_socket.send_json(
                        {
                            "version": PROTOCOL_VERSION,
                            "type": "match_ended",
                            "payload": {"result": result},
                        }
                    )
            await self._remove_room(room)
            return False
        elif message_type == "leave":
            return False
        else:
            await self._error(room.players[player_id], "Unknown message type.")
        return True

    @staticmethod
    async def _error(socket: WebSocket, message: str) -> None:
        await socket.send_json(
            {
                "version": PROTOCOL_VERSION,
                "type": "error",
                "payload": {"message": message},
            }
        )

    async def disconnect(self, room: MatchRoom, player_id: str) -> None:
        if self.rooms.get(room.code) is not room:
            return
        if (
            room.expiry_task is not None
            and room.expiry_task is not asyncio.current_task()
        ):
            room.expiry_task.cancel()
        opponent_id = "player2" if player_id == "player1" else "player1"
        opponent = room.players.get(opponent_id)
        if opponent is not None:
            try:
                await opponent.send_json(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "opponent_disconnected",
                        "payload": {},
                    }
                )
            except RuntimeError as error:
                logger.info("Could not notify opponent of disconnect: %s", error)
        await self._remove_room(room)


match_manager = MatchManager()


@router.get("/api/v1/matches/config")
def multiplayer_config() -> dict[str, float]:
    return {"join_timeout_seconds": match_manager.join_timeout_seconds}


@router.websocket("/api/v1/matches")
async def multiplayer_match(socket: WebSocket) -> None:
    await socket.accept()
    room: MatchRoom | None = None
    player_id: str | None = None
    queued_host: QueuedHost | None = None
    pending_message: Any | None = None
    try:
        request = await socket.receive_json()
        if (
            not isinstance(request, dict)
            or request.get("version") != PROTOCOL_VERSION
            or not isinstance(request.get("payload"), dict)
        ):
            await match_manager._error(socket, "Invalid handshake.")
            await socket.close(code=1008)
            return

        payload = request["payload"]
        name = payload.get("player_name", "Player")
        if not isinstance(name, str):
            name = "Player"
        name = name.strip()[:32] or "Player"
        if request.get("type") == "host":
            result = await match_manager.host_or_queue(socket, name)
            if isinstance(result, QueuedHost):
                queued_host = result
                room, pending_message = await match_manager.wait_for_room(
                    socket, queued_host
                )
                if room is None:
                    return
            else:
                room = result
                await socket.send_json(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "room_created",
                        "payload": {"room_code": room.code, "player_id": "player1"},
                    }
                )
            player_id = "player1"
        elif request.get("type") == "join":
            code = payload.get("room_code")
            if not isinstance(code, str):
                await match_manager._error(socket, "Enter a valid room code.")
                await socket.close(code=1008)
                return
            try:
                room = await match_manager.join_room(socket, code.strip().upper(), name)
            except ValueError as error:
                await match_manager._error(socket, str(error))
                await socket.close(code=1008)
                return
            player_id = "player2"
        else:
            await match_manager._error(socket, "Handshake type must be host or join.")
            await socket.close(code=1008)
            return

        while True:
            if pending_message is not None:
                message = pending_message
                pending_message = None
            else:
                message = await socket.receive_json()
            keep_open = await match_manager.handle_message(room, player_id, message)
            if not keep_open:
                if isinstance(message, dict) and message.get("type") == "leave":
                    await match_manager.disconnect(room, player_id)
                return
    except WebSocketDisconnect:
        if queued_host is not None and room is None:
            await match_manager.cancel_queue(queued_host)
        elif room is not None and player_id is not None:
            await match_manager.disconnect(room, player_id)
