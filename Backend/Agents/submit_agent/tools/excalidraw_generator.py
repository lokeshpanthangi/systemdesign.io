"""
Excalidraw Element Generator — ID-Based
Converts the LLM's node/edge structure into valid Excalidraw element JSON.
Connections use element IDs. Colors are optional. Sizes fit text.
Supports UPDATING existing elements and properly binds arrows to shapes.
"""
import uuid
import copy
from typing import Dict, Any, List, Optional, Tuple


def _id() -> str:
    return uuid.uuid4().hex[:20]


def _seed(s: str) -> int:
    return abs(hash(s)) % (2**31)


# ─── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_STROKE = "#1e1e1e"
DEFAULT_BG = "transparent"


# ─── Size based on text ──────────────────────────────────────────────────────
def _text_based_size(label: str) -> Tuple[int, int]:
    """Calculate shape size so the label fits in a single line."""
    char_width = 10    # approx px per char at fontSize 16
    padding_x = 50     # horizontal padding (left + right)
    min_width = 140
    w = max(min_width, len(label) * char_width + padding_x)
    h = 60             # single-line height
    return w, h


# ─── Build existing element maps ─────────────────────────────────────────────
def _build_maps(existing_elements: List[Dict]):
    """Build lookup maps from existing canvas elements."""
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


# ─── Find position that doesn't overlap ──────────────────────────────────────
def _find_position(
    all_positions: List[Tuple[float, float, float, float]],
    new_w: int, new_h: int,
    col: int, row: int,
) -> Tuple[float, float]:
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


# ─── Create shape + bound text ───────────────────────────────────────────────
def _create_shape(
    shape_id: str, label: str, shape_type: str,
    x: float, y: float, w: int, h: int,
    bg_color: Optional[str] = None,
    stroke_color: Optional[str] = None,
    text_color: Optional[str] = None,
) -> Tuple[Dict, Dict]:
    """Create a shape element + bound text label."""
    text_id = _id()

    bg = bg_color or DEFAULT_BG
    stroke = stroke_color or DEFAULT_STROKE
    txt_color = text_color or stroke

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
        "roundness": {"type": 3} if shape_type == "rectangle" else {"type": 2},
        "seed": _seed(shape_id),
        "version": 1,
        "versionNonce": _seed(shape_id + "v"),
        "isDeleted": False,
        "boundElements": [{"id": text_id, "type": "text"}],
        "updated": 1,
        "link": None,
        "locked": False,
    }

    text = {
        "id": text_id,
        "type": "text",
        "x": x + 10,
        "y": y + h / 2 - 12,
        "width": w - 20,
        "height": 24,
        "angle": 0,
        "strokeColor": txt_color,
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
        "seed": _seed(text_id),
        "version": 1,
        "versionNonce": _seed(text_id + "v"),
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
        "containerId": shape_id,
        "originalText": label,
        "autoResize": True,
        "lineHeight": 1.25,
    }

    return shape, text


# ─── Create arrow ─────────────────────────────────────────────────────────────
def _create_arrow(
    from_id: str, to_id: str,
    from_pos: Tuple[float, float, float, float],
    to_pos: Tuple[float, float, float, float],
    label: Optional[str] = None,
    direction: str = "one-way",
    stroke_color: Optional[str] = None,
) -> List[Dict]:
    """Create an arrow between two elements using their positions."""
    arrow_id = _id()
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
        "seed": _seed(arrow_id),
        "version": 1,
        "versionNonce": _seed(arrow_id + "v"),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
        "points": [[0, 0], [ex - sx, ey - sy]],
        "lastCommittedPoint": None,
        "startBinding": {"elementId": from_id, "focus": 0, "gap": 5, "fixedPoint": None},
        "endBinding":   {"elementId": to_id,   "focus": 0, "gap": 5, "fixedPoint": None},
        "startArrowhead": start_arrow,
        "endArrowhead": "arrow",
        "elbowed": False,
    }

    result = [arrow]

    if label:
        tid = _id()
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
            "seed": _seed(tid), "version": 1, "versionNonce": _seed(tid + "v"),
            "isDeleted": False, "boundElements": None, "updated": 1,
            "link": None, "locked": False,
            "text": label, "fontSize": 13, "fontFamily": 1,
            "textAlign": "center", "verticalAlign": "middle",
            "containerId": arrow_id,
            "originalText": label, "autoResize": True, "lineHeight": 1.25,
        })

    return result, arrow_id


# ─── Add arrow binding to a shape (new or existing) ──────────────────────────
def _add_arrow_to_shape(
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
            # Bump version so Excalidraw treats it as newer
            existing_updates[shape_id]["version"] = existing_updates[shape_id].get("version", 1) + 1
            existing_updates[shape_id]["versionNonce"] = _seed(shape_id + str(existing_updates[shape_id]["version"]))

        shape = existing_updates[shape_id]
        bound = shape.get("boundElements") or []
        if not isinstance(bound, list):
            bound = []
        if not any(b.get("id") == arrow_id for b in bound):
            bound.append({"id": arrow_id, "type": "arrow"})
        shape["boundElements"] = bound


# ─── Main builder ─────────────────────────────────────────────────────────────
def build_diagram_from_description(
    description: dict,
    existing_elements: List[Dict] = None,
) -> List[Dict]:
    """
    Convert the LLM's node/edge JSON into Excalidraw elements.

    Supports:
    - Creating new nodes (new IDs)
    - Updating existing nodes (existing IDs → modifies label/colors)
    - Connecting by ID with proper bidirectional binding
    - Text-based sizing (boxes fit their labels)

    Returns a flat list of elements to MERGE BY ID on the frontend.
    """
    existing_elements = existing_elements or []
    nodes = description.get("nodes", {})
    edges = description.get("edges", [])

    id_to_elem, id_to_pos, existing_ids = _build_maps(existing_elements)

    # Track positions (existing + new)
    all_positions: Dict[str, Tuple[float, float, float, float]] = dict(id_to_pos)
    all_pos_list = list(id_to_pos.values())

    # Output collections
    output_elements: List[Dict] = []
    new_shape_map: Dict[str, Dict] = {}       # node_id -> shape element (for binding updates)
    existing_updates: Dict[str, Dict] = {}     # existing elements that need boundElements updates

    cols = max(1, min(3, (len(nodes) + 1) // 2))
    node_idx = 0

    # ── Process nodes ─────────────────────────────────────────────────────
    for node_id, node_def in nodes.items():
        label = node_def.get("label", "Component")
        shape_type = node_def.get("shape", "rectangle").lower()
        if shape_type not in ("rectangle", "ellipse", "diamond"):
            shape_type = "rectangle"

        bg_color = node_def.get("backgroundColor")
        stroke_color = node_def.get("strokeColor")
        text_color = node_def.get("textColor")

        if node_id in existing_ids:
            # ── UPDATE existing node ──────────────────────────────────
            updated = copy.deepcopy(id_to_elem[node_id])
            if label:
                # Find and update the bound text element
                for elem in existing_elements:
                    if isinstance(elem, dict) and elem.get("type") == "text" and elem.get("containerId") == node_id:
                        text_update = copy.deepcopy(elem)
                        text_update["text"] = label
                        text_update["originalText"] = label
                        text_update["version"] = text_update.get("version", 1) + 1
                        output_elements.append(text_update)
                        break

            # Update colors if provided
            if bg_color:
                updated["backgroundColor"] = bg_color
            if stroke_color:
                updated["strokeColor"] = stroke_color

            # Resize to fit new label
            new_w, new_h = _text_based_size(label)
            updated["width"] = new_w
            updated["height"] = new_h
            updated["version"] = updated.get("version", 1) + 1
            updated["versionNonce"] = _seed(node_id + str(updated["version"]))

            existing_updates[node_id] = updated
            all_positions[node_id] = (updated["x"], updated["y"], new_w, new_h)
        else:
            # ── CREATE new node ───────────────────────────────────────
            w, h = _text_based_size(label)

            col = node_idx % cols
            row = node_idx // cols
            x, y = _find_position(all_pos_list, w, h, col, row)

            shape, text = _create_shape(
                shape_id=node_id, label=label, shape_type=shape_type,
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
        stroke_color = edge.get("strokeColor")

        arrow_elems, arrow_id = _create_arrow(
            from_id, to_id, from_pos, to_pos,
            label=arrow_label, direction=direction, stroke_color=stroke_color,
        )

        # Bind arrow to BOTH endpoints (new or existing)
        _add_arrow_to_shape(from_id, arrow_id, new_shape_map, existing_updates, id_to_elem)
        _add_arrow_to_shape(to_id, arrow_id, new_shape_map, existing_updates, id_to_elem)

        output_elements.extend(arrow_elems)

    # ── Add updated existing elements to output ───────────────────────────
    output_elements.extend(existing_updates.values())

    return output_elements


# ─── Streaming version ───────────────────────────────────────────────────────
def build_diagram_streaming(
    description: dict,
    existing_elements: List[Dict] = None,
):
    """
    Generator that yields element batches one at a time.
    Each yield is a list of elements to merge by ID on the frontend.
    """
    existing_elements = existing_elements or []
    nodes = description.get("nodes", {})
    edges = description.get("edges", [])

    id_to_elem, id_to_pos, existing_ids = _build_maps(existing_elements)

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
        if shape_type not in ("rectangle", "ellipse", "diamond"):
            shape_type = "rectangle"

        bg_color = node_def.get("backgroundColor")
        stroke_color = node_def.get("strokeColor")
        text_color = node_def.get("textColor")

        batch = []

        if node_id in existing_ids:
            # UPDATE existing
            updated = copy.deepcopy(id_to_elem[node_id])
            new_w, new_h = _text_based_size(label)
            updated["width"] = new_w
            updated["height"] = new_h
            if bg_color:
                updated["backgroundColor"] = bg_color
            if stroke_color:
                updated["strokeColor"] = stroke_color
            updated["version"] = updated.get("version", 1) + 1
            updated["versionNonce"] = _seed(node_id + str(updated["version"]))

            existing_updates[node_id] = updated
            all_positions[node_id] = (updated["x"], updated["y"], new_w, new_h)
            batch.append(updated)

            # Update bound text
            for elem in existing_elements:
                if isinstance(elem, dict) and elem.get("type") == "text" and elem.get("containerId") == node_id:
                    text_update = copy.deepcopy(elem)
                    text_update["text"] = label
                    text_update["originalText"] = label
                    text_update["version"] = text_update.get("version", 1) + 1
                    batch.append(text_update)
                    break
        else:
            # CREATE new
            w, h = _text_based_size(label)
            col = node_idx % cols
            row = node_idx // cols
            x, y = _find_position(all_pos_list, w, h, col, row)

            shape, text = _create_shape(
                shape_id=node_id, label=label, shape_type=shape_type,
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

    # Yield edges one by one (including any existing element updates for bindings)
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
        stroke_color = edge.get("strokeColor")

        arrow_elems, arrow_id = _create_arrow(
            from_id, to_id, from_pos, to_pos,
            label=arrow_label, direction=direction, stroke_color=stroke_color,
        )

        # Bind arrow to both endpoints
        _add_arrow_to_shape(from_id, arrow_id, new_shape_map, existing_updates, id_to_elem)
        _add_arrow_to_shape(to_id, arrow_id, new_shape_map, existing_updates, id_to_elem)

        # Include updated existing shapes in this batch so frontend can merge them
        batch = list(arrow_elems)
        for eid in (from_id, to_id):
            if eid in existing_updates:
                batch.append(existing_updates[eid])

        yield batch
