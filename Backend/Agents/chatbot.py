"""
AI Chat Route — LangGraph Agent with SSE Streaming
Sidebar chat that acts as a system design mentor.
Uses a LangGraph agent that can optionally fetch page context.
"""
from dotenv import load_dotenv
load_dotenv()

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List
from bson import ObjectId

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .chat_agent.graph import create_chat_agent_graph
from .chat_agent.tools import execute_get_page_context
from .tools.excalidraw_extractor import extract_excalidraw_components
from .prompts.chat_agent_prompt import CHAT_AGENT_SYSTEM_PROMPT

from auth import get_current_user
from models import User
from database import db

chat = APIRouter(prefix="/sessions", tags=["AI Chat"])

# Store chat history per session (in-memory, keyed by session_id)
chat_histories: Dict[str, List] = {}


class ChatRequest(BaseModel):
    message: str
    diagram_data: Dict[Any, Any] = {}


@chat.post("/chat/health")
async def chat_health_check():
    return {"status": "healthy"}


@chat.post("/{session_id}/ai-chat")
async def chat_with_ai(
    session_id: str,
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Stream AI chat response using LangGraph agent with SSE."""
    
    # Get session
    sessions_collection = db.get_collection("sessions")
    session = await sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": current_user.id
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get problem details
    problems_collection = db.get_collection("problems")
    problem = await problems_collection.find_one({
        "_id": ObjectId(session["problem_id"])
    })
    
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Extract context
    problem_title = problem.get("title", "System Design Problem")
    problem_description = problem.get("description", "No description provided.")
    requirements = ", ".join(problem.get("requirements", []))
    diagram_data = request.diagram_data
    
    # Get or initialize chat history
    if session_id not in chat_histories:
        chat_histories[session_id] = []
    
    history = chat_histories[session_id]
    
    # Build LangGraph messages from history
    langchain_messages = []
    for msg in history[-10:]:  # Last 10 messages (5 Q/A pairs)
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))
    
    # Add current user message
    langchain_messages.append(HumanMessage(content=request.message))
    history.append({"role": "user", "content": request.message})
    
    # Create the agent graph with current session context
    graph = create_chat_agent_graph(
        problem_title=problem_title,
        problem_description=problem_description,
        problem_requirements=requirements,
        diagram_data=diagram_data
    )
    
    # Stream response via SSE
    async def generate_stream():
        collected_response = ""
        try:
            # Use astream_events to get token-level streaming
            async for event in graph.astream_events(
                {"messages": langchain_messages},
                version="v2"
            ):
                kind = event.get("event", "")
                
                # Stream tokens from the LLM (chat model stream events)
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Only stream text content, not tool calls
                        if not (hasattr(chunk, "tool_calls") and chunk.tool_calls):
                            token = chunk.content
                            collected_response += token
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                
                # Notify when tool is being called
                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'status', 'content': 'Analyzing your diagram...'})}\n\n"
            
            # Send done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
            # Save assistant response to history
            if collected_response:
                history.append({"role": "assistant", "content": collected_response})
            
            # Trim history to last 10 messages
            if len(history) > 10:
                chat_histories[session_id] = history[-10:]
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )