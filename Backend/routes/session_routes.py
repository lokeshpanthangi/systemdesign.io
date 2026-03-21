from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
from auth import get_current_user
from models import User
from database import db
from bson import ObjectId
import CRUD.session_crud as session_crud
import CRUD.problem_crud as problem_crud
from Agents.checking_agent import analyze_user_solution
from Agents.submit_agent import evaluate_submission, evaluate_submission_stream

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Pydantic Models
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime

class SessionCreate(BaseModel):
    problem_id: str

class SessionAutosave(BaseModel):
    diagram_data: Dict[Any, Any]
    time_spent: int

class SessionPause(BaseModel):
    time_spent: int

class ChatMessageCreate(BaseModel):
    role: str
    content: str

class CheckFeedbackResponse(BaseModel):
    session_id: str
    problem_id: str
    feedback: Dict[str, List[str]]  # Changed from str to structured dict
    timestamp: datetime
    diagram_hash: str
    cached: bool = False

class ResourceItem(BaseModel):
    title: str
    url: str
    channel: Optional[str] = None
    source: Optional[str] = None
    reason: Optional[str] = None

class ScoreBreakdownItem(BaseModel):
    requirement: str
    achieved: bool
    points: float
    note: Optional[str] = None

class SubmitResponse(BaseModel):
    submission_id: str
    session_id: str
    problem_id: str
    score: float
    max_score: float
    breakdown: List[ScoreBreakdownItem]
    feedback: Dict[str, List[str]]  # {implemented, missing, next_steps}
    tips: List[str]
    resources: Dict[str, List[ResourceItem]]  # {videos, docs}
    timestamp: datetime

class ExcalidrawExtractResponse(BaseModel):
    session_id: str
    problem_id: str
    total_elements: int
    components: List[Dict[str, Any]]
    arrows: List[Dict[str, Any]]
    text_elements: List[Dict[str, Any]]
    raw_diagram_data: Dict[Any, Any]

class SessionResponse(BaseModel):
    id: str
    user_id: str
    problem_id: str
    diagram_data: Dict[Any, Any]
    diagram_hash: str
    time_spent: int
    status: str
    chat_messages: List[ChatMessage]
    last_saved_at: datetime
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

def format_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Format session document for response"""
    # Ensure chat_messages contents are strings to satisfy response model
    raw_messages = session.get("chat_messages", []) or []
    sanitized_messages: List[Dict[str, Any]] = []

    for m in raw_messages:
        try:
            role = m.get("role", "")
            content = m.get("content", "")
            # If content is a dict (previous bug), serialize to JSON string
            if isinstance(content, dict):
                content_str = json.dumps(content)
            else:
                content_str = str(content) if content is not None else ""

            timestamp = m.get("timestamp")
            # Ensure timestamp is a datetime when possible (if stored as string, leave as-is)
            sanitized_messages.append({
                "role": role,
                "content": content_str,
                "timestamp": timestamp
            })
        except Exception:
            # Fallback: skip malformed message
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

@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new practice session or return existing active session for this problem.
    
    - Checks if user already has an active/paused session for this problem
    - If yes, returns existing session (auto-resume)
    - If no, creates new session
    """
    try:
        # Check for existing active session
        existing_session = await session_crud.get_active_session_for_problem(
            current_user.id,
            session_data.problem_id
        )
        
        if existing_session:
            # Return existing session (auto-resume)
            return format_session(existing_session)
        
        # Create new session
        session = await session_crud.create_session(
            user_id=current_user.id,
            problem_id=session_data.problem_id
        )
        
        return format_session(session)
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get session by ID"""
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify ownership
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    return format_session(session)

@router.get("/problem/{problem_id}", response_model=Optional[SessionResponse])
async def get_active_session_for_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get user's active or paused session for a specific problem.
    Returns null if no active session exists.
    """
    session = await session_crud.get_active_session_for_problem(
        current_user.id,
        problem_id
    )
    
    if not session:
        return None
    
    return format_session(session)

@router.put("/{session_id}/autosave", response_model=SessionResponse)
async def autosave_session(
    session_id: str,
    autosave_data: SessionAutosave,
    current_user: User = Depends(get_current_user)
):
    """
    Auto-save session data (called every 10 seconds from frontend).
    
    - Only saves if diagram data actually changed (hash comparison)
    - Always updates time_spent
    - Updates last_saved_at timestamp
    """
    session = await session_crud.autosave_session(
        session_id=session_id,
        diagram_data=autosave_data.diagram_data,
        time_spent=autosave_data.time_spent,
        user_id=current_user.id
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return format_session(session)

@router.put("/{session_id}/pause", response_model=SessionResponse)
async def pause_session(
    session_id: str,
    pause_data: SessionPause,
    current_user: User = Depends(get_current_user)
):
    """
    Pause a session (user navigates away from practice page).
    Updates time_spent and sets status to 'paused'.
    """
    session = await session_crud.pause_session(
        session_id=session_id,
        user_id=current_user.id,
        time_spent=pause_data.time_spent
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return format_session(session)

@router.put("/{session_id}/resume", response_model=SessionResponse)
async def resume_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Resume a paused session.
    Sets status back to 'active'.
    """
    session = await session_crud.resume_session(
        session_id=session_id,
        user_id=current_user.id
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return format_session(session)

@router.post("/{session_id}/chat", response_model=SessionResponse)
async def add_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Add a chat message to the session.
    Used during practice for AI assistance.
    """
    session = await session_crud.add_chat_message_to_session(
        session_id=session_id,
        user_id=current_user.id,
        role=message_data.role,
        content=message_data.content
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return format_session(session)

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def abandon_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Abandon a session (mark as abandoned, not deleted).
    User can start fresh without resuming.
    """
    success = await session_crud.abandon_session(
        session_id=session_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return None

@router.get("/{session_id}/extract", response_model=ExcalidrawExtractResponse)
async def extract_excalidraw_data(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Extract and parse Excalidraw diagram data from session.
    
    Returns structured breakdown of:
    - Components (rectangles, ellipses, diamonds)
    - Arrows/Connections (with start/end bindings)
    - Text elements
    - Raw diagram data
    
    Useful for:
    - Testing diagram extraction
    - Debugging Excalidraw data structure
    - Viewing what AI agent will analyze
    """
    # Get session
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify ownership
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Get diagram data
    diagram_data = session.get("diagram_data", {})
    
    if not diagram_data or not diagram_data.get("elements"):
        return ExcalidrawExtractResponse(
            session_id=session_id,
            problem_id=session.get("problem_id", ""),
            total_elements=0,
            components=[],
            arrows=[],
            text_elements=[],
            raw_diagram_data=diagram_data
        )
    
    # Extract and categorize elements
    elements = diagram_data.get("elements", [])
    components = []
    arrows = []
    text_elements = []
    
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        
        # Extract required fields
        extracted = {
            "id": elem.get("id", ""),
            "type": elem.get("type", ""),
            "text": elem.get("text", ""),
            "groupIds": elem.get("groupIds", []),
            "boundElements": elem.get("boundElements", [])
        }
        
        # Categorize by type
        elem_type = elem.get("type", "")
        
        if elem_type == "arrow":
            # Add arrow-specific fields
            extracted["startBinding"] = elem.get("startBinding", {})
            extracted["endBinding"] = elem.get("endBinding", {})
            arrows.append(extracted)
        elif elem_type == "text":
            text_elements.append(extracted)
        elif elem_type in ["rectangle", "ellipse", "diamond"]:
            components.append(extracted)
        else:
            # Other shapes also count as components
            components.append(extracted)
    
    return ExcalidrawExtractResponse(
        session_id=session_id,
        problem_id=session.get("problem_id", ""),
        total_elements=len(elements),
        components=components,
        arrows=arrows,
        text_elements=text_elements,
        raw_diagram_data=diagram_data
    )

@router.post("/{session_id}/check", response_model=CheckFeedbackResponse)
async def check_solution(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check user's solution using AI agent.
    
    - Analyzes Excalidraw diagram against question requirements
    - Uses hash-based caching: returns cached feedback if diagram unchanged
    - Saves feedback to session's chat_messages as assistant message
    - Returns: what's implemented, what's missing, next steps
    """
    # Get session
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify ownership
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Compute current diagram hash from stored diagram_data (ensure we use the
    # actual diagram the user has, rather than relying on an older session field)
    diagram_data = session.get("diagram_data", {})
    try:
        current_hash = session_crud.calculate_diagram_hash(diagram_data)
    except Exception:
        # Fallback to stored hash if calculation fails
        current_hash = session.get("diagram_hash", "")
    
    # Check if we have cached feedback for this exact diagram
    # Look for last assistant message with role="system_check"
    chat_messages = session.get("chat_messages", [])
    cached_feedback = None
    
    for msg in reversed(chat_messages):
        if msg.get("role") == "system_check":
            # Check if this feedback was for the same diagram version
            if msg.get("diagram_hash") == current_hash:
                cached_feedback_str = msg.get("content", "")
                try:
                    # Parse JSON string back to dict
                    cached_feedback = json.loads(cached_feedback_str)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, skip this cached entry
                    continue
                break
    
    # If diagram unchanged and we have feedback, return cached
    if cached_feedback:
        return CheckFeedbackResponse(
            session_id=session_id,
            problem_id=session["problem_id"],
            feedback=cached_feedback,
            timestamp=datetime.utcnow(),
            diagram_hash=current_hash,
            cached=True
        )
    
    # Diagram changed or no cache - call AI agent
    # Get problem data
    problem = await problem_crud.get_problem_by_id(session["problem_id"])
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Format problem data for agent
    problem_data = {
        "title": problem.get("title", ""),
        "description": problem.get("description", ""),
        "requirements": problem.get("requirements", []),
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "difficulty": problem.get("difficulty", ""),
        "categories": problem.get("categories", [])
    }
    
    # Get diagram data
    diagram_data = session.get("diagram_data", {})
    
    # Run AI agent analysis
    try:
        feedback = await analyze_user_solution(
            problem_data=problem_data,
            diagram_data=diagram_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(e)}"
        )
    
    # Save feedback to session's chat_messages with special role
    # Store as JSON string to maintain compatibility with chat_messages schema
    await session_crud.add_chat_message_to_session(
        session_id=session_id,
        user_id=current_user.id,
        role="system_check",
        content=json.dumps(feedback)  # Convert dict to JSON string
    )

    # Update the session's stored diagram_hash and attach diagram_hash to the
    # appended chat message so future checks can quickly find cached feedback.
    from database import db
    sessions_collection = db.get_collection("sessions")

    # Update session-level diagram_hash (useful for other flows)
    await sessions_collection.update_one(
        {"_id": session["_id"]},
        {"$set": {
            "diagram_hash": current_hash,
            "updated_at": datetime.utcnow()
        }}
    )

    # Attach diagram_hash to the newly appended chat message. We compute the
    # index as the current length of chat_messages (before append) which is
    # stored in chat_messages variable earlier.
    try:
        await sessions_collection.update_one(
            {"_id": session["_id"]},
            {"$set": {f"chat_messages.{len(chat_messages)}.diagram_hash": current_hash}}
        )
    except Exception:
        # Non-critical: if this fails, it's ok — caching will still work next time
        pass
    
    return CheckFeedbackResponse(
        session_id=session_id,
        problem_id=session["problem_id"],
        feedback=feedback,
        timestamp=datetime.utcnow(),
        diagram_hash=current_hash,
        cached=False
    )

@router.get("/user/my-sessions", response_model=List[SessionResponse])
async def get_my_sessions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    Get all sessions for the current user.
    Includes active, paused, submitted, and abandoned sessions.
    """
    sessions = await session_crud.get_sessions_by_user(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return [format_session(session) for session in sessions]

@router.post("/{session_id}/submit", response_model=SubmitResponse)
async def submit_solution(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Submit the user's solution for final evaluation.
    
    - Scores the solution (0-100)
    - Provides detailed feedback (implemented, missing, next steps)
    - Generates personalized tips
    - Fetches learning resources (YouTube videos + documentation)
    - Marks session as 'submitted'
    - Creates a submission record
    
    Returns comprehensive evaluation result.
    """
    # Get session
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify ownership
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Check if already submitted
    if session.get("status") == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already submitted. Create a new session to try again."
        )
    
    # Get problem data
    problem = await problem_crud.get_problem_by_id(session["problem_id"])
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Format problem data for agent
    problem_data = {
        "title": problem.get("title", ""),
        "description": problem.get("description", ""),
        "requirements": problem.get("requirements", []),
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "difficulty": problem.get("difficulty", ""),
        "categories": problem.get("categories", [])
    }
    
    # Get diagram data
    diagram_data = session.get("diagram_data", {})
    
    # Validate diagram
    elements = diagram_data.get("elements", [])
    if not elements or len(elements) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit empty diagram. Please draw your solution first."
        )
    
    # Run submission evaluation
    try:
        evaluation = await evaluate_submission(
            problem_data=problem_data,
            diagram_data=diagram_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Submission evaluation failed: {str(e)}"
        )
    
    # Create submission record in database
    from database import db
    submissions_collection = db.get_collection("submissions")
    
    submission_doc = {
        "user_id": current_user.id,
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
    
    # Update session status to 'submitted'
    await session_crud.mark_session_submitted(session_id, current_user.id)
    
    # Return evaluation result
    return SubmitResponse(
        submission_id=submission_id,
        session_id=session_id,
        problem_id=session["problem_id"],
        score=evaluation["score"],
        max_score=evaluation["max_score"],
        breakdown=[ScoreBreakdownItem(**item) for item in evaluation["breakdown"]],
        feedback=evaluation["feedback"],
        tips=evaluation["tips"],
        resources={
            "videos": [ResourceItem(**v) for v in evaluation["resources"]["videos"]],
            "docs": [ResourceItem(**d) for d in evaluation["resources"]["docs"]]
        },
        timestamp=datetime.utcnow()
    )


@router.post("/{session_id}/submit-stream")
async def submit_solution_stream(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Submit the user's solution with STREAMING evaluation.
    
    Returns SSE events as each evaluation step completes:
    - status: step progress updates
    - score_result: scoring data
    - tips_result: improvement tips
    - resources_result: videos and docs
    - done: complete evaluation result
    """
    # Get session
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Verify ownership
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    # Check if already submitted
    if session.get("status") == "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already submitted. Create a new session to try again."
        )
    
    # Get problem data
    problem = await problem_crud.get_problem_by_id(session["problem_id"])
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Format problem data
    problem_data = {
        "title": problem.get("title", ""),
        "description": problem.get("description", ""),
        "requirements": problem.get("requirements", []),
        "constraints": problem.get("constraints", []),
        "hints": problem.get("hints", []),
        "difficulty": problem.get("difficulty", ""),
        "categories": problem.get("categories", [])
    }
    
    # Get diagram data
    diagram_data = session.get("diagram_data", {})
    
    # Validate diagram
    elements = diagram_data.get("elements", [])
    if not elements or len(elements) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit empty diagram. Please draw your solution first."
        )
    
    # Streaming generator that also saves submission on completion
    async def stream_and_save():
        import json as _json
        final_result = None
        
        async for event_str in evaluate_submission_stream(
            problem_data=problem_data,
            diagram_data=diagram_data
        ):
            yield event_str
            
            # Capture final result from 'done' event
            if '"type": "done"' in event_str:
                try:
                    event_data = _json.loads(event_str.replace("data: ", "").strip())
                    final_result = event_data.get("data")
                except Exception:
                    pass
        
        # After streaming completes, save submission to database
        if final_result:
            try:
                submissions_collection = db.get_collection("submissions")
                submission_doc = {
                    "user_id": current_user.id,
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
                await session_crud.mark_session_submitted(session_id, current_user.id)
            except Exception as e:
                print(f"Error saving submission after stream: {e}")
    
    return StreamingResponse(
        stream_and_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@router.get("/problem/{problem_id}/submissions")
async def get_problem_submissions(
    problem_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all submissions for a specific problem by the current user.
    Used to show previous solutions in the Solutions tab.
    """
    from database import db
    submissions_collection = db.get_collection("submissions")
    
    # Find all submissions for this problem by this user
    cursor = submissions_collection.find({
        "user_id": current_user.id,
        "problem_id": problem_id
    }).sort("submitted_at", -1)  # Most recent first
    
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
