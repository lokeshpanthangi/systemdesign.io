"""
Session Routes — Thin HTTP layer
All business logic is in features/session_service.py
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from core.auth import get_current_user
from core.models import User
import CRUD.session as session_crud
from features.session_service import (
    format_session,
    check_solution_logic,
    submit_solution_logic,
    submit_solution_stream_logic,
    extract_excalidraw_logic,
    get_problem_submissions_logic,
)

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
    feedback: Dict[str, List[str]]
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
    feedback: Dict[str, List[str]]
    tips: List[str]
    resources: Dict[str, List[ResourceItem]]
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


# ---------- Routes ----------

@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new practice session or return existing active session."""
    try:
        existing_session = await session_crud.get_active_session_for_problem(
            current_user.id,
            session_data.problem_id
        )
        
        if existing_session:
            return format_session(existing_session)
        
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this session")
    
    return format_session(session)

@router.get("/problem/{problem_id}", response_model=Optional[SessionResponse])
async def get_active_session_for_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get user's active or paused session for a specific problem."""
    session = await session_crud.get_active_session_for_problem(current_user.id, problem_id)
    
    if not session:
        return None
    
    return format_session(session)

@router.put("/{session_id}/autosave", response_model=SessionResponse)
async def autosave_session(
    session_id: str,
    autosave_data: SessionAutosave,
    current_user: User = Depends(get_current_user)
):
    """Auto-save session data (called every 10 seconds from frontend)."""
    session = await session_crud.autosave_session(
        session_id=session_id,
        diagram_data=autosave_data.diagram_data,
        time_spent=autosave_data.time_spent,
        user_id=current_user.id
    )
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied")
    
    return format_session(session)

@router.put("/{session_id}/pause", response_model=SessionResponse)
async def pause_session(
    session_id: str,
    pause_data: SessionPause,
    current_user: User = Depends(get_current_user)
):
    """Pause a session."""
    session = await session_crud.pause_session(
        session_id=session_id,
        user_id=current_user.id,
        time_spent=pause_data.time_spent
    )
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied")
    
    return format_session(session)

@router.put("/{session_id}/resume", response_model=SessionResponse)
async def resume_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Resume a paused session."""
    session = await session_crud.resume_session(session_id=session_id, user_id=current_user.id)
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied")
    
    return format_session(session)

@router.post("/{session_id}/chat", response_model=SessionResponse)
async def add_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Add a chat message to the session."""
    session = await session_crud.add_chat_message_to_session(
        session_id=session_id,
        user_id=current_user.id,
        role=message_data.role,
        content=message_data.content
    )
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied")
    
    return format_session(session)

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def abandon_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Abandon a session (mark as abandoned, not deleted)."""
    success = await session_crud.abandon_session(session_id=session_id, user_id=current_user.id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or access denied")
    
    return None

@router.get("/{session_id}/extract", response_model=ExcalidrawExtractResponse)
async def extract_excalidraw_data(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Extract and parse Excalidraw diagram data from session."""
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this session")
    
    result = extract_excalidraw_logic(session, session_id)
    return ExcalidrawExtractResponse(**result)

@router.post("/{session_id}/check", response_model=CheckFeedbackResponse)
async def check_solution(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check user's solution using AI agent."""
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this session")
    
    try:
        result = await check_solution_logic(session, current_user.id, session_id)
        return CheckFeedbackResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI analysis failed: {str(e)}")

@router.get("/user/my-sessions", response_model=List[SessionResponse])
async def get_my_sessions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get all sessions for the current user."""
    sessions = await session_crud.get_sessions_by_user(user_id=current_user.id, skip=skip, limit=limit)
    return [format_session(session) for session in sessions]

@router.post("/{session_id}/submit", response_model=SubmitResponse)
async def submit_solution(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Submit the user's solution for final evaluation."""
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this session")
    
    if session.get("status") == "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already submitted.")
    
    elements = session.get("diagram_data", {}).get("elements", [])
    if not elements or len(elements) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot submit empty diagram.")
    
    try:
        result = await submit_solution_logic(session, current_user.id, session_id)
        return SubmitResponse(
            submission_id=result["submission_id"],
            session_id=result["session_id"],
            problem_id=result["problem_id"],
            score=result["score"],
            max_score=result["max_score"],
            breakdown=[ScoreBreakdownItem(**item) for item in result["breakdown"]],
            feedback=result["feedback"],
            tips=result["tips"],
            resources={
                "videos": [ResourceItem(**v) for v in result["resources"]["videos"]],
                "docs": [ResourceItem(**d) for d in result["resources"]["docs"]]
            },
            timestamp=result["timestamp"]
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Submission evaluation failed: {str(e)}")


@router.post("/{session_id}/submit-stream")
async def submit_solution_stream(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """Submit the user's solution with STREAMING evaluation."""
    session = await session_crud.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this session")
    
    if session.get("status") == "submitted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already submitted.")
    
    elements = session.get("diagram_data", {}).get("elements", [])
    if not elements or len(elements) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot submit empty diagram.")
    
    return StreamingResponse(
        submit_solution_stream_logic(session, current_user.id, session_id),
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
    """Get all submissions for a specific problem by the current user."""
    return await get_problem_submissions_logic(current_user.id, problem_id)
