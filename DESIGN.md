# Konflikt-Simulator - Design Document

## 1. Übersicht

Eine macOS Desktop-Anwendung für KI-gestützte Konfliktsimulation und Mediationstraining. Zwei LLM-Agenten simulieren einen realistischen zwischenmenschlichen Konflikt, während der Benutzer als Mediator eingreifen oder selbst eine der Konfliktparteien übernehmen kann.

### 1.1 Kernfeatures

- **Multi-Agenten-Simulation**: Zwei KI-Persönlichkeiten führen einen authentischen Konfliktdialog
- **Zwei Modi**:
  - **Mediator**: Beobachte und greife als Coach/Vermittler ein
  - **Teilnehmer**: Übernimm selbst eine der Rollen
- **Echtzeit-Streaming**: Token-by-Token Ausgabe für natürliches "Tippen"
- **Intelligentes Routing**: Haiku-LLM entscheidet dynamisch, wer als nächstes spricht
- **Coach-Feedback**: Detaillierte Analyse mit Scores am Ende jeder Session
- **Konfigurierbare Persönlichkeiten**: Prompts vollständig anpassbar

---

## 2. Architektur

```
┌─────────────────────────────────────────────────────────────────────┐
│                      macOS App (SwiftUI)                            │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │   Chat UI   │  │   Agent     │  │   Session   │  │  Settings  │ │
│  │  (Messages, │  │   Editor    │  │   Manager   │  │  (Server,  │ │
│  │  Streaming) │  │  (Prompts)  │  │   (Liste)   │  │   Keys)    │ │
│  └──────┬──────┘  └─────────────┘  └─────────────┘  └────────────┘ │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    WebSocketService                             ││
│  │              (URLSessionWebSocketTask)                          ││
│  └──────────────────────────┬──────────────────────────────────────┘│
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              │ ws://localhost:8080/ws
                              │ (JSON Messages)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Python Backend (FastAPI)                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    WebSocket Handler                            ││
│  │         (Empfängt Commands, Sendet Events)                      ││
│  └──────────────────────────┬──────────────────────────────────────┘│
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                 LangGraph State Machine                         ││
│  │                                                                 ││
│  │     ┌───────────┐      ┌───────────┐      ┌───────────┐        ││
│  │     │  Agent A  │◄────►│  Router   │◄────►│  Agent B  │        ││
│  │     │  (Sonnet) │      │  (Haiku)  │      │  (Sonnet) │        ││
│  │     └─────┬─────┘      └─────┬─────┘      └─────┬─────┘        ││
│  │           │                  │                  │               ││
│  │           └──────────────────┼──────────────────┘               ││
│  │                              │                                  ││
│  │                              ▼                                  ││
│  │                       ┌───────────┐                             ││
│  │                       │ Evaluator │                             ││
│  │                       │  (Sonnet) │                             ││
│  │                       └───────────┘                             ││
│  └─────────────────────────────────────────────────────────────────┘│
│                             │                                       │
│         ┌───────────────────┼───────────────────┐                  │
│         ▼                   ▼                   ▼                  │
│  ┌────────────┐     ┌─────────────┐     ┌─────────────┐           │
│  │   SQLite   │     │  Anthropic  │     │   Prompts   │           │
│  │  Database  │     │  Claude API │     │   (Files)   │           │
│  └────────────┘     └─────────────┘     └─────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. LangGraph State Machine

### 3.1 State Definition

```python
class SimulationState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]  # Chat-Historie
    session_id: str                                        # Eindeutige Session-ID
    mode: Literal["mediator", "participant"]               # Simulationsmodus
    next_speaker: Literal["agent_a", "agent_b", "human", "evaluator"]
    turns: int                                             # Anzahl Sprecherwechsel
    agent_a_config: AgentConfig                            # Name + Prompt
    agent_b_config: AgentConfig                            # Name + Prompt
    user_role: Optional[str]                               # Bei participant: welche Rolle
    should_stop: bool                                      # Stop-Flag
    streaming_content: Optional[str]                       # Aktueller Stream
```

### 3.2 Graph Flow

```
                         ┌─────────┐
                         │  START  │
                         └────┬────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    Agent A      │ ◄──────────────┐
                    │ (Lisa/Sonnet)   │                │
                    └────────┬────────┘                │
                             │                         │
                             ▼                         │
                    ┌─────────────────┐                │
                    │  Smart Router   │                │
                    │    (Haiku)      │                │
                    └────────┬────────┘                │
                             │                         │
            ┌────────────────┼────────────────┐       │
            ▼                ▼                ▼       │
    ┌───────────┐    ┌───────────┐    ┌───────────┐  │
    │  Agent B  │    │   Human   │    │ Evaluator │  │
    │ (Thomas)  │    │  (Wait)   │    │  (Coach)  │  │
    └─────┬─────┘    └─────┬─────┘    └─────┬─────┘  │
          │                │                │        │
          │                │                ▼        │
          │                │          ┌─────────┐    │
          │                │          │   END   │    │
          │                │          └─────────┘    │
          │                │                         │
          └────────────────┴─────────────────────────┘
```

### 3.3 Smart Router Logik

Der Router (Haiku) analysiert die letzten 4 Nachrichten und entscheidet:

| Situation | Entscheidung |
|-----------|--------------|
| Agent B wurde direkt angesprochen | → `AGENT_B` |
| Agent A wurde direkt angesprochen | → `AGENT_A` |
| Eskalation / Sackgasse | → `HUMAN` (Mediator eingreifen) |
| Einigung oder totale Eskalation | → `EVALUATOR` (Session beenden) |

```python
ROUTER_SYSTEM_PROMPT = """
Analysiere die letzten Nachrichten und entscheide:
- AGENT_A: Wenn Agent A antworten soll
- AGENT_B: Wenn Agent B antworten soll
- HUMAN: Wenn der Mediator eingreifen sollte
- EVALUATOR: Wenn das Gespräch beendet werden sollte
"""
```

---

## 4. WebSocket Protokoll

### 4.1 Client → Server Messages

#### Start Session
```json
{
  "type": "start_session",
  "mode": "mediator",
  "agent_a_config": {
    "name": "Lisa",
    "prompt": "Du bist Lisa, 34 Jahre..."
  },
  "agent_b_config": {
    "name": "Thomas",
    "prompt": "Du bist Thomas, 36 Jahre..."
  },
  "scenario": "Lisa und Thomas streiten über...",
  "user_role": null
}
```

#### User Message
```json
{
  "type": "user_message",
  "session_id": "uuid",
  "content": "Ich verstehe, dass ihr beide frustriert seid...",
  "role": "mediator"
}
```

#### Control Messages
```json
{"type": "continue", "session_id": "uuid"}
{"type": "stop", "session_id": "uuid"}
{"type": "request_evaluation", "session_id": "uuid"}
{"type": "interrupt", "session_id": "uuid"}
```

#### Analyze Message (Experten-Analyse)
```json
{
  "type": "analyze_message",
  "session_id": "uuid",
  "message_id": "uuid",
  "message_content": "Das stimmt doch gar nicht!",
  "message_agent": "agent_a",
  "agent_name": "Lisa",
  "conversation_context": [
    {"agent": "agent_b", "agent_name": "Thomas", "content": "Du hörst mir nie zu!"}
  ]
}
```

### 4.2 Server → Client Messages

#### Session Started
```json
{
  "type": "session_started",
  "session_id": "uuid"
}
```

#### Typing Indicator
```json
{
  "type": "typing",
  "session_id": "uuid",
  "agent": "a",
  "agent_name": "Lisa"
}
```

#### Streaming Chunk
```json
{
  "type": "streaming_chunk",
  "session_id": "uuid",
  "agent": "a",
  "agent_name": "Lisa",
  "chunk": "Ich finde es unfair, ",
  "is_final": false
}
```

#### Agent Message (Final)
```json
{
  "type": "agent_message",
  "session_id": "uuid",
  "agent": "a",
  "agent_name": "Lisa",
  "content": "Lisa: Ich finde es unfair, dass du nie...",
  "timestamp": "2025-01-03T20:30:00Z"
}
```

#### Waiting for Input
```json
{
  "type": "waiting_for_input",
  "session_id": "uuid",
  "expected_role": "mediator"
}
```

#### Evaluation
```json
{
  "type": "evaluation",
  "session_id": "uuid",
  "content": "COACH: Analyse des Gesprächs...\n\nBEWERTUNG:\n- Eskalationslevel: 7/10\n..."
}
```

#### Message Analysis (Experten-Analyse Antwort)
```json
{
  "type": "message_analysis",
  "message_id": "uuid",
  "analysis": "## Was wird gesagt\nLisa bestreitet eine Aussage...\n\n## Was wird NICHT gesagt\n- Konkrete Begründung...",
  "analysis_type": "party"
}
```

---

## 5. Modell-Konfiguration

### 5.1 Verwendete Modelle

| Zweck | Modell | Temperatur | Begründung |
|-------|--------|------------|------------|
| Agenten (Roleplay) | `claude-sonnet-4-5-20250514` | 0.7 | Beste Nuancen, natürliches Deutsch |
| Router | `claude-3-5-haiku-20241022` | 0.0 | Schnell, deterministisch, günstig |
| Evaluator | `claude-sonnet-4-5-20250514` | 0.7 | Detaillierte Analyse |

### 5.2 System Prompts

#### Agent A (Default: Lisa)
```
Du bist Lisa, 34 Jahre alt. Du bist emotional, fühlst dich oft
ungerecht behandelt und hast Schwierigkeiten, deine Gefühle
sachlich auszudrücken.

WICHTIGE VERHALTENSREGELN:
- Du reagierst emotional auf Kritik und wirst schnell defensiv
- Du verwendest oft "Du machst immer..." oder "Du machst nie..."
- Du unterbrichst manchmal, wenn du dich angegriffen fühlst
...
```

#### Agent B (Default: Thomas)
```
Du bist Thomas, 36 Jahre alt. Du bist rational, analytisch und
versuchst Konflikte mit Logik zu lösen. Du verstehst oft nicht,
warum andere so emotional reagieren.

WICHTIGE VERHALTENSREGELN:
- Du bleibst oberflächlich ruhig, wirst aber sarkastisch wenn frustriert
- Du versuchst Probleme zu "lösen" statt Gefühle zu validieren
...
```

#### Evaluator (Coach)
```
Du bist ein erfahrener Konflikt-Coach mit 20 Jahren Erfahrung.

ANALYSE-FRAMEWORK:
1. ESKALATIONSLEVEL (0-10)
2. LÖSUNGSFORTSCHRITT (0-10)
3. KOMMUNIKATIONSQUALITÄT (0-10 pro Person)

FEEDBACK-STRUKTUR:
1. Was lief gut?
2. Was könnte verbessert werden?
3. Konkrete Tipps für jeden Teilnehmer
...
```

---

## 6. Vordefinierte Szenarien

| ID | Name | Beschreibung |
|----|------|--------------|
| `couple` | Paar-Konflikt | Lisa & Thomas - Haushaltsaufteilung |
| `workplace` | Arbeitsplatz | Maria & Stefan - Projektverantwortung |
| `family` | Familie | Renate & Markus - Lebensführung |
| `roommates` | WG | Alex & Kim - Lärm und Rücksichtnahme |
| `friends` | Freundschaft | Jana & Sophie - Entfremdung |

---

## 7. Frontend-Architektur (SwiftUI)

### 7.1 View-Hierarchie

```
KonfliktSimulatorApp
└── ContentView
    ├── SidebarView (Navigation)
    │   ├── Neue Session Button
    │   └── Verbindungsstatus
    │
    ├── ChatView (Hauptansicht)
    │   ├── ScrollView mit Messages
    │   │   ├── MessageBubble (pro Nachricht)
    │   │   └── TypingIndicator
    │   └── InputArea
    │       ├── TextField
    │       ├── Send Button
    │       └── Stop Button
    │
    └── Sheets
        ├── NewSessionSheet
        │   ├── Modus-Auswahl
        │   ├── Szenario-Auswahl
        │   └── AgentConfigPanel
        └── SettingsView
```

### 7.2 State Management

```swift
@MainActor
class ChatViewModel: ObservableObject {
    @Published var messages: [Message] = []
    @Published var streamingMessage: Message? = nil
    @Published var isWaitingForInput: Bool = false
    @Published var typingAgentName: String? = nil

    let webSocketService: WebSocketService

    func startSession(mode:, agentAConfig:, agentBConfig:, ...)
    func sendMessage()
    func stopAndEvaluate()
}
```

---

## 8. Persistenz (SQLite)

### 8.1 Schema

```sql
-- Sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    agent_a_name TEXT NOT NULL,
    agent_a_prompt TEXT NOT NULL,
    agent_b_name TEXT NOT NULL,
    agent_b_prompt TEXT NOT NULL,
    scenario TEXT,
    user_role TEXT,
    turns INTEGER DEFAULT 0,
    messages JSON DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Agent Configs (für Custom-Presets)
CREATE TABLE agent_configs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    is_preset INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 9. Deployment

### 9.1 Entwicklung

```bash
# Backend (Terminal 1)
cd backend
poetry run python -m uvicorn src.main:app --reload --port 8080

# Frontend (Terminal 2)
cd frontend/KonfliktSimulator
swift build && .build/debug/KonfliktSimulator
```

### 9.2 Umgebungsvariablen

```bash
# backend/.env
ANTHROPIC_API_KEY=sk-ant-api03-...
DATABASE_PATH=konflikt_simulator.db  # Optional
```

---

## 10. Implementierte Features (v0.2.0)

### 10.1 Umfassendes Logging

Das Backend loggt jetzt alle wichtigen Events:

```
[konflikt.graph] [Session-ID] Agent A (Lisa) beginnt...
[konflikt.graph] [Session-ID] Agent A RAW: "Lisa: Ich finde das..."
[konflikt.graph] [Session-ID] Agent A CLEANED: "Ich finde das..."
[konflikt.router] [Session-ID] Router RAW-Antwort: 'AGENT_B'
```

**Logger-Hierarchie:**
- `konflikt.main` - Server-Startup, Verbindungen
- `konflikt.graph` - Graph-Ausführung, Streaming
- `konflikt.router` - Routing-Entscheidungen
- `konflikt.websocket` - WebSocket-Nachrichten

### 10.2 Interrupt-Mechanismus (User greift ein)

User kann jetzt aktiv während des Streamings eingreifen:

```json
// Client -> Server
{"type": "interrupt", "session_id": "uuid"}

// Server -> Client
{"type": "interrupted", "session_id": "uuid", "message": "Session unterbrochen..."}
{"type": "waiting_for_input", "session_id": "uuid", "expected_role": "mediator"}
```

**UI-Element:** Oranger "Eingreifen"-Button erscheint während Agents tippen.

### 10.3 Antwort-Bereinigung

Das Backend bereinigt Agent-Antworten automatisch:
- Entfernt doppelte Namen (`"Lisa: Lisa: Text"` -> `"Lisa: Text"`)
- Erkennt verschiedene Formatierungen (`**Lisa**:`, `*Lisa*:`)
- Loggt Warnungen bei leeren Antworten

### 10.4 Mimik/Gestik in dritter Person

Agenten beschreiben ihre Körpersprache jetzt für den Leser:

| Vorher (1. Person) | Nachher (3. Person) |
|-------------------|---------------------|
| *Ich verschränke die Arme* | *Lisa verschränkt die Arme* |
| *seufze* | *Thomas seufzt* |

### 10.5 Experten-Analyse (Sparkles Icon)

Jede Nachricht hat ein kleines Analyse-Icon (✨). Beim Klick erhält man:

**Für Konfliktparteien (Lisa/Thomas):**
- Was wird explizit gesagt (Oberflächenebene)
- Was wird NICHT gesagt (Tiefenebene, verborgene Bedürfnisse)
- Kommunikationsmuster erkennen
- Konkrete Hinweise für den Mediator

**Für Mediator-Beiträge:**
- Identifikation der verwendeten Technik (Harvard, GFK, Glasl, etc.)
- Bewertung der Intervention
- Was hätte besser sein können
- Alternative Formulierungen mit wissenschaftlicher Begründung

**Modell:** Claude Haiku 3.5 für schnelle Analyse (~1-2s Response)

**UI:** Popover erscheint rechts neben der Nachricht mit scrollbarer Analyse.

---

## 11. Erweiterungsmöglichkeiten

1. **Mehr Szenarien**: Weitere vordefinierte Konfliktszenarien
2. **Session-Export**: PDF/Markdown Export der Konversation
3. **Replay-Modus**: Vergangene Sessions abspielen
4. **Mehrsprachigkeit**: UI und Agenten in anderen Sprachen
5. **Metriken-Dashboard**: Fortschritt über mehrere Sessions
6. **Voice-Integration**: Text-to-Speech für Agenten
