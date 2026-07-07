from datetime import datetime
from pydantic import BaseModel, ConfigDict
import uuid

# --- Core Request/Response Schemas ---

class SessionCreate(BaseModel):
    transcript_text: str

class MatchedPattern(BaseModel):
    id: uuid.UUID
    title: str
    category: str | None
    similarity_score: float

class SessionResponse(BaseModel):
    id: uuid.UUID
    transcript_text: str | None = None
    risk_score: int
    ai_explanation: str
    matched_patterns: list[MatchedPattern] | None = None
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str

class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
