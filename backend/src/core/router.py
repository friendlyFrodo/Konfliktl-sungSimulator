"""Router-Logik für die LangGraph State Machine.

Entscheidet, wer als nächstes sprechen soll.
"""

from typing import Literal
from langchain_core.messages import HumanMessage

from .state import SimulationState


def route_next_speaker(state: SimulationState) -> Literal["agent_a", "agent_b", "human", "evaluator", "end"]:
    """Entscheidet, wer als nächstes dran ist.

    Logik:
    1. Wenn should_stop=True -> evaluator (für Abschluss-Feedback)
    2. Wenn next_speaker explizit gesetzt -> diesen verwenden
    3. Sonst: Abwechselnde Konversation mit Human-Intervention

    Args:
        state: Aktueller State der Simulation

    Returns:
        Der nächste Sprecher
    """
    # User möchte stoppen -> Evaluator für Abschluss
    if state.get("should_stop", False):
        return "evaluator"

    # Explizit gesetzter nächster Sprecher
    next_speaker = state.get("next_speaker")
    if next_speaker:
        return next_speaker

    # Fallback: Basierend auf letzter Nachricht entscheiden
    messages = state.get("messages", [])
    if not messages:
        return "agent_a"  # Start mit Agent A

    last_message = messages[-1]
    mode = state.get("mode", "mediator")

    # Wer hat zuletzt gesprochen?
    last_speaker = getattr(last_message, "name", None)

    if mode == "mediator":
        # Mediator-Modus: Agenten sprechen miteinander, Human interveniert
        if last_speaker == "agent_a":
            # Nach A kommt B
            return "agent_b"
        elif last_speaker == "agent_b":
            # Nach B kommt entweder A oder Human darf eingreifen
            # Alle 3-4 Turns bekommt der Mediator die Chance einzugreifen
            if state.get("turns", 0) % 4 == 0:
                return "human"
            return "agent_a"
        elif isinstance(last_message, HumanMessage):
            # Nach Human-Input reagiert der Agent, der angesprochen wurde
            # Default: Agent A reagiert auf Mediator
            return "agent_a"
        else:
            return "agent_a"

    elif mode == "participant":
        # Participant-Modus: User übernimmt eine Rolle
        user_role = state.get("user_role")

        if user_role == "agent_a":
            # User ist Agent A -> B ist KI
            if last_speaker == "agent_b" or isinstance(last_message, HumanMessage):
                return "agent_b"
            else:
                return "human"  # User (als A) ist dran
        elif user_role == "agent_b":
            # User ist Agent B -> A ist KI
            if last_speaker == "agent_a" or isinstance(last_message, HumanMessage):
                return "agent_a"
            else:
                return "human"  # User (als B) ist dran
        else:
            # Fallback
            return "agent_a"

    return "agent_a"


def should_continue(state: SimulationState) -> Literal["continue", "wait_for_human", "evaluate", "end"]:
    """Entscheidet ob der Graph weiterlaufen soll.

    Returns:
        - "continue": Graph läuft weiter
        - "wait_for_human": Pause für User-Input
        - "evaluate": Evaluator aufrufen
        - "end": Graph beenden
    """
    if state.get("should_stop", False):
        return "evaluate"

    next_speaker = route_next_speaker(state)

    if next_speaker == "human":
        return "wait_for_human"
    elif next_speaker == "evaluator":
        return "evaluate"
    elif next_speaker == "end":
        return "end"
    else:
        return "continue"


def determine_expected_role(state: SimulationState) -> Literal["mediator", "agent_a", "agent_b"]:
    """Bestimmt welche Rolle vom User erwartet wird.

    Returns:
        Die erwartete Rolle des Users
    """
    mode = state.get("mode", "mediator")

    if mode == "mediator":
        return "mediator"
    elif mode == "participant":
        user_role = state.get("user_role")
        if user_role == "agent_a":
            return "agent_a"
        elif user_role == "agent_b":
            return "agent_b"

    return "mediator"
