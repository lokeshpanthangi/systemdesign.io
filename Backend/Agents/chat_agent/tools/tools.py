"""
Chat Agent Tools
Each @tool contains the REAL logic — no empty shells.

Tools are created via create_chat_tools() factory because they need
session context (problem info, diagram data) which is only available
at request time.

Tool structure:
  1. Parse input from the LLM
  2. Call helper functions from helpers.py
  3. Format and return the result
"""
import json
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
    """

    # ═══════════════════════════════════════════════════════════════════════
    #  TOOL 1: get_page_context
    # ═══════════════════════════════════════════════════════════════════════

    @tool
    def get_page_context(placeholder: str = "") -> str:
        """
        Fetch the current diagram and problem context.
        Returns the problem requirements and a list of all existing diagram
        elements WITH their IDs and sizes, so you can reference them when drawing.

        ALWAYS call this before calling modify_diagram.
        """
        diagram_summary = extract_diagram_context(diagram_data)

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
    # ═══════════════════════════════════════════════════════════════════════

    @tool
    def modify_diagram(diagram_description: str) -> str:
        """
        Add nodes (including containers with children inside them) and edges to the diagram.

        IMPORTANT: Call get_page_context FIRST to see existing element IDs and sizes.

        Pass a JSON string with this EXACT format:
        {
          "nodes": {
            "backend_box": {
              "label": "Backend Service",
              "shape": "rectangle",
              "width": 520,
              "height": 380,
              "children": ["app_logic", "db_layer", "cache"]
            },
            "app_logic": {
              "label": "App Logic",
              "shape": "rectangle",
              "width": 150,
              "height": 70
            },
            "db_layer": {
              "label": "PostgreSQL",
              "shape": "ellipse",
              "width": 160,
              "height": 80
            },
            "cache": {
              "label": "Redis",
              "shape": "rectangle",
              "width": 140,
              "height": 70
            },
            "api_gw": {
              "label": "API Gateway",
              "shape": "rectangle",
              "width": 180,
              "height": 70
            }
          },
          "edges": [
            {"from": "api_gw", "to": "backend_box", "label": "HTTP"},
            {"from": "app_logic", "to": "db_layer", "label": "SQL"}
          ]
        }

        RULES:
        - "width" and "height" are REQUIRED for containers (nodes with children). Make containers big enough to hold their children with padding.
        - "width" and "height" are OPTIONAL for leaf nodes (auto-sized from label if omitted).
        - "children": list of node IDs that live INSIDE this container visually. They will be auto-laid out inside the parent box.
        - "shape": "rectangle" (services/containers), "ellipse" (databases), "diamond" (routers/decisions)
        - "direction": "one-way" (default) or "two-way" on edges
        - Colors are OPTIONAL: "backgroundColor", "strokeColor", "textColor" — only set if meaningful
        - Do NOT add nodes that already exist on canvas (check get_page_context)
        - Do NOT specify x/y — layout is handled automatically
        - Container sizing guide: allow ~180px width and ~120px height per child, plus 80px padding on all sides
        """
        try:
            description = json.loads(diagram_description)
        except (json.JSONDecodeError, TypeError):
            return "❌ Failed to parse diagram JSON. Please send valid JSON."

        total_nodes = len(description.get("nodes", {}))
        total_edges = len(description.get("edges", []))
        total_steps = total_nodes + total_edges
        existing_elements = diagram_data.get("elements", [])
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

                streamed_batches.append({
                    "elements": batch,
                    "label": label,
                    "progress": f"{step}/{total_steps}",
                })

        except Exception as e:
            return f"❌ Failed to generate diagram: {str(e)}"

        return f"✓ Built {total_nodes} node(s) with {total_edges} edge(s)."

    return [get_page_context, modify_diagram]
