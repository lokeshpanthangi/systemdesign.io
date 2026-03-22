from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List
from CRUD.problem import (
    create_problem,
    get_problem_by_id,
    get_all_problems,
    get_problems_by_user,
    update_problem,
    delete_problem,
    search_problems
)
from core.auth import verify_access_token

problem_router = APIRouter(prefix="/problems", tags=["Problems"])


# ---------- Pydantic Models ----------

class ProblemCreate(BaseModel):
    title: str
    description: str
    difficulty: str  # "easy" | "medium" | "hard"
    categories: List[str] = []
    estimated_time: str = "30 mins"
    requirements: List[str] = []
    constraints: List[str] = []
    hints: List[str] = []


class ProblemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[str] = None
    categories: Optional[List[str]] = None
    estimated_time: Optional[str] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    hints: Optional[List[str]] = None


class ProblemResponse(BaseModel):
    id: str
    title: str
    description: str
    difficulty: str
    categories: List[str]
    estimated_time: str
    requirements: List[str]
    constraints: List[str]
    hints: List[str]
    created_by: str
    created_at: str
    updated_at: str


# ---------- Helper Function ----------

async def get_current_user_email(token_data: dict = Depends(verify_access_token)) -> str:
    """
    Extract and return the current user's email from the JWT token.
    """
    email = token_data.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    return email


# ---------- Routes ----------

@problem_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_problem(
    payload: ProblemCreate,
    current_user_email: str = Depends(get_current_user_email)
):
    """
    Create a new problem. Requires authentication.
    """
    problem = await create_problem(
        title=payload.title,
        description=payload.description,
        difficulty=payload.difficulty,
        categories=payload.categories,
        estimated_time=payload.estimated_time,
        requirements=payload.requirements,
        constraints=payload.constraints,
        hints=payload.hints,
        created_by=current_user_email
    )

    if not problem:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create problem"
        )

    return {
        "message": "Problem created successfully",
        "problem": {
            "id": problem["_id"],
            "title": problem["title"],
            "description": problem["description"],
            "difficulty": problem["difficulty"],
            "categories": problem["categories"],
            "estimated_time": problem["estimated_time"],
            "requirements": problem["requirements"],
            "constraints": problem["constraints"],
            "hints": problem["hints"],
            "created_by": problem["created_by"],
            "created_at": problem["created_at"].isoformat(),
            "updated_at": problem["updated_at"].isoformat()
        }
    }


@problem_router.get("/{problem_id}")
async def get_problem(problem_id: str):
    """
    Get a specific problem by ID. Public endpoint (no auth required).
    """
    problem = await get_problem_by_id(problem_id)
    
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )

    return {
        "id": problem["_id"],
        "title": problem["title"],
        "description": problem["description"],
        "difficulty": problem["difficulty"],
        "categories": problem["categories"],
        "estimated_time": problem["estimated_time"],
        "requirements": problem["requirements"],
        "constraints": problem["constraints"],
        "hints": problem.get("hints", []),
        "created_by": problem.get("created_by", "Unknown"),
        "created_at": problem["created_at"].isoformat(),
        "updated_at": problem["updated_at"].isoformat()
    }


@problem_router.get("/")
async def list_problems(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Get all problems with pagination. Public endpoint (no auth required).
    """
    problems = await get_all_problems(skip=skip, limit=limit)
    
    return {
        "total": len(problems),
        "skip": skip,
        "limit": limit,
        "problems": [
            {
                "id": problem["_id"],
                "title": problem["title"],
                "description": problem["description"],
                "difficulty": problem["difficulty"],
                "categories": problem["categories"],
                "estimated_time": problem["estimated_time"],
                "requirements": problem["requirements"],
                "constraints": problem["constraints"],
                "hints": problem.get("hints", []),
                "created_by": problem.get("created_by", "Unknown"),
                "created_at": problem["created_at"].isoformat(),
                "updated_at": problem["updated_at"].isoformat()
            }
            for problem in problems
        ]
    }


@problem_router.get("/user/my-problems")
async def get_my_problems(
    current_user_email: str = Depends(get_current_user_email),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Get all problems created by the authenticated user.
    """
    problems = await get_problems_by_user(current_user_email, skip=skip, limit=limit)
    
    return {
        "total": len(problems),
        "skip": skip,
        "limit": limit,
        "problems": [
            {
                "id": problem["_id"],
                "title": problem["title"],
                "description": problem["description"],
                "difficulty": problem["difficulty"],
                "categories": problem["categories"],
                "estimated_time": problem["estimated_time"],
                "requirements": problem["requirements"],
                "constraints": problem["constraints"],
                "hints": problem.get("hints", []),
                "created_by": problem.get("created_by"),
                "created_at": problem["created_at"].isoformat(),
                "updated_at": problem["updated_at"].isoformat()
            }
            for problem in problems
        ]
    }


@problem_router.put("/{problem_id}")
async def update_existing_problem(
    problem_id: str,
    payload: ProblemUpdate,
    current_user_email: str = Depends(get_current_user_email)
):
    """
    Update a problem. Only the creator can update.
    """
    updated_problem = await update_problem(
        problem_id=problem_id,
        title=payload.title,
        description=payload.description,
        difficulty=payload.difficulty,
        categories=payload.categories,
        estimated_time=payload.estimated_time,
        requirements=payload.requirements,
        constraints=payload.constraints,
        hints=payload.hints,
        user_email=current_user_email
    )

    if not updated_problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    if updated_problem.get("error") == "Unauthorized":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this problem"
        )

    return {
        "message": "Problem updated successfully",
        "problem": {
            "id": updated_problem["_id"],
            "title": updated_problem["title"],
            "description": updated_problem["description"],
            "difficulty": updated_problem["difficulty"],
            "categories": updated_problem["categories"],
            "estimated_time": updated_problem["estimated_time"],
            "requirements": updated_problem["requirements"],
            "constraints": updated_problem["constraints"],
            "hints": updated_problem.get("hints", []),
            "created_by": updated_problem["created_by"],
            "created_at": updated_problem["created_at"].isoformat(),
            "updated_at": updated_problem["updated_at"].isoformat()
        }
    }


@problem_router.delete("/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_problem(
    problem_id: str,
    current_user_email: str = Depends(get_current_user_email)
):
    """
    Delete a problem. Only the creator can delete.
    """
    deleted = await delete_problem(problem_id, current_user_email)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found or you are not authorized to delete it"
        )

    return None


@problem_router.get("/search/query")
async def search_for_problems(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """
    Search problems by title or description.
    """
    problems = await search_problems(q, skip=skip, limit=limit)
    
    return {
        "total": len(problems),
        "query": q,
        "skip": skip,
        "limit": limit,
        "problems": [
            {
                "id": problem["_id"],
                "title": problem["title"],
                "description": problem["description"],
                "difficulty": problem["difficulty"],
                "categories": problem["categories"],
                "estimated_time": problem["estimated_time"],
                "requirements": problem["requirements"],
                "constraints": problem["constraints"],
                "hints": problem.get("hints", []),
                "created_by": problem.get("created_by", "Unknown"),
                "created_at": problem["created_at"].isoformat(),
                "updated_at": problem["updated_at"].isoformat()
            }
            for problem in problems
        ]
    }
