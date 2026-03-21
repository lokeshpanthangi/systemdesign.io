"""
Submit Agent — Streaming Chain
Orchestrates the submission evaluation with SSE streaming:
1. Streams scoring evaluation
2. Streams tips generation
3. Fetches learning resources (YouTube videos + docs)
4. Returns comprehensive submission result
"""
import json
import asyncio
from typing import Dict, Any, AsyncGenerator
from .tools.scoring import score_solution
from .tools.tips_generator import generate_tips
from .tools.youtube_fetcher import fetch_youtube_videos
from .tools.docs_fetcher import fetch_documentation


def extract_diagram_summary(diagram_data: Dict[str, Any]) -> str:
    """Extract and format diagram summary for analysis"""
    if not diagram_data or not isinstance(diagram_data, dict):
        return "Empty diagram"
    
    elements = diagram_data.get("elements", [])
    
    if not elements:
        return "No elements in diagram"
    
    components = []
    arrows = []
    text_elements = []
    
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        
        elem_type = elem.get("type", "")
        elem_id = elem.get("id", "")[:8]
        elem_text = elem.get("text", "")
        
        if elem_type == "arrow":
            start = elem.get("startBinding", {}).get("elementId", "")[:8]
            end = elem.get("endBinding", {}).get("elementId", "")[:8]
            arrows.append(f"Arrow({elem_id}): {start} → {end}" + (f' "{elem_text}"' if elem_text else ''))
        elif elem_type == "text":
            text_elements.append(f'Text: "{elem_text}"')
        else:
            components.append(f"{elem_type.upper()}({elem_id})" + (f': "{elem_text}"' if elem_text else ''))
    
    lines = [
        f"=== DIAGRAM SUMMARY ===",
        f"Total: {len(elements)} elements",
        f"Components: {len(components)}",
        f"Connections: {len(arrows)}",
        "",
        "=== COMPONENTS ===" if components else "",
        *[f"- {c}" for c in components],
        "",
        "=== CONNECTIONS ===" if arrows else "",
        *[f"- {a}" for a in arrows],
        "",
        "=== LABELS ===" if text_elements else "",
        *[f"- {t}" for t in text_elements[:10]]
    ]
    
    return "\n".join(line for line in lines if line)


async def evaluate_submission_stream(
    problem_data: Dict[str, Any],
    diagram_data: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Streaming version of evaluate_submission.
    Yields SSE-formatted JSON events as each step completes.
    
    Events:
      {"type": "status", "step": "scoring"} - Step started
      {"type": "score_result", "data": {...}} - Scoring complete
      {"type": "status", "step": "tips"} - Tips generation started
      {"type": "tips_result", "data": [...]} - Tips complete
      {"type": "status", "step": "resources"} - Resource fetch started
      {"type": "resources_result", "data": {...}} - Resources complete
      {"type": "done", "data": {...}} - Full result
    """
    diagram_str = extract_diagram_summary(diagram_data)
    
    # Step 1: Score the solution
    yield f"data: {json.dumps({'type': 'status', 'step': 'scoring', 'message': 'Evaluating your solution...'})}\n\n"
    
    scoring_result = await score_solution(problem_data, diagram_data, diagram_str)
    
    score = scoring_result.get("score", 0)
    max_score = scoring_result.get("max_score", 100)
    breakdown = scoring_result.get("breakdown", [])
    implemented = scoring_result.get("implemented", [])
    missing = scoring_result.get("missing", [])
    
    yield f"data: {json.dumps({'type': 'score_result', 'data': {'score': score, 'max_score': max_score, 'breakdown': breakdown, 'implemented': implemented, 'missing': missing}})}\n\n"
    
    # Step 2: Generate tips
    yield f"data: {json.dumps({'type': 'status', 'step': 'tips', 'message': 'Generating improvement tips...'})}\n\n"
    
    tips = await generate_tips(problem_data, scoring_result, diagram_str)
    
    yield f"data: {json.dumps({'type': 'tips_result', 'data': tips})}\n\n"
    
    # Step 3: Fetch resources (in parallel)
    yield f"data: {json.dumps({'type': 'status', 'step': 'resources', 'message': 'Finding learning resources...'})}\n\n"
    
    videos_task = fetch_youtube_videos(problem_data, missing)
    docs_task = fetch_documentation(problem_data, missing)
    
    videos, docs = await asyncio.gather(videos_task, docs_task)
    
    yield f"data: {json.dumps({'type': 'resources_result', 'data': {'videos': videos, 'docs': docs}})}\n\n"
    
    # Final complete result
    result = {
        "score": score,
        "max_score": max_score,
        "breakdown": breakdown,
        "feedback": {
            "implemented": implemented,
            "missing": missing,
            "next_steps": tips[:3] if len(tips) > 3 else tips
        },
        "tips": tips,
        "resources": {
            "videos": videos,
            "docs": docs
        }
    }
    
    yield f"data: {json.dumps({'type': 'done', 'data': result})}\n\n"


async def evaluate_submission(
    problem_data: Dict[str, Any],
    diagram_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Non-streaming version (backward compatibility).
    Collects all streaming results and returns final dict.
    """
    diagram_str = extract_diagram_summary(diagram_data)
    
    # Step 1: Score
    scoring_result = await score_solution(problem_data, diagram_data, diagram_str)
    score = scoring_result.get("score", 0)
    max_score = scoring_result.get("max_score", 100)
    breakdown = scoring_result.get("breakdown", [])
    implemented = scoring_result.get("implemented", [])
    missing = scoring_result.get("missing", [])
    
    # Step 2: Tips
    tips = await generate_tips(problem_data, scoring_result, diagram_str)
    
    # Step 3: Resources
    videos_task = fetch_youtube_videos(problem_data, missing)
    docs_task = fetch_documentation(problem_data, missing)
    videos, docs = await asyncio.gather(videos_task, docs_task)
    
    return {
        "score": score,
        "max_score": max_score,
        "breakdown": breakdown,
        "feedback": {
            "implemented": implemented,
            "missing": missing,
            "next_steps": tips[:3] if len(tips) > 3 else tips
        },
        "tips": tips,
        "resources": {
            "videos": videos,
            "docs": docs
        }
    }
