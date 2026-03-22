"""
Chat Agent Tools
Each @tool contains REAL logic — no empty shells.

Tools created via create_chat_tools() factory because they need
session context (problem info, diagram data) available at request time.

The LLM can call up to 10 tools per run. It can:
  1. get_page_context  — read current diagram + problem details
  2. modify_diagram    — add/update nodes and edges
  3. delete_nodes      — remove specific nodes + their connections
  4. update_style      — change colors/position of existing elements
  5. edit_edges        — delete or modify existing edges
"""
import json
from langchain_core.tools import tool

from Agents.chat_agent.tools.helpers import (
    extract_diagram_context,
    build_diagram_streaming,
    delete_elements_from_diagram,
    update_style_elements,
    edit_edges_elements,
    MIN_SIZES,
)


def validate_node(node_id: str, node_def: dict, existing_ids: set) -> list:
    """
    Validate that a node has all mandatory fields.
    Returns list of error messages (empty if valid).
    """
    errors = []

    # Check required fields
    if not node_id:
        errors.append(f"Node missing 'id'")
        return errors

    if "label" not in node_def:
        errors.append(f"Node '{node_id}' missing 'label'")

    if "shape" not in node_def:
        errors.append(f"Node '{node_id}' missing 'shape' (use: rectangle, ellipse, diamond)")

    # Check for position - either x,y OR row,col is required
    has_xy = "x" in node_def and "y" in node_def
    has_grid = "row" in node_def and "col" in node_def
    is_existing = node_id in existing_ids

    if not is_existing and not has_xy and not has_grid:
        errors.append(f"Node '{node_id}' missing position. Provide either (x, y) or (row, col)")

    # Validate shape
    shape = node_def.get("shape", "").lower()
    if shape and shape not in ("rectangle", "ellipse", "diamond"):
        errors.append(f"Node '{node_id}' invalid shape '{shape}'. Use: rectangle, ellipse, diamond")

    return errors


def create_chat_tools(
    problem_title: str,
    problem_description: str,
    problem_requirements: str,
    diagram_data: dict,
    streamed_batches: list,
):
    """
    Factory that creates chat agent tools with session context baked in.
    """

    @tool
    def get_page_context(placeholder: str = "") -> str:
        """
        Get current diagram and problem context.
        Call this FIRST before modifying anything to see existing IDs and positions.
        Returns: problem details + all nodes/edges with their IDs, labels, positions.
        """
        diagram_summary = extract_diagram_context(diagram_data)
        existing_elements = diagram_data.get("elements", [])

        # Count existing nodes
        node_count = sum(1 for e in existing_elements
                        if isinstance(e, dict) and e.get("type") in ("rectangle", "ellipse", "diamond"))
        edge_count = sum(1 for e in existing_elements
                        if isinstance(e, dict) and e.get("type") == "arrow")

        # Add minimum size reference
        size_guide = """
MINIMUM SIZES (always exceed these):
| Shape      | Min W | Min H | Use Case           |
|------------|-------|--------|---------------------|
| rectangle  | 140   | 60     | Services, boxes     |
| ellipse    | 120   | 60     | Databases, storage  |
| diamond    | 100   | 80     | Decisions, routers  |
| container  | 300   | 200    | Groups, boundaries  |

SPACING: 80px minimum gap between nodes. First node near (200, 150).
"""

        return f"""=== CURRENT PAGE CONTEXT ===

**Problem:** {problem_title}

**Description:**
{problem_description}

**Requirements:**
{problem_requirements}

**Current Diagram:**
{diagram_summary}

**Existing:** {node_count} nodes, {edge_count} edges
{size_guide}"""

    @tool
    def modify_diagram(diagram_description: str) -> str:
        """
        Add or update nodes/edges in the diagram.

        MANDATORY fields for each node:
          - id: unique identifier (lowercase, underscores)
          - label: display text
          - shape: "rectangle" | "ellipse" | "diamond"
          - x: center X position (number)
          - y: center Y position (number)
          - width: width in pixels (number, see minimums)
          - height: height in pixels (number, see minimums)

        JSON format:
        {
          "nodes": {
            "node_id": {
              "label": "Name",
              "shape": "rectangle",
              "x": 200, "y": 150,
              "width": 160, "height": 70,
              "backgroundColor": "#hex",     // optional
              "strokeColor": "#hex",           // optional
              "children": ["child_id"]         // for containers
            }
          },
          "edges": [
            {"from": "src_id", "to": "dst_id", "label": "text", "direction": "one-way"}
          ]
        }

        Call get_page_context first to see minimum sizes and existing positions.
        """
        try:
            description = json.loads(diagram_description)
        except (json.JSONDecodeError, TypeError):
            return "Error: Invalid JSON. Check your JSON syntax."

        nodes = description.get("nodes", {})
        edges = description.get("edges", [])
        existing_elements = diagram_data.get("elements", [])
        existing_ids = {e["id"] for e in existing_elements if isinstance(e, dict) and e.get("id")}

        # Validate all nodes before processing
        validation_errors = []
        for node_id, node_def in nodes.items():
            if not isinstance(node_def, dict):
                validation_errors.append(f"Node '{node_id}' has invalid definition")
                continue
            errors = validate_node(node_id, node_def, existing_ids)
            validation_errors.extend(errors)

        if validation_errors:
            return "Validation errors:\n" + "\n".join(f"- {e}" for e in validation_errors)

        total_nodes = len(nodes)
        total_edges = len(edges)
        step = 0

        try:
            for batch in build_diagram_streaming(description, existing_elements):
                step += 1
                first = batch[0] if batch else {}
                if first.get("type") == "arrow":
                    label = "Drawing connection..."
                else:
                    label_text = next(
                        (b["text"] for b in batch if b.get("type") == "text" and b.get("text")),
                        ""
                    )
                    label = f"Adding {label_text}..." if label_text else "Adding component..."

                streamed_batches.append({
                    "elements": batch,
                    "label": label,
                    "progress": f"{step}/{total_nodes + total_edges}",
                })

        except Exception as e:
            return f"Error: {str(e)}"

        return f"Built {total_nodes} node(s) with {total_edges} edge(s)."

    @tool
    def delete_nodes(node_ids: str) -> str:
        """
        Remove nodes by their IDs. Also removes connected edges.

        Pass JSON array of IDs: ["node_id1", "node_id2"]
        Call get_page_context first to get current IDs.
        """
        try:
            ids_to_delete = json.loads(node_ids)
            if not isinstance(ids_to_delete, list):
                return "Error: Expected JSON array like [\"id1\", \"id2\"]"
        except (json.JSONDecodeError, TypeError):
            return "Error: Invalid JSON."

        existing_elements = diagram_data.get("elements", [])
        deleted_batch, count = delete_elements_from_diagram(ids_to_delete, existing_elements)

        if deleted_batch:
            streamed_batches.append({
                "elements": deleted_batch,
                "label": f"Removing {count} element(s)...",
                "progress": "delete",
            })

        return f"Deleted {count} element(s)."

    @tool
    def update_style(style_updates: str) -> str:
        """
        Change colors and/or position of existing elements by ID.

        Pass JSON array:
        [
          {
            "id": "element_id",
            "x": 150,                    // new center X (optional)
            "y": 200,                    // new center Y (optional)
            "backgroundColor": "#hex",   // optional
            "strokeColor": "#hex",       // optional
            "textColor": "#hex"          // optional
          }
        ]

        Works on shapes (rectangle/ellipse/diamond) and arrows.
        Call get_page_context first for IDs.
        """
        try:
            updates = json.loads(style_updates)
            if not isinstance(updates, list):
                return "Error: Expected JSON array."
        except (json.JSONDecodeError, TypeError):
            return "Error: Invalid JSON."

        existing_elements = diagram_data.get("elements", [])
        updated_batch, count = update_style_elements(updates, existing_elements)

        if updated_batch:
            streamed_batches.append({
                "elements": updated_batch,
                "label": f"Updating {count} element(s)...",
                "progress": "style",
            })

        return f"Updated {count} element(s)."

    @tool
    def edit_edges(edge_edits: str) -> str:
        """
        Delete or modify existing edges (arrows) by ID.

        Pass JSON array:
        [
          {
            "id": "arrow_id",
            "action": "delete" | "edit",
            // For edit, optional fields:
            "from": "new_source_id",     // change source
            "to": "new_target_id",       // change target
            "label": "new text",         // change label
            "strokeColor": "#hex",       // change color
            "direction": "one-way|two-way"
          }
        ]

        Actions:
        - delete: removes the arrow and its label
        - edit: modify color, label, direction, or re-route to different nodes

        Call get_page_context first to see existing edge IDs.
        """
        try:
            edits = json.loads(edge_edits)
            if not isinstance(edits, list):
                return "Error: Expected JSON array."
        except (json.JSONDecodeError, TypeError):
            return "Error: Invalid JSON."

        existing_elements = diagram_data.get("elements", [])
        edit_batch, count = edit_edges_elements(edits, existing_elements)

        if edit_batch:
            streamed_batches.append({
                "elements": edit_batch,
                "label": f"Editing {count} edge(s)...",
                "progress": "edit",
            })

        return f"Edited {count} edge(s)."

    return [get_page_context, modify_diagram, delete_nodes, update_style, edit_edges]