"""
Review Agent Tool Helpers
Helper functions for extracting and formatting question/diagram data.
"""
from typing import Dict, Any, List


def extract_question_data(problem_data: Dict[str, Any]) -> str:
    """Extract and format question requirements for LLM input."""
    output_lines = []
    
    output_lines.append("=== QUESTION ===")
    output_lines.append(f"Title: {problem_data.get('title', 'Unknown')}")
    output_lines.append(f"Difficulty: {problem_data.get('difficulty', 'Unknown').upper()}")
    output_lines.append("")
    
    description = problem_data.get('description', '')
    if description:
        output_lines.append("=== DESCRIPTION ===")
        output_lines.append(description)
        output_lines.append("")
    
    requirements = problem_data.get('requirements', [])
    if requirements:
        output_lines.append("=== REQUIRED COMPONENTS ===")
        for idx, req in enumerate(requirements, 1):
            output_lines.append(f"{idx}. {req}")
        output_lines.append("")
    
    constraints = problem_data.get('constraints', [])
    if constraints:
        output_lines.append("=== CONSTRAINTS & ASSUMPTIONS ===")
        for idx, constraint in enumerate(constraints, 1):
            output_lines.append(f"{idx}. {constraint}")
        output_lines.append("")
    
    return "\n".join(output_lines)


def extract_diagram_data(diagram_data: Dict[str, Any]) -> str:
    """Extract and format Excalidraw diagram components for LLM input."""
    if not diagram_data or not isinstance(diagram_data, dict):
        return "No diagram data provided"
    
    elements = diagram_data.get("elements", [])
    
    if not elements:
        return "Empty diagram - no elements found"
    
    components = []
    arrows = []
    text_elements = []
    
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        
        component = {
            "id": elem.get("id", "unknown"),
            "type": elem.get("type", "unknown"),
            "text": elem.get("text", ""),
            "groupIds": elem.get("groupIds", []),
            "boundElements": elem.get("boundElements", []),
        }
        
        if elem.get("type") == "arrow":
            component["startBinding"] = elem.get("startBinding", {})
            component["endBinding"] = elem.get("endBinding", {})
            arrows.append(component)
        elif elem.get("type") == "text":
            text_elements.append(component)
        else:
            components.append(component)
    
    output_lines = []
    output_lines.append(f"=== DIAGRAM SUMMARY ===")
    output_lines.append(f"Total Elements: {len(elements)}")
    output_lines.append(f"Components: {len(components)}")
    output_lines.append(f"Arrows/Connections: {len(arrows)}")
    output_lines.append(f"Text Labels: {len(text_elements)}")
    output_lines.append("")
    
    if components:
        output_lines.append("=== COMPONENTS ===")
        for idx, comp in enumerate(components, 1):
            output_lines.append(f"{idx}. {comp['type'].upper()} (ID: {comp['id'][:8]}...)")
            if comp['text']:
                output_lines.append(f'   Label: "{comp["text"]}"')
            if comp['boundElements']:
                output_lines.append(f"   Connected to: {len(comp['boundElements'])} elements")
            output_lines.append("")
    
    if arrows:
        output_lines.append("=== CONNECTIONS ===")
        for idx, arrow in enumerate(arrows, 1):
            start = arrow.get('startBinding', {}).get('elementId', 'unknown')
            end = arrow.get('endBinding', {}).get('elementId', 'unknown')
            label = arrow.get('text', '')
            
            output_lines.append(f"{idx}. ARROW (ID: {arrow['id'][:8]}...)")
            output_lines.append(f"   From: {start[:8]}... → To: {end[:8]}...")
            if label:
                output_lines.append(f'   Label: "{label}"')
            output_lines.append("")
    
    if text_elements:
        output_lines.append("=== TEXT ANNOTATIONS ===")
        for idx, text in enumerate(text_elements, 1):
            output_lines.append(f'{idx}. "{text.get("text", "")}"')
        output_lines.append("")
    
    return "\n".join(output_lines)
