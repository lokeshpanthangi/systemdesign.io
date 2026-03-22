"""
Submission Service — Business Logic
Handles submission-from-session conversion logic.
"""
from datetime import datetime
from typing import Dict, Any

from database.database import db
from CRUD.session import get_session_by_id, mark_session_submitted
from CRUD.submission import create_submission, get_submission_by_id


async def create_submission_from_session_logic(
    session_id: str,
    user_email: str
) -> Dict[str, Any]:
    """
    Convert a practice session to a final submission.
    
    - Fetches session data
    - Creates submission with session's diagram_data, time_spent, and chat_messages
    - Marks session as 'submitted'
    - Returns the created submission
    
    Raises:
        ValueError: If session not found, unauthorized, or already submitted
    """
    session = await get_session_by_id(session_id)
    
    if not session:
        raise ValueError("Session not found")
    
    if session["user_id"] != user_email:
        raise PermissionError("Not authorized to submit this session")
    
    if session["status"] == "submitted":
        raise ValueError("Session already submitted")
    
    # Create submission from session data
    submission = await create_submission(
        user_id=session["user_id"],
        problem_id=session["problem_id"],
        diagram_data=session.get("diagram_data", {}),
        status="completed"
    )
    
    if not submission:
        raise RuntimeError("Failed to create submission")
    
    # Copy session data to submission
    submissions_collection = db.get_collection("submissions")
    
    await submissions_collection.update_one(
        {"_id": submission["_id"]},
        {"$set": {
            "time_spent": session.get("time_spent", 0),
            "chat_messages": session.get("chat_messages", []),
            "updated_at": datetime.utcnow()
        }}
    )
    
    # Mark session as submitted
    await mark_session_submitted(session_id, user_email)
    
    # Fetch updated submission
    updated_submission = await get_submission_by_id(str(submission["_id"]))
    
    return updated_submission
