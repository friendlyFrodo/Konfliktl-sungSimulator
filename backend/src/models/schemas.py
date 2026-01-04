"""Pydantic Schemas für API Requests/Responses."""

from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


# === Client -> Server Messages ===

class AgentConfigSchema(BaseModel):
    """Konfiguration für einen Agenten."""
    name: str
    prompt: str


class StartSessionMessage(BaseModel):
    """Nachricht zum Starten einer neuen Session."""
    type: Literal["start_session"] = "start_session"
    mode: Literal["mediator", "participant"]
    agent_a_config: AgentConfigSchema
    agent_b_config: AgentConfigSchema
    scenario: Optional[str] = None
    user_role: Optional[Literal["agent_a", "agent_b"]] = None  # Nur bei participant


class UserMessage(BaseModel):
    """User-Nachricht in einer laufenden Session."""
    type: Literal["user_message"] = "user_message"
    session_id: str
    content: str
    role: Literal["mediator", "agent_a", "agent_b"]


class ContinueMessage(BaseModel):
    """Session fortsetzen."""
    type: Literal["continue"] = "continue"
    session_id: str


class StopMessage(BaseModel):
    """Session stoppen."""
    type: Literal["stop"] = "stop"
    session_id: str


class RequestEvaluationMessage(BaseModel):
    """Evaluierung anfordern."""
    type: Literal["request_evaluation"] = "request_evaluation"
    session_id: str


class InterruptMessage(BaseModel):
    """Sofortige Unterbrechung während Streaming."""
    type: Literal["interrupt"] = "interrupt"
    session_id: str


class AnalyzeMessageRequest(BaseModel):
    """Anfrage zur Analyse einer einzelnen Nachricht."""
    type: Literal["analyze_message"] = "analyze_message"
    session_id: str
    message_id: str  # UUID der zu analysierenden Nachricht
    message_content: str
    message_agent: Literal["agent_a", "agent_b", "mediator"]
    agent_name: str
    # Kontext: vorherige Nachrichten für bessere Analyse
    conversation_context: list[dict]  # [{agent, agent_name, content}, ...]


# === Server -> Client Messages ===

class AgentMessageResponse(BaseModel):
    """Agent spricht."""
    type: Literal["agent_message"] = "agent_message"
    session_id: str
    agent: Literal["a", "b"]
    agent_name: str
    content: str
    timestamp: datetime


class StreamingChunkResponse(BaseModel):
    """Streaming-Chunk für Echtzeit-Updates."""
    type: Literal["streaming_chunk"] = "streaming_chunk"
    session_id: str
    agent: Literal["a", "b", "evaluator"]
    agent_name: str
    chunk: str
    is_final: bool = False


class WaitingForInputResponse(BaseModel):
    """Warte auf User-Input."""
    type: Literal["waiting_for_input"] = "waiting_for_input"
    session_id: str
    expected_role: Literal["mediator", "agent_a", "agent_b"]


class TypingResponse(BaseModel):
    """Typing Indicator."""
    type: Literal["typing"] = "typing"
    session_id: str
    agent: Literal["a", "b", "evaluator"]
    agent_name: str


class EvaluationScores(BaseModel):
    """Bewertungs-Scores."""
    escalation_level: int  # 0-10
    resolution_progress: int  # 0-10
    communication_quality_a: int  # 0-10
    communication_quality_b: int  # 0-10


class EvaluationResponse(BaseModel):
    """Evaluierung/Coach-Feedback."""
    type: Literal["evaluation"] = "evaluation"
    session_id: str
    content: str
    scores: EvaluationScores


class SessionStartedResponse(BaseModel):
    """Session wurde gestartet."""
    type: Literal["session_started"] = "session_started"
    session_id: str


class ErrorResponse(BaseModel):
    """Fehler."""
    type: Literal["error"] = "error"
    message: str


class InterruptedResponse(BaseModel):
    """Session wurde unterbrochen (User greift ein)."""
    type: Literal["interrupted"] = "interrupted"
    session_id: str
    message: str = "Session unterbrochen - Du kannst jetzt eingreifen"


class MessageAnalysisResponse(BaseModel):
    """Analyse einer einzelnen Nachricht."""
    type: Literal["message_analysis"] = "message_analysis"
    message_id: str
    analysis: str
    analysis_type: Literal["party", "mediator"]  # Welche Art von Analyse


# === Scenario REST API Schemas ===

class ScenarioCreate(BaseModel):
    """Request zum Erstellen eines neuen Szenarios."""
    name: str
    scenario_text: str
    agent_a_name: str
    agent_a_prompt: str
    agent_b_name: str
    agent_b_prompt: str


class ScenarioUpdate(BaseModel):
    """Request zum Aktualisieren eines Szenarios."""
    name: Optional[str] = None
    scenario_text: Optional[str] = None
    agent_a_name: Optional[str] = None
    agent_a_prompt: Optional[str] = None
    agent_b_name: Optional[str] = None
    agent_b_prompt: Optional[str] = None


class ScenarioResponse(BaseModel):
    """Response für ein Szenario."""
    id: str
    name: str
    scenario_text: str
    agent_a_name: str
    agent_a_prompt: str
    agent_b_name: str
    agent_b_prompt: str
    is_preset: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """Response für Liste von Szenarien."""
    scenarios: list[ScenarioResponse]
    total: int
