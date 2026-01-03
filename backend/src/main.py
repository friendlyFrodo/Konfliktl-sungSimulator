"""FastAPI Server für den Konflikt-Simulator."""

import os
import sys
import uuid
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api.websocket import manager, handle_websocket_message
from .api.scenarios import router as scenarios_router
from .core.graph import simulator
from .db.database import init_db, seed_preset_scenarios

# Environment laden
load_dotenv()

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

# Log-Level für spezifische Module
logging.getLogger("konflikt").setLevel(logging.DEBUG)
logging.getLogger("konflikt.graph").setLevel(logging.DEBUG)
logging.getLogger("konflikt.router").setLevel(logging.DEBUG)
logging.getLogger("konflikt.websocket").setLevel(logging.DEBUG)

# Externe Bibliotheken leiser stellen
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.INFO)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)

logger = logging.getLogger("konflikt.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown Events."""
    # Startup
    logger.info("=" * 60)
    logger.info("Konflikt-Simulator Backend startet...")
    logger.info("=" * 60)

    # Datenbank initialisieren
    await init_db()
    logger.info("Datenbank initialisiert.")

    # Preset-Szenarien seeden
    await seed_preset_scenarios()
    logger.info("Preset-Szenarien geladen.")

    # API Key prüfen
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("ANTHROPIC_API_KEY nicht gesetzt!")
    else:
        logger.info("API Key konfiguriert.")

    logger.info("Server bereit auf Port 8080")

    yield

    # Shutdown
    logger.info("Konflikt-Simulator Backend beendet.")


app = FastAPI(
    title="Konflikt-Simulator API",
    description="Backend für KI-gestützte Konfliktsimulation",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS für lokale Entwicklung
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Production einschränken
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API Router einbinden
app.include_router(scenarios_router)


@app.get("/")
async def root():
    """Health Check."""
    return {
        "status": "running",
        "name": "Konflikt-Simulator API",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Detaillierter Health Check."""
    api_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))
    return {
        "status": "healthy" if api_key_set else "degraded",
        "api_key_configured": api_key_set,
        "active_sessions": len(simulator.sessions),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket Endpoint für Echtzeit-Kommunikation."""
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    logger.info(f"🔌 Client {client_id[:8]} verbunden")

    try:
        while True:
            # Auf Nachricht warten - handle both text and bytes
            message = await websocket.receive()

            if "text" in message:
                import json
                data = json.loads(message["text"])
                await handle_websocket_message(websocket, client_id, data)
            elif "bytes" in message:
                import json
                data = json.loads(message["bytes"].decode())
                await handle_websocket_message(websocket, client_id, data)
            elif message.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"🔌 Client {client_id[:8]} getrennt")

    except Exception as e:
        import traceback
        logger.error(f"WebSocket Fehler: {e}")
        traceback.print_exc()
        manager.disconnect(client_id)


@app.get("/sessions")
async def list_sessions():
    """Listet alle aktiven Sessions."""
    sessions = []
    for session_id, state in simulator.sessions.items():
        sessions.append({
            "session_id": session_id,
            "mode": state["mode"],
            "turns": state["turns"],
            "agent_a": state["agent_a_config"]["name"],
            "agent_b": state["agent_b_config"]["name"],
        })
    return {"sessions": sessions}


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Gibt Details einer Session zurück."""
    state = simulator.get_session_state(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "mode": state["mode"],
        "turns": state["turns"],
        "agent_a_config": state["agent_a_config"],
        "agent_b_config": state["agent_b_config"],
        "messages": [
            {
                "content": msg.content,
                "type": type(msg).__name__,
                "name": getattr(msg, "name", None),
            }
            for msg in state["messages"]
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
