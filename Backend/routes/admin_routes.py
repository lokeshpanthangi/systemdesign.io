"""
Admin Routes — LLM Connection & Model Management
===================================================
API endpoints for:
  - Admin password verification (gate)
  - LLM connection status, reconnecting, re-auth
  - Model selection (switch between OpenAI, Anthropic, Gemini, Grok)
"""

import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.llm_provider import (
    get_llm_status,
    get_provider,
    get_device_flow,
    complete_device_flow,
    initialize_provider,
    ConnectionStatus,
    get_available_models,
    get_current_model,
    set_current_model,
)

load_dotenv()

admin_router = APIRouter(prefix="/admin", tags=["Admin — LLM Management"])


# ─── Response Models ─────────────────────────────────────────────────────────

class LLMStatusResponse(BaseModel):
    status: str
    model: str
    provider: str
    message: str
    has_github_token: bool
    last_refresh: Optional[str] = None
    token_expires_at: Optional[str] = None


class DeviceFlowStartResponse(BaseModel):
    user_code: str
    verification_uri: str
    expires_in: int


class DeviceFlowPollResponse(BaseModel):
    status: str
    message: str


class GenericResponse(BaseModel):
    success: bool
    message: str


class AdminAuthRequest(BaseModel):
    password: str


class ModelChangeRequest(BaseModel):
    password: str
    model_id: str


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    tier: str
    description: str


class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    current_model: str


# ─── Admin Auth ──────────────────────────────────────────────────────────────

@admin_router.post("/verify-password")
async def verify_admin_password(request: AdminAuthRequest):
    """Verify the admin password."""
    admin_pass = os.getenv("ADMIN_PASS", "")
    if not admin_pass:
        raise HTTPException(status_code=500, detail="ADMIN_PASS not configured in .env")

    if request.password != admin_pass:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    return {"success": True, "message": "Authentication successful"}


# ─── LLM Status ─────────────────────────────────────────────────────────────

@admin_router.get("/llm/status", response_model=LLMStatusResponse)
async def llm_status():
    """Get the current LLM connection status."""
    status = get_llm_status()
    return LLMStatusResponse(**status)


# ─── Reconnect ──────────────────────────────────────────────────────────────

@admin_router.post("/llm/reconnect", response_model=GenericResponse)
async def llm_reconnect():
    """Force-reconnect the LLM provider."""
    provider = get_provider()

    if provider is None:
        result = initialize_provider()
        if result["status"] == ConnectionStatus.AUTH_REQUIRED:
            raise HTTPException(
                status_code=401,
                detail="GitHub authentication required. Start the device flow first."
            )
        elif result["status"] == ConnectionStatus.ERROR:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to reconnect: {result['message']}"
            )
        return GenericResponse(success=True, message="LLM provider initialized successfully")

    try:
        provider.force_refresh()
        return GenericResponse(success=True, message="Token refreshed successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reconnect failed: {str(e)}")


# ─── Device Flow Auth ───────────────────────────────────────────────────────

@admin_router.post("/llm/auth/start", response_model=DeviceFlowStartResponse)
async def llm_auth_start():
    """Start the GitHub OAuth device flow."""
    try:
        flow = get_device_flow()
        result = flow.start()
        return DeviceFlowStartResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start auth flow: {str(e)}")


@admin_router.post("/llm/auth/poll", response_model=DeviceFlowPollResponse)
async def llm_auth_poll():
    """Poll the GitHub OAuth device flow for completion."""
    flow = get_device_flow()

    if not flow.device_code:
        raise HTTPException(status_code=400, detail="No auth flow in progress. Start one first.")

    result = flow.poll()

    if result["status"] == "completed":
        try:
            complete_device_flow()
        except Exception as e:
            return DeviceFlowPollResponse(
                status="error",
                message=f"Auth succeeded but LLM init failed: {str(e)}"
            )

    return DeviceFlowPollResponse(**result)


# ─── Model Management ───────────────────────────────────────────────────────

@admin_router.get("/models", response_model=ModelsResponse)
async def get_models():
    """Get all available models and the currently active model."""
    models = get_available_models()
    return ModelsResponse(
        models=[ModelInfo(**m) for m in models],
        current_model=get_current_model(),
    )


@admin_router.post("/models/change", response_model=GenericResponse)
async def change_model(request: ModelChangeRequest):
    """Change the active LLM model. Requires admin password."""
    admin_pass = os.getenv("ADMIN_PASS", "")
    if not admin_pass:
        raise HTTPException(status_code=500, detail="ADMIN_PASS not configured")

    if request.password != admin_pass:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    success = set_current_model(request.model_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Unknown model: {request.model_id}")

    return GenericResponse(
        success=True,
        message=f"Model changed to {request.model_id}"
    )


# ─── Health ──────────────────────────────────────────────────────────────────

@admin_router.get("/health")
async def admin_health():
    """Quick health check for the admin panel."""
    status = get_llm_status()
    return {
        "admin": "ok",
        "llm_status": status["status"],
        "llm_provider": status["provider"],
        "current_model": get_current_model(),
    }
