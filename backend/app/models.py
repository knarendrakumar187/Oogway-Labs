import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, Integer
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="New Conversation")
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan", order_by="MessageModel.created_at")

class MessageModel(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    provider_used = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)

    session = relationship("SessionModel", back_populates="messages")
    sources_cited = relationship("SourceCitedModel", back_populates="message", cascade="all, delete-orphan")

class SourceCitedModel(Base):
    __tablename__ = "sources_cited"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    episode_slug = Column(String(100), nullable=True)
    episode_title = Column(String(255), nullable=False)
    speaker = Column(String(100), nullable=False)
    timestamp_range = Column(String(50), nullable=False)  # e.g. "00:00:26 - 00:03:45"
    start_seconds = Column(Integer, nullable=True, default=0)
    youtube_url = Column(String(500), nullable=True)
    quote_text = Column(Text, nullable=True)
    relevance_score = Column(Float, nullable=True, default=0.0)

    message = relationship("MessageModel", back_populates="sources_cited")
