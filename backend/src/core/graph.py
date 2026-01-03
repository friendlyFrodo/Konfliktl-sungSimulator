"""LangGraph State Machine für die Konfliktsimulation."""

import uuid
import logging
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

# Logging konfigurieren
logger = logging.getLogger("konflikt.graph")
logger.setLevel(logging.DEBUG)


class ConflictSimulator:
    """Orchestriert die Konfliktsimulation mit LangGraph."""

    def __init__(self):
        self.memory = MemorySaver()
        self.graph = self._build_graph()
        self.sessions: dict[str, SimulationState] = {}
        # Interrupt-Flags für aktive Streams
        self._interrupt_flags: dict[str, bool] = {}

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

        # Initiale Nachrichten - mindestens eine HumanMessage für die Claude API
        if scenario:
            # Szenario als Kontext für den Konflikt
            initial_messages = [
                HumanMessage(content=f"[SZENARIO: {scenario}]\n\nBitte beginne das Gespräch.", name="system")
            ]
        else:
            # Default: einfacher Start-Prompt
            initial_messages = [
                HumanMessage(content="Bitte beginne das Gespräch. Du bist in einem Konflikt mit der anderen Person.", name="system")
            ]

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

    def interrupt_session(self, session_id: str) -> bool:
        """Unterbricht eine laufende Session sofort.

        Args:
            session_id: Session ID

        Returns:
            True bei Erfolg
        """
        if session_id in self.sessions:
            self._interrupt_flags[session_id] = True
            self.sessions[session_id]["should_stop"] = True
            logger.info(f"[{session_id[:8]}] 🛑 Interrupt-Signal gesetzt")
            return True
        return False

    def _clean_agent_response(self, content: str, agent_name: str) -> str:
        """Bereinigt die Agent-Antwort und entfernt doppelte Namen.

        Das Modell antwortet manchmal mit "Name: Text" oder nur mit "Name:",
        was zu leeren oder doppelten Namen führt.
        """
        content = content.strip()

        # Entferne führenden Namen wenn vorhanden (mit verschiedenen Varianten)
        prefixes_to_remove = [
            f"{agent_name}:",
            f"{agent_name.lower()}:",
            f"{agent_name.upper()}:",
            f"**{agent_name}**:",
            f"*{agent_name}*:",
        ]

        for prefix in prefixes_to_remove:
            if content.lower().startswith(prefix.lower()):
                content = content[len(prefix):].strip()
                logger.debug(f"Entfernt Präfix '{prefix}' von Antwort")
                break

        return content

    async def run_with_streaming(
        self,
        session_id: str,
    ) -> AsyncIterator[dict]:
        """Führt den Graphen mit Token-Streaming aus.

        Yields:
            Streaming-Events während der Ausführung
        """
        if session_id not in self.sessions:
            logger.error(f"[{session_id[:8]}] Session nicht gefunden")
            yield {"type": "error", "message": "Session not found"}
            return

        # Interrupt-Flag initialisieren
        self._interrupt_flags[session_id] = False

        state = self.sessions[session_id]
        next_speaker = state.get("next_speaker", "agent_a")

        logger.info(f"[{session_id[:8]}] ▶️ Streaming gestartet, nächster Sprecher: {next_speaker}")

        while next_speaker not in ["human", "evaluator", "end"]:
            # Prüfe Interrupt
            if self._interrupt_flags.get(session_id, False):
                logger.info(f"[{session_id[:8]}] 🛑 Interrupt erkannt, breche ab")
                next_speaker = "evaluator"
                break

            if state.get("should_stop"):
                logger.info(f"[{session_id[:8]}] should_stop=True, wechsle zu Evaluator")
                next_speaker = "evaluator"
                break

            # Typing-Indikator
            if next_speaker == "agent_a":
                agent_name = state["agent_a_config"]["name"]
                logger.info(f"[{session_id[:8]}] 💬 Agent A ({agent_name}) beginnt...")
                yield {
                    "type": "typing",
                    "agent": "a",
                    "agent_name": agent_name,
                }

                # Streaming mit Interrupt-Prüfung
                full_content = ""
                chunk_count = 0
                async for chunk, is_final in agent_a_node_streaming(state):
                    # Interrupt-Check während Streaming
                    if self._interrupt_flags.get(session_id, False):
                        logger.info(f"[{session_id[:8]}] 🛑 Streaming unterbrochen für Agent A")
                        break

                    if is_final:
                        full_content = chunk
                    else:
                        chunk_count += 1
                        yield {
                            "type": "streaming_chunk",
                            "agent": "a",
                            "agent_name": agent_name,
                            "chunk": chunk,
                            "is_final": False,
                        }

                # Bereinige Antwort
                cleaned_content = self._clean_agent_response(full_content, agent_name)

                logger.info(f"[{session_id[:8]}] ✅ Agent A fertig: {chunk_count} Chunks, {len(cleaned_content)} Zeichen")
                logger.debug(f"[{session_id[:8]}] 📝 Agent A RAW: {full_content[:200]}...")
                logger.debug(f"[{session_id[:8]}] 📝 Agent A CLEANED: {cleaned_content[:200]}...")

                # Validierung: Leere Antwort?
                if not cleaned_content:
                    logger.warning(f"[{session_id[:8]}] ⚠️ Leere Antwort von Agent A!")

                # Finale Nachricht
                state["messages"].append(
                    AIMessage(content=f"{agent_name}: {cleaned_content}", name="agent_a")
                )
                state["turns"] += 1

                yield {
                    "type": "agent_message",
                    "agent": "a",
                    "agent_name": agent_name,
                    "content": cleaned_content,
                }

            elif next_speaker == "agent_b":
                agent_name = state["agent_b_config"]["name"]
                logger.info(f"[{session_id[:8]}] 💬 Agent B ({agent_name}) beginnt...")
                yield {
                    "type": "typing",
                    "agent": "b",
                    "agent_name": agent_name,
                }

                full_content = ""
                chunk_count = 0
                async for chunk, is_final in agent_b_node_streaming(state):
                    # Interrupt-Check
                    if self._interrupt_flags.get(session_id, False):
                        logger.info(f"[{session_id[:8]}] 🛑 Streaming unterbrochen für Agent B")
                        break

                    if is_final:
                        full_content = chunk
                    else:
                        chunk_count += 1
                        yield {
                            "type": "streaming_chunk",
                            "agent": "b",
                            "agent_name": agent_name,
                            "chunk": chunk,
                            "is_final": False,
                        }

                # Bereinige Antwort
                cleaned_content = self._clean_agent_response(full_content, agent_name)

                logger.info(f"[{session_id[:8]}] ✅ Agent B fertig: {chunk_count} Chunks, {len(cleaned_content)} Zeichen")
                logger.debug(f"[{session_id[:8]}] 📝 Agent B RAW: {full_content[:200]}...")
                logger.debug(f"[{session_id[:8]}] 📝 Agent B CLEANED: {cleaned_content[:200]}...")

                if not cleaned_content:
                    logger.warning(f"[{session_id[:8]}] ⚠️ Leere Antwort von Agent B!")

                state["messages"].append(
                    AIMessage(content=f"{agent_name}: {cleaned_content}", name="agent_b")
                )
                state["turns"] += 1

                yield {
                    "type": "agent_message",
                    "agent": "b",
                    "agent_name": agent_name,
                    "content": cleaned_content,
                }

            # Nächsten Sprecher bestimmen (mit intelligentem LLM-Routing)
            logger.debug(f"[{session_id[:8]}] 🔀 Router wird aufgerufen...")
            next_speaker = await smart_route_next_speaker(state)
            state["next_speaker"] = next_speaker
            logger.info(f"[{session_id[:8]}] 🔀 Router-Entscheidung: {next_speaker}")

        # Evaluator mit Streaming
        if next_speaker == "evaluator":
            logger.info(f"[{session_id[:8]}] 📊 Evaluator startet...")
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

            logger.info(f"[{session_id[:8]}] 📊 Evaluator fertig: {len(full_content)} Zeichen")
            logger.debug(f"[{session_id[:8]}] 📝 Evaluator: {full_content[:300]}...")

            state["messages"].append(
                AIMessage(content=f"COACH: {full_content.strip()}", name="evaluator")
            )

            yield {
                "type": "evaluation",
                "content": full_content,
            }

        # Cleanup
        if session_id in self._interrupt_flags:
            del self._interrupt_flags[session_id]

        # State speichern
        self.sessions[session_id] = state

        # Prüfen ob Human-Input erwartet wird
        if next_speaker == "human":
            logger.info(f"[{session_id[:8]}] ⏸️ Warte auf User-Input")
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
