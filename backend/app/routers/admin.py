import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
import networkx as nx
from datetime import timezone

from app.database import get_db
from app.models import FraudSession, SessionMessage, FraudEntity, FraudLink
from app.auth import require_law_enforcement
from app.schemas import SessionResponse, SessionDetailResponse, MessageResponse, MatchedPattern

router = APIRouter(prefix="/api/admin", tags=["admin"])

class StatusUpdate(BaseModel):
    status: str

@router.get("/sessions", dependencies=[Depends(require_law_enforcement)])
async def list_sessions(
    sort: str = "created_at", 
    status: Optional[str] = "flagged", 
    skip: int = 0, 
    limit: int = 50, 
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FraudSession)
    if status:
        stmt = stmt.where(FraudSession.status == status)
        
    if sort == "risk_score":
        stmt = stmt.order_by(desc(FraudSession.risk_score))
    else:
        stmt = stmt.order_by(desc(FraudSession.created_at))
        
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    
    session_ids = [s.id for s in sessions]
    entities_by_session = {sid: [] for sid in session_ids}
    
    if session_ids:
        l_stmt = select(FraudLink).where(FraudLink.session_id.in_(session_ids))
        l_result = await db.execute(l_stmt)
        links = l_result.scalars().all()
        
        if links:
            entity_ids = [link.entity_id for link in links]
            e_stmt = select(FraudEntity).where(FraudEntity.id.in_(entity_ids))
            e_result = await db.execute(e_stmt)
            ents = e_result.scalars().all()
            
            ent_map = {e.id: e for e in ents}
            
            for link in links:
                e = ent_map.get(link.entity_id)
                if e:
                    entities_by_session[link.session_id].append({
                        "id": str(e.id),
                        "type": e.entity_type,
                        "value": e.entity_value
                    })

    return [{
        "id": str(s.id),
        "risk_score": s.risk_score,
        "ai_explanation": s.ai_explanation,
        "status": s.status,
        "created_at": s.created_at.isoformat() + ("Z" if not s.created_at.tzinfo else ""),
        "entities": entities_by_session.get(s.id, [])
    } for s in sessions]


@router.get("/sessions/{session_id}", dependencies=[Depends(require_law_enforcement)])
async def get_session_detail(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(FraudSession).where(FraudSession.id == session_id)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
        
    msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.created_at)
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()
    
    # Also fetch linked entities
    links_stmt = select(FraudLink).where(FraudLink.session_id == session_id)
    links_result = await db.execute(links_stmt)
    links = links_result.scalars().all()
    
    entities = []
    if links:
        entity_ids = [link.entity_id for link in links]
        e_stmt = select(FraudEntity).where(FraudEntity.id.in_(entity_ids))
        e_result = await db.execute(e_stmt)
        ents = e_result.scalars().all()
        entities = [{"id": e.id, "type": e.entity_type, "value": e.entity_value} for e in ents]
    
    from app.utils.scoring import get_matched_patterns_for_session
    matched_patterns = await get_matched_patterns_for_session(db, s)
    
    return {
        "id": s.id,
        "transcript_text": s.transcript_text,
        "risk_score": s.risk_score,
        "ai_explanation": s.ai_explanation,
        "status": s.status,
        "created_at": s.created_at.replace(tzinfo=timezone.utc) if not s.created_at.tzinfo else s.created_at,
        "matched_patterns": matched_patterns,
        "messages": [MessageResponse.model_validate(m) for m in messages],
        "entities": entities
    }

@router.patch("/sessions/{session_id}", dependencies=[Depends(require_law_enforcement)])
async def update_session_status(session_id: uuid.UUID, status_update: StatusUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(FraudSession).where(FraudSession.id == session_id)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
        
    s.status = status_update.status
    await db.commit()
    return {"message": "Status updated successfully"}


@router.get("/graph", dependencies=[Depends(require_law_enforcement)])
async def get_fraud_graph(db: AsyncSession = Depends(get_db)):
    """
    Returns nodes + edges for graph visualization
    """
    # We load all entities that have links, and the sessions they are linked to
    l_stmt = select(FraudLink)
    l_result = await db.execute(l_stmt)
    links = l_result.scalars().all()
    
    session_ids = list(set([str(link.session_id) for link in links]))
    entity_ids = list(set([str(link.entity_id) for link in links]))
    
    if not links:
        return {"nodes": [], "edges": []}
        
    e_stmt = select(FraudEntity).where(FraudEntity.id.in_(entity_ids))
    e_result = await db.execute(e_stmt)
    entities = e_result.scalars().all()
    
    s_stmt = select(FraudSession).where(FraudSession.id.in_(session_ids))
    s_result = await db.execute(s_stmt)
    sessions = s_result.scalars().all()
    
    nodes = []
    edges = []
    
    for s in sessions:
        nodes.append({
            "id": str(s.id),
            "group": "session",
            "val": 10, # Size for session nodes
            "label": f"Report: {s.risk_score} Risk",
            "risk_score": s.risk_score,
            "ai_explanation": s.ai_explanation,
            "transcript_snippet": s.transcript_text[:150] + ("..." if len(s.transcript_text) > 150 else ""),
            "created_at": s.created_at.isoformat() + ("Z" if not s.created_at.tzinfo else "")
        })
        
    for e in entities:
        nodes.append({
            "id": str(e.id),
            "group": "entity",
            "val": 5 + (e.report_count * 5), # Node size scales with reports
            "label": f"{e.entity_type}: {e.entity_value}",
            "entity_type": e.entity_type,
            "entity_value": e.entity_value,
            "report_count": e.report_count,
            "first_seen": e.first_seen.isoformat() + ("Z" if not e.first_seen.tzinfo else "")
        })
        
    for link in links:
        edges.append({
            "source": str(link.session_id),
            "target": str(link.entity_id)
        })
        
    return {"nodes": nodes, "edges": edges}

@router.get("/graph/entity/{entity_id}", dependencies=[Depends(require_law_enforcement)])
async def get_sessions_by_entity(entity_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    l_stmt = select(FraudLink).where(FraudLink.entity_id == entity_id)
    l_result = await db.execute(l_stmt)
    links = l_result.scalars().all()
    
    session_ids = [link.session_id for link in links]
    if not session_ids:
        return []
        
    s_stmt = select(FraudSession).where(FraudSession.id.in_(session_ids))
    s_result = await db.execute(s_stmt)
    sessions = s_result.scalars().all()
    
    return [{
        "id": s.id,
        "risk_score": s.risk_score,
        "status": s.status,
        "created_at": s.created_at.replace(tzinfo=timezone.utc) if not s.created_at.tzinfo else s.created_at
    } for s in sessions]
