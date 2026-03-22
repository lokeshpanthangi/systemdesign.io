"""
Scoring Tool
Evaluates user's system design solution using LLM.
Uses centralized LLM provider (GitHub Copilot API).
"""
from typing import Dict, Any
import json
from langchain_core.prompts import ChatPromptTemplate

from core.llm_provider import get_llm


async def score_solution(
    problem_data: Dict[str, Any],
    diagram_data: Dict[str, Any],
    diagram_str: str
) -> Dict[str, Any]:
    """
    Use LLM to evaluate the system design solution.
    
    Args:
        problem_data: Problem requirements and info
        diagram_data: Raw Excalidraw data
        diagram_str: Formatted diagram summary
    
    Returns:
        Scoring result dict with score, breakdown, implemented, missing
    """
    # Check if diagram is empty
    elements = diagram_data.get("elements", [])
    if not elements:
        return {
            "score": 0,
            "max_score": 100,
            "breakdown": [{
                "requirement": "Any component",
                "achieved": False,
                "points": 0,
                "note": "Empty diagram"
            }],
            "implemented": [],
            "missing": ["No components drawn on canvas"]
        }
    
    try:
        llm = get_llm(temperature=0.3)
        
        system_prompt = """You are a system design evaluator. Score the student's diagram (0-100) against requirements.

Evaluate: components, connections, scalability, best practices, labels.

Focus strictly on the system design question and diagram provided. Do NOT introduce requirements or advice unrelated to this problem. If information is missing from the diagram, point that out instead of speculating.

Scoring: 90-100 (exceptional), 80-89 (very good), 70-79 (good), 60-69 (adequate), 50-59 (needs work), 0-49 (incomplete).

Return ONLY valid JSON:
{{"score": 0-100, "implemented": ["what's good (3-6 items)"], "missing": ["what's missing (2-5 items)"], "breakdown": [{{"requirement": "req name", "achieved": true/false, "points": number, "note": "brief note"}}]}}

Be specific, reference actual component names, and tie every remark back to the stated requirements."""

        user_prompt = f"""Problem: {problem_data.get('title', 'Unknown')}

Description: {problem_data.get('description', 'No description')[:200]}

Requirements:
{chr(10).join(f"{i+1}. {req}" for i, req in enumerate(problem_data.get('requirements', ['No requirements'])[:7]))}

Student's Diagram:
{diagram_str[:800]}

Stats: {len(elements)} elements, {len([e for e in elements if e.get('type') in ['rectangle', 'ellipse', 'diamond']])} components, {len([e for e in elements if e.get('type') == 'arrow'])} arrows, {len([e for e in elements if e.get('type') == 'text'])} labels

Deliver feedback that applies ONLY to this problem statement. If a requirement is unclear or absent in the diagram, flag it as missing rather than inventing new scope.

Score and provide detailed feedback in JSON."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", user_prompt)
        ])
        
        chain = prompt | llm
        result = await chain.ainvoke({})
        
        # Parse JSON response
        feedback_json = json.loads(result.content)
        
        # Ensure required keys and validate
        if "score" not in feedback_json or not isinstance(feedback_json["score"], (int, float)):
            feedback_json["score"] = 50
        
        if "implemented" not in feedback_json or not isinstance(feedback_json["implemented"], list):
            feedback_json["implemented"] = ["Diagram structure created"]
        
        if "missing" not in feedback_json or not isinstance(feedback_json["missing"], list):
            feedback_json["missing"] = ["Some requirements may need attention"]
        
        if "breakdown" not in feedback_json or not isinstance(feedback_json["breakdown"], list):
            feedback_json["breakdown"] = [{
                "requirement": "Overall Design",
                "achieved": feedback_json["score"] >= 60,
                "points": feedback_json["score"],
                "note": "Evaluated by AI"
            }]
        
        # Ensure score is within bounds
        feedback_json["score"] = max(0, min(100, float(feedback_json["score"])))
        feedback_json["max_score"] = 100
        
        print(f"LLM scoring successful: {feedback_json['score']}/100")
        return feedback_json
        
    except json.JSONDecodeError as e:
        print(f"LLM returned invalid JSON: {e}")
        return {
            "score": 0,
            "max_score": 100,
            "breakdown": [{
                "requirement": "LLM Evaluation",
                "achieved": False,
                "points": 0,
                "note": "Failed to parse AI response"
            }],
            "implemented": [],
            "missing": ["AI evaluation failed - invalid response format"]
        }
    except Exception as e:
        print(f"LLM scoring error: {e}")
        return {
            "score": 0,
            "max_score": 100,
            "breakdown": [{
                "requirement": "LLM Evaluation",
                "achieved": False,
                "points": 0,
                "note": str(e)
            }],
            "implemented": [],
            "missing": [f"AI evaluation error: {str(e)}"]
        }
