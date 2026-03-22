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

# ════════════════════════════════════════════════════════════════════════════
# MINIMUM SIZES - Enforce these to ensure readable diagrams
# ════════════════════════════════════════════════════════════════════════════

MIN_SIZES = {
    "rectangle": {"width": 140, "height": 60},
    "ellipse": {"width": 120, "height": 60},
    "diamond": {"width": 100, "height": 80},
    "container": {"width": 300, "height": 200},  # for nodes with children
}

# Minimum spacing between nodes
MIN_NODE_GAP = 80

# First node default position (avoid canvas edge cutoff)
CANVAS_START_X = 200
CANVAS_START_Y = 150


def enforce_minimum_size(shape_type: str, width: int, height: int, is_container: bool = False) -> Tuple[int, int]:
    """
    Enforce minimum sizes for shapes to ensure readable diagrams.
    Returns (width, height) with minimums applied.
    """
    key = "container" if is_container else shape_type
    min_w = MIN_SIZES.get(key, MIN_SIZES["rectangle"])["width"]
    min_h = MIN_SIZES.get(key, MIN_SIZES["rectangle"])["height"]
    return max(width, min_w), max(height, min_h)


# ─── Text-Based Auto-Sizing ──────────────────────────────────────────────────

def calculate_text_size(
    label: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    shape_type: str = "rectangle",
    is_container: bool = False
) -> Tuple[int, int]:
    """
    Return (width, height) for a node.
    Enforces minimum sizes and uses LLM-provided values when given.
    """
    # Get minimum sizes
    min_w, min_h = enforce_minimum_size(shape_type, 0, 0, is_container)

    if width and height:
        # Both provided - enforce minimums
        return max(int(width), min_w), max(int(height), min_h)

    if width:
        # Width provided, calculate height from label
        w = max(int(width), min_w)
        h = max(min_h, 60)  # Default reasonable height
        return w, h

    if height:
        # Height provided, calculate width from label
        char_width = 10
        padding_x = 50
        w = max(min_w, len(label) * char_width + padding_x)
        return w, max(int(height), min_h)

    # Fully auto - calculate from label
    char_width = 10
    padding_x = 50
    w = max(min_w, len(label) * char_width + padding_x)
    h = max(min_h, 60)
    return w, h


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
    Shows: id, label, shape, size WxH, center position (cx, cy), parent/children, colors.
    The LLM should use these cx/cy values to understand layout and pass its own
    cx/cy when creating new nodes.
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
    lines.append("COORDINATE SYSTEM: cx/cy are the CENTER point of each element.")
    lines.append("When creating new nodes pass \"x\" and \"y\" as the desired CENTER point.")
    lines.append("")

    if components:
        lines.append("=== NODES ===")
        for comp in components:
            cid = comp["id"]
            ctype = comp.get("type", "rectangle")
            label = shape_labels.get(cid, "(no label)")
            w = int(comp.get("width", 0))
            h = int(comp.get("height", 0))
            # Center point
            cx = int(comp.get("x", 0) + w / 2)
            cy = int(comp.get("y", 0) + h / 2)
            bg   = comp.get("backgroundColor", "transparent")
            stroke = comp.get("strokeColor", "#1e1e1e")
            line = f'- id="{cid}"  label="{label}"  shape={ctype}  size={w}x{h}  center=({cx},{cy})'
            if bg not in ("transparent", None, ""):
                line += f'  bg={bg}'
            if stroke not in ("#1e1e1e", None, ""):
                line += f'  stroke={stroke}'
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
            aid = arrow.get("id", "?")
            start_id = (arrow.get("startBinding") or {}).get("elementId", "?")
            end_id = (arrow.get("endBinding") or {}).get("elementId", "?")
            start_label = shape_labels.get(start_id, "?")
            end_label = shape_labels.get(end_id, "?")
            arrow_label = ""
            for b in (arrow.get("boundElements") or []):
                if isinstance(b, dict) and b.get("type") == "text":
                    text_elem = id_to_elem.get(b.get("id", ""), {})
                    arrow_label = (text_elem.get("text") or "").strip()
            stroke = arrow.get("strokeColor", "")
            conn = f'- id="{aid}"  "{start_label}" ({start_id}) → "{end_label}" ({end_id})'
            if arrow_label:
                conn += f'  label=[{arrow_label}]'
            if stroke and stroke not in ("#1e1e1e", None, ""):
                conn += f'  stroke={stroke}'
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
    nodes = description.get("nodes") or {}
    edges = description.get("edges") or []
    if not isinstance(nodes, dict):
        nodes = {}
    if not isinstance(edges, list):
        edges = []

    id_to_elem, id_to_pos, existing_ids = build_element_maps(existing_elements)

    # Track all positions (existing + new)
    all_positions: Dict[str, Tuple[float, float, float, float]] = dict(id_to_pos)
    all_pos_list: List[Tuple[float, float, float, float]] = list(id_to_pos.values())

    new_shape_map: Dict[str, Dict] = {}
    existing_updates: Dict[str, Dict] = {}

    # Sanitize nodes: ensure all values are dicts (LLMs sometimes output null or strings)
    sane_nodes = {nid: nd for nid, nd in nodes.items() if isinstance(nd, dict)}

    # ── PASS 1: Figure out which nodes are children ─────────────────────────
    children_claimed: Set[str] = set()
    for node_id, node_def in sane_nodes.items():
        for child_id in node_def.get("children", []):
            children_claimed.add(child_id)

    # PASS 1-GRID: If nodes have row/col, resolve them to pixel positions first
    layout_mode = description.get("layout", "")
    direction   = description.get("direction", "top-bottom")
    has_grid = any("row" in nd or "col" in nd for nd in sane_nodes.values())
    if layout_mode == "grid" or has_grid:
        grid_positions = resolve_grid_positions(sane_nodes, id_to_pos, direction)
        for nid, pos in grid_positions.items():
            if nid not in existing_ids:
                all_positions[nid] = pos
                all_pos_list.append(pos)

    container_positions: Dict[str, Tuple[float, float, int, int]] = {}

    for node_id, node_def in sane_nodes.items():
        children = node_def.get("children", [])
        if not children:
            continue  # Not a container — handled below

        if node_id in existing_ids:
            continue  # Container already on canvas

        label = node_def.get("label", "Container")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in SHAPE_CREATORS:
            shape_type = "rectangle"

        # Use LLM-provided size for container, enforce minimums
        w, h = calculate_text_size(label, node_def.get("width"), node_def.get("height"), shape_type, is_container=True)

        # Get position from LLM or auto-place
        if "x" in node_def and "y" in node_def:
            x = float(node_def["x"]) - w / 2
            y = float(node_def["y"]) - h / 2
        else:
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
            child_shape = child_def.get("shape", "rectangle").lower()
            cw, ch = calculate_text_size(child_label, child_def.get("width"), child_def.get("height"), child_shape)
            children_sizes.append((child_id, cw, ch))

        child_xy = layout_children_inside(x, y, w, h, children_sizes)

        for child_id, cx_y in child_xy.items():
            child_def = sane_nodes[child_id]
            child_label = child_def.get("label", "Component")
            child_shape = child_def.get("shape", "rectangle").lower()
            cw, ch = calculate_text_size(child_label, child_def.get("width"), child_def.get("height"), child_shape)
            cx, cy = cx_y
            all_positions[child_id] = (cx, cy, cw, ch)
            all_pos_list.append((cx, cy, cw, ch))

    # PASS 1b: Lay out free (non-child) leaf nodes on canvas
    for node_id, node_def in sane_nodes.items():
        if node_id in children_claimed:
            continue
        if node_id in container_positions:
            continue
        if node_id in existing_ids:
            continue
        if node_id in all_positions:
            continue

        label = node_def.get("label", "Component")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in SHAPE_CREATORS:
            shape_type = "rectangle"
        w, h = calculate_text_size(label, node_def.get("width"), node_def.get("height"), shape_type)

        # If LLM provides x/y, treat as CENTER point and convert to top-left
        if "x" in node_def and "y" in node_def:
            x = float(node_def["x"]) - w / 2
            y = float(node_def["y"]) - h / 2
        else:
            x, y = find_canvas_position(all_pos_list, w, h)

        all_positions[node_id] = (x, y, w, h)
        all_pos_list.append((x, y, w, h))

    # ── PASS 2: Yield elements in render order ───────────────────────────────
    render_order = _resolve_node_order(sane_nodes)

    for node_id in render_order:
        if node_id not in sane_nodes:
            continue

        node_def = sane_nodes[node_id]
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


# ═══════════════════════════════════════════════════════════════════════════════
#  DELETE NODES
# ═══════════════════════════════════════════════════════════════════════════════

def delete_elements_from_diagram(
    node_ids: List[str],
    existing_elements: List[Dict],
) -> Tuple[List[Dict], int]:
    """
    Mark shapes, their bound text labels, and connected arrows as isDeleted.

    Returns:
        (deleted_batch, count_deleted)
        deleted_batch: list of element dicts with isDeleted=True to send to canvas
        count_deleted: number of primary elements (shapes) deleted
    """
    ids_to_delete: Set[str] = set(node_ids)
    deleted_batch: List[Dict] = []
    count = 0

    # Pass 1: collect text element IDs bound to the shapes being deleted
    # and collect arrow IDs that start/end at deleted nodes
    bound_text_ids: Set[str] = set()
    arrow_ids_to_delete: Set[str] = set()

    for elem in existing_elements:
        if not isinstance(elem, dict):
            continue

        eid = elem.get("id", "")

        # Text bound to a deleted shape
        if elem.get("type") == "text" and elem.get("containerId") in ids_to_delete:
            bound_text_ids.add(eid)

        # Arrows that connect to deleted nodes
        if elem.get("type") == "arrow":
            start = (elem.get("startBinding") or {}).get("elementId", "")
            end = (elem.get("endBinding") or {}).get("elementId", "")
            if start in ids_to_delete or end in ids_to_delete:
                arrow_ids_to_delete.add(eid)
                # Also grab the arrow's bound text label
                for b in (elem.get("boundElements") or []):
                    if isinstance(b, dict) and b.get("type") == "text":
                        bound_text_ids.add(b.get("id", ""))

    # Pass 2: build the deletion batch
    all_to_delete = ids_to_delete | bound_text_ids | arrow_ids_to_delete

    for elem in existing_elements:
        if not isinstance(elem, dict):
            continue
        eid = elem.get("id", "")
        if eid not in all_to_delete:
            continue

        deleted = copy.deepcopy(elem)
        deleted["isDeleted"] = True
        deleted["version"] = deleted.get("version", 1) + 1
        deleted["versionNonce"] = _generate_seed(eid + "del")
        deleted_batch.append(deleted)

        if eid in ids_to_delete:
            count += 1

    return deleted_batch, count


# ═══════════════════════════════════════════════════════════════════════════════
#  GRID LAYOUT RESOLVER
# ═══════════════════════════════════════════════════════════════════════════════

# Gap between grid cells
GRID_GAP_X = 100
GRID_GAP_Y = 80

# Starting canvas position for grid origin (0, 0)
GRID_ORIGIN_X = 100.0
GRID_ORIGIN_Y = 100.0


def resolve_grid_positions(
    nodes: Dict[str, dict],
    existing_positions: Dict[str, Tuple[float, float, float, float]],
    direction: str = "top-bottom",
) -> Dict[str, Tuple[float, float, int, int]]:
    """
    Convert row/col grid coordinates to pixel (x, y, w, h) for each node.
    Row → Y axis, Col → X axis (top-to-bottom flow).
    Returns {node_id: (x, y, w, h)} only for nodes with row/col defined.
    """
    node_sizes: Dict[str, Tuple[int, int]] = {}
    for nid, node_def in nodes.items():
        if "row" not in node_def and "col" not in node_def:
            continue
        label = node_def.get("label", "")
        w, h = calculate_text_size(label, node_def.get("width"), node_def.get("height"))
        node_sizes[nid] = (w, h)

    if not node_sizes:
        return {}

    max_row = max(nodes[nid].get("row", 0) for nid in node_sizes)
    max_col = max(nodes[nid].get("col", 0) for nid in node_sizes)

    row_heights: Dict[int, int] = {r: 0 for r in range(max_row + 1)}
    col_widths: Dict[int, int] = {c: 0 for c in range(max_col + 1)}

    for nid, (w, h) in node_sizes.items():
        row = nodes[nid].get("row", 0)
        col = nodes[nid].get("col", 0)
        row_heights[row] = max(row_heights[row], h)
        col_widths[col] = max(col_widths[col], w)

    if existing_positions:
        max_existing_x = max(x + w for (x, _, w, _) in existing_positions.values())
        origin_x = max_existing_x + GRID_GAP_X
    else:
        origin_x = GRID_ORIGIN_X
    origin_y = GRID_ORIGIN_Y

    col_x: Dict[int, float] = {}
    acc = origin_x
    for c in range(max_col + 1):
        col_x[c] = acc
        acc += col_widths[c] + GRID_GAP_X

    row_y: Dict[int, float] = {}
    acc = origin_y
    for r in range(max_row + 1):
        row_y[r] = acc
        acc += row_heights[r] + GRID_GAP_Y

    result: Dict[str, Tuple[float, float, int, int]] = {}
    for nid, (w, h) in node_sizes.items():
        row = nodes[nid].get("row", 0)
        col = nodes[nid].get("col", 0)

        x = col_x[col]
        y = row_y[row]
        cell_w = col_widths[col]
        cell_h = row_heights[row]
        cx = x + (cell_w - w) / 2
        cy = y + (cell_h - h) / 2

        result[nid] = (cx, cy, w, h)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  UPDATE STYLE & POSITION
# ═══════════════════════════════════════════════════════════════════════════════

def update_style_elements(
    updates: List[Dict],
    existing_elements: List[Dict],
) -> Tuple[List[Dict], int]:
    """
    Apply style/position changes to existing elements by ID.

    Each update dict:
      {
        "id": "element_id",
        "x": 150,                    # optional — new center X position
        "y": 200,                    # optional — new center Y position
        "backgroundColor": "#hex",   # optional
        "strokeColor": "#hex",       # optional — applies to shapes AND arrows
        "textColor": "#hex",         # optional — applied to the bound text element
      }

    Returns (updated_batch, count_updated).
    """
    update_map: Dict[str, Dict] = {}
    for u in updates:
        uid = u.get("id")
        if uid:
            update_map[uid] = u

    if not update_map:
        return [], 0

    # Build a map of containerId → text element so we can update textColor
    container_to_text: Dict[str, str] = {}
    for elem in existing_elements:
        if isinstance(elem, dict) and elem.get("type") == "text":
            cid = elem.get("containerId")
            if cid:
                container_to_text[cid] = elem["id"]

    updated_batch: List[Dict] = []
    count = 0
    text_ids_to_update: Dict[str, str] = {}  # text_id → textColor

    for elem in existing_elements:
        if not isinstance(elem, dict):
            continue
        eid = elem.get("id", "")
        if eid not in update_map:
            continue

        u = update_map[eid]
        updated = copy.deepcopy(elem)
        changed = False

        # Position updates (x, y are center coords)
        if "x" in u or "y" in u:
            w = elem.get("width", 160)
            h = elem.get("height", 70)
            new_x = u.get("x", elem.get("x", 0) + w / 2) - w / 2 if "x" in u else elem.get("x", 0)
            new_y = u.get("y", elem.get("y", 0) + h / 2) - h / 2 if "y" in u else elem.get("y", 0)
            updated["x"] = new_x
            updated["y"] = new_y
            changed = True

        if "backgroundColor" in u and u["backgroundColor"]:
            updated["backgroundColor"] = u["backgroundColor"]
            changed = True
        if "strokeColor" in u and u["strokeColor"]:
            updated["strokeColor"] = u["strokeColor"]
            changed = True

        # Queue text color update for the bound text element
        if "textColor" in u and u["textColor"] and eid in container_to_text:
            text_ids_to_update[container_to_text[eid]] = u["textColor"]

        if changed:
            updated["version"] = updated.get("version", 1) + 1
            updated["versionNonce"] = _generate_seed(eid + "style")
            updated_batch.append(updated)
            count += 1

    # Apply text color changes
    for elem in existing_elements:
        if not isinstance(elem, dict):
            continue
        eid = elem.get("id", "")
        if eid not in text_ids_to_update:
            continue
        updated = copy.deepcopy(elem)
        updated["strokeColor"] = text_ids_to_update[eid]  # Excalidraw uses strokeColor for text color
        updated["version"] = updated.get("version", 1) + 1
        updated["versionNonce"] = _generate_seed(eid + "textcol")
        updated_batch.append(updated)

    return updated_batch, count


# ═══════════════════════════════════════════════════════════════════════════════
#  EDIT EDGES
# ═══════════════════════════════════════════════════════════════════════════════

def edit_edges_elements(
    edits: List[Dict],
    existing_elements: List[Dict],
) -> Tuple[List[Dict], int]:
    """
    Edit or delete existing edges (arrows) by ID.

    Each edit dict:
      {
        "id": "arrow_id",           # required
        "action": "delete"|"edit",  # required
        # For edit action, optional fields:
        "from": "new_source_id",    # change source node
        "to": "new_target_id",      # change target node
        "label": "new label",       # change arrow label
        "strokeColor": "#hex",      # change color
        "direction": "one-way"|"two-way"
      }

    Returns (updated_batch, count_updated).
    """
    edit_map: Dict[str, Dict] = {}
    for e in edits:
        eid = e.get("id")
        if eid:
            edit_map[eid] = e

    if not edit_map:
        return [], 0

    # Build lookup maps
    id_to_elem: Dict[str, Dict] = {}
    id_to_pos: Dict[str, Tuple[float, float, float, float]] = {}
    arrow_to_text: Dict[str, str] = {}  # arrow_id -> bound text id
    text_to_arrow: Dict[str, str] = {}   # text_id -> arrow_id

    for elem in existing_elements:
        if not isinstance(elem, dict) or not elem.get("id"):
            continue
        eid = elem["id"]
        id_to_elem[eid] = elem

        if elem.get("type") == "arrow":
            w = elem.get("width", 0)
            h = elem.get("height", 0)
            id_to_pos[eid] = (elem.get("x", 0), elem.get("y", 0), abs(w), abs(h))
            # Find bound text
            for b in (elem.get("boundElements") or []):
                if isinstance(b, dict) and b.get("type") == "text":
                    arrow_to_text[eid] = b.get("id", "")
        elif elem.get("type") == "text":
            cid = elem.get("containerId")
            if cid:
                text_to_arrow[eid] = cid

    # Also get shape positions for re-routing arrows
    for elem in existing_elements:
        if isinstance(elem, dict) and elem.get("type") in ("rectangle", "ellipse", "diamond"):
            eid = elem["id"]
            id_to_pos[eid] = (
                elem.get("x", 0), elem.get("y", 0),
                elem.get("width", 200), elem.get("height", 80),
            )

    updated_batch: List[Dict] = []
    deleted_batch: List[Dict] = []
    count = 0

    for arrow_id, edit in edit_map.items():
        if arrow_id not in id_to_elem:
            continue

        action = edit.get("action", "edit")
        arrow = id_to_elem[arrow_id]

        if action == "delete":
            # Mark arrow as deleted
            deleted = copy.deepcopy(arrow)
            deleted["isDeleted"] = True
            deleted["version"] = deleted.get("version", 1) + 1
            deleted["versionNonce"] = _generate_seed(arrow_id + "del")
            deleted_batch.append(deleted)
            count += 1

            # Also delete bound text label if exists
            if arrow_id in arrow_to_text:
                text_id = arrow_to_text[arrow_id]
                text_elem = id_to_elem.get(text_id)
                if text_elem:
                    deleted_text = copy.deepcopy(text_elem)
                    deleted_text["isDeleted"] = True
                    deleted_text["version"] = deleted_text.get("version", 1) + 1
                    deleted_text["versionNonce"] = _generate_seed(text_id + "del")
                    deleted_batch.append(deleted_text)
            continue

        # Edit action
        updated = copy.deepcopy(arrow)
        changed = False

        # Color change
        if "strokeColor" in edit and edit["strokeColor"]:
            updated["strokeColor"] = edit["strokeColor"]
            changed = True

        # Direction change
        if "direction" in edit:
            direction = edit["direction"]
            if direction == "two-way":
                updated["startArrowhead"] = "arrow"
            else:
                updated["startArrowhead"] = None
            changed = True

        # Label change
        if "label" in edit:
            new_label = edit["label"]
            text_id = arrow_to_text.get(arrow_id)
            if new_label and not text_id:
                # Need to create a new text label
                tid = _generate_id()
                sx, sy = arrow.get("x", 0), arrow.get("y", 0)
                w, h = arrow.get("width", 0), arrow.get("height", 0)
                mid_x = sx + w / 2
                mid_y = sy + h / 2
                stroke = arrow.get("strokeColor", "#1e1e1e")
                updated["boundElements"] = [{"id": tid, "type": "text"}]
                text_elem = {
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
                    "text": new_label, "fontSize": 13, "fontFamily": 1,
                    "textAlign": "center", "verticalAlign": "middle",
                    "containerId": arrow_id,
                    "originalText": new_label, "autoResize": True, "lineHeight": 1.25,
                }
                updated_batch.append(text_elem)
                changed = True
            elif text_id:
                text_elem = id_to_elem.get(text_id)
                if text_elem:
                    text_update = copy.deepcopy(text_elem)
                    if new_label:
                        text_update["text"] = new_label
                        text_update["originalText"] = new_label
                    else:
                        # Empty label = delete text
                        text_update["isDeleted"] = True
                    text_update["version"] = text_update.get("version", 1) + 1
                    text_update["versionNonce"] = _generate_seed(text_id + "edit")
                    updated_batch.append(text_update)

        # Re-route: change from/to
        if ("from" in edit or "to" in edit) and arrow.get("type") == "arrow":
            new_from = edit.get("from", (arrow.get("startBinding") or {}).get("elementId", ""))
            new_to = edit.get("to", (arrow.get("endBinding") or {}).get("elementId", ""))

            from_pos = id_to_pos.get(new_from)
            to_pos = id_to_pos.get(new_to)

            if from_pos and to_pos:
                fx, fy, fw, fh = from_pos
                tx, ty, tw, th = to_pos

                # Calculate new arrow points
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

                updated["x"] = sx
                updated["y"] = sy
                updated["width"] = ex - sx
                updated["height"] = ey - sy
                updated["points"] = [[0, 0], [ex - sx, ey - sy]]
                updated["startBinding"] = {"elementId": new_from, "focus": 0, "gap": 5, "fixedPoint": None}
                updated["endBinding"] = {"elementId": new_to, "focus": 0, "gap": 5, "fixedPoint": None}
                changed = True

        if changed:
            updated["version"] = updated.get("version", 1) + 1
            updated["versionNonce"] = _generate_seed(arrow_id + "edit")
            updated_batch.append(updated)
            count += 1

    return deleted_batch + updated_batch, count
