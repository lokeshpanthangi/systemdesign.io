from datetime import datetime
from typing import Optional, List
from bson import ObjectId
from database.database import db


async def create_problem(
    title: str,
    description: str,
    difficulty: str,
    categories: List[str],
    estimated_time: str,
    requirements: List[str],
    constraints: List[str],
    hints: List[str],
    created_by: str  # user email
) -> Optional[dict]:
    """
    Create a new problem in the database.
    """
    problem = {
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "categories": categories,
        "estimated_time": estimated_time,
        "requirements": requirements,
        "constraints": constraints,
        "hints": hints,
        "created_by": created_by,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await db.problems.insert_one(problem)
    problem["_id"] = str(result.inserted_id)
    return problem


async def get_problem_by_id(problem_id: str) -> Optional[dict]:
    """
    Retrieve a problem by its ID.
    """
    if not ObjectId.is_valid(problem_id):
        return None
    
    problem = await db.problems.find_one({"_id": ObjectId(problem_id)})
    if not problem:
        return None

    problem["_id"] = str(problem["_id"])
    return problem


async def get_all_problems(skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Retrieve all problems with pagination.
    """
    cursor = db.problems.find().skip(skip).limit(limit).sort("created_at", -1)
    problems = await cursor.to_list(length=limit)
    
    for problem in problems:
        problem["_id"] = str(problem["_id"])
    
    return problems


async def get_problems_by_user(user_email: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Retrieve all problems created by a specific user.
    """
    cursor = db.problems.find({"created_by": user_email}).skip(skip).limit(limit).sort("created_at", -1)
    problems = await cursor.to_list(length=limit)
    
    for problem in problems:
        problem["_id"] = str(problem["_id"])
    
    return problems


async def update_problem(
    problem_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    difficulty: Optional[str] = None,
    categories: Optional[List[str]] = None,
    estimated_time: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    constraints: Optional[List[str]] = None,
    hints: Optional[List[str]] = None,
    user_email: str = None
) -> Optional[dict]:
    """
    Update a problem. Only the creator can update their problem.
    """
    if not ObjectId.is_valid(problem_id):
        return None

    # Check if problem exists and user is the creator
    existing_problem = await db.problems.find_one({"_id": ObjectId(problem_id)})
    if not existing_problem:
        return None
    
    if existing_problem.get("created_by") != user_email:
        return {"error": "Unauthorized"}

    update_data = {"updated_at": datetime.utcnow()}
    
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if difficulty is not None:
        update_data["difficulty"] = difficulty
    if categories is not None:
        update_data["categories"] = categories
    if estimated_time is not None:
        update_data["estimated_time"] = estimated_time
    if requirements is not None:
        update_data["requirements"] = requirements
    if constraints is not None:
        update_data["constraints"] = constraints
    if hints is not None:
        update_data["hints"] = hints

    result = await db.problems.update_one(
        {"_id": ObjectId(problem_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        return None

    updated_problem = await get_problem_by_id(problem_id)
    return updated_problem


async def delete_problem(problem_id: str, user_email: str) -> bool:
    """
    Delete a problem. Only the creator can delete their problem.
    """
    if not ObjectId.is_valid(problem_id):
        return False

    # Check if problem exists and user is the creator
    existing_problem = await db.problems.find_one({"_id": ObjectId(problem_id)})
    if not existing_problem:
        return False
    
    if existing_problem.get("created_by") != user_email:
        return False

    result = await db.problems.delete_one({"_id": ObjectId(problem_id)})
    return result.deleted_count > 0


async def search_problems(query: str, skip: int = 0, limit: int = 100) -> List[dict]:
    """
    Search problems by title or description.
    """
    search_filter = {
        "$or": [
            {"title": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}}
        ]
    }
    
    cursor = db.problems.find(search_filter).skip(skip).limit(limit).sort("created_at", -1)
    problems = await cursor.to_list(length=limit)
    
    for problem in problems:
        problem["_id"] = str(problem["_id"])
    
    return problems
