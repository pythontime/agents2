"""
Contoso HR Agent — FastAPI engine.

Serves the web UI (static files from web/) and REST API endpoints:
  POST /api/chat          — HR policy Q&A chatbot
  POST /api/upload        — Resume file upload → queued for evaluation
  GET  /api/candidates    — List evaluated candidates (for grid view)
  GET  /api/candidates/{id} — Full evaluation detail
  GET  /api/stats         — Aggregate statistics

Kills port ENGINE_PORT on startup to ensure clean bind.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_config
from .logging_setup import get_hr_logger, print_banner, setup_logging
from .memory.sqlite_store import HRSQLiteStore
from .models import (
    CandidateSummary,
    ChatMessage,
    ChatResponse,
    EvaluationResult,
    UploadResponse,
)
from .util.port_utils import force_kill_port

# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Contoso HR Agent",
    description="AI-powered resume screening and HR policy Q&A",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Chat session memory — persisted to data/chat_sessions/{session_id}.json
#
# Each session file is a JSON array of {role, content} dicts, matching the
# LangChain message format. The in-memory dict is a write-through cache:
# reads load from disk on first access, writes flush to disk immediately.
# This gives the LLM full conversation context across server restarts.
# ---------------------------------------------------------------------------

_chat_histories: dict[str, list[dict]] = {}


def _sessions_dir() -> Path:
    config = get_config()
    d = config.data_dir / "chat_sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_session(session_id: str) -> list[dict]:
    """Load history from disk into the in-memory cache if not already loaded."""
    if session_id not in _chat_histories:
        path = _sessions_dir() / f"{session_id}.json"
        if path.exists():
            try:
                _chat_histories[session_id] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                _chat_histories[session_id] = []
        else:
            _chat_histories[session_id] = []
    return _chat_histories[session_id]


def _save_session(session_id: str, history: list[dict]) -> None:
    """Flush the current history to disk."""
    path = _sessions_dir() / f"{session_id}.json"
    try:
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # non-fatal — memory still works in-process

HR_SYSTEM_PROMPT = """You are the Contoso HR Assistant, an AI-powered chatbot that helps
recruiters and hiring managers evaluate technical trainer candidates and answer HR policy questions.

Contoso hires technical trainers for Microsoft Azure, M365, and Security certification courses.
Key hiring criteria you understand: MCT (Microsoft Certified Trainer) status, Azure/M365/Security
certifications (AZ-104, AZ-305, AZ-400, SC-300, SC-200, AI-102, etc.), training delivery
volume and learner satisfaction scores, curriculum development experience.

You can:
1. Answer questions about Contoso HR policy (trainer qualifications, compensation bands, EEO, benefits)
2. Accept resume uploads for AI-powered trainer evaluation (use the upload panel)
3. Explain what the AI pipeline looks for: policy compliance → technical skills → delivery track record → decision
4. Interpret evaluation results from the Candidates dashboard

When a user wants to submit a resume, guide them to the file upload panel (right side).
Uploaded resumes trigger the full 3-agent evaluation pipeline automatically.

Be professional, helpful, and concise. Base policy answers on Contoso's documented HR policies."""


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage) -> ChatResponse:
    """Handle a chat message and return an AI response.

    Uses Azure AI Foundry (AzureChatOpenAI) for response generation.
    Maintains per-session conversation history.
    """
    logger = get_hr_logger()
    config = get_config()

    # Load (or create) persistent session history
    history = _load_session(message.session_id)
    history.append({"role": "user", "content": message.message})

    # Send last 20 turns to the LLM to stay well within context limits
    recent_history = history[-20:]

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        llm = config.get_llm()
        lc_messages = [SystemMessage(content=HR_SYSTEM_PROMPT)]
        for turn in recent_history[:-1]:  # last item is the current user message
            if turn["role"] == "user":
                lc_messages.append(HumanMessage(content=turn["content"]))
            else:
                lc_messages.append(AIMessage(content=turn["content"]))
        lc_messages.append(HumanMessage(content=message.message))

        response = await asyncio.to_thread(llm.invoke, lc_messages)
        reply = response.content

    except Exception as e:
        logger.error(f"Chat LLM error: {e}", e)
        reply = (
            "I'm sorry, I encountered an error processing your request. "
            "Please check that Azure AI Foundry is configured correctly."
        )

    history.append({"role": "assistant", "content": reply})

    # Persist to disk so context survives server restarts
    _save_session(message.session_id, history)

    # Generate context-aware suggestions
    suggestions = _get_suggestions(message.message)

    return ChatResponse(
        reply=reply,
        session_id=message.session_id,
        suggestions=suggestions,
    )


@app.post("/api/upload", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> UploadResponse:
    """Accept a resume file upload and queue it for evaluation.

    Saves the file to data/incoming/ where the watcher will pick it up.
    Returns immediately with a queued status.
    """
    logger = get_hr_logger()
    config = get_config()

    # Validate file type
    allowed_extensions = {".txt", ".md", ".pdf", ".docx"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_extensions:
        return UploadResponse(
            candidate_id="",
            filename=file.filename or "",
            status="error",
            message=f"Supported formats: .txt, .md, .pdf, .docx. Got: {suffix}",
        )

    # Generate a safe filename
    candidate_id = str(uuid.uuid4())[:8]
    safe_name = f"upload_{candidate_id}{suffix}"
    dest = config.incoming_dir / safe_name

    config.incoming_dir.mkdir(parents=True, exist_ok=True)

    try:
        content = await file.read()
        dest.write_bytes(content)
        logger.file_operation("Queued upload", str(dest))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return UploadResponse(
            candidate_id=candidate_id,
            filename=file.filename or safe_name,
            status="error",
            message=f"Failed to save file: {e}",
        )

    return UploadResponse(
        candidate_id=candidate_id,
        filename=file.filename or safe_name,
        status="queued",
        message=(
            "Resume queued for evaluation! "
            "The AI pipeline will process it shortly. "
            "Check the Candidates page for results (auto-refreshes every 10s)."
        ),
    )


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str) -> dict:
    """Return the persisted chat history for a session.

    Useful for debugging memory persistence and for the MCP server.
    """
    history = _load_session(session_id)
    return {"session_id": session_id, "message_count": len(history), "history": history}


@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str) -> dict:
    """Delete the persisted chat history for a session."""
    _chat_histories.pop(session_id, None)
    path = _sessions_dir() / f"{session_id}.json"
    if path.exists():
        path.unlink()
    return {"session_id": session_id, "cleared": True}


@app.get("/api/candidates", response_model=list[CandidateSummary])
async def list_candidates(
    limit: int = 50,
    decision: Optional[str] = None,
) -> list[CandidateSummary]:
    """Return the list of evaluated candidates for the grid view.

    Args:
        limit: Maximum number of results (default 50).
        decision: Filter by advance/hold/reject (optional).
    """
    config = get_config()
    store = HRSQLiteStore(config.data_dir / "hr.db")

    if decision:
        return store.get_candidates_by_decision(decision, limit)
    return store.get_recent_candidates(limit)


@app.get("/api/candidates/{candidate_id}", response_model=EvaluationResult)
async def get_candidate(candidate_id: str) -> EvaluationResult:
    """Return the full evaluation result for a specific candidate.

    Args:
        candidate_id: Unique candidate identifier.
    """
    config = get_config()
    store = HRSQLiteStore(config.data_dir / "hr.db")
    result = store.get_result(candidate_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
    return result


@app.get("/api/stats")
async def get_stats() -> dict:
    """Return aggregate evaluation statistics."""
    config = get_config()
    store = HRSQLiteStore(config.data_dir / "hr.db")
    return store.get_stats()


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "contoso-hr-agent"}


# ---------------------------------------------------------------------------
# Static file serving (web UI)
# ---------------------------------------------------------------------------

def _mount_static() -> None:
    """Mount the web/ directory for static file serving."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "web").exists():
            web_dir = parent / "web"
            app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")
            return


_mount_static()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_suggestions(user_message: str) -> list[str]:
    """Generate context-aware quick-reply suggestions."""
    msg_lower = user_message.lower()
    if any(w in msg_lower for w in ["salary", "pay", "compensation", "band"]):
        return ["What is the salary band for a Senior Trainer?", "How are bonuses calculated?"]
    if any(w in msg_lower for w in ["mct", "certified trainer", "certification"]):
        return ["Is MCT required for all trainer roles?", "Which Azure certs does Contoso value most?"]
    if any(w in msg_lower for w in ["interview", "hire", "hiring", "process"]):
        return ["What is the trainer interview process?", "What does the technical screen involve?"]
    if any(w in msg_lower for w in ["resume", "cv", "upload", "candidate"]):
        return ["How do I submit a resume?", "What makes a strong trainer resume?"]
    if any(w in msg_lower for w in ["score", "decision", "advance", "reject", "hold"]):
        return ["What score threshold means advance?", "What does 'hold' mean for a candidate?"]
    return [
        "What certifications does Contoso require for trainers?",
        "How do I submit a resume for evaluation?",
        "What is Contoso's EEO policy?",
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the FastAPI server on ENGINE_PORT, killing any existing process first."""
    import uvicorn

    config = get_config()
    setup_logging(config.log_level)
    print_banner()

    port = config.engine_port
    force_kill_port(port)

    print(f"\n  Web UI:  http://localhost:{port}/chat.html")
    print(f"  API:     http://localhost:{port}/api/")
    print(f"  Docs:    http://localhost:{port}/docs\n")

    uvicorn.run(
        "contoso_hr.engine:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=config.log_level.lower(),
    )
