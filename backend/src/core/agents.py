"""Agent Nodes für die LangGraph State Machine."""

import os
import logging
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import AsyncIterator

from .state import SimulationState

# Logging
logger = logging.getLogger("konflikt.agents")
logger.setLevel(logging.DEBUG)

# Prompts laden
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Modell-Konfiguration
# Sonnet 4.5 für alle Aufgaben
AGENT_MODEL = "claude-sonnet-4-5"
ROUTER_MODEL = "claude-sonnet-4-5"


def load_prompt(filename: str) -> str:
    """Lädt einen Prompt aus einer Datei."""
    prompt_path = PROMPTS_DIR / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return ""


DEFAULT_AGENT_A_PROMPT = load_prompt("agent_a_default.txt")
DEFAULT_AGENT_B_PROMPT = load_prompt("agent_b_default.txt")
EVALUATOR_PROMPT = load_prompt("evaluator.txt")


def get_agent_llm(streaming: bool = True) -> ChatAnthropic:
    """Erstellt eine Claude-Instanz für Roleplay-Agenten (Sonnet 4.5)."""
    return ChatAnthropic(
        model=AGENT_MODEL,
        temperature=0.7,
        streaming=streaming,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def get_router_llm() -> ChatAnthropic:
    """Erstellt eine Claude-Instanz für Router-Entscheidungen (Haiku)."""
    return ChatAnthropic(
        model=ROUTER_MODEL,
        temperature=0.0,  # Deterministischer für Routing
        streaming=False,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


async def agent_a_node(state: SimulationState) -> dict:
    """Node für Agent A."""
    llm = get_agent_llm(streaming=False)

    config = state["agent_a_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_A_PROMPT
    agent_name = config.get("name", "Agent A")

    # System-Nachricht mit Kontext
    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *state["messages"]
    ]

    response = await llm.ainvoke(messages)

    return {
        "messages": [AIMessage(content=f"{agent_name}: {response.content.strip()}", name="agent_a")],
        "turns": state["turns"] + 1,
        "streaming_content": None,
    }


async def agent_a_node_streaming(
    state: SimulationState,
) -> AsyncIterator[tuple[str, bool]]:
    """Streaming-Version von Agent A Node.

    Yields:
        Tuple von (chunk, is_final)
    """
    llm = get_agent_llm(streaming=True)

    config = state["agent_a_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_A_PROMPT
    agent_name = config.get("name", "Agent A")

    # Konvertiere Nachrichten: Agent A's eigene = AIMessage, andere = HumanMessage
    cleaned_messages = []
    for msg in state["messages"]:
        content = msg.content.rstrip() if hasattr(msg, 'content') else ""
        msg_name = getattr(msg, 'name', None)

        # Agent A's eigene Nachrichten bleiben AIMessage
        if msg_name == "agent_a":
            cleaned_messages.append(AIMessage(content=content, name=msg_name))
        # Alle anderen (agent_b, mediator, system) werden HumanMessage
        elif isinstance(msg, AIMessage):
            cleaned_messages.append(HumanMessage(content=content, name=msg_name))
        else:
            cleaned_messages.append(HumanMessage(content=content, name=msg_name))

    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *cleaned_messages
    ]

    logger.debug(f"Agent A: {len(messages)} Nachrichten im Kontext")

    full_response = ""
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                full_response += chunk.content
                yield (chunk.content, False)
    except Exception as e:
        logger.error(f"Agent A Streaming-Fehler: {e}")
        raise

    if not full_response:
        logger.warning(f"Agent A: Leere Antwort erhalten!")

    yield (full_response, True)


async def agent_b_node(state: SimulationState) -> dict:
    """Node für Agent B."""
    llm = get_agent_llm(streaming=False)

    config = state["agent_b_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_B_PROMPT
    agent_name = config.get("name", "Agent B")

    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *state["messages"]
    ]

    response = await llm.ainvoke(messages)

    return {
        "messages": [AIMessage(content=f"{agent_name}: {response.content.strip()}", name="agent_b")],
        "turns": state["turns"] + 1,
        "streaming_content": None,
    }


async def agent_b_node_streaming(
    state: SimulationState,
) -> AsyncIterator[tuple[str, bool]]:
    """Streaming-Version von Agent B Node."""
    llm = get_agent_llm(streaming=True)

    config = state["agent_b_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_B_PROMPT
    agent_name = config.get("name", "Agent B")

    # Konvertiere Nachrichten: Agent B's eigene = AIMessage, andere = HumanMessage
    cleaned_messages = []
    for msg in state["messages"]:
        content = msg.content.rstrip() if hasattr(msg, 'content') else ""
        msg_name = getattr(msg, 'name', None)

        # Agent B's eigene Nachrichten bleiben AIMessage
        if msg_name == "agent_b":
            cleaned_messages.append(AIMessage(content=content, name=msg_name))
        # Alle anderen (agent_a, mediator, system) werden HumanMessage
        elif isinstance(msg, AIMessage):
            cleaned_messages.append(HumanMessage(content=content, name=msg_name))
        else:
            cleaned_messages.append(HumanMessage(content=content, name=msg_name))

    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *cleaned_messages
    ]

    logger.debug(f"Agent B: {len(messages)} Nachrichten im Kontext")
    logger.debug(f"Agent B: Name={agent_name}, Prompt={system_prompt[:100]}...")
    # Log ALLE Nachrichten für Debugging
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        content_preview = msg.content[:80].replace('\n', ' ') if msg.content else 'LEER'
        logger.debug(f"Agent B Msg[{i}] ({msg_type}): {content_preview}...")

    full_response = ""
    chunk_count = 0
    try:
        async for chunk in llm.astream(messages):
            chunk_count += 1
            # Log jeden Chunk mit repr() um Whitespace zu sehen
            logger.debug(f"Agent B Chunk {chunk_count}: content={repr(chunk.content)}, metadata={chunk.response_metadata}")
            if chunk.content:
                full_response += chunk.content
                yield (chunk.content, False)
    except Exception as e:
        logger.error(f"Agent B Streaming-Fehler: {e}")
        raise

    logger.debug(f"Agent B: {chunk_count} Chunks empfangen, full_response={repr(full_response[:200]) if full_response else 'LEER'}")

    if not full_response:
        logger.warning(f"Agent B: Leere Antwort! Versuche non-streaming...")
        # Fallback: Non-streaming um Fehler zu sehen
        try:
            non_stream_llm = get_agent_llm(streaming=False)
            response = await non_stream_llm.ainvoke(messages)
            logger.info(f"Agent B Non-Stream Response: {repr(response.content[:200]) if response.content else 'AUCH LEER'}")
            if response.content:
                full_response = response.content
                yield (full_response, False)
        except Exception as e:
            logger.error(f"Agent B Non-Stream Fehler: {e}")

    yield (full_response, True)


async def evaluator_node(state: SimulationState) -> dict:
    """Evaluator Node für Coach-Feedback."""
    llm = get_agent_llm(streaming=False)

    agent_a_name = state["agent_a_config"].get("name", "Agent A")
    agent_b_name = state["agent_b_config"].get("name", "Agent B")

    context = f"""
Die Teilnehmer sind:
- {agent_a_name}
- {agent_b_name}

Analysiere den folgenden Gesprächsverlauf und gib strukturiertes Feedback.
Gib am Ende deine Bewertung in diesem Format:

BEWERTUNG:
- Eskalationslevel: X/10
- Lösungsfortschritt: X/10
- Kommunikationsqualität {agent_a_name}: X/10
- Kommunikationsqualität {agent_b_name}: X/10
"""

    messages = [
        SystemMessage(content=EVALUATOR_PROMPT + context),
        *state["messages"]
    ]

    response = await llm.ainvoke(messages)

    return {
        "messages": [AIMessage(content=f"COACH: {response.content.strip()}", name="evaluator")],
    }


async def evaluator_node_streaming(
    state: SimulationState,
) -> AsyncIterator[tuple[str, bool]]:
    """Streaming-Version des Evaluator Node."""
    llm = get_agent_llm(streaming=True)

    agent_a_name = state["agent_a_config"].get("name", "Agent A")
    agent_b_name = state["agent_b_config"].get("name", "Agent B")

    context = f"""
Die Teilnehmer sind:
- {agent_a_name}
- {agent_b_name}

Analysiere den folgenden Gesprächsverlauf und gib strukturiertes Feedback.
Gib am Ende deine Bewertung in diesem Format:

BEWERTUNG:
- Eskalationslevel: X/10
- Lösungsfortschritt: X/10
- Kommunikationsqualität {agent_a_name}: X/10
- Kommunikationsqualität {agent_b_name}: X/10
"""

    # Strip any trailing whitespace from previous messages to avoid API errors
    cleaned_messages = []
    for msg in state["messages"]:
        content = msg.content.rstrip() if hasattr(msg, 'content') else ""
        if isinstance(msg, AIMessage):
            cleaned_messages.append(AIMessage(content=content, name=getattr(msg, 'name', None)))
        elif isinstance(msg, HumanMessage):
            cleaned_messages.append(HumanMessage(content=content, name=getattr(msg, 'name', None)))
        else:
            cleaned_messages.append(msg)

    messages = [
        SystemMessage(content=EVALUATOR_PROMPT + context),
        *cleaned_messages
    ]

    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content
            yield (chunk.content, False)

    yield (full_response, True)
