"""WebSocket Handler für Echtzeit-Kommunikation."""

import json
import logging
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
    InterruptMessage,
    AnalyzeMessageRequest,
    AgentMessageResponse,
    StreamingChunkResponse,
    WaitingForInputResponse,
    TypingResponse,
    SessionStartedResponse,
    ErrorResponse,
    InterruptedResponse,
    MessageAnalysisResponse,
)
from ..core.agents import analyze_single_message

# Logging
logger = logging.getLogger("konflikt.websocket")
logger.setLevel(logging.DEBUG)


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
    logger.info(f"[{client_id[:8]}] 📥 Empfangen: {msg_type}")

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

        elif msg_type == "interrupt":
            await handle_interrupt(websocket, client_id, message)

        elif msg_type == "analyze_message":
            await handle_analyze_message(websocket, client_id, message)

        else:
            logger.warning(f"[{client_id[:8]}] ⚠️ Unbekannter Nachrichtentyp: {msg_type}")
            await websocket.send_json(
                ErrorResponse(message=f"Unknown message type: {msg_type}").model_dump()
            )

    except Exception as e:
        logger.error(f"[{client_id[:8]}] ❌ Fehler: {e}")
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

        # Erster Agent spricht (Single Turn)
        async for event in simulator.run_single_turn(session_id):
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

        # Nächster Agent spricht (Single Turn)
        async for event in simulator.run_single_turn(msg.session_id):
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
    """Lässt den nächsten Agent sprechen (User hat entschieden)."""
    try:
        msg = ContinueMessage(**message)
        logger.info(f"[{client_id[:8]}] ▶️ Continue - nächster Agent spricht")

        async for event in simulator.run_single_turn(msg.session_id):
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
        logger.info(f"[{client_id[:8]}] 🛑 Stop - Evaluator wird aufgerufen")

        success = await simulator.stop_session(msg.session_id)
        if not success:
            await websocket.send_json(
                ErrorResponse(message="Session not found").model_dump()
            )
            return

        # Evaluator aufrufen
        async for event in simulator.run_single_turn(msg.session_id):
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
        logger.info(f"[{client_id[:8]}] 📊 Evaluierung angefordert")

        # Stop und Evaluate
        await simulator.stop_session(msg.session_id)

        async for event in simulator.run_single_turn(msg.session_id):
            await send_event(websocket, msg.session_id, event)

    except Exception as e:
        await websocket.send_json(
            ErrorResponse(message=f"Failed to evaluate: {str(e)}").model_dump()
        )


async def handle_interrupt(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Unterbricht eine laufende Session sofort (User greift ein)."""
    try:
        msg = InterruptMessage(**message)
        logger.info(f"[{client_id[:8]}] 🛑 Interrupt für Session {msg.session_id[:8]}")

        success = simulator.interrupt_session(msg.session_id)
        if not success:
            await websocket.send_json(
                ErrorResponse(message="Session not found").model_dump()
            )
            return

        # Bestätigung senden
        await websocket.send_json(
            InterruptedResponse(session_id=msg.session_id).model_dump()
        )

        # Waiting for Input Status
        await websocket.send_json({
            "type": "waiting_for_input",
            "session_id": msg.session_id,
            "expected_role": "mediator",
        })

    except Exception as e:
        logger.error(f"[{client_id[:8]}] ❌ Interrupt-Fehler: {e}")
        await websocket.send_json(
            ErrorResponse(message=f"Failed to interrupt: {str(e)}").model_dump()
        )


async def handle_analyze_message(
    websocket: WebSocket,
    client_id: str,
    message: dict,
):
    """Analysiert eine einzelne Nachricht (Experten-Modus)."""
    try:
        msg = AnalyzeMessageRequest(**message)
        logger.info(f"[{client_id[:8]}] 🔍 Analyse angefordert für {msg.message_agent}")

        # Analyse durchführen
        analysis = await analyze_single_message(
            message_content=msg.message_content,
            message_agent=msg.message_agent,
            agent_name=msg.agent_name,
            conversation_context=msg.conversation_context,
        )

        # Analyse-Typ bestimmen
        analysis_type = "mediator" if msg.message_agent == "mediator" else "party"

        # Antwort senden
        response = MessageAnalysisResponse(
            message_id=msg.message_id,
            analysis=analysis,
            analysis_type=analysis_type,
        )
        await websocket.send_json(response.model_dump())

        logger.info(f"[{client_id[:8]}] ✅ Analyse gesendet ({len(analysis)} Zeichen)")

    except Exception as e:
        logger.error(f"[{client_id[:8]}] ❌ Analyse-Fehler: {e}")
        await websocket.send_json(
            ErrorResponse(message=f"Failed to analyze message: {str(e)}").model_dump()
        )


async def send_event(websocket: WebSocket, session_id: str, event: dict):
    """Sendet ein Event an den Client."""
    event_type = event.get("type")

    if event_type == "agent_message":
        # Format timestamp as ISO8601 with Z suffix for Swift compatibility
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        await websocket.send_json({
            "type": "agent_message",
            "session_id": session_id,
            "agent": event["agent"],
            "agent_name": event["agent_name"],
            "content": event["content"],
            "timestamp": timestamp,
        })

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

    elif event_type == "waiting_for_decision":
        # Neue Architektur: User entscheidet nach jedem Agent-Statement
        await websocket.send_json({
            "type": "waiting_for_decision",
            "session_id": session_id,
            "suggested_next": event["suggested_next"],
            "suggested_next_name": event["suggested_next_name"],
            "agent_a_name": event["agent_a_name"],
            "agent_b_name": event["agent_b_name"],
        })

    elif event_type == "error":
        response = ErrorResponse(message=event["message"])
        await websocket.send_json(response.model_dump())
