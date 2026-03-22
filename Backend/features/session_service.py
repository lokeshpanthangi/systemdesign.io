"""
Session Service — Business Logic
All session-related business logic extracted from routes.
Routes only call these functions and format the HTTP response.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from database.database import db
import CRUD.session as session_crud
import CRUD.problem as problem_crud
from Agents.review_agent.agent import analyze_user_solution
from Agents.submit_agent.agent import evaluate_submission, evaluate_submission_stream


def format_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Format session document for response"""
    raw_messages = session.get("chat_messages", []) or []
    sanitized_messages: List[Dict[str, Any]] = []

    for m in raw_messages:
        try:
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, dict):
                content_str = json.dumps(content)
            else:
                content_str = str(content) if content is not None else ""

            timestamp = m.get("timestamp")
            sanitized_messages.append({
                "role": role,
                "content": content_str,
                "timestamp": timestamp
            })
        except Exception:
            continue

    return {
        "id": str(session["_id"]),
        "user_id": session["user_id"],
        "problem_id": session["problem_id"],
        "diagram_data": session.get("diagram_data", {}),
        "diagram_hash": session.get("diagram_hash", ""),
        "time_spent": session.get("time_spent", 0),
        "status": session["status"],
        "chat_messages": sanitized_messages,
        "last_saved_at": session.get("last_saved_at"),
        "started_at": session.get("started_at"),
        "ended_at": session.get("ended_at"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at")
    }


async def check_solution_logic(session: Dict, user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Check user's solution using AI agent.
    Returns cached feedback if diagram unchanged, otherwise calls AI.
    
    Returns:
        Dict with keys: feedback, timestamp, diagram_hash, cached, session_id, problem_id
    """
    # Compute current diagram hash
    diagram_data = session.get("diagram_data", {})
    try:
        current_hash = session_crud.calculate_diagram_hash(diagram_data)
    except Exception:
        current_hash = session.get("diagram_hash", "")
    
    # Check for cached feedback
    chat_messages = session.get("chat_messages", [])
    cached_feedback = None
    
    for msg in reversed(chat_messages):
        if msg.get("role") == "system_check":
            if msg.get("diagram_hash") == current_hash:
                cached_feedback_str = msg.get("content", "")
                try:
                    cached_feedback = json.loads(cached_feedback_str)
                except (json.JSONDecodeError, TypeError):
                    continue
                break
    
    if cached_feedback:
        return {
            "session_id": session_id,
            "problem_id": session["problem_id"],
            "feedback": cached_feedback,
            "timestamp": datetime.utcnow(),
            "diagram_hash": current_hash,
            "cached": True
        }
    
    # Get problem data
    problem = await problem_crud.get_problem_by_id(session["problem_id"])
    if not problem:
        raise ValueError("Problem not found")
    
    problem_data = {
        "title": problem.get("title", ""),
        "description": problem.get("description", ""),
        "requirements": problem.get("requirements", []),
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "difficulty": problem.get("difficulty", ""),
        "categories": problem.get("categories", [])
    }
    
    # Run AI agent analysis
    feedback = await analyze_user_solution(
        problem_data=problem_data,
        diagram_data=diagram_data
    )
    
    # Save feedback to session
    await session_crud.add_chat_message_to_session(
        session_id=session_id,
        user_id=user_id,
        role="system_check",
        content=json.dumps(feedback)
    )

    # Update diagram hash on the session
    sessions_collection = db.get_collection("sessions")
    await sessions_collection.update_one(
        {"_id": session["_id"]},
        {"$set": {
            "diagram_hash": current_hash,
            "updated_at": datetime.utcnow()
        }}
    )

    # Attach diagram_hash to the appended chat message
    try:
        await sessions_collection.update_one(
            {"_id": session["_id"]},
            {"$set": {f"chat_messages.{len(chat_messages)}.diagram_hash": current_hash}}
        )
    except Exception:
        pass
    
    return {
        "session_id": session_id,
        "problem_id": session["problem_id"],
        "feedback": feedback,
        "timestamp": datetime.utcnow(),
        "diagram_hash": current_hash,
        "cached": False
    }


async def submit_solution_logic(session: Dict, user_id: str, session_id: str) -> Dict[str, Any]:
    """
    Submit solution for final evaluation (non-streaming).
    Scores, generates tips, fetches resources, saves submission.
    
    Returns:
        Dict with submission result data.
    """
    # Get problem data
    problem = await problem_crud.get_problem_by_id(session["problem_id"])
    if not problem:
        raise ValueError("Problem not found")
    
    problem_data = {
        "title": problem.get("title", ""),
        "description": problem.get("description", ""),
        "requirements": problem.get("requirements", []),
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "difficulty": problem.get("difficulty", ""),
        "categories": problem.get("categories", [])
    }
    
    diagram_data = session.get("diagram_data", {})
    
    # Run submission evaluation
    evaluation = await evaluate_submission(
        problem_data=problem_data,
        diagram_data=diagram_data
    )
    
    # Create submission record
    submissions_collection = db.get_collection("submissions")
    
    submission_doc = {
        "user_id": user_id,
        "problem_id": session["problem_id"],
        "session_id": session_id,
        "diagram_data": diagram_data,
        "score": evaluation["score"],
        "max_score": evaluation["max_score"],
        "breakdown": evaluation["breakdown"],
        "feedback": evaluation["feedback"],
        "tips": evaluation["tips"],
        "resources": evaluation["resources"],
        "time_spent": session.get("time_spent", 0),
        "status": "completed",
        "submitted_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await submissions_collection.insert_one(submission_doc)
    submission_id = str(result.inserted_id)
    
    # Mark session as submitted
    await session_crud.mark_session_submitted(session_id, user_id)
    
    return {
        "submission_id": submission_id,
        "session_id": session_id,
        "problem_id": session["problem_id"],
        **evaluation,
        "timestamp": datetime.utcnow()
    }


async def submit_solution_stream_logic(session: Dict, user_id: str, session_id: str):
    """
    Streaming submission evaluation generator.
    Yields SSE events and saves submission on completion.
    """
    import json as _json
    
    problem = await problem_crud.get_problem_by_id(session["problem_id"])
    if not problem:
        raise ValueError("Problem not found")
    
    problem_data = {
        "title": problem.get("title", ""),
        "description": problem.get("description", ""),
        "requirements": problem.get("requirements", []),
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "difficulty": problem.get("difficulty", ""),
        "categories": problem.get("categories", [])
    }
    
    diagram_data = session.get("diagram_data", {})
    final_result = None
    
    async for event_str in evaluate_submission_stream(
        problem_data=problem_data,
        diagram_data=diagram_data
    ):
        yield event_str
        
        if '"type": "done"' in event_str:
            try:
                event_data = _json.loads(event_str.replace("data: ", "").strip())
                final_result = event_data.get("data")
            except Exception:
                pass
    
    # Save submission after stream completes
    if final_result:
        try:
            submissions_collection = db.get_collection("submissions")
            submission_doc = {
                "user_id": user_id,
                "problem_id": session["problem_id"],
                "session_id": session_id,
                "diagram_data": diagram_data,
                "score": final_result["score"],
                "max_score": final_result["max_score"],
                "breakdown": final_result["breakdown"],
                "feedback": final_result["feedback"],
                "tips": final_result["tips"],
                "resources": final_result["resources"],
                "time_spent": session.get("time_spent", 0),
                "status": "completed",
                "submitted_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            await submissions_collection.insert_one(submission_doc)
            await session_crud.mark_session_submitted(session_id, user_id)
        except Exception as e:
            print(f"Error saving submission after stream: {e}")


async def get_problem_submissions_logic(user_id: str, problem_id: str) -> List[Dict]:
    """Get all submissions for a problem by a user."""
    submissions_collection = db.get_collection("submissions")
    
    cursor = submissions_collection.find({
        "user_id": user_id,
        "problem_id": problem_id
    }).sort("submitted_at", -1)
    
    submissions = []
    async for doc in cursor:
        submissions.append({
            "submission_id": str(doc["_id"]),
            "session_id": doc.get("session_id"),
            "score": doc.get("score", 0),
            "max_score": doc.get("max_score", 100),
            "diagram_data": doc.get("diagram_data", {}),
            "submitted_at": doc.get("submitted_at"),
            "time_spent": doc.get("time_spent", 0)
        })
    
    return submissions


def extract_excalidraw_logic(session: Dict, session_id: str) -> Dict[str, Any]:
    """
    Extract and categorize Excalidraw diagram elements from a session.
    Pure logic — no DB calls needed.
    """
    diagram_data = session.get("diagram_data", {})
    
    if not diagram_data or not diagram_data.get("elements"):
        return {
            "session_id": session_id,
            "problem_id": session.get("problem_id", ""),
            "total_elements": 0,
            "components": [],
            "arrows": [],
            "text_elements": [],
            "raw_diagram_data": diagram_data
        }
    
    elements = diagram_data.get("elements", [])
    components = []
    arrows = []
    text_elements = []
    
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        
        extracted = {
            "id": elem.get("id", ""),
            "type": elem.get("type", ""),
            "text": elem.get("text", ""),
            "groupIds": elem.get("groupIds", []),
            "boundElements": elem.get("boundElements", [])
        }
        
        elem_type = elem.get("type", "")
        
        if elem_type == "arrow":
            extracted["startBinding"] = elem.get("startBinding", {})
            extracted["endBinding"] = elem.get("endBinding", {})
            arrows.append(extracted)
        elif elem_type == "text":
            text_elements.append(extracted)
        elif elem_type in ["rectangle", "ellipse", "diamond"]:
            components.append(extracted)
        else:
            components.append(extracted)
    
    return {
        "session_id": session_id,
        "problem_id": session.get("problem_id", ""),
        "total_elements": len(elements),
        "components": components,
        "arrows": arrows,
        "text_elements": text_elements,
        "raw_diagram_data": diagram_data
    }
