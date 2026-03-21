"""
Chat Agent Tools
Tools the LangGraph chat agent can call to fetch page context
and modify the Excalidraw diagram.
"""
import json
from typing import Generator, List, Dict, Any
from langchain_core.tools import tool
from Agents.tools.excalidraw_extractor import extract_excalidraw_components
from Agents.tools.excalidraw_generator import build_diagram_streaming


@tool
def get_page_context(placeholder: str = "") -> str:
    """
    Fetch the current diagram and problem context.
    Returns the problem requirements and a list of all existing diagram
    elements WITH their IDs, so you can reference them when drawing.

    ALWAYS call this before calling modify_diagram.
    """
    return "Page context will be injected at runtime."


@tool
def modify_diagram(diagram_description: str) -> str:
    """
    Add nodes and edges to the user's Excalidraw diagram.

    IMPORTANT: Call get_page_context FIRST to see existing element IDs.

    Pass a JSON string with this EXACT format:
    {
      "nodes": {
        "unique_id_1": {"label": "API Gateway", "shape": "rectangle"},
        "unique_id_2": {"label": "User DB", "shape": "ellipse"}
      },
      "edges": [
        {"from": "unique_id_1", "to": "existing_element_id", "label": "HTTP request"},
        {"from": "unique_id_1", "to": "unique_id_2", "direction": "two-way"}
      ]
    }

    RULES:
    - Each node key is a UNIQUE ID (use descriptive strings like "api_gw", "user_db")
    - To connect to an EXISTING element, use its ID from get_page_context output
    - "shape": "rectangle" (services), "ellipse" (databases), "diamond" (routers)
    - "direction": "one-way" (default) or "two-way"
    - Colors are OPTIONAL: "backgroundColor", "strokeColor", "textColor" — only set if needed
    - Do NOT add nodes that already exist on canvas (check get_page_context)
    - Do NOT specify x/y — auto-layout handles positioning
    """
    return "Diagram modification will be executed at runtime."


def execute_get_page_context(
    problem_title: str, problem_description: str,
    problem_requirements: str, diagram_data: dict
) -> str:
    """Actually execute the page context fetch with real data."""
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


def execute_modify_diagram_streaming(
    diagram_description_json: str,
    existing_elements: List[Dict],
) -> Generator[Dict[str, Any], None, None]:
    """
    Streaming version of diagram execution.
    Yields batches: {"type": "elements", "elements": [...], "label": "..."}
    then {"type": "done", "message": "..."} at the end.
    """
    try:
        description = json.loads(diagram_description_json)
    except (json.JSONDecodeError, TypeError):
        yield {"type": "error", "message": "Failed to parse diagram description JSON."}
        return

    total_nodes = len(description.get("nodes", {}))
    total_edges = len(description.get("edges", []))
    total_steps = total_nodes + total_edges
    step = 0

    try:
        for batch in build_diagram_streaming(description, existing_elements):
            step += 1
            first = batch[0] if batch else {}
            if first.get("type") == "arrow":
                label = "Drawing connection..."
            else:
                label_text = ""
                for b in batch:
                    if b.get("type") == "text" and b.get("text"):
                        label_text = b["text"]
                        break
                label = f"Adding {label_text}..." if label_text else "Adding component..."

            yield {
                "type": "elements",
                "elements": batch,
                "label": label,
                "progress": f"{step}/{total_steps}",
            }

        yield {
            "type": "done",
            "message": f"✓ Built {total_nodes} node(s) with {total_edges} edge(s)."
        }

    except Exception as e:
        yield {"type": "error", "message": f"Failed to generate diagram: {str(e)}"}


# List of tools to bind to the LLM
chat_tools = [get_page_context, modify_diagram]
