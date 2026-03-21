"""
Chat Agent Graph
LangGraph graph for the sidebar AI chat agent.
Two nodes: agent (LLM) and tools (page context fetcher).
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END

from .state import ChatAgentState
from .tools import chat_tools, execute_get_page_context
from ..prompts.chat_agent_prompt import CHAT_AGENT_SYSTEM_PROMPT

load_dotenv()


def create_chat_agent_graph(
    problem_title: str,
    problem_description: str,
    problem_requirements: str,
    diagram_data: dict
):
    """
    Create and compile the chat agent graph for a given session context.
    
    Args:
        problem_title: Title of the current problem
        problem_requirements: Formatted requirements string
        diagram_data: Current excalidraw diagram data
    
    Returns:
        Compiled LangGraph graph ready for streaming
    """
    # Initialize LLM with tool binding
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,
        streaming=True
    )
    model_with_tools = model.bind_tools(chat_tools)

    # Format system prompt with context
    system_prompt = CHAT_AGENT_SYSTEM_PROMPT.format(
        problem_title=problem_title,
        problem_description=problem_description,
        problem_requirements=problem_requirements
    )

    # --- Node: Agent (LLM call) ---
    async def agent_node(state: ChatAgentState) -> Dict[str, Any]:
        """Call the LLM with messages and tools."""
        messages = state["messages"]
        
        # Prepend system message if not already there
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + list(messages)
        
        response = await model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    # --- Node: Tools (execute page context fetch) ---
    async def tool_node(state: ChatAgentState) -> Dict[str, Any]:
        """Execute tool calls from the agent."""
        last_message = state["messages"][-1]
        tool_messages = []
        
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "get_page_context":
                # Execute with actual session data
                result = execute_get_page_context(
                    problem_title=problem_title,
                    problem_description=problem_description,
                    problem_requirements=problem_requirements,
                    diagram_data=diagram_data
                )
            else:
                result = f"Unknown tool: {tool_call['name']}"
            
            tool_messages.append(
                ToolMessage(content=result, tool_call_id=tool_call["id"])
            )
        
        return {"messages": tool_messages}

    # --- Conditional edge: should we call tools? ---
    def should_call_tools(state: ChatAgentState) -> str:
        """Check if the last message has tool calls."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    # --- Build Graph ---
    graph = StateGraph(ChatAgentState)
    
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    
    graph.set_entry_point("agent")
    
    graph.add_conditional_edges(
        "agent",
        should_call_tools,
        {"tools": "tools", END: END}
    )
    graph.add_edge("tools", "agent")
    
    return graph.compile()
