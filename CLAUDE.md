# Claude Code Instructions für Konflikt-Simulator

## Projekt-Übersicht

Der **Konflikt-Simulator** ist eine macOS App für KI-gestützte Konfliktsimulation. Zwei LLM-Agenten (z.B. Lisa & Thomas) simulieren einen realistischen Konflikt, während der User als Mediator eingreifen oder selbst eine Rolle übernehmen kann.

## Source of Truth

**WICHTIG**: Die Datei `DESIGN.md` ist die **Quelle der Wahrheit** für alle Design-Entscheidungen, Architektur und Implementierungsdetails.

### Vor Beginn jeder Arbeit

1. **Immer zuerst `DESIGN.md` lesen** - Enthält:
   - Architektur-Diagramme
   - WebSocket-Protokoll
   - LangGraph State Machine Details
   - Modell-Konfiguration
   - Implementierte Features (Logging, Interrupt, etc.)

### DESIGN.md MUSS live gehalten werden!

**Bei jedem Code-Commit:**

| Änderungstyp | DESIGN.md aktualisieren |
|--------------|-------------------------|
| Neues Feature | Abschnitt 10 (Implementierte Features) |
| Neue WebSocket-Nachricht | Abschnitt 4 (Protokoll) |
| Architektur-Änderung | Entsprechendes Diagramm |
| Bug-Fix mit Design-Impact | Dokumentieren |

**Workflow:**
```
1. Code implementieren
2. DESIGN.md aktualisieren
3. Beides im gleichen Commit!
```

## Repository-Struktur

```
Konfliktl-sungSimulator/
├── CLAUDE.md              # Diese Datei
├── DESIGN.md              # Source of Truth für Design
├── README.md              # Öffentliche Dokumentation
├── .gitignore             # Schützt .env mit API Key
│
├── backend/               # Python Backend
│   ├── .env               # API Key (NICHT committen!)
│   ├── .env.example       # Template
│   ├── pyproject.toml     # Poetry Dependencies
│   └── src/
│       ├── main.py        # FastAPI Server
│       ├── api/           # WebSocket Handler
│       ├── core/          # LangGraph Logic
│       ├── db/            # SQLite Persistenz
│       ├── models/        # Pydantic Schemas
│       └── prompts/       # Agent Prompts
│
└── frontend/              # Swift macOS App
    └── KonfliktSimulator/
        ├── Package.swift
        └── Sources/
            └── KonfliktSimulator/
                ├── Models/
                ├── Views/
                ├── ViewModels/
                └── Services/
```

## Schnellstart

### Backend starten
```bash
cd backend
cp .env.example .env  # API Key eintragen!
poetry install
poetry run python -m uvicorn src.main:app --reload --port 8080
```

### Frontend starten
```bash
cd frontend/KonfliktSimulator
swift build
.build/debug/KonfliktSimulator
```

## Tech Stack

| Komponente | Technologie |
|------------|-------------|
| Backend Framework | FastAPI + WebSocket |
| Agent Orchestrierung | LangGraph |
| LLM (Agenten) | Claude Sonnet 4.5 |
| LLM (Router) | Claude Haiku 3.5 |
| Persistenz | SQLite + SQLAlchemy |
| Frontend | SwiftUI (macOS 14+) |
| Kommunikation | WebSocket mit Streaming |

## Wichtige Dateien

| Datei | Beschreibung |
|-------|--------------|
| `backend/src/core/graph.py` | LangGraph State Machine |
| `backend/src/core/agents.py` | Agent Nodes + LLM Config |
| `backend/src/core/router.py` | Smart Routing mit Haiku |
| `backend/src/api/websocket.py` | WebSocket Handler |
| `frontend/.../ChatViewModel.swift` | Frontend State Management |
| `frontend/.../WebSocketService.swift` | WebSocket Client |

## Git Workflow

- **Branch**: `main`
- **Remote**: `https://github.com/friendlyFrodo/Konfliktl-sungSimulator`

### Commit-Konvention
```
<typ>: <kurze Beschreibung>

<details>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## Aktuelle Konfiguration

- **Port**: 8080 (Backend)
- **WebSocket**: `ws://localhost:8080/ws`
- **Modelle**:
  - Agenten: `claude-sonnet-4-5-20250514`
  - Router: `claude-3-5-haiku-20241022`

## Bekannte Issues / TODOs

- [ ] SQLite Persistenz noch nicht vollständig integriert
- [ ] Session-Resume nach App-Neustart
- [ ] Evaluator Scores parsen und anzeigen
- [ ] Mehr Szenarien hinzufügen
