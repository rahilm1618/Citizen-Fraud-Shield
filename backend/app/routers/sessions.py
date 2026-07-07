import uuid
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import FraudSession, ScamPattern, SessionMessage
from app.schemas import SessionCreate, SessionResponse, SessionDetailResponse, MessageCreate, MessageResponse, MatchedPattern
from app.services.session_service import process_new_session, process_followup_message, create_live_session, update_session_score
from app.services.transcription_service import transcribe_audio_chunk

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(session_data: SessionCreate, db: AsyncSession = Depends(get_db)):
    """
    Submit a new transcript for fraud analysis.
    """
    try:
        new_session = await process_new_session(session_data, db)
        
        # We need to fetch the matched patterns to return them in the response
        matched_patterns = []
        if new_session.matched_pattern_ids:
            stmt = select(ScamPattern).where(ScamPattern.id.in_(new_session.matched_pattern_ids))
            result = await db.execute(stmt)
            patterns = result.scalars().all()
            for p in patterns:
                matched_patterns.append(MatchedPattern(
                    id=p.id,
                    title=p.title,
                    category=p.category,
                    similarity_score=0.0 # We don't have the exact similarity score here without recomputing or returning it from the service
                ))
                
        return SessionResponse(
            id=new_session.id,
            transcript_text=new_session.transcript_text,
            risk_score=new_session.risk_score,
            ai_explanation=new_session.ai_explanation,
            status=new_session.status,
            created_at=new_session.created_at,
            matched_patterns=matched_patterns
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/live", response_model=SessionResponse)
async def start_live_session(db: AsyncSession = Depends(get_db)):
    """
    Start a live audio tracking session without running initial scoring.
    """
    try:
        new_session = await create_live_session(db)
        return SessionResponse(
            id=new_session.id,
            transcript_text=new_session.transcript_text,
            risk_score=new_session.risk_score,
            ai_explanation=new_session.ai_explanation,
            status=new_session.status,
            created_at=new_session.created_at,
            matched_patterns=[]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/finalize", response_model=SessionResponse)
async def finalize_live_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(FraudSession).where(FraudSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    from app.services.entity_service import extract_entities, upsert_entities
    if session.transcript_text:
        extracted_entities = await extract_entities(session.transcript_text)
        if extracted_entities:
            await upsert_entities(session.id, extracted_entities, db)
            await db.flush()
            
    return SessionResponse(
        id=session.id,
        transcript_text=session.transcript_text,
        risk_score=session.risk_score,
        ai_explanation=session.ai_explanation,
        status=session.status,
        created_at=session.created_at,
        matched_patterns=[]
    )

@router.post("/{session_id}/audio-chunk", response_model=SessionResponse)
async def process_audio_chunk(
    session_id: uuid.UUID, 
    audio: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Transcribe audio chunk, append to transcript, and re-score session.
    """
    # 1. Retrieve existing session
    stmt = select(FraudSession).where(FraudSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 2. Transcribe Audio
    audio_bytes = await audio.read()
    transcription = await transcribe_audio_chunk(audio_bytes, filename=audio.filename or "chunk.webm")
    
    if not transcription.strip():
        # No text transcribed, just return current state
        pass
    else:
        # 3. Append to transcript
        if session.transcript_text:
            session.transcript_text += " " + transcription.strip()
        else:
            session.transcript_text = transcription.strip()
            
        # 4. Re-score session
        session = await update_session_score(session, db)
        
    # 5. Format matched patterns for response
    matched_patterns = []
    if session.matched_pattern_ids:
        stmt = select(ScamPattern).where(ScamPattern.id.in_(session.matched_pattern_ids))
        result = await db.execute(stmt)
        patterns = result.scalars().all()
        for p in patterns:
            matched_patterns.append(MatchedPattern(
                id=p.id,
                title=p.title,
                category=p.category,
                similarity_score=0.0
            ))
            
    return SessionResponse(
        id=session.id,
        transcript_text=session.transcript_text,
        risk_score=session.risk_score,
        ai_explanation=session.ai_explanation,
        status=session.status,
        created_at=session.created_at,
        matched_patterns=matched_patterns
    )



@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a session and its message history.
    """
    stmt = select(FraudSession).where(FraudSession.id == session_id)
    result = await db.execute(stmt)
    fraud_session = result.scalar_one_or_none()
    
    if not fraud_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.created_at)
    msg_result = await db.execute(msg_stmt)
    messages = msg_result.scalars().all()
    
    matched_patterns = []
    if fraud_session.matched_pattern_ids:
        p_stmt = select(ScamPattern).where(ScamPattern.id.in_(fraud_session.matched_pattern_ids))
        p_result = await db.execute(p_stmt)
        patterns = p_result.scalars().all()
        for p in patterns:
            matched_patterns.append(MatchedPattern(
                id=p.id,
                title=p.title,
                category=p.category,
                similarity_score=0.0
            ))
            
    response = SessionDetailResponse(
        id=fraud_session.id,
        risk_score=fraud_session.risk_score,
        ai_explanation=fraud_session.ai_explanation,
        status=fraud_session.status,
        created_at=fraud_session.created_at,
        matched_patterns=matched_patterns,
        messages=[MessageResponse.model_validate(m) for m in messages]
    )
    return response


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def add_message(session_id: uuid.UUID, message_data: MessageCreate, db: AsyncSession = Depends(get_db)):
    """
    Send a follow-up chat message to the AI assistant for an existing session.
    """
    try:
        ai_msg = await process_followup_message(session_id, message_data, db)
        return MessageResponse.model_validate(ai_msg)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
