import logging
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.config import settings
from backend.app.database import get_db, engine
from backend.app.models import SessionModel, MessageModel, SourceCitedModel
from backend.app.schemas import (
    ChatRequest,
    ChatResponse,
    SourceItem,
    Ship30Request,
    Ship30Response,
    SessionCreate,
    SessionSummary,
    SessionDetail,
    MessageSchema,
    HealthResponse,
    ErrorResponse
)
from backend.app.services.rag import rag_service
from backend.app.services.llm import generate_llm_response, get_available_providers, ProviderError
from backend.app.services.ship30 import execute_ship30_skill

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health_check():
    """Returns application health, provider readiness, and knowledge base stats."""
    db_name = "PostgreSQL" if "postgresql" in str(engine.url) else "SQLite"
    stats = rag_service.get_stats()
    available_providers = get_available_providers()

    return HealthResponse(
        status="ok",
        active_provider=settings.LLM_PROVIDER,
        available_providers=available_providers,
        database_backend=db_name,
        indexed_chunks=stats["indexed_chunks"],
        episodes_indexed=stats["episodes_indexed"]
    )

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Core conversational RAG endpoint:
    - Creates or retrieves session
    - Performs vector similarity search with grounding check
    - Synthesizes grounded answer using active or requested LLM provider
    - Persists user & assistant messages and source citations to DB
    """
    logger.info("Chat request received: '%s...' (provider: %s)", request.message[:50], request.provider or settings.LLM_PROVIDER)

    # 1. Resolve or create Session
    session_id = request.session_id
    session = None
    if session_id:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    
    if not session:
        # Create new session with title derived from the first prompt
        title = request.message[:45] + ("..." if len(request.message) > 45 else "")
        session = SessionModel(
            id=str(uuid.uuid4()),
            title=title,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # 2. Vector search & grounding check
    retrieved_chunks, is_grounded = rag_service.search(request.message)

    # 3. Call LLM provider
    try:
        answer, provider_used = generate_llm_response(
            query=request.message,
            retrieved_chunks=retrieved_chunks,
            is_grounded=is_grounded,
            provider=request.provider
        )
    except ProviderError as pe:
        # Return structured provider failure with troubleshooting tips
        logger.error("Provider error in /chat: %s (%s)", pe.message, pe.code)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "LLM Provider Unavailable",
                "detail": pe.message,
                "code": pe.code,
                "troubleshooting": pe.troubleshooting
            }
        )
    except Exception as e:
        logger.exception("Unexpected error in /chat endpoint: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Error",
                "detail": str(e),
                "code": "INTERNAL_SERVER_ERROR",
                "troubleshooting": "Check application console logs."
            }
        )

    # 4. Save user message
    user_msg = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="user",
        content=request.message,
        created_at=datetime.now(timezone.utc)
    )
    db.add(user_msg)

    # 5. Save assistant message
    asst_msg = MessageModel(
        id=str(uuid.uuid4()),
        session_id=session_id,
        role="assistant",
        content=answer,
        provider_used=provider_used,
        created_at=datetime.now(timezone.utc)
    )
    db.add(asst_msg)

    # 6. Save cited sources (only if grounded)
    sources_to_return: List[SourceItem] = []
    if is_grounded and retrieved_chunks:
        for chunk in retrieved_chunks:
            source_rec = SourceCitedModel(
                id=str(uuid.uuid4()),
                message_id=asst_msg.id,
                episode_slug=chunk.get("episode_slug"),
                episode_title=chunk.get("episode_title", "Unknown Episode"),
                speaker=chunk.get("primary_speaker", "Guest"),
                timestamp_range=f"{chunk.get('start_timestamp')} - {chunk.get('end_timestamp')}",
                start_seconds=chunk.get("start_seconds", 0),
                youtube_url=chunk.get("timestamped_url") or chunk.get("youtube_url"),
                quote_text=chunk.get("summary_snippet"),
                relevance_score=chunk.get("score", 0.0)
            )
            db.add(source_rec)
            sources_to_return.append(
                SourceItem(
                    episode_slug=source_rec.episode_slug,
                    episode_title=source_rec.episode_title,
                    speaker=source_rec.speaker,
                    timestamp_range=source_rec.timestamp_range,
                    start_seconds=source_rec.start_seconds,
                    youtube_url=source_rec.youtube_url,
                    quote_text=source_rec.quote_text,
                    relevance_score=source_rec.relevance_score
                )
            )

    # Update session timestamp
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(
        session_id=session_id,
        message_id=asst_msg.id,
        answer=answer,
        sources=sources_to_return,
        provider_used=provider_used,
        is_grounded=is_grounded
    )

@router.post("/chat/ship30", response_model=Ship30Response)
def ship30_skill_endpoint(request: Ship30Request, db: Session = Depends(get_db)):
    """
    Ship 30 for 30 Skill Transformation:
    Takes a grounded conversation answer and transforms it into a publication-ready essay.
    """
    grounded_answer = request.grounded_answer
    sources_list = []

    # If message_id is provided, fetch original message and sources from database
    if request.message_id:
        msg = db.query(MessageModel).filter(MessageModel.id == request.message_id).first()
        if msg:
            grounded_answer = msg.content
            for s in msg.sources_cited:
                sources_list.append({
                    "guest": s.speaker,
                    "speaker": s.speaker,
                    "episode_title": s.episode_title,
                    "timestamp_range": s.timestamp_range,
                    "timestamped_url": s.youtube_url,
                    "quote_snippet": s.quote_text
                })

    if not grounded_answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Missing input", "detail": "Either message_id or grounded_answer must be provided.", "code": "INVALID_ARGUMENT"}
        )

    # Run Ship 30 for 30 transformation
    essay_data = execute_ship30_skill(
        grounded_answer=grounded_answer,
        sources=sources_list,
        topic=request.topic,
        provider=request.provider
    )

    formatted_sources = [
        SourceItem(
            episode_title=s.get("episode_title", "Lenny's Podcast"),
            speaker=s.get("speaker") or s.get("guest", "Guest"),
            timestamp_range=s.get("timestamp_range", "00:00:00"),
            youtube_url=s.get("timestamped_url"),
            quote_text=s.get("quote_snippet"),
            relevance_score=0.95
        )
        for s in sources_list
    ]

    return Ship30Response(
        title=essay_data["title"],
        essay_markdown=essay_data["essay_markdown"],
        essay_html=essay_data["essay_html"],
        word_count=essay_data["word_count"],
        core_takeaway=essay_data["core_takeaway"],
        sources=formatted_sources,
        provider_used=essay_data["provider_used"]
    )

@router.get("/sessions", response_model=List[SessionSummary])
def list_sessions(limit: int = 50, db: Session = Depends(get_db)):
    """List recent conversation sessions."""
    sessions = db.query(SessionModel).order_by(desc(SessionModel.updated_at)).limit(limit).all()
    results = []
    for s in sessions:
        results.append(
            SessionSummary(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=len(s.messages)
            )
        )
    return results

@router.post("/sessions", response_model=SessionSummary)
def create_session(payload: SessionCreate, db: Session = Depends(get_db)):
    """Explicitly create a new chat session."""
    session = SessionModel(
        id=str(uuid.uuid4()),
        title=payload.title or "New Conversation",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionSummary(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )

@router.get("/sessions/{session_id}", response_model=SessionDetail)
def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Retrieve full message history and cited sources for a given session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Session Not Found", "detail": f"No session found with id {session_id}", "code": "SESSION_NOT_FOUND"}
        )

    messages_out = []
    for m in session.messages:
        sources_out = [
            SourceItem(
                episode_slug=s.episode_slug,
                episode_title=s.episode_title,
                speaker=s.speaker,
                timestamp_range=s.timestamp_range,
                start_seconds=s.start_seconds,
                youtube_url=s.youtube_url,
                quote_text=s.quote_text,
                relevance_score=s.relevance_score or 0.0
            )
            for s in m.sources_cited
        ]
        messages_out.append(
            MessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                provider_used=m.provider_used,
                created_at=m.created_at,
                sources_cited=sources_out
            )
        )

    return SessionDetail(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=messages_out
    )

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a conversation session and all its messages."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Session Not Found", "detail": f"No session found with id {session_id}", "code": "SESSION_NOT_FOUND"}
        )
    db.delete(session)
    db.commit()
    return None
