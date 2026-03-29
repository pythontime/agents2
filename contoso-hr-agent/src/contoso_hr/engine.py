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


def _build_past_session_context(current_session_id: str, max_sessions: int = 2, max_turns: int = 6) -> str:
    """Return a compact excerpt from the most recent past sessions.

    Pulls up to `max_turns` turns from each of the `max_sessions` most
    recently modified session files, skipping the current session. Each
    message is truncated to 200 chars to keep the prompt tight.
    """
    sessions_dir = _sessions_dir()
    past_files = sorted(
        [p for p in sessions_dir.glob("*.json") if p.stem != current_session_id],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:max_sessions]

    if not past_files:
        return ""

    blocks = []
    for path in past_files:
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not history:
            continue
        excerpt_turns = history[-max_turns:]
        lines = []
        for turn in excerpt_turns:
            role_label = "User" if turn.get("role") == "user" else "Alex (you)"
            lines.append(f"  {role_label}: {turn.get('content', '')[:200]}")
        blocks.append("\n".join(lines))

    if not blocks:
        return ""

    return "\n\n---\n".join(blocks)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@app.post("/api/chat", response_model=ChatResponse)
async def chat(message: ChatMessage) -> ChatResponse:
    """Handle a chat message via the ChatConcierge CrewAI agent.

    The concierge uses the query_hr_policy tool so policy answers are
    grounded in ChromaDB-retrieved Contoso documentation. Conversation
    history is included in the task prompt for context continuity.
    """
    logger = get_hr_logger()
    config = get_config()

    # Load (or create) persistent session history
    history = _load_session(message.session_id)
    history.append({"role": "user", "content": message.message})

    # Build a compact transcript of recent turns to give the agent context
    recent = history[-20:]
    transcript_lines = []
    for turn in recent[:-1]:  # exclude current message — it's the task
        role_label = "User" if turn["role"] == "user" else "Alex (you)"
        transcript_lines.append(f"{role_label}: {turn['content'][:300]}")
    transcript = "\n".join(transcript_lines) if transcript_lines else "(new conversation)"

    # Pull in excerpts from recent past sessions so the agent can reference
    # things the user mentioned in previous conversations.
    past_context = _build_past_session_context(message.session_id)
    past_context_block = (
        f"\nPRIOR SESSION CONTEXT (recent past conversations — use only if relevant):\n{past_context}\n"
        if past_context else ""
    )

    try:
        from crewai import Crew, Process, Task
        from contoso_hr.pipeline.agents import ChatConciergeAgent

        llm = config.get_crew_llm()
        agent = ChatConciergeAgent.create(llm)

        task = Task(
            description=f"""Respond to the user's message as Alex, the Contoso HR Chat Concierge.
{past_context_block}
CURRENT CONVERSATION:
{transcript}

USER'S CURRENT MESSAGE:
{message.message}

Use query_hr_policy for any policy question. Keep the response concise and conversational.
Do not repeat the conversation history in your reply — just answer the current message.""",
            expected_output="A helpful, concise conversational reply to the user's message.",
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        result = await asyncio.to_thread(crew.kickoff)
        reply = result.raw.strip()

    except Exception as e:
        logger.error(f"Chat concierge error: {e}", e)
        reply = (
            "I'm sorry, I encountered an error. "
            "Please check that Azure AI Foundry is configured and the knowledge base is seeded."
        )

    history.append({"role": "assistant", "content": reply})

    # Persist to disk so context survives server restarts
    _save_session(message.session_id, history)

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


@app.get("/api/chat/sessions")
async def list_chat_sessions() -> dict:
    """List all persisted chat sessions, sorted by most recently updated.

    Returns metadata for each session: id, message count, last user message
    preview, and last-updated timestamp (Unix seconds).
    """
    sessions_dir = _sessions_dir()
    sessions = []
    for path in sorted(sessions_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        session_id = path.stem
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
            last_user = next(
                (m["content"] for m in reversed(history) if m.get("role") == "user"), ""
            )
            sessions.append({
                "session_id": session_id,
                "message_count": len(history),
                "last_message_preview": last_user[:80],
                "last_updated": path.stat().st_mtime,
            })
        except Exception:
            continue
    return {"sessions": sessions}


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
    if any(w in msg_lower for w in ["score", "decision", "match", "qualified", "review", "disposition"]):
        return ["What does 'Strong Match' mean?", "When does a candidate get 'Needs Review'?"]
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

    mcp_port = config.mcp_port
    print(f"\n  Web UI:  http://localhost:{port}/chat.html")
    print(f"  API:     http://localhost:{port}/api/")
    print(f"  Docs:    http://localhost:{port}/docs")
    print(f"  MCP SSE: http://localhost:{mcp_port}/sse\n")

    uvicorn.run(
        "contoso_hr.engine:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level=config.log_level.lower(),
    )
