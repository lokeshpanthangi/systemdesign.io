from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from database import db


async def create_submission(
    user_id: str,
    problem_id: str,
    diagram_data: dict,
    status: str = "in-progress"
) -> Optional[dict]:
    """
    Create a new submission in the database.
    """
    submission = {
        "user_id": user_id,
        "problem_id": problem_id,
        "diagram_data": diagram_data,
        "score": 0,
        "time_spent": 0,
        "status": status,
        "feedback": {
            "strengths": [],
            "improvements": [],
            "missing_components": []
        },
        "chat_messages": [],
        "submitted_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.submissions.insert_one(submission)
    submission["_id"] = str(result.inserted_id)
    return submission


async def get_submission_by_id(submission_id: str) -> Optional[dict]:
    """
    Retrieve a submission by its ID.
    """
    if not ObjectId.is_valid(submission_id):
        return None
    
    submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not submission:
        return None

    submission["_id"] = str(submission["_id"])
    return submission


async def get_submissions_by_user(user_id: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Retrieve all submissions by a specific user.
    """
    cursor = db.submissions.find({"user_id": user_id}).skip(skip).limit(limit).sort("submitted_at", -1)
    submissions = await cursor.to_list(length=limit)
    
    for submission in submissions:
        submission["_id"] = str(submission["_id"])
    
    return submissions


async def get_submissions_by_problem(problem_id: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Retrieve all submissions for a specific problem.
    """
    cursor = db.submissions.find({"problem_id": problem_id}).skip(skip).limit(limit).sort("submitted_at", -1)
    submissions = await cursor.to_list(length=limit)
    
    for submission in submissions:
        submission["_id"] = str(submission["_id"])
    
    return submissions


async def get_user_submission_for_problem(user_id: str, problem_id: str) -> Optional[dict]:
    """
    Get a specific user's submission for a specific problem.
    """
    submission = await db.submissions.find_one({
        "user_id": user_id,
        "problem_id": problem_id
    })
    
    if not submission:
        return None
    
    submission["_id"] = str(submission["_id"])
    return submission


async def update_submission(
    submission_id: str,
    diagram_data: Optional[dict] = None,
    score: Optional[int] = None,
    time_spent: Optional[int] = None,
    status: Optional[str] = None,
    feedback: Optional[dict] = None,
    user_id: str = None
) -> Optional[dict]:
    """
    Update a submission. Only the owner can update their submission.
    """
    if not ObjectId.is_valid(submission_id):
        return None

    # Check if submission exists and user is the owner
    existing_submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not existing_submission:
        return None
    
    if existing_submission.get("user_id") != user_id:
        return {"error": "Unauthorized"}

    update_data = {"updated_at": datetime.utcnow()}
    
    if diagram_data is not None:
        update_data["diagram_data"] = diagram_data
    if score is not None:
        update_data["score"] = score
    if time_spent is not None:
        update_data["time_spent"] = time_spent
    if status is not None:
        update_data["status"] = status
    if feedback is not None:
        update_data["feedback"] = feedback

    result = await db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        return None

    updated_submission = await get_submission_by_id(submission_id)
    return updated_submission


async def add_chat_message(
    submission_id: str,
    role: str,
    content: str,
    user_id: str
) -> Optional[dict]:
    """
    Add a chat message to a submission.
    """
    if not ObjectId.is_valid(submission_id):
        return None

    # Check if submission exists and user is the owner
    existing_submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not existing_submission:
        return None
    
    if existing_submission.get("user_id") != user_id:
        return {"error": "Unauthorized"}

    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }

    result = await db.submissions.update_one(
        {"_id": ObjectId(submission_id)},
        {
            "$push": {"chat_messages": message},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

    if result.modified_count == 0:
        return None

    updated_submission = await get_submission_by_id(submission_id)
    return updated_submission


async def delete_submission(submission_id: str, user_id: str) -> bool:
    """
    Delete a submission. Only the owner can delete their submission.
    """
    if not ObjectId.is_valid(submission_id):
        return False

    # Check if submission exists and user is the owner
    existing_submission = await db.submissions.find_one({"_id": ObjectId(submission_id)})
    if not existing_submission:
        return False
    
    if existing_submission.get("user_id") != user_id:
        return False

    result = await db.submissions.delete_one({"_id": ObjectId(submission_id)})
    return result.deleted_count > 0
