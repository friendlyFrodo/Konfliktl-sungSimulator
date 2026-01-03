"""WebSocket Handler für Echtzeit-Kommunikation."""

import json
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional

from ..core.graph import simulator
from ..core.state import AgentConfig
from ..models.schemas import (
    StartSessionMessage,
    UserMessage,
    ContinueMessage,
    StopMessage,
    RequestEvaluationMessage,
    AgentMessageResponse,
    StreamingChunkResponse,
    WaitingForInputResponse,
    TypingResponse,
    SessionStartedResponse,
    ErrorResponse,
)


class ConnectionManager:
    """Verwaltet WebSocket-Verbindungen."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Verbindung akzeptieren und registrieren."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """Verbindung entfernen."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_json(self, client_id: str, data: dict):
        """JSON an einen Client senden."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)

    async def broadcast(self, data: dict):
        """An alle Clients senden."""
        for connection in self.active_connections.values():
            await connection.send_json(data)


manager = ConnectionManager()


async def handle_websocket_message(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Verarbeitet eingehende WebSocket-Nachrichten."""
    msg_type = message.get("type")

    try:
        if msg_type == "start_session":
            await handle_start_session(websocket, client_id, message)

        elif msg_type == "user_message":
            await handle_user_message(websocket, client_id, message)

        elif msg_type == "continue":
            await handle_continue(websocket, client_id, message)

        elif msg_type == "stop":
            await handle_stop(websocket, client_id, message)

        elif msg_type == "request_evaluation":
            await handle_request_evaluation(websocket, client_id, message)

        else:
            await websocket.send_json(
                ErrorResponse(message=f"Unknown message type: {msg_type}").model_dump()
            )

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=str(e)).model_dump()
        )


async def handle_start_session(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Startet eine neue Session."""
    try:
        msg = StartSessionMessage(**message)

        agent_a_config: AgentConfig = {
            "name": msg.agent_a_config.name,
            "prompt": msg.agent_a_config.prompt,
        }
        agent_b_config: AgentConfig = {
            "name": msg.agent_b_config.name,
            "prompt": msg.agent_b_config.prompt,
        }

        session_id, _ = await simulator.start_session(
            mode=msg.mode,
            agent_a_config=agent_a_config,
            agent_b_config=agent_b_config,
            scenario=msg.scenario,
            user_role=msg.user_role,
        )

        # Session gestartet
        await websocket.send_json(
            SessionStartedResponse(session_id=session_id).model_dump()
        )

        # Simulation starten (mit Streaming)
        async for event in simulator.run_with_streaming(session_id):
            await send_event(websocket, session_id, event)

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=f"Failed to start session: {str(e)}").model_dump()
        )


async def handle_user_message(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Verarbeitet eine User-Nachricht."""
    try:
        msg = UserMessage(**message)

        success = await simulator.add_human_message(
            session_id=msg.session_id,
            content=msg.content,
            role=msg.role,
        )

        if not success:
            await websocket.send_json(
                ErrorResponse(message="Session not found").model_dump()
            )
            return

        # Simulation fortsetzen
        async for event in simulator.run_with_streaming(msg.session_id):
            await send_event(websocket, msg.session_id, event)

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=f"Failed to process message: {str(e)}").model_dump()
        )


async def handle_continue(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Setzt eine pausierte Session fort."""
    try:
        msg = ContinueMessage(**message)

        async for event in simulator.run_with_streaming(msg.session_id):
            await send_event(websocket, msg.session_id, event)

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=f"Failed to continue: {str(e)}").model_dump()
        )


async def handle_stop(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Stoppt eine Session und ruft Evaluierung auf."""
    try:
        msg = StopMessage(**message)

        success = await simulator.stop_session(msg.session_id)
        if not success:
            await websocket.send_json(
                ErrorResponse(message="Session not found").model_dump()
            )
            return

        # Evaluator aufrufen
        async for event in simulator.run_with_streaming(msg.session_id):
            await send_event(websocket, msg.session_id, event)

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=f"Failed to stop: {str(e)}").model_dump()
        )


async def handle_request_evaluation(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Fordert eine Evaluierung an."""
    try:
        msg = RequestEvaluationMessage(**message)

        # Stop und Evaluate
        await simulator.stop_session(msg.session_id)

        async for event in simulator.run_with_streaming(msg.session_id):
            await send_event(websocket, msg.session_id, event)

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=f"Failed to evaluate: {str(e)}").model_dump()
        )


async def send_event(websocket: WebSocket, session_id: str, event: dict):
    """Sendet ein Event an den Client."""
    event_type = event.get("type")

    if event_type == "agent_message":
        response = AgentMessageResponse(
            session_id=session_id,
            agent=event["agent"],
            agent_name=event["agent_name"],
            content=event["content"],
            timestamp=datetime.now(),
        )
        await websocket.send_json(response.model_dump(mode="json"))

    elif event_type == "streaming_chunk":
        response = StreamingChunkResponse(
            session_id=session_id,
            agent=event["agent"],
            agent_name=event["agent_name"],
            chunk=event["chunk"],
            is_final=event.get("is_final", False),
        )
        await websocket.send_json(response.model_dump())

    elif event_type == "typing":
        response = TypingResponse(
            session_id=session_id,
            agent=event["agent"],
            agent_name=event["agent_name"],
        )
        await websocket.send_json(response.model_dump())

    elif event_type == "waiting_for_input":
        response = WaitingForInputResponse(
            session_id=session_id,
            expected_role=event["expected_role"],
        )
        await websocket.send_json(response.model_dump())

    elif event_type == "evaluation":
        # Evaluation ohne Scores (Scores werden aus Content geparst)
        await websocket.send_json({
            "type": "evaluation",
            "session_id": session_id,
            "content": event["content"],
        })

    elif event_type == "error":
        response = ErrorResponse(message=event["message"])
        await websocket.send_json(response.model_dump())
