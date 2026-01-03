"""FastAPI Server für den Konflikt-Simulator."""

import os
import uuid
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .api.websocket import manager, handle_websocket_message
from .core.graph import simulator
from .db.database import init_db

# Environment laden
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/Shutdown Events."""
    # Startup
    print("Konflikt-Simulator Backend startet...")

    # Datenbank initialisieren
    await init_db()
    print("Datenbank initialisiert.")

    # API Key prüfen
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("WARNUNG: ANTHROPIC_API_KEY nicht gesetzt!")

    yield

    # Shutdown
    print("Konflikt-Simulator Backend beendet.")


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

    try:
        while True:
            # Auf Nachricht warten
            data = await websocket.receive_json()
            await handle_websocket_message(websocket, client_id, data)

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")

    except Exception as e:
        print(f"WebSocket error: {e}")
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


@app.get("/scenarios")
async def list_scenarios():
    """Listet vordefinierte Szenarien."""
    return {
        "scenarios": [
            {
                "id": "couple",
                "name": "Paar-Konflikt",
                "description": "Lisa & Thomas - Streit über Haushaltsaufteilung",
                "agent_a": {
                    "name": "Lisa",
                    "prompt": None,  # Default verwenden
                },
                "agent_b": {
                    "name": "Thomas",
                    "prompt": None,
                },
                "scenario": "Lisa und Thomas sind seit 5 Jahren zusammen. Sie streiten sich immer wieder über die Haushaltsaufteilung. Lisa fühlt sich überarbeitet, Thomas versteht nicht, warum sie sich so aufregt.",
            },
            {
                "id": "workplace",
                "name": "Arbeitsplatz",
                "description": "Maria & Stefan - Konflikt über Projektverantwortung",
                "agent_a": {
                    "name": "Maria",
                    "prompt": "Du bist Maria, 42 Jahre, Senior Projektmanagerin. Du fühlst dich von deinem Kollegen Stefan übergangen, der deine Entscheidungen vor dem Chef infrage stellt. Du bist direkt, aber professionell.",
                },
                "agent_b": {
                    "name": "Stefan",
                    "prompt": "Du bist Stefan, 35 Jahre, ambitionierter Projektmitarbeiter. Du hast das Gefühl, dass Maria deine Ideen nie ernst nimmt und du nie Verantwortung bekommst. Du bist ehrgeizig und manchmal ungeduldig.",
                },
                "scenario": "Maria und Stefan arbeiten am selben Projekt. Letzte Woche hat Stefan dem Chef eine Idee präsentiert, ohne Maria einzubeziehen. Maria ist wütend, Stefan versteht das Problem nicht.",
            },
            {
                "id": "family",
                "name": "Familie",
                "description": "Mutter & erwachsenes Kind - Diskussion über Lebensführung",
                "agent_a": {
                    "name": "Renate",
                    "prompt": "Du bist Renate, 58 Jahre, besorgte Mutter. Du machst dir Sorgen um deinen erwachsenen Sohn, der aus deiner Sicht sein Potenzial verschwendet. Du willst nur das Beste für ihn, aber deine Ratschläge kommen als Kritik an.",
                },
                "agent_b": {
                    "name": "Markus",
                    "prompt": "Du bist Markus, 28 Jahre. Du hast deinen sicheren Job gekündigt, um als Künstler zu arbeiten. Du fühlst dich von deiner Mutter nicht unterstützt und unter Druck gesetzt, 'normal' zu sein.",
                },
                "scenario": "Markus hat seiner Mutter gerade erzählt, dass er seinen IT-Job gekündigt hat, um Vollzeit als Künstler zu arbeiten. Renate ist schockiert.",
            },
            {
                "id": "roommates",
                "name": "WG",
                "description": "Mitbewohner - Lärm und Rücksichtnahme",
                "agent_a": {
                    "name": "Alex",
                    "prompt": "Du bist Alex, 24, Student. Du arbeitest nachts an deiner Masterarbeit und brauchst tagsüber Ruhe zum Schlafen. Dein Mitbewohner ist ständig laut. Du bist passiv-aggressiv und vermeidest direkte Konfrontation.",
                },
                "agent_b": {
                    "name": "Kim",
                    "prompt": "Du bist Kim, 23, arbeitest im Home-Office. Du machst gerne Musik und hast Freunde zu Besuch. Du findest, Alex ist überempfindlich und sollte sich anpassen. Du wirst schnell defensiv.",
                },
                "scenario": "Es ist Sonntagmittag. Alex wurde gerade von Kims lauter Musik geweckt, nachdem er die ganze Nacht durchgearbeitet hat. Das ist das dritte Mal diese Woche.",
            },
            {
                "id": "friends",
                "name": "Freundschaft",
                "description": "Alte Freunde - Entfremdung und Vorwürfe",
                "agent_a": {
                    "name": "Jana",
                    "prompt": "Du bist Jana, 30. Deine beste Freundin seit der Schulzeit hat sich seit ihrer Beförderung kaum noch gemeldet. Du fühlst dich im Stich gelassen und bist verletzt, zeigst das aber durch Vorwürfe statt Verletzlichkeit.",
                },
                "agent_b": {
                    "name": "Sophie",
                    "prompt": "Du bist Sophie, 30. Seit deiner Beförderung bist du gestresst und hast wenig Zeit. Du verstehst nicht, warum Jana so vorwurfsvoll ist - du meldest dich doch, wenn du kannst. Du fühlst dich schuldig, aber auch genervt.",
                },
                "scenario": "Jana und Sophie treffen sich zum ersten Mal seit zwei Monaten. Jana hat Sophie mehrfach geschrieben, aber nur kurze Antworten bekommen. Jetzt sitzen sie im Café.",
            },
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
