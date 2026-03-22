"""
AI Chat Route — LangGraph Agent with SSE Streaming
Sidebar chat that acts as a system design mentor.
Uses a LangGraph agent that can optionally fetch page context.
"""
from dotenv import load_dotenv
load_dotenv()

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List
from bson import ObjectId

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from Agents.chat_agent.graph import create_chat_agent_graph

from core.auth import get_current_user
from core.models import User
from database.database import db


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

    sessions_collection = db.get_collection("sessions")
    session = await sessions_collection.find_one({
        "_id": ObjectId(session_id),
        "user_id": current_user.id
    })

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    problems_collection = db.get_collection("problems")
    problem = await problems_collection.find_one({
        "_id": ObjectId(session["problem_id"])
    })

    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    problem_title    = problem.get("title", "System Design Problem")
    problem_description = problem.get("description", "No description provided.")
    requirements     = ", ".join(problem.get("requirements", []))
    diagram_data     = request.diagram_data

    if session_id not in chat_histories:
        chat_histories[session_id] = []

    history = chat_histories[session_id]

    langchain_messages = []
    for msg in history[-10:]:
        if msg["role"] == "user":
            langchain_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            langchain_messages.append(AIMessage(content=msg["content"]))

    langchain_messages.append(HumanMessage(content=request.message))
    history.append({"role": "user", "content": request.message})

    graph = create_chat_agent_graph(
        problem_title=problem_title,
        problem_description=problem_description,
        problem_requirements=requirements,
        diagram_data=diagram_data
    )

    # ── Shared cursor so we can drain new batches as they land ──────────────
    # streamed_batches is a list that the tool appends to during graph execution.
    # We track how many we've already sent so we can flush new ones in real-time.
    streamed_batches: list = graph._streamed_diagram_batches
    last_sent_idx = 0

    def drain_new_batches():
        """Yield SSE events for any diagram batches that haven't been sent yet."""
        nonlocal last_sent_idx
        events = []
        while last_sent_idx < len(streamed_batches):
            batch = streamed_batches[last_sent_idx]
            elements = batch.get("elements", [])
            label    = batch.get("label", "Building...")
            progress = batch.get("progress", "")
            if elements:
                events.append(f"data: {json.dumps({'type': 'diagram_update', 'elements': elements, 'label': label, 'progress': progress})}\n\n")
            last_sent_idx += 1
        return events

    async def generate_stream():
        nonlocal last_sent_idx
        collected_response = ""

        try:
            async for event in graph.astream_events(
                {"messages": langchain_messages},
                version="v2"
            ):
                kind = event.get("event", "")

                # ── Token stream ────────────────────────────────────────────
                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        if not (hasattr(chunk, "tool_calls") and chunk.tool_calls):
                            token = chunk.content
                            collected_response += token
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

                # ── Tool call started ───────────────────────────────────────
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    if tool_name == "get_page_context":
                        status = "Analyzing your diagram..."
                    elif tool_name == "modify_diagram":
                        status = "Building your diagram..."
                    else:
                        status = f"Running {tool_name}..."
                    yield f"data: {json.dumps({'type': 'status', 'content': status})}\n\n"

                # ── Tool call finished — flush any new diagram batches NOW ──
                elif kind == "on_tool_end":
                    for sse_event in drain_new_batches():
                        yield sse_event

            # ── After graph completes — flush any remaining batches ─────────
            for sse_event in drain_new_batches():
                yield sse_event

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            if collected_response:
                history.append({"role": "assistant", "content": collected_response})

            if len(history) > 10:
                chat_histories[session_id] = history[-10:]

        except Exception as e:
            import traceback
            traceback.print_exc()
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
