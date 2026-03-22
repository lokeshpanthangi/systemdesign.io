"""
Chat Agent Tools
Each @tool contains the REAL logic — no empty shells.

Tools are created via create_chat_tools() factory because they need
session context (problem info, diagram data) which is only available
at request time. The factory closes over that context so each @tool
function can use it directly.

Tool structure:
  1. Parse input from the LLM
  2. Call helper functions from tool_helpers.py
  3. Format and return the result

All heavy implementation lives in tool_helpers.py (DRY).
"""
import json
from typing import List, Dict, Any
from langchain_core.tools import tool

from Agents.chat_agent.tools.helpers import (
    extract_diagram_context,
    build_diagram_streaming,
)


def create_chat_tools(
    problem_title: str,
    problem_description: str,
    problem_requirements: str,
    diagram_data: dict,
    streamed_batches: list,
):
    """
    Factory that creates the chat agent tools with session context baked in.

    Args:
        problem_title:        Title of the current problem
        problem_description:  Problem description text
        problem_requirements: Formatted requirements string
        diagram_data:         Current excalidraw diagram JSON
        streamed_batches:     Shared list — modify_diagram appends element
                              batches here so chatbot.py can stream them to
                              the frontend.

    Returns:
        List of LangChain tools ready to bind to the LLM.
    """

    # ═══════════════════════════════════════════════════════════════════════
    #  TOOL 1: get_page_context
    #  LLM calls this → fetches Excalidraw data → formats it → returns to LLM
    # ═══════════════════════════════════════════════════════════════════════

    @tool
    def get_page_context(placeholder: str = "") -> str:
        """
        Fetch the current diagram and problem context.
        Returns the problem requirements and a list of all existing diagram
        elements WITH their IDs, so you can reference them when drawing.

        ALWAYS call this before calling modify_diagram.
        """
        # Step 1: Extract & format the diagram using helper
        diagram_summary = extract_diagram_context(diagram_data)

        # Step 2: Build the full context string for the LLM
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

    # ═══════════════════════════════════════════════════════════════════════
    #  TOOL 2: modify_diagram
    #  LLM sends JSON → tool parses it → creates the diagram → returns result
    # ═══════════════════════════════════════════════════════════════════════

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
        # Step 1: Parse the JSON input from the LLM
        try:
            description = json.loads(diagram_description)
        except (json.JSONDecodeError, TypeError):
            return "❌ Failed to parse diagram JSON. Please send valid JSON."

        total_nodes = len(description.get("nodes", {}))
        total_edges = len(description.get("edges", []))
        total_steps = total_nodes + total_edges
        existing_elements = diagram_data.get("elements", [])
        step = 0

        # Step 2: Build diagram elements using helper (streaming)
        try:
            for batch in build_diagram_streaming(description, existing_elements):
                step += 1

                # Format a human-readable label for this batch
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

                # Step 3: Push batch to shared list (frontend picks this up)
                streamed_batches.append({
                    "elements": batch,
                    "label": label,
                    "progress": f"{step}/{total_steps}",
                })

        except Exception as e:
            return f"❌ Failed to generate diagram: {str(e)}"

        # Step 4: Return success message to the LLM
        return f"✓ Built {total_nodes} node(s) with {total_edges} edge(s)."

    # ─── Return the tools list ────────────────────────────────────────────
    return [get_page_context, modify_diagram]
