import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import ScamPattern
from app.auth import require_admin
from app.services.embedding_service import get_embedding

router = APIRouter(prefix="/api/admin/scam-patterns", tags=["scam-patterns"])

class ScamPatternCreate(BaseModel):
    title: str
    script_text: str
    category: Optional[str] = None
    source: Optional[str] = None

class ScamPatternResponse(BaseModel):
    id: uuid.UUID
    title: str
    script_text: str
    category: Optional[str] = None
    source: Optional[str] = None
    
    class Config:
        from_attributes = True

@router.get("", response_model=list[ScamPatternResponse], dependencies=[Depends(require_admin)])
async def list_patterns(db: AsyncSession = Depends(get_db)):
    stmt = select(ScamPattern).order_by(ScamPattern.created_at.desc())
    result = await db.execute(stmt)
    patterns = result.scalars().all()
    return patterns

@router.post("", response_model=ScamPatternResponse, dependencies=[Depends(require_admin)])
async def add_pattern(pattern: ScamPatternCreate, db: AsyncSession = Depends(get_db)):
    # Generate embedding for the new pattern
    emb = await get_embedding(pattern.script_text)
    
    db_pattern = ScamPattern(
        title=pattern.title,
        script_text=pattern.script_text,
        category=pattern.category,
        source=pattern.source,
        embedding=emb
    )
    db.add(db_pattern)
    await db.commit()
    await db.refresh(db_pattern)
    return db_pattern

@router.delete("/{pattern_id}", dependencies=[Depends(require_admin)])
async def delete_pattern(pattern_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(ScamPattern).where(ScamPattern.id == pattern_id)
    result = await db.execute(stmt)
    pattern = result.scalar_one_or_none()
    
    if not pattern:
        raise HTTPException(status_code=404, detail="Pattern not found")
        
    await db.delete(pattern)
    await db.commit()
    return {"message": "Pattern deleted successfully"}
