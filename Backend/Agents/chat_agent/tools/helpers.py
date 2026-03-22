"""
Chat Agent Tool Helpers
All implementation functions for the chat agent tools.
This file contains the actual logic — tools.py only handles
input parsing, function calling, and output formatting.

DRY: Shape creation uses a shared base with per-shape wrappers.
"""
import uuid
import copy
import json
from typing import Dict, Any, List, Optional, Tuple, Generator


# ─── ID & Seed Generators ────────────────────────────────────────────────────

def _generate_id() -> str:
    """Generate a unique 20-char hex ID for Excalidraw elements."""
    return uuid.uuid4().hex[:20]


def _generate_seed(s: str) -> int:
    """Deterministic seed from a string (for Excalidraw rendering consistency)."""
    return abs(hash(s)) % (2**31)


# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_STROKE = "#1e1e1e"
DEFAULT_BG = "transparent"


# ─── Text-Based Sizing ───────────────────────────────────────────────────────

def calculate_text_size(label: str) -> Tuple[int, int]:
    """Calculate shape dimensions so the label fits in a single line."""
    char_width = 10      # approx px per char at fontSize 16
    padding_x = 50       # horizontal padding (left + right)
    min_width = 140
    w = max(min_width, len(label) * char_width + padding_x)
    h = 60               # single-line height
    return w, h


# ─── Element Map Builder ─────────────────────────────────────────────────────

def build_element_maps(existing_elements: List[Dict]) -> Tuple[
    Dict[str, Dict], Dict[str, Tuple[float, float, float, float]], set
]:
    """
    Build lookup maps from existing canvas elements.

    Returns:
        id_to_elem:  {element_id: element_dict}
        id_to_pos:   {element_id: (x, y, width, height)}  — shapes only
        existing_ids: set of all element IDs on canvas
    """
    id_to_elem: Dict[str, Dict] = {}
    id_to_pos: Dict[str, Tuple[float, float, float, float]] = {}
    existing_ids: set = set()

    for elem in existing_elements:
        if not isinstance(elem, dict) or not elem.get("id"):
            continue
        eid = elem["id"]
        id_to_elem[eid] = elem
        existing_ids.add(eid)
        if elem.get("type") in ("rectangle", "ellipse", "diamond"):
            id_to_pos[eid] = (
                elem.get("x", 0), elem.get("y", 0),
                elem.get("width", 200), elem.get("height", 80),
            )

    return id_to_elem, id_to_pos, existing_ids


# ─── Auto-Layout Positioning ─────────────────────────────────────────────────

def find_position(
    all_positions: List[Tuple[float, float, float, float]],
    new_w: int, new_h: int,
    col: int, row: int,
) -> Tuple[float, float]:
    """Find a non-overlapping position for a new element on the canvas."""
    gap_x = new_w + 80
    gap_y = new_h + 70

    if all_positions:
        max_x = max(p[0] + p[2] for p in all_positions) + 80
        base_x = max_x
        base_y = 100
    else:
        base_x = 100
        base_y = 100

    return base_x + col * gap_x, base_y + row * gap_y


# ─── Excalidraw Data Extraction (for LLM context) ────────────────────────────

def extract_diagram_context(diagram_data: dict) -> str:
    """
    Extract and format existing diagram elements for the LLM.
    Shows element IDs + labels so the LLM can reference them.
    """
    if not diagram_data or not isinstance(diagram_data, dict):
        return "No diagram data provided"

    elements = diagram_data.get("elements", [])
    if not elements:
        return "Empty diagram - no elements found"

    # Build id -> element map
    id_to_elem: Dict[str, dict] = {}
    for elem in elements:
        if isinstance(elem, dict) and elem.get("id"):
            id_to_elem[elem["id"]] = elem

    # Build shape_id -> label map (text elements bound to shapes)
    shape_labels: Dict[str, str] = {}
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        if elem.get("type") == "text":
            text = (elem.get("text") or elem.get("originalText") or "").strip()
            container_id = elem.get("containerId")
            if text and container_id:
                shape_labels[container_id] = text

    # Also check shapes with direct text
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        if elem.get("type") in ("rectangle", "ellipse", "diamond"):
            direct_text = (elem.get("text") or "").strip()
            if direct_text and elem["id"] not in shape_labels:
                shape_labels[elem["id"]] = direct_text

    # Classify elements
    components = []
    arrows = []

    for elem in elements:
        if not isinstance(elem, dict):
            continue
        etype = elem.get("type", "")
        if etype == "arrow":
            arrows.append(elem)
        elif etype in ("rectangle", "ellipse", "diamond"):
            components.append(elem)

    # Format output with IDs
    lines = []
    lines.append("=== EXISTING DIAGRAM ===")
    lines.append(f"Components: {len(components)}, Connections: {len(arrows)}")
    lines.append("")

    if components:
        lines.append("=== NODES (use these IDs in edges) ===")
        for comp in components:
            cid = comp["id"]
            ctype = comp.get("type", "rectangle")
            label = shape_labels.get(cid, "(no label)")
            w = int(comp.get("width", 0))
            h = int(comp.get("height", 0))
            lines.append(f'- id="{cid}" label="{label}" shape={ctype} size={w}x{h}')
        lines.append("")

    if arrows:
        lines.append("=== EDGES ===")
        for arrow in arrows:
            start_id = (arrow.get("startBinding") or {}).get("elementId", "?")
            end_id = (arrow.get("endBinding") or {}).get("elementId", "?")
            start_label = shape_labels.get(start_id, "?")
            end_label = shape_labels.get(end_id, "?")

            # Check arrow's own text label
            arrow_label = ""
            for b in (arrow.get("boundElements") or []):
                if isinstance(b, dict) and b.get("type") == "text":
                    text_elem = id_to_elem.get(b.get("id", ""), {})
                    arrow_label = (text_elem.get("text") or "").strip()

            conn = f'- "{start_label}" ({start_id}) → "{end_label}" ({end_id})'
            if arrow_label:
                conn += f'  [{arrow_label}]'
            lines.append(conn)
        lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  SHAPE CREATION — DRY Architecture
#  _create_base_shape() does all the work.
#  create_rectangle(), create_ellipse(), create_diamond() are clean wrappers.
# ═══════════════════════════════════════════════════════════════════════════════

def _create_bound_text(
    text_id: str,
    container_id: str,
    label: str,
    x: float, y: float, w: int, h: int,
    text_color: str,
) -> Dict:
    """Create a text element bound to a shape container."""
    return {
        "id": text_id,
        "type": "text",
        "x": x + 10,
        "y": y + h / 2 - 12,
        "width": w - 20,
        "height": 24,
        "angle": 0,
        "strokeColor": text_color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "index": None,
        "roundness": None,
        "seed": _generate_seed(text_id),
        "version": 1,
        "versionNonce": _generate_seed(text_id + "v"),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "text": label,
        "fontSize": 16,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": container_id,
        "originalText": label,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def _create_base_shape(
    shape_id: str,
    label: str,
    shape_type: str,
    x: float, y: float, w: int, h: int,
    bg_color: Optional[str] = None,
    stroke_color: Optional[str] = None,
    text_color: Optional[str] = None,
) -> Tuple[Dict, Dict]:
    """
    Core shape creation — shared by all shape wrappers.
    Creates the shape element + its bound text label.

    Args:
        shape_id:     Unique ID for this shape
        label:        Text displayed inside the shape
        shape_type:   "rectangle", "ellipse", or "diamond"
        x, y:         Position on canvas
        w, h:         Dimensions
        bg_color:     Optional background color
        stroke_color: Optional border color
        text_color:   Optional text color

    Returns:
        (shape_element, text_element)
    """
    text_id = _generate_id()

    bg = bg_color or DEFAULT_BG
    stroke = stroke_color or DEFAULT_STROKE
    txt_color = text_color or stroke

    # Roundness depends on shape type
    if shape_type == "rectangle":
        roundness = {"type": 3}
    else:
        roundness = {"type": 2}

    shape = {
        "id": shape_id,
        "type": shape_type,
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "index": None,
        "roundness": roundness,
        "seed": _generate_seed(shape_id),
        "version": 1,
        "versionNonce": _generate_seed(shape_id + "v"),
        "isDeleted": False,
        "boundElements": [{"id": text_id, "type": "text"}],
        "updated": 1,
        "link": None,
        "locked": False,
    }

    text = _create_bound_text(
        text_id=text_id,
        container_id=shape_id,
        label=label,
        x=x, y=y, w=w, h=h,
        text_color=txt_color,
    )

    return shape, text


# ─── Per-Shape Wrappers (DRY) ────────────────────────────────────────────────

def create_rectangle(
    shape_id: str, label: str,
    x: float, y: float, w: int, h: int,
    bg_color: Optional[str] = None,
    stroke_color: Optional[str] = None,
    text_color: Optional[str] = None,
) -> Tuple[Dict, Dict]:
    """Create a rectangle element + bound text. Used for services/components."""
    return _create_base_shape(
        shape_id, label, "rectangle", x, y, w, h,
        bg_color, stroke_color, text_color,
    )


def create_ellipse(
    shape_id: str, label: str,
    x: float, y: float, w: int, h: int,
    bg_color: Optional[str] = None,
    stroke_color: Optional[str] = None,
    text_color: Optional[str] = None,
) -> Tuple[Dict, Dict]:
    """Create an ellipse/circle element + bound text. Used for databases."""
    return _create_base_shape(
        shape_id, label, "ellipse", x, y, w, h,
        bg_color, stroke_color, text_color,
    )


def create_diamond(
    shape_id: str, label: str,
    x: float, y: float, w: int, h: int,
    bg_color: Optional[str] = None,
    stroke_color: Optional[str] = None,
    text_color: Optional[str] = None,
) -> Tuple[Dict, Dict]:
    """Create a diamond element + bound text. Used for routers/load balancers."""
    return _create_base_shape(
        shape_id, label, "diamond", x, y, w, h,
        bg_color, stroke_color, text_color,
    )


# Map shape type string -> creator function
SHAPE_CREATORS = {
    "rectangle": create_rectangle,
    "ellipse": create_ellipse,
    "diamond": create_diamond,
}


# ─── Arrow / Connection Creation ─────────────────────────────────────────────

def create_arrow(
    from_id: str, to_id: str,
    from_pos: Tuple[float, float, float, float],
    to_pos: Tuple[float, float, float, float],
    label: Optional[str] = None,
    direction: str = "one-way",
    stroke_color: Optional[str] = None,
) -> Tuple[List[Dict], str]:
    """
    Create an arrow between two elements using their positions.

    Args:
        from_id:      Source element ID
        to_id:        Target element ID
        from_pos:     (x, y, w, h) of source
        to_pos:       (x, y, w, h) of target
        label:        Optional text on the arrow
        direction:    "one-way" or "two-way"
        stroke_color: Optional arrow color

    Returns:
        (list_of_elements, arrow_id)
    """
    arrow_id = _generate_id()
    stroke = stroke_color or DEFAULT_STROKE

    fx, fy, fw, fh = from_pos
    tx, ty, tw, th = to_pos

    # Connection points based on relative position
    dx = tx - fx
    dy = ty - fy

    if abs(dy) > abs(dx):
        if dy > 0:
            sx, sy = fx + fw / 2, fy + fh
            ex, ey = tx + tw / 2, ty
        else:
            sx, sy = fx + fw / 2, fy
            ex, ey = tx + tw / 2, ty + th
    else:
        if dx > 0:
            sx, sy = fx + fw, fy + fh / 2
            ex, ey = tx, ty + th / 2
        else:
            sx, sy = fx, fy + fh / 2
            ex, ey = tx + tw, ty + th / 2

    start_arrow = "arrow" if direction == "two-way" else None

    arrow = {
        "id": arrow_id,
        "type": "arrow",
        "x": sx, "y": sy,
        "width": ex - sx,
        "height": ey - sy,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "index": None,
        "roundness": {"type": 2},
        "seed": _generate_seed(arrow_id),
        "version": 1,
        "versionNonce": _generate_seed(arrow_id + "v"),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [ex - sx, ey - sy]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": from_id, "focus": 0, "gap": 5, "fixedPoint": None},
        "endBinding": {"elementId": to_id, "focus": 0, "gap": 5, "fixedPoint": None},
        "startArrowhead": start_arrow,
        "endArrowhead": "arrow",
        "elbowed": False,
    }

    result = [arrow]

    if label:
        tid = _generate_id()
        mid_x = sx + (ex - sx) / 2
        mid_y = sy + (ey - sy) / 2
        arrow["boundElements"] = [{"id": tid, "type": "text"}]
        result.append({
            "id": tid, "type": "text",
            "x": mid_x - 40, "y": mid_y - 12,
            "width": 80, "height": 20,
            "angle": 0,
            "strokeColor": stroke,
            "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 1,
            "strokeStyle": "solid", "roughness": 1, "opacity": 100,
            "groupIds": [], "frameId": None, "index": None, "roundness": None,
            "seed": _generate_seed(tid), "version": 1, "versionNonce": _generate_seed(tid + "v"),
            "isDeleted": False, "boundElements": None, "updated": 1,
            "link": None, "locked": False,
            "text": label, "fontSize": 13, "fontFamily": 1,
            "textAlign": "center", "verticalAlign": "middle",
            "containerId": arrow_id,
            "originalText": label, "autoResize": True, "lineHeight": 1.25,
        })

    return result, arrow_id


# ─── Arrow Binding Helper ────────────────────────────────────────────────────

def add_arrow_binding_to_shape(
    shape_id: str, arrow_id: str,
    new_elements: Dict[str, Dict],
    existing_updates: Dict[str, Dict],
    id_to_elem: Dict[str, Dict],
):
    """
    Ensure a shape knows about an arrow in its boundElements.
    Works for both newly created shapes AND existing canvas shapes.
    """
    # Check if it's a newly created shape
    if shape_id in new_elements:
        bound = new_elements[shape_id].get("boundElements", [])
        if not any(b.get("id") == arrow_id for b in bound):
            bound.append({"id": arrow_id, "type": "arrow"})
            new_elements[shape_id]["boundElements"] = bound
        return

    # It's an existing shape — create an updated copy
    if shape_id in id_to_elem:
        if shape_id not in existing_updates:
            existing_updates[shape_id] = copy.deepcopy(id_to_elem[shape_id])
            existing_updates[shape_id]["version"] = existing_updates[shape_id].get("version", 1) + 1
            existing_updates[shape_id]["versionNonce"] = _generate_seed(
                shape_id + str(existing_updates[shape_id]["version"])
            )

        shape = existing_updates[shape_id]
        bound = shape.get("boundElements") or []
        if not isinstance(bound, list):
            bound = []
        if not any(b.get("id") == arrow_id for b in bound):
            bound.append({"id": arrow_id, "type": "arrow"})
        shape["boundElements"] = bound


# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM BUILDERS — Orchestrate shape + arrow creation from LLM JSON
# ═══════════════════════════════════════════════════════════════════════════════

def build_diagram_from_json(
    description: dict,
    existing_elements: List[Dict] = None,
) -> List[Dict]:
    """
    Convert the LLM's node/edge JSON into Excalidraw elements.

    Supports:
    - Creating new nodes (with per-shape creator functions)
    - Updating existing nodes (label, colors, resize)
    - Connecting by ID with proper bidirectional binding

    Returns a flat list of elements to MERGE BY ID on the frontend.
    """
    existing_elements = existing_elements or []
    nodes = description.get("nodes", {})
    edges = description.get("edges", [])

    id_to_elem, id_to_pos, existing_ids = build_element_maps(existing_elements)

    # Track positions (existing + new)
    all_positions: Dict[str, Tuple[float, float, float, float]] = dict(id_to_pos)
    all_pos_list = list(id_to_pos.values())

    # Output collections
    output_elements: List[Dict] = []
    new_shape_map: Dict[str, Dict] = {}
    existing_updates: Dict[str, Dict] = {}

    cols = max(1, min(3, (len(nodes) + 1) // 2))
    node_idx = 0

    # ── Process nodes ─────────────────────────────────────────────────────
    for node_id, node_def in nodes.items():
        label = node_def.get("label", "Component")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in SHAPE_CREATORS:
            shape_type = "rectangle"

        bg_color = node_def.get("backgroundColor")
        stroke_color = node_def.get("strokeColor")
        text_color = node_def.get("textColor")

        if node_id in existing_ids:
            # ── UPDATE existing node ──────────────────────────────────
            updated = copy.deepcopy(id_to_elem[node_id])
            if label:
                for elem in existing_elements:
                    if (isinstance(elem, dict)
                            and elem.get("type") == "text"
                            and elem.get("containerId") == node_id):
                        text_update = copy.deepcopy(elem)
                        text_update["text"] = label
                        text_update["originalText"] = label
                        text_update["version"] = text_update.get("version", 1) + 1
                        output_elements.append(text_update)
                        break

            if bg_color:
                updated["backgroundColor"] = bg_color
            if stroke_color:
                updated["strokeColor"] = stroke_color

            new_w, new_h = calculate_text_size(label)
            updated["width"] = new_w
            updated["height"] = new_h
            updated["version"] = updated.get("version", 1) + 1
            updated["versionNonce"] = _generate_seed(node_id + str(updated["version"]))

            existing_updates[node_id] = updated
            all_positions[node_id] = (updated["x"], updated["y"], new_w, new_h)
        else:
            # ── CREATE new node using shape-specific creator ──────────
            w, h = calculate_text_size(label)
            col = node_idx % cols
            row = node_idx // cols
            x, y = find_position(all_pos_list, w, h, col, row)

            creator_fn = SHAPE_CREATORS[shape_type]
            shape, text = creator_fn(
                shape_id=node_id, label=label,
                x=x, y=y, w=w, h=h,
                bg_color=bg_color, stroke_color=stroke_color, text_color=text_color,
            )

            all_positions[node_id] = (x, y, w, h)
            all_pos_list.append((x, y, w, h))
            new_shape_map[node_id] = shape
            output_elements.extend([shape, text])

        node_idx += 1

    # ── Process edges ─────────────────────────────────────────────────────
    drawn = set()
    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")

        if not from_id or not to_id or from_id == to_id:
            continue
        pair = (from_id, to_id)
        if pair in drawn:
            continue
        drawn.add(pair)

        from_pos = all_positions.get(from_id)
        to_pos = all_positions.get(to_id)
        if not from_pos or not to_pos:
            continue

        arrow_label = edge.get("label")
        direction = edge.get("direction", "one-way")
        edge_stroke = edge.get("strokeColor")

        arrow_elems, arrow_id = create_arrow(
            from_id, to_id, from_pos, to_pos,
            label=arrow_label, direction=direction, stroke_color=edge_stroke,
        )

        add_arrow_binding_to_shape(from_id, arrow_id, new_shape_map, existing_updates, id_to_elem)
        add_arrow_binding_to_shape(to_id, arrow_id, new_shape_map, existing_updates, id_to_elem)

        output_elements.extend(arrow_elems)

    # ── Add updated existing elements to output ───────────────────────────
    output_elements.extend(existing_updates.values())

    return output_elements


def build_diagram_streaming(
    description: dict,
    existing_elements: List[Dict] = None,
) -> Generator[List[Dict], None, None]:
    """
    Generator that yields element batches one at a time.
    Each yield is a list of elements to merge by ID on the frontend.
    """
    existing_elements = existing_elements or []
    nodes = description.get("nodes", {})
    edges = description.get("edges", [])

    id_to_elem, id_to_pos, existing_ids = build_element_maps(existing_elements)

    all_positions: Dict[str, Tuple[float, float, float, float]] = dict(id_to_pos)
    all_pos_list = list(id_to_pos.values())
    new_shape_map: Dict[str, Dict] = {}
    existing_updates: Dict[str, Dict] = {}

    cols = max(1, min(3, (len(nodes) + 1) // 2))
    node_idx = 0

    # Yield nodes one by one
    for node_id, node_def in nodes.items():
        label = node_def.get("label", "Component")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in SHAPE_CREATORS:
            shape_type = "rectangle"

        bg_color = node_def.get("backgroundColor")
        stroke_color = node_def.get("strokeColor")
        text_color = node_def.get("textColor")

        batch = []

        if node_id in existing_ids:
            # UPDATE existing
            updated = copy.deepcopy(id_to_elem[node_id])
            new_w, new_h = calculate_text_size(label)
            updated["width"] = new_w
            updated["height"] = new_h
            if bg_color:
                updated["backgroundColor"] = bg_color
            if stroke_color:
                updated["strokeColor"] = stroke_color
            updated["version"] = updated.get("version", 1) + 1
            updated["versionNonce"] = _generate_seed(node_id + str(updated["version"]))

            existing_updates[node_id] = updated
            all_positions[node_id] = (updated["x"], updated["y"], new_w, new_h)
            batch.append(updated)

            # Update bound text
            for elem in existing_elements:
                if (isinstance(elem, dict)
                        and elem.get("type") == "text"
                        and elem.get("containerId") == node_id):
                    text_update = copy.deepcopy(elem)
                    text_update["text"] = label
                    text_update["originalText"] = label
                    text_update["version"] = text_update.get("version", 1) + 1
                    batch.append(text_update)
                    break
        else:
            # CREATE new using shape-specific creator
            w, h = calculate_text_size(label)
            col = node_idx % cols
            row = node_idx // cols
            x, y = find_position(all_pos_list, w, h, col, row)

            creator_fn = SHAPE_CREATORS[shape_type]
            shape, text = creator_fn(
                shape_id=node_id, label=label,
                x=x, y=y, w=w, h=h,
                bg_color=bg_color, stroke_color=stroke_color, text_color=text_color,
            )
            all_positions[node_id] = (x, y, w, h)
            all_pos_list.append((x, y, w, h))
            new_shape_map[node_id] = shape
            batch.extend([shape, text])

        node_idx += 1
        if batch:
            yield batch

    # Yield edges one by one
    drawn = set()
    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")

        if not from_id or not to_id or from_id == to_id:
            continue
        pair = (from_id, to_id)
        if pair in drawn:
            continue
        drawn.add(pair)

        from_pos = all_positions.get(from_id)
        to_pos = all_positions.get(to_id)
        if not from_pos or not to_pos:
            continue

        arrow_label = edge.get("label")
        direction = edge.get("direction", "one-way")
        edge_stroke = edge.get("strokeColor")

        arrow_elems, arrow_id = create_arrow(
            from_id, to_id, from_pos, to_pos,
            label=arrow_label, direction=direction, stroke_color=edge_stroke,
        )

        add_arrow_binding_to_shape(from_id, arrow_id, new_shape_map, existing_updates, id_to_elem)
        add_arrow_binding_to_shape(to_id, arrow_id, new_shape_map, existing_updates, id_to_elem)

        # Include updated existing shapes in this batch
        batch = list(arrow_elems)
        for eid in (from_id, to_id):
            if eid in existing_updates:
                batch.append(existing_updates[eid])

        yield batch
