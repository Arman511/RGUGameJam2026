from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from websockets.exceptions import ConnectionClosed
from websockets.sync.client import ClientConnection, connect

from elemental_game.config import ELEMENTAL_KEEP_API_BASE_URL

PROTOCOL_VERSION = 1
MATCH_PATH = "/api/v1/matches"


class MultiplayerError(RuntimeError):
    """Raised when a multiplayer operation cannot be completed."""


class MultiplayerClient:
    """Manage one room connection and exchange validated match messages."""

    def __init__(self, connection: ClientConnection, player_name: str) -> None:
        self.connection = connection
        self.player_name = player_name
        self.room_code: str | None = None
        self.player_id: str | None = None
        self.opponent_name = "Opponent"
        self.queue_position: int | None = None
        self.closed = False

    @classmethod
    def host(
        cls, player_name: str, *, base_url: str = ELEMENTAL_KEEP_API_BASE_URL
    ) -> MultiplayerClient:
        client = cls._open(player_name, "host", {}, base_url=base_url)
        response = client._receive_handshake()
        if response.get("type") == "queued":
            client.queue_position = response["payload"].get("position")
        elif response.get("type") == "room_created":
            client._set_room(response["payload"])
        else:
            client.close()
            raise MultiplayerError(client._server_error(response))
        return client

    @classmethod
    def join(
        cls,
        player_name: str,
        room_code: str,
        *,
        base_url: str = ELEMENTAL_KEEP_API_BASE_URL,
    ) -> MultiplayerClient:
        client = cls._open(
            player_name,
            "join",
            {"room_code": room_code},
            base_url=base_url,
        )
        response = client._receive_handshake()
        if response.get("type") != "match_started":
            client.close()
            raise MultiplayerError(client._server_error(response))
        client._set_match(response["payload"])
        return client

    @classmethod
    def _open(
        cls,
        player_name: str,
        handshake_type: str,
        payload: dict[str, Any],
        *,
        base_url: str = ELEMENTAL_KEEP_API_BASE_URL,
    ) -> MultiplayerClient:
        parts = urlsplit(base_url)
        scheme = "wss" if parts.scheme == "https" else "ws"
        uri = urlunsplit((scheme, parts.netloc, MATCH_PATH, "", ""))
        try:
            connection = connect(uri, open_timeout=5, close_timeout=1, max_size=65536)
        except (OSError, TimeoutError) as error:
            raise MultiplayerError(
                f"Could not connect to the game server: {error}"
            ) from error
        client = cls(connection, player_name)
        client._send(
            handshake_type,
            {"player_name": player_name, **payload},
        )
        return client

    def _send(self, message_type: str, payload: dict[str, Any]) -> None:
        if self.closed:
            raise MultiplayerError("The multiplayer connection is closed.")
        try:
            self.connection.send(
                json.dumps(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": message_type,
                        "payload": payload,
                    }
                )
            )
        except ConnectionClosed as error:
            self.closed = True
            raise MultiplayerError(
                "The connection to the game server was lost."
            ) from error

    def _receive_handshake(self) -> dict[str, Any]:
        try:
            response = json.loads(self.connection.recv(timeout=5))
        except TimeoutError as error:
            self.close()
            raise MultiplayerError(
                "The game server did not respond in time."
            ) from error
        except (ConnectionClosed, json.JSONDecodeError) as error:
            self.close()
            raise MultiplayerError(
                "The game server returned an invalid response."
            ) from error
        if (
            not isinstance(response, dict)
            or response.get("version") != PROTOCOL_VERSION
            or not isinstance(response.get("payload"), dict)
        ):
            self.close()
            raise MultiplayerError("The game server returned an invalid response.")
        return response

    @staticmethod
    def _server_error(response: dict[str, Any]) -> str:
        payload = response.get("payload", {})
        if isinstance(payload, dict) and isinstance(payload.get("message"), str):
            return payload["message"]
        return "The game server returned an unexpected response."

    def _set_match(self, payload: dict[str, Any]) -> None:
        self.room_code = payload["room_code"]
        self.player_id = payload["player_id"]
        self.opponent_name = payload.get("opponent_name", "Opponent")

    def _set_room(self, payload: dict[str, Any]) -> None:
        self.room_code = payload["room_code"]
        self.player_id = payload["player_id"]
        self.queue_position = None

    def poll(self) -> list[dict[str, Any]]:
        if self.closed:
            return []
        messages = []
        for _ in range(10):
            try:
                raw_message = self.connection.recv(timeout=0)
            except TimeoutError:
                break
            except ConnectionClosed:
                self.closed = True
                messages.append(
                    {
                        "version": PROTOCOL_VERSION,
                        "type": "opponent_disconnected",
                        "payload": {},
                    }
                )
                break
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError as error:
                raise MultiplayerError("The game server sent invalid JSON.") from error
            if (
                not isinstance(message, dict)
                or message.get("version") != PROTOCOL_VERSION
                or not isinstance(message.get("type"), str)
                or not isinstance(message.get("payload"), dict)
            ):
                raise MultiplayerError("The game server sent an invalid message.")
            if message["type"] == "match_started":
                self._set_match(message["payload"])
            elif message["type"] == "room_created":
                self._set_room(message["payload"])
            elif message["type"] == "queue_status":
                self.queue_position = message["payload"].get("position")
            messages.append(message)
        return messages

    def send_action(self, action: str, element: str | None = None) -> None:
        self._send("action", {"action": action, "element": element})

    def send_wave(self, wave: int) -> None:
        self._send("state_update", {"wave": wave})

    def end_match(self) -> None:
        if not self.closed:
            self._send("match_ended", {"result": "defeat"})

    def close(self) -> None:
        if self.closed:
            return
        try:
            self.connection.close()
        finally:
            self.closed = True
