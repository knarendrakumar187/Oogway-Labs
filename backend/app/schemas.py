from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SourceItem(BaseModel):
    episode_slug: Optional[str] = None
    episode_title: str
    speaker: str
    timestamp_range: str
    start_seconds: Optional[int] = 0
    youtube_url: Optional[str] = None
    quote_text: Optional[str] = None
    relevance_score: float = 0.0

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Existing session UUID or null to create one")
    message: str = Field(..., min_length=1, description="User prompt or question")
    provider: Optional[str] = Field(default=None, description="Optional per-request provider override (ollama, openai, anthropic, mock)")

class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    provider_used: Optional[str] = None
    created_at: datetime
    sources_cited: List[SourceItem] = []

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    answer: str
    sources: List[SourceItem] = []
    provider_used: str
    is_grounded: bool = True

class Ship30Request(BaseModel):
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    grounded_answer: Optional[str] = None
    topic: Optional[str] = None
    provider: Optional[str] = None

class Ship30Response(BaseModel):
    title: str
    essay_markdown: str
    essay_html: str
    word_count: int
    core_takeaway: str
    sources: List[SourceItem] = []
    provider_used: str

class SessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class SessionSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True

class SessionDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageSchema] = []

    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    status: str
    active_provider: str
    available_providers: Dict[str, bool]
    database_backend: str
    indexed_chunks: int
    episodes_indexed: int

class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str
    troubleshooting: Optional[str] = None
