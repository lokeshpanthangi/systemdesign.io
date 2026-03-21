"""
Chat Agent Tools
Tools the LangGraph chat agent can call to fetch page context.
"""
from langchain_core.tools import tool
from ..tools.excalidraw_extractor import extract_excalidraw_components


@tool
def get_page_context(placeholder: str = "") -> str:
    """
    Fetch the current diagram and problem context from the user's practice session.
    
    Call this tool ONLY when the user asks about their specific design, diagram,
    or solution on the canvas. Do NOT call this for general system design questions.
    
    Returns a formatted string with the problem requirements and current diagram analysis.
    """
    # This is a placeholder — the actual data is injected by the graph runner
    # before tool execution. The tool's docstring is what matters for the LLM
    # to decide when to call it.
    return "Page context will be injected at runtime."


def execute_get_page_context(problem_title: str, problem_description: str, problem_requirements: str, diagram_data: dict) -> str:
    """
    Actually execute the page context fetch with real data.
    Called by the tool node in the graph with injected session data.
    """
    # Extract diagram components
    try:
        diagram_summary = extract_excalidraw_components.invoke({"diagram_data": diagram_data})
    except Exception:
        diagram_summary = "Unable to extract diagram data."
    
    context = f"""=== CURRENT PAGE CONTEXT ===

**Problem:** {problem_title}

**Description:**
{problem_description}

**Requirements:**
{problem_requirements}

**Current Diagram:**
{diagram_summary}
"""
    return context


# List of tools to bind to the LLM
chat_tools = [get_page_context]
