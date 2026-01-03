"""LangGraph State Definition für die Konfliktsimulation."""

from typing import TypedDict, Annotated, Literal, Optional
from langchain_core.messages import BaseMessage
import operator


class AgentConfig(TypedDict):
    """Konfiguration für einen Agenten."""
    name: str
    prompt: str


class SimulationState(TypedDict):
    """State für die LangGraph State Machine.

    Attributes:
        messages: Liste aller Nachrichten im Gespräch
        session_id: Eindeutige ID der Session
        mode: Modus der Simulation (mediator oder participant)
        next_speaker: Wer ist als nächstes dran
        turns: Anzahl der bisherigen Turns
        agent_a_config: Konfiguration für Agent A
        agent_b_config: Konfiguration für Agent B
        user_role: Bei participant-Modus: welche Rolle der User übernimmt
        should_stop: Flag ob der User die Simulation stoppen möchte
        streaming_content: Aktueller Streaming-Content (für Echtzeit-Updates)
    """
    messages: Annotated[list[BaseMessage], operator.add]
    session_id: str
    mode: Literal["mediator", "participant"]
    next_speaker: Literal["agent_a", "agent_b", "human", "evaluator"]
    turns: int
    agent_a_config: AgentConfig
    agent_b_config: AgentConfig
    user_role: Optional[Literal["agent_a", "agent_b"]]
    should_stop: bool
    streaming_content: Optional[str]
