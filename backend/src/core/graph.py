"""LangGraph State Machine für die Konfliktsimulation."""

import uuid
from typing import AsyncIterator, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from .state import SimulationState, AgentConfig
from .agents import (
    agent_a_node,
    agent_b_node,
    evaluator_node,
    agent_a_node_streaming,
    agent_b_node_streaming,
    evaluator_node_streaming,
)
from .router import route_next_speaker, should_continue, determine_expected_role, smart_route_next_speaker


class ConflictSimulator:
    """Orchestriert die Konfliktsimulation mit LangGraph."""

    def __init__(self):
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self.sessions: dict[str, SimulationState] = {}

    def _build_graph(self) -> StateGraph:
        """Baut den LangGraph Graphen."""
        workflow = StateGraph(SimulationState)

        # Nodes hinzufügen
        workflow.add_node("agent_a", agent_a_node)
        workflow.add_node("agent_b", agent_b_node)
        workflow.add_node("evaluator", evaluator_node)

        # Entry Point
        workflow.set_entry_point("agent_a")

        # Conditional Edges basierend auf Router
        workflow.add_conditional_edges(
            "agent_a",
            self._route_from_agent,
            {
                "agent_b": "agent_b",
                "human": END,  # Pause für Human Input
                "evaluator": "evaluator",
                "end": END,
            }
        )

        workflow.add_conditional_edges(
            "agent_b",
            self._route_from_agent,
            {
                "agent_a": "agent_a",
                "human": END,
                "evaluator": "evaluator",
                "end": END,
            }
        )

        # Evaluator führt immer zu END
        workflow.add_edge("evaluator", END)

        return workflow.compile(checkpointer=self.memory)

    def _route_from_agent(self, state: SimulationState) -> str:
        """Router-Funktion für conditional edges."""
        result = should_continue(state)

        if result == "continue":
            return route_next_speaker(state)
        elif result == "wait_for_human":
            return "human"
        elif result == "evaluate":
            return "evaluator"
        else:
            return "end"

    async def start_session(
        self,
        mode: str,
        agent_a_config: AgentConfig,
        agent_b_config: AgentConfig,
        scenario: Optional[str] = None,
        user_role: Optional[str] = None,
    ) -> tuple[str, SimulationState]:
        """Startet eine neue Session.

        Args:
            mode: "mediator" oder "participant"
            agent_a_config: Konfiguration für Agent A
            agent_b_config: Konfiguration für Agent B
            scenario: Optionaler Kontext/Szenario
            user_role: Bei participant: welche Rolle der User übernimmt

        Returns:
            Tuple von (session_id, initial_state)
        """
        session_id = str(uuid.uuid4())

        initial_messages = []
        if scenario:
            # Szenario als System-Kontext
            initial_messages.append(
                HumanMessage(content=f"[SZENARIO: {scenario}]", name="system")
            )

        initial_state: SimulationState = {
            "messages": initial_messages,
            "session_id": session_id,
            "mode": mode,
            "next_speaker": "agent_a",
            "turns": 0,
            "agent_a_config": agent_a_config,
            "agent_b_config": agent_b_config,
            "user_role": user_role,
            "should_stop": False,
            "streaming_content": None,
        }

        self.sessions[session_id] = initial_state
        return session_id, initial_state

    async def run_until_human(
        self,
        session_id: str,
    ) -> AsyncIterator[dict]:
        """Führt den Graphen aus bis Human-Input benötigt wird.

        Yields:
            Events während der Ausführung (für Streaming)
        """
        if session_id not in self.sessions:
            yield {"type": "error", "message": "Session not found"}
            return

        config = {"configurable": {"thread_id": session_id}}
        state = self.sessions[session_id]

        async for event in self.graph.astream(state, config):
            # Event-Typ bestimmen
            for node_name, node_output in event.items():
                if node_name == "agent_a":
                    yield {
                        "type": "agent_message",
                        "agent": "a",
                        "agent_name": state["agent_a_config"]["name"],
                        "content": node_output["messages"][-1].content if node_output.get("messages") else "",
                    }
                elif node_name == "agent_b":
                    yield {
                        "type": "agent_message",
                        "agent": "b",
                        "agent_name": state["agent_b_config"]["name"],
                        "content": node_output["messages"][-1].content if node_output.get("messages") else "",
                    }
                elif node_name == "evaluator":
                    yield {
                        "type": "evaluation",
                        "content": node_output["messages"][-1].content if node_output.get("messages") else "",
                    }

            # State aktualisieren
            if event:
                for node_output in event.values():
                    if isinstance(node_output, dict):
                        for key, value in node_output.items():
                            if key == "messages" and value:
                                state["messages"].extend(value)
                            elif key in state:
                                state[key] = value

        # Aktuellen State speichern
        self.sessions[session_id] = state

        # Prüfen ob Human-Input erwartet wird
        next_speaker = route_next_speaker(state)
        if next_speaker == "human":
            yield {
                "type": "waiting_for_input",
                "expected_role": determine_expected_role(state),
            }

    async def run_with_streaming(
        self,
        session_id: str,
    ) -> AsyncIterator[dict]:
        """Führt den Graphen mit Token-Streaming aus.

        Yields:
            Streaming-Events während der Ausführung
        """
        if session_id not in self.sessions:
            yield {"type": "error", "message": "Session not found"}
            return

        state = self.sessions[session_id]
        next_speaker = state.get("next_speaker", "agent_a")

        while next_speaker not in ["human", "evaluator", "end"]:
            if state.get("should_stop"):
                next_speaker = "evaluator"
                break

            # Typing-Indikator
            if next_speaker == "agent_a":
                yield {
                    "type": "typing",
                    "agent": "a",
                    "agent_name": state["agent_a_config"]["name"],
                }

                # Streaming
                full_content = ""
                async for chunk, is_final in agent_a_node_streaming(state):
                    if is_final:
                        full_content = chunk
                    else:
                        yield {
                            "type": "streaming_chunk",
                            "agent": "a",
                            "agent_name": state["agent_a_config"]["name"],
                            "chunk": chunk,
                            "is_final": False,
                        }

                # Finale Nachricht
                agent_name = state["agent_a_config"]["name"]
                state["messages"].append(
                    AIMessage(content=f"{agent_name}: {full_content}", name="agent_a")
                )
                state["turns"] += 1

                yield {
                    "type": "agent_message",
                    "agent": "a",
                    "agent_name": agent_name,
                    "content": f"{agent_name}: {full_content}",
                }

            elif next_speaker == "agent_b":
                yield {
                    "type": "typing",
                    "agent": "b",
                    "agent_name": state["agent_b_config"]["name"],
                }

                full_content = ""
                async for chunk, is_final in agent_b_node_streaming(state):
                    if is_final:
                        full_content = chunk
                    else:
                        yield {
                            "type": "streaming_chunk",
                            "agent": "b",
                            "agent_name": state["agent_b_config"]["name"],
                            "chunk": chunk,
                            "is_final": False,
                        }

                agent_name = state["agent_b_config"]["name"]
                state["messages"].append(
                    AIMessage(content=f"{agent_name}: {full_content}", name="agent_b")
                )
                state["turns"] += 1

                yield {
                    "type": "agent_message",
                    "agent": "b",
                    "agent_name": agent_name,
                    "content": f"{agent_name}: {full_content}",
                }

            # Nächsten Sprecher bestimmen (mit intelligentem LLM-Routing)
            next_speaker = await smart_route_next_speaker(state)
            state["next_speaker"] = next_speaker

        # Evaluator mit Streaming
        if next_speaker == "evaluator":
            yield {
                "type": "typing",
                "agent": "evaluator",
                "agent_name": "Coach",
            }

            full_content = ""
            async for chunk, is_final in evaluator_node_streaming(state):
                if is_final:
                    full_content = chunk
                else:
                    yield {
                        "type": "streaming_chunk",
                        "agent": "evaluator",
                        "agent_name": "Coach",
                        "chunk": chunk,
                        "is_final": False,
                    }

            state["messages"].append(
                AIMessage(content=f"COACH: {full_content}", name="evaluator")
            )

            yield {
                "type": "evaluation",
                "content": f"COACH: {full_content}",
            }

        # State speichern
        self.sessions[session_id] = state

        # Prüfen ob Human-Input erwartet wird
        if next_speaker == "human":
            yield {
                "type": "waiting_for_input",
                "expected_role": determine_expected_role(state),
            }

    async def add_human_message(
        self,
        session_id: str,
        content: str,
        role: str,
    ) -> bool:
        """Fügt eine Human-Nachricht hinzu.

        Args:
            session_id: Session ID
            content: Nachricht
            role: Rolle (mediator, agent_a, agent_b)

        Returns:
            True bei Erfolg
        """
        if session_id not in self.sessions:
            return False

        state = self.sessions[session_id]

        # Nachricht hinzufügen
        if role == "mediator":
            state["messages"].append(
                HumanMessage(content=f"[MEDIATOR]: {content}", name="mediator")
            )
            # Nach Mediator-Input reagiert ein Agent
            state["next_speaker"] = "agent_a"
        elif role == "agent_a":
            agent_name = state["agent_a_config"]["name"]
            state["messages"].append(
                HumanMessage(content=f"{agent_name}: {content}", name="agent_a")
            )
            state["next_speaker"] = "agent_b"
        elif role == "agent_b":
            agent_name = state["agent_b_config"]["name"]
            state["messages"].append(
                HumanMessage(content=f"{agent_name}: {content}", name="agent_b")
            )
            state["next_speaker"] = "agent_a"

        self.sessions[session_id] = state
        return True

    async def stop_session(self, session_id: str) -> bool:
        """Markiert eine Session zum Stoppen.

        Args:
            session_id: Session ID

        Returns:
            True bei Erfolg
        """
        if session_id not in self.sessions:
            return False

        self.sessions[session_id]["should_stop"] = True
        return True

    def get_session_state(self, session_id: str) -> Optional[SimulationState]:
        """Gibt den aktuellen State einer Session zurück."""
        return self.sessions.get(session_id)


# Globale Instanz
simulator = ConflictSimulator()
