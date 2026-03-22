from bson import ObjectId
from datetime import datetime
from typing import Optional, Dict, Any, List
import hashlib
import json
from database.database import db

sessions_collection = db.get_collection("sessions")

def calculate_diagram_hash(diagram_data: Dict[Any, Any]) -> str:
    """Calculate hash of diagram data for change detection"""
    diagram_str = json.dumps(diagram_data, sort_keys=True)
    return hashlib.md5(diagram_str.encode()).hexdigest()

async def create_session(user_id: str, problem_id: str) -> Dict[str, Any]:
    """Create a new practice session"""
    now = datetime.utcnow()
    
    session = {
        "user_id": user_id,
        "problem_id": problem_id,
        "diagram_data": {},
        "diagram_hash": calculate_diagram_hash({}),
        "time_spent": 0,
        "status": "active",
        "chat_messages": [],
        "last_saved_at": now,
        "started_at": now,
        "ended_at": None,
        "created_at": now,
        "updated_at": now
    }
    
    result = await sessions_collection.insert_one(session)
    session["_id"] = result.inserted_id
    
    return session

async def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session by ID"""
    if not ObjectId.is_valid(session_id):
        return None
    
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return session

async def get_active_session_for_problem(user_id: str, problem_id: str) -> Optional[Dict[str, Any]]:
    """Get user's active session for a specific problem"""
    session = await sessions_collection.find_one({
        "user_id": user_id,
        "problem_id": problem_id,
        "status": {"$in": ["active", "paused"]}
    })
    return session

async def get_sessions_by_user(user_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all sessions for a user"""
    cursor = sessions_collection.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
    sessions = await cursor.to_list(length=limit)
    return sessions

async def autosave_session(
    session_id: str, 
    diagram_data: Dict[Any, Any], 
    time_spent: int,
    user_id: str
) -> Optional[Dict[str, Any]]:
    """Auto-save session data (called every 10 seconds)"""
    if not ObjectId.is_valid(session_id):
        return None
    
    # Get current session to verify ownership
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        return None
    
    # Calculate new hash
    new_hash = calculate_diagram_hash(diagram_data)
    old_hash = session.get("diagram_hash", "")
    
    # Only update if diagram actually changed
    if new_hash != old_hash:
        update_data = {
            "diagram_data": diagram_data,
            "diagram_hash": new_hash,
            "time_spent": time_spent,
            "last_saved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": update_data}
        )
    else:
        # Even if diagram didn't change, update time_spent
        await sessions_collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {
                "time_spent": time_spent,
                "last_saved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
    
    # Return updated session
    updated_session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return updated_session

async def pause_session(session_id: str, user_id: str, time_spent: int) -> Optional[Dict[str, Any]]:
    """Pause a session (user navigates away)"""
    if not ObjectId.is_valid(session_id):
        return None
    
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        return None
    
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "status": "paused",
            "time_spent": time_spent,
            "updated_at": datetime.utcnow()
        }}
    )
    
    updated_session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return updated_session

async def resume_session(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Resume a paused session"""
    if not ObjectId.is_valid(session_id):
        return None
    
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        return None
    
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "status": "active",
            "updated_at": datetime.utcnow()
        }}
    )
    
    updated_session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return updated_session

async def add_chat_message_to_session(
    session_id: str,
    user_id: str,
    role: str,
    content: str
) -> Optional[Dict[str, Any]]:
    """Add a chat message to session"""
    if not ObjectId.is_valid(session_id):
        return None
    
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        return None
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {
            "$push": {"chat_messages": message},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    updated_session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return updated_session

async def mark_session_submitted(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Mark session as submitted (when converting to submission)"""
    if not ObjectId.is_valid(session_id):
        return None
    
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        return None
    
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "status": "submitted",
            "ended_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    updated_session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    return updated_session

async def abandon_session(session_id: str, user_id: str) -> bool:
    """Abandon/delete a session"""
    if not ObjectId.is_valid(session_id):
        return False
    
    session = await sessions_collection.find_one({"_id": ObjectId(session_id)})
    if not session or session["user_id"] != user_id:
        return False
    
    # Mark as abandoned instead of deleting (for analytics)
    await sessions_collection.update_one(
        {"_id": ObjectId(session_id)},
        {"$set": {
            "status": "abandoned",
            "ended_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    return True

async def cleanup_old_sessions(days: int = 7) -> int:
    """Clean up abandoned sessions older than X days"""
    cutoff_date = datetime.utcnow()
    from datetime import timedelta
    cutoff_date = cutoff_date - timedelta(days=days)
    
    result = await sessions_collection.delete_many({
        "status": "abandoned",
        "updated_at": {"$lt": cutoff_date}
    })
    
    return result.deleted_count
