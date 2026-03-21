"""
Chat Agent State
Defines the LangGraph state for the sidebar AI chat agent.
"""
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class ChatAgentState(TypedDict):
    """State for the chat agent graph."""
    # Core message history (LangGraph manages this via add_messages reducer)
    messages: Annotated[list, add_messages]
    
    # Session context (passed in at invocation, not modified by agent)
    session_id: str
    problem_title: str
    problem_requirements: str
    
    # Diagram summary — populated by the get_page_context tool when called
    diagram_summary: str
