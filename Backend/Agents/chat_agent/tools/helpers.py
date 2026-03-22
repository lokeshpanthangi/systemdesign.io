"""
Chat Agent Tool Helpers — Nested Container Edition
All implementation functions for the chat agent tools.

Key additions vs previous version:
  - Two-pass layout: containers are placed first, children laid out INSIDE them
  - LLM-provided width/height respected (falls back to auto-size)
  - extract_diagram_context shows parent= and children= so LLM can reason about nesting
  - No groupIds — parent and child are fully independent Excalidraw elements
"""
import uuid
import copy
from typing import Dict, Any, List, Optional, Tuple, Generator, Set


# ─── ID & Seed Generators ────────────────────────────────────────────────────

def _generate_id() -> str:
    """Generate a unique 20-char hex ID for Excalidraw elements."""
    return uuid.uuid4().hex[:20]


def _generate_seed(s: str) -> int:
    """Deterministic seed from a string."""
    return abs(hash(s)) % (2**31)


# ─── Constants ────────────────────────────────────────────────────────────────

DEFAULT_STROKE = "#1e1e1e"
DEFAULT_BG = "transparent"

# Padding inside a container (left/top/right/bottom)
CONTAINER_PADDING = 60

# Gap between children inside a container
CHILD_GAP_X = 40
CHILD_GAP_Y = 40

# Title area at top of container (so label doesn't overlap children)
CONTAINER_TITLE_HEIGHT = 50

# Gap between top-level nodes on canvas
CANVAS_GAP_X = 100
CANVAS_GAP_Y = 80

# Default sizes when LLM doesn't specify
DEFAULT_LEAF_W = 160
DEFAULT_LEAF_H = 70


# ─── Text-Based Auto-Sizing ──────────────────────────────────────────────────

def calculate_text_size(label: str, width: Optional[int] = None, height: Optional[int] = None) -> Tuple[int, int]:
    """
    Return (width, height) for a node.
    Uses LLM-provided values if given, otherwise auto-sizes from label.
    """
    if width and height:
        return int(width), int(height)
    if width:
        return int(width), DEFAULT_LEAF_H
    if height:
        char_width = 10
        padding_x = 50
        min_width = 140
        w = max(min_width, len(label) * char_width + padding_x)
        return w, int(height)

    # Fully auto
    char_width = 10
    padding_x = 50
    min_width = 140
    w = max(min_width, len(label) * char_width + padding_x)
    return w, DEFAULT_LEAF_H


# ─── Element Map Builder ─────────────────────────────────────────────────────

def build_element_maps(existing_elements: List[Dict]) -> Tuple[
    Dict[str, Dict],
    Dict[str, Tuple[float, float, float, float]],
    Set[str],
]:
    """
    Build lookup maps from existing canvas elements.

    Returns:
        id_to_elem:   {element_id: element_dict}
        id_to_pos:    {element_id: (x, y, width, height)}  — shapes only
        existing_ids: set of all element IDs on canvas
    """
    id_to_elem: Dict[str, Dict] = {}
    id_to_pos: Dict[str, Tuple[float, float, float, float]] = {}
    existing_ids: Set[str] = set()

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


# ─── Canvas Layout ───────────────────────────────────────────────────────────

def find_canvas_position(
    all_positions: List[Tuple[float, float, float, float]],
    new_w: int,
    new_h: int,
) -> Tuple[float, float]:
    """
    Find a non-overlapping position on the canvas for a top-level node.
    Places nodes left→right with CANVAS_GAP_X spacing.
    """
    if not all_positions:
        return 100.0, 100.0

    max_x = max(p[0] + p[2] for p in all_positions) + CANVAS_GAP_X
    base_y = 100.0
    return max_x, base_y


# ─── Container Child Layout ──────────────────────────────────────────────────

def layout_children_inside(
    parent_x: float,
    parent_y: float,
    parent_w: int,
    parent_h: int,
    children_sizes: List[Tuple[str, int, int]],  # [(node_id, w, h), ...]
) -> Dict[str, Tuple[float, float]]:
    """
    Lay out child nodes in a grid inside the parent container.
    Returns {node_id: (x, y)} for each child.

    Layout: left-to-right row, wrapping when the row would exceed parent width.
    Title area at top is reserved (CONTAINER_TITLE_HEIGHT + CONTAINER_PADDING).
    """
    positions: Dict[str, Tuple[float, float]] = {}

    # Working area inside the container
    inner_left = parent_x + CONTAINER_PADDING
    inner_top = parent_y + CONTAINER_PADDING + CONTAINER_TITLE_HEIGHT
    inner_width = parent_w - (CONTAINER_PADDING * 2)

    cursor_x = inner_left
    cursor_y = inner_top
    row_height = 0

    for node_id, w, h in children_sizes:
        # Wrap to next row if this child doesn't fit
        if cursor_x + w > inner_left + inner_width and cursor_x > inner_left:
            cursor_x = inner_left
            cursor_y += row_height + CHILD_GAP_Y
            row_height = 0

        positions[node_id] = (cursor_x, cursor_y)
        cursor_x += w + CHILD_GAP_X
        row_height = max(row_height, h)

    return positions


# ─── Excalidraw Context Extraction (for LLM) ────────────────────────────────

def extract_diagram_context(diagram_data: dict) -> str:
    """
    Format existing diagram elements for the LLM.
    Shows: id, label, shape, size=WxH, and parent/children relationships.
    """
    if not diagram_data or not isinstance(diagram_data, dict):
        return "No diagram data provided"

    elements = diagram_data.get("elements", [])
    if not elements:
        return "Empty diagram - no elements found"

    id_to_elem: Dict[str, dict] = {}
    for elem in elements:
        if isinstance(elem, dict) and elem.get("id"):
            id_to_elem[elem["id"]] = elem

    # Build shape_id → label
    shape_labels: Dict[str, str] = {}
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        if elem.get("type") == "text":
            text = (elem.get("text") or "").strip()
            cid = elem.get("containerId")
            if text and cid:
                shape_labels[cid] = text
    for elem in elements:
        if isinstance(elem, dict) and elem.get("type") in ("rectangle", "ellipse", "diamond"):
            direct_text = (elem.get("text") or "").strip()
            if direct_text and elem["id"] not in shape_labels:
                shape_labels[elem["id"]] = direct_text

    # Infer parent-child from containment in bounding boxes
    shapes = [e for e in elements if isinstance(e, dict) and e.get("type") in ("rectangle", "ellipse", "diamond")]

    def contains(outer: dict, inner: dict) -> bool:
        """True if outer's bounding box fully contains inner's bounding box."""
        ox, oy = outer.get("x", 0), outer.get("y", 0)
        ow, oh = outer.get("width", 0), outer.get("height", 0)
        ix, iy = inner.get("x", 0), inner.get("y", 0)
        iw, ih = inner.get("width", 0), inner.get("height", 0)
        return (ox < ix and iy < oy + oh and
                ix + iw < ox + ow and iy + ih < oy + oh and
                inner["id"] != outer["id"])

    # Build parent/children maps
    parent_of: Dict[str, str] = {}
    children_of: Dict[str, List[str]] = {}

    for shape in shapes:
        sid = shape["id"]
        children_of[sid] = []

    for shape in shapes:
        sid = shape["id"]
        # Find smallest container that contains this shape
        best_parent = None
        best_area = float("inf")
        for candidate in shapes:
            if candidate["id"] == sid:
                continue
            if contains(candidate, shape):
                area = candidate.get("width", 0) * candidate.get("height", 0)
                if area < best_area:
                    best_area = area
                    best_parent = candidate["id"]
        if best_parent:
            parent_of[sid] = best_parent
            children_of[best_parent].append(sid)

    # Format output
    components = [e for e in elements if isinstance(e, dict) and e.get("type") in ("rectangle", "ellipse", "diamond")]
    arrows = [e for e in elements if isinstance(e, dict) and e.get("type") == "arrow"]

    lines = []
    lines.append("=== EXISTING DIAGRAM ===")
    lines.append(f"Components: {len(components)}, Connections: {len(arrows)}")
    lines.append("")

    if components:
        lines.append("=== NODES (use these IDs in edges or as parent references) ===")
        for comp in components:
            cid = comp["id"]
            ctype = comp.get("type", "rectangle")
            label = shape_labels.get(cid, "(no label)")
            w = int(comp.get("width", 0))
            h = int(comp.get("height", 0))
            line = f'- id="{cid}"  label="{label}"  shape={ctype}  size={w}x{h}'
            if cid in parent_of:
                parent_label = shape_labels.get(parent_of[cid], parent_of[cid])
                line += f'  parent="{parent_label}"'
            if children_of.get(cid):
                child_labels = [f'"{shape_labels.get(c, c)}"' for c in children_of[cid]]
                line += f'  children=[{", ".join(child_labels)}]'
            lines.append(line)
        lines.append("")

    if arrows:
        lines.append("=== EDGES ===")
        for arrow in arrows:
            start_id = (arrow.get("startBinding") or {}).get("elementId", "?")
            end_id = (arrow.get("endBinding") or {}).get("elementId", "?")
            start_label = shape_labels.get(start_id, "?")
            end_label = shape_labels.get(end_id, "?")
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
#  SHAPE CREATION
# ═══════════════════════════════════════════════════════════════════════════════

def _create_bound_text(
    text_id: str,
    container_id: str,
    label: str,
    x: float, y: float, w: int, h: int,
    text_color: str,
    is_container: bool = False,
) -> Dict:
    """Create a text element bound to a shape container."""
    # For containers, pin label to top so it doesn't overlap children
    if is_container:
        text_y = y + 16
        text_h = 24
        v_align = "top"
    else:
        text_y = y + h / 2 - 12
        text_h = 24
        v_align = "middle"

    return {
        "id": text_id,
        "type": "text",
        "x": x + 10,
        "y": text_y,
        "width": w - 20,
        "height": text_h,
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
        "verticalAlign": v_align,
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
    is_container: bool = False,
) -> Tuple[Dict, Dict]:
    """
    Core shape creation — creates the shape element + its bound text label.
    Returns (shape_element, text_element).
    """
    text_id = _generate_id()

    bg = bg_color or DEFAULT_BG
    stroke = stroke_color or DEFAULT_STROKE
    txt_color = text_color or stroke

    # Containers use dashed border to visually distinguish from leaf nodes
    stroke_style = "dashed" if is_container else "solid"

    roundness = {"type": 3} if shape_type == "rectangle" else {"type": 2}

    shape = {
        "id": shape_id,
        "type": shape_type,
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": stroke_style,
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
        is_container=is_container,
    )

    return shape, text


def create_rectangle(shape_id, label, x, y, w, h, bg_color=None, stroke_color=None, text_color=None, is_container=False):
    return _create_base_shape(shape_id, label, "rectangle", x, y, w, h, bg_color, stroke_color, text_color, is_container)


def create_ellipse(shape_id, label, x, y, w, h, bg_color=None, stroke_color=None, text_color=None, is_container=False):
    return _create_base_shape(shape_id, label, "ellipse", x, y, w, h, bg_color, stroke_color, text_color, is_container)


def create_diamond(shape_id, label, x, y, w, h, bg_color=None, stroke_color=None, text_color=None, is_container=False):
    return _create_base_shape(shape_id, label, "diamond", x, y, w, h, bg_color, stroke_color, text_color, is_container)


SHAPE_CREATORS = {
    "rectangle": create_rectangle,
    "ellipse": create_ellipse,
    "diamond": create_diamond,
}


# ─── Arrow Creation ──────────────────────────────────────────────────────────

def create_arrow(
    from_id: str, to_id: str,
    from_pos: Tuple[float, float, float, float],
    to_pos: Tuple[float, float, float, float],
    label: Optional[str] = None,
    direction: str = "one-way",
    stroke_color: Optional[str] = None,
) -> Tuple[List[Dict], str]:
    """Create an arrow between two elements using their positions."""
    arrow_id = _generate_id()
    stroke = stroke_color or DEFAULT_STROKE

    fx, fy, fw, fh = from_pos
    tx, ty, tw, th = to_pos

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


# ─── Arrow Binding ───────────────────────────────────────────────────────────

def add_arrow_binding_to_shape(
    shape_id: str, arrow_id: str,
    new_elements: Dict[str, Dict],
    existing_updates: Dict[str, Dict],
    id_to_elem: Dict[str, Dict],
):
    """Ensure a shape knows about an arrow in its boundElements."""
    if shape_id in new_elements:
        bound = new_elements[shape_id].get("boundElements", [])
        if not any(b.get("id") == arrow_id for b in bound):
            bound.append({"id": arrow_id, "type": "arrow"})
            new_elements[shape_id]["boundElements"] = bound
        return

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
#  TWO-PASS DIAGRAM BUILDER — Orchestrates nested containers
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_node_order(nodes: Dict[str, dict]) -> List[str]:
    """
    Return node IDs in render order: containers before their children.
    This ensures containers are drawn first (visually behind children).
    """
    children_claimed: Set[str] = set()
    for node_def in nodes.values():
        for child_id in node_def.get("children", []):
            children_claimed.add(child_id)

    # Containers first, then free leaves
    containers = [nid for nid in nodes if nodes[nid].get("children")]
    free_leaves = [nid for nid in nodes if nid not in children_claimed and nid not in containers]
    nested_leaves = [nid for nid in nodes if nid in children_claimed]

    # Order: containers → their children (matched) → free leaves
    ordered = []
    for container_id in containers:
        ordered.append(container_id)
        for child_id in nodes[container_id].get("children", []):
            if child_id in nodes:
                ordered.append(child_id)
    for nid in free_leaves:
        if nid not in ordered:
            ordered.append(nid)
    # Any remaining (shouldn't happen)
    for nid in nodes:
        if nid not in ordered:
            ordered.append(nid)

    return ordered


def build_diagram_streaming(
    description: dict,
    existing_elements: List[Dict] = None,
) -> Generator[List[Dict], None, None]:
    """
    Two-pass streaming diagram builder supporting nested containers.

    Pass 1: Determine all positions (canvas layout + child placement inside containers).
    Pass 2: Yield elements one by one (container first, then its children, then edges).

    No groupIds — container and children are independent elements.
    """
    existing_elements = existing_elements or []
    nodes = description.get("nodes", {})
    edges = description.get("edges", [])

    id_to_elem, id_to_pos, existing_ids = build_element_maps(existing_elements)

    # Track all positions (existing + new)
    all_positions: Dict[str, Tuple[float, float, float, float]] = dict(id_to_pos)
    all_pos_list: List[Tuple[float, float, float, float]] = list(id_to_pos.values())

    new_shape_map: Dict[str, Dict] = {}
    existing_updates: Dict[str, Dict] = {}

    # ── PASS 1: Figure out which nodes are children ─────────────────────────
    children_claimed: Set[str] = set()
    for node_id, node_def in nodes.items():
        for child_id in node_def.get("children", []):
            children_claimed.add(child_id)

    # PASS 1a: Lay out containers + their children
    container_positions: Dict[str, Tuple[float, float, int, int]] = {}

    for node_id, node_def in nodes.items():
        children = node_def.get("children", [])
        if not children:
            continue  # Not a container — handled below

        if node_id in existing_ids:
            continue  # Container already on canvas

        label = node_def.get("label", "Container")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in SHAPE_CREATORS:
            shape_type = "rectangle"

        # Use LLM-provided size for container
        w, h = calculate_text_size(label, node_def.get("width"), node_def.get("height"))

        # Place container on canvas
        x, y = find_canvas_position(all_pos_list, w, h)

        all_positions[node_id] = (x, y, w, h)
        all_pos_list.append((x, y, w, h))
        container_positions[node_id] = (x, y, w, h)

        # Lay out children INSIDE the container
        children_sizes = []
        for child_id in children:
            if child_id not in nodes or child_id in existing_ids:
                continue
            child_def = nodes[child_id]
            child_label = child_def.get("label", "Component")
            cw, ch = calculate_text_size(child_label, child_def.get("width"), child_def.get("height"))
            children_sizes.append((child_id, cw, ch))

        child_xy = layout_children_inside(x, y, w, h, children_sizes)

        for child_id, cx_y in child_xy.items():
            child_def = nodes[child_id]
            child_label = child_def.get("label", "Component")
            cw, ch = calculate_text_size(child_label, child_def.get("width"), child_def.get("height"))
            cx, cy = cx_y
            all_positions[child_id] = (cx, cy, cw, ch)
            all_pos_list.append((cx, cy, cw, ch))

    # PASS 1b: Lay out free (non-child) leaf nodes on canvas
    for node_id, node_def in nodes.items():
        if node_id in children_claimed:
            continue
        if node_id in container_positions:
            continue
        if node_id in existing_ids:
            continue
        if node_id in all_positions:
            continue

        label = node_def.get("label", "Component")
        w, h = calculate_text_size(label, node_def.get("width"), node_def.get("height"))
        x, y = find_canvas_position(all_pos_list, w, h)
        all_positions[node_id] = (x, y, w, h)
        all_pos_list.append((x, y, w, h))

    # ── PASS 2: Yield elements in render order ───────────────────────────────
    render_order = _resolve_node_order(nodes)

    for node_id in render_order:
        if node_id not in nodes:
            continue

        node_def = nodes[node_id]
        label = node_def.get("label", "Component")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in SHAPE_CREATORS:
            shape_type = "rectangle"

        bg_color = node_def.get("backgroundColor")
        stroke_color = node_def.get("strokeColor")
        text_color = node_def.get("textColor")
        is_container = bool(node_def.get("children"))

        batch = []

        if node_id in existing_ids:
            # UPDATE existing shape
            updated = copy.deepcopy(id_to_elem[node_id])
            pos = all_positions.get(node_id, (0, 0, 160, 70))
            new_w = int(node_def.get("width") or pos[2])
            new_h = int(node_def.get("height") or pos[3])
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
            # CREATE new shape
            pos = all_positions.get(node_id)
            if not pos:
                continue  # Position wasn't resolved — skip

            x, y, w, h = pos

            creator_fn = SHAPE_CREATORS[shape_type]
            shape, text = creator_fn(
                shape_id=node_id, label=label,
                x=x, y=y, w=w, h=h,
                bg_color=bg_color,
                stroke_color=stroke_color,
                text_color=text_color,
                is_container=is_container,
            )

            new_shape_map[node_id] = shape
            batch.extend([shape, text])

        if batch:
            yield batch

    # ── Yield edges ──────────────────────────────────────────────────────────
    drawn: Set[Tuple[str, str]] = set()

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

        batch = list(arrow_elems)
        for eid in (from_id, to_id):
            if eid in existing_updates:
                batch.append(existing_updates[eid])
        yield batch
