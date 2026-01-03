# Konflikt-Simulator

Eine macOS App für KI-gestützte Konfliktsimulation mit LangGraph und Claude.

## Features

- **Multi-Agenten-Simulation**: Zwei KI-Agenten (z.B. Lisa & Thomas) simulieren einen Konflikt
- **Zwei Modi**:
  - **Mediator**: Beobachte den Konflikt und greife als Coach ein
  - **Teilnehmer**: Übernimm selbst eine der Rollen
- **Echtzeit-Streaming**: Antworten werden live gestreamt
- **Konfiguierbare Persönlichkeiten**: Passe Agenten-Prompts individuell an
- **Vordefinierte Szenarien**: Paar, Arbeitsplatz, Familie, WG, Freundschaft
- **Coach-Feedback**: Evaluierung mit Scores und konkreten Tipps

## Tech Stack

### Backend (Python)
- FastAPI mit WebSocket
- LangGraph für Multi-Agenten-Orchestrierung
- Claude (Anthropic) als LLM
- SQLite für Persistenz

### Frontend (Swift)
- SwiftUI für macOS 14+
- Native WebSocket-Integration

## Setup

### Backend

```bash
cd backend

# Environment
cp .env.example .env
# ANTHROPIC_API_KEY in .env eintragen

# Dependencies installieren
poetry install

# Server starten
poetry run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend/KonfliktSimulator

# Build & Run
swift build
swift run

# Oder in Xcode öffnen
open Package.swift
```

## WebSocket API

### Client → Server

```json
// Session starten
{"type": "start_session", "mode": "mediator", "agent_a_config": {...}, "agent_b_config": {...}}

// Nachricht senden
{"type": "user_message", "session_id": "...", "content": "...", "role": "mediator"}

// Session stoppen
{"type": "stop", "session_id": "..."}
```

### Server → Client

```json
// Agent-Nachricht
{"type": "agent_message", "agent": "a", "agent_name": "Lisa", "content": "..."}

// Streaming
{"type": "streaming_chunk", "agent": "a", "chunk": "..."}

// Warte auf Input
{"type": "waiting_for_input", "expected_role": "mediator"}

// Evaluierung
{"type": "evaluation", "content": "..."}
```

## Architektur

```
┌─────────────────────────────────────────┐
│           macOS App (SwiftUI)           │
│  Chat UI │ Agent Editor │ Settings      │
└────────────────┬────────────────────────┘
                 │ WebSocket
                 ▼
┌─────────────────────────────────────────┐
│         Python Backend (FastAPI)        │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │    LangGraph State Machine      │   │
│  │  Agent A ◄─► Router ◄─► Agent B │   │
│  │            ▼                    │   │
│  │        Evaluator                │   │
│  └─────────────────────────────────┘   │
│                 │                       │
│         Claude (Anthropic)              │
└─────────────────────────────────────────┘
```

## Lizenz

MIT
