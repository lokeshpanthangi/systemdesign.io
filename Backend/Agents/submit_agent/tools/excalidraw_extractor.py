"""
Excalidraw Code Extractor Tool
Extracts and formats Excalidraw diagram components for LLM analysis.
Resolves bound text elements and outputs element IDs so the LLM can
reference them directly when creating connections.
"""
from typing import Dict, Any, List
from langchain_core.tools import tool


@tool
def extract_excalidraw_components(diagram_data: dict) -> str:
    """
    Extract structured components from Excalidraw diagram.
    Shows element IDs alongside labels so the LLM can reference
    existing elements by ID when creating connections.
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
    
    # Classify
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


def extract_component_list(diagram_data: dict) -> List[Dict[str, Any]]:
    """
    Helper function to extract raw component list with all required fields.
    Used by checking_agent for structured data processing.
    """
    if not diagram_data or not isinstance(diagram_data, dict):
        return []
    
    elements = diagram_data.get("elements", [])
    extracted = []
    
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        
        component = {
            "id": elem.get("id", ""),
            "type": elem.get("type", ""),
            "text": elem.get("text", ""),
            "groupIds": elem.get("groupIds", []),
            "boundElements": elem.get("boundElements", []),
        }
        
        if elem.get("type") == "arrow":
            component["startBinding"] = elem.get("startBinding", {})
            component["endBinding"] = elem.get("endBinding", {})
        
        extracted.append(component)
    
    return extracted
