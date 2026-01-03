"""Agent Nodes für die LangGraph State Machine."""

import os
from pathlib import Path
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from typing import AsyncIterator

from .state import SimulationState

# Prompts laden
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str) -> str:
    """Lädt einen Prompt aus einer Datei."""
    prompt_path = PROMPTS_DIR / filename
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return ""


DEFAULT_AGENT_A_PROMPT = load_prompt("agent_a_default.txt")
DEFAULT_AGENT_B_PROMPT = load_prompt("agent_b_default.txt")
EVALUATOR_PROMPT = load_prompt("evaluator.txt")


def get_llm(streaming: bool = True) -> ChatAnthropic:
    """Erstellt eine Claude-Instanz."""
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=0.7,
        streaming=streaming,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


async def agent_a_node(state: SimulationState) -> dict:
    """Node für Agent A."""
    llm = get_llm(streaming=False)

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
        "messages": [AIMessage(content=f"{agent_name}: {response.content}", name="agent_a")],
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
    llm = get_llm(streaming=True)

    config = state["agent_a_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_A_PROMPT
    agent_name = config.get("name", "Agent A")

    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *state["messages"]
    ]

    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content
            yield (chunk.content, False)

    yield (full_response, True)


async def agent_b_node(state: SimulationState) -> dict:
    """Node für Agent B."""
    llm = get_llm(streaming=False)

    config = state["agent_b_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_B_PROMPT
    agent_name = config.get("name", "Agent B")

    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *state["messages"]
    ]

    response = await llm.ainvoke(messages)

    return {
        "messages": [AIMessage(content=f"{agent_name}: {response.content}", name="agent_b")],
        "turns": state["turns"] + 1,
        "streaming_content": None,
    }


async def agent_b_node_streaming(
    state: SimulationState,
) -> AsyncIterator[tuple[str, bool]]:
    """Streaming-Version von Agent B Node."""
    llm = get_llm(streaming=True)

    config = state["agent_b_config"]
    system_prompt = config.get("prompt") or DEFAULT_AGENT_B_PROMPT
    agent_name = config.get("name", "Agent B")

    messages = [
        SystemMessage(content=f"{system_prompt}\n\nDein Name ist {agent_name}."),
        *state["messages"]
    ]

    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content
            yield (chunk.content, False)

    yield (full_response, True)


async def evaluator_node(state: SimulationState) -> dict:
    """Evaluator Node für Coach-Feedback."""
    llm = get_llm(streaming=False)

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
        "messages": [AIMessage(content=f"COACH: {response.content}", name="evaluator")],
    }


async def evaluator_node_streaming(
    state: SimulationState,
) -> AsyncIterator[tuple[str, bool]]:
    """Streaming-Version des Evaluator Node."""
    llm = get_llm(streaming=True)

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

    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content
            yield (chunk.content, False)

    yield (full_response, True)
