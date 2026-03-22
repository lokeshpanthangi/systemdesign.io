"""
Chat Agent Graph
LangGraph graph for the sidebar AI chat agent.
Uses the prebuilt ToolNode — no custom tool dispatcher needed.
"""
from typing import Dict, Any

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition

from Agents.chat_agent.state import ChatAgentState
from Agents.chat_agent.tools.tools import create_chat_tools
from Agents.prompts.chat_agent_prompt import CHAT_AGENT_SYSTEM_PROMPT
from core.llm_provider import get_llm


def create_chat_agent_graph(
    problem_title: str,
    problem_description: str,
    problem_requirements: str,
    diagram_data: dict
):
    """
    Create and compile the chat agent graph for a given session context.

    Returns:
        Compiled LangGraph graph ready for streaming.
        compiled._streamed_diagram_batches collects diagram element
        batches for the SSE stream.
    """
    # Diagram element batches — tools write to this, chatbot.py reads from it
    streamed_batches: list = []

    # Create tools with session context baked in
    chat_tools = create_chat_tools(
        problem_title=problem_title,
        problem_description=problem_description,
        problem_requirements=problem_requirements,
        diagram_data=diagram_data,
        streamed_batches=streamed_batches,
    )

    # Initialize LLM via centralized provider (GitHub Copilot API)
    model = get_llm(temperature=0.2, streaming=True)
    model_with_tools = model.bind_tools(chat_tools)

    # Format system prompt
    system_prompt = CHAT_AGENT_SYSTEM_PROMPT.format(
        problem_title=problem_title,
        problem_description=problem_description,
        problem_requirements=problem_requirements
    )

    # --- Node: Agent (LLM call) ---
    async def agent_node(state: ChatAgentState) -> Dict[str, Any]:
        """Call the LLM with messages and tools."""
        messages = state["messages"]

        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + list(messages)

        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # --- Build Graph ---
    graph = StateGraph(ChatAgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(chat_tools))

    graph.set_entry_point("agent")

    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")

    compiled = graph.compile()
    # recursion_limit = 25 → supports ~10 tool calls
    # Each tool call = 2 graph steps (agent → tools → agent).
    # 10 tool calls × 2 = 20 steps + 1 initial agent + 1 final = 22 max. 25 is a safe ceiling.
    compiled.recursion_limit = 25
    compiled._streamed_diagram_batches = streamed_batches
    return compiled
