from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from CRUD.user import create_user, authenticate_user, get_user_by_email
from core.auth import create_access_token, create_refresh_token, verify_access_token, verify_refresh_token

user_router = APIRouter(prefix="/users", tags=["Users"])



class UserSignup(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    created_at: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ---------- Routes ----------

@user_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup):
    user = await create_user(
        payload.first_name,
        payload.last_name,
        payload.email,
        payload.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists."
        )

    return {"message": "User created successfully", "user": user}


@user_router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login endpoint with JWT access and refresh tokens.
    Session persists until token expires (24 hours default).
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Create both access and refresh tokens
    access_token = create_access_token({"sub": user["email"]})
    refresh_token = create_refresh_token({"sub": user["email"]})
    
    created_at_str = user["created_at"].isoformat() if user.get("created_at") else None

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 86400,  # 24 hours
        "user": {
            "id": user.get("_id"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "email": user.get("email"),
            "created_at": created_at_str,
        },
    }


@user_router.get("/me", response_model=UserResponse)
async def get_user_profile(token_data: dict = Depends(verify_access_token)):
    email = token_data.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = await get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    created_at_str = user["created_at"].isoformat() if user.get("created_at") else None

    return {
        "id": user.get("_id"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "email": user.get("email"),
        "created_at": created_at_str,
    }


@user_router.post("/refresh", response_model=dict)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Refresh endpoint to generate new access token from refresh token.
    Allows session to persist without re-login as long as refresh token is valid.
    """
    user = await verify_refresh_token(request.refresh_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Generate new access token
    new_access_token = create_access_token({"sub": user["email"]})
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 86400  # 24 hours
    }
