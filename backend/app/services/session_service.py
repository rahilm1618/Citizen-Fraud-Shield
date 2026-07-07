import uuid

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScamPattern, FraudSession, SessionMessage
from app.schemas import SessionCreate, SessionResponse, MatchedPattern, MessageCreate, MessageResponse
from app.services.embedding_service import get_embedding
from app.services.llm_service import score_transcript, answer_followup


async def create_live_session(db: AsyncSession) -> FraudSession:
    """Creates a blank session for live audio."""
    new_session = FraudSession(
        transcript_text="",
        risk_score=0,
        ai_explanation="",
        status="pending"
    )
    db.add(new_session)
    await db.flush()
    return new_session


async def update_session_score(session: FraudSession, db: AsyncSession) -> FraudSession:
    """Runs the scoring pipeline (embedding, search, LLM) on an existing session."""
    transcript = session.transcript_text
    
    if not transcript.strip():
        # Empty transcript, skip LLM calls
        return session
        
    transcript_emb = await get_embedding(transcript)
    session.embedding = transcript_emb
    
    stmt = (
        select(ScamPattern)
        .order_by(ScamPattern.embedding.cosine_distance(transcript_emb))
        .limit(5)
    )
    result = await db.execute(stmt)
    top_patterns = result.scalars().all()
    
    matched_patterns_dicts = []
    matched_pattern_ids = []
    for pattern in top_patterns:
        matched_patterns_dicts.append({
            "id": str(pattern.id),
            "title": pattern.title,
            "category": pattern.category,
            "script_text": pattern.script_text,
        })
        matched_pattern_ids.append(pattern.id)
        
    session.matched_pattern_ids = matched_pattern_ids
    
    llm_result = await score_transcript(transcript, matched_patterns_dicts)
    session.risk_score = llm_result.get("risk_score", 0)
    session.ai_explanation = llm_result.get("explanation", "No explanation provided.")
    session.status = "flagged"
    
    await db.flush()
    return session


async def process_new_session(session_data: SessionCreate, db: AsyncSession) -> FraudSession:
    # 1. Create the session
    new_session = FraudSession(
        transcript_text=session_data.transcript_text,
        risk_score=0,
        ai_explanation="",
        status="flagged"
    )
    db.add(new_session)
    await db.flush()
    
    # 2. Run the scoring pipeline
    session = await update_session_score(new_session, db)
    
    # 3. Extract entities for the final transcript
    from app.services.entity_service import extract_entities, upsert_entities
    if session.transcript_text:
        extracted_entities = await extract_entities(session.transcript_text)
        if extracted_entities:
            await upsert_entities(session.id, extracted_entities, db)
            await db.flush()
            
    return session


async def process_followup_message(session_id: uuid.UUID, message_data: MessageCreate, db: AsyncSession) -> SessionMessage:
    # 1. Retrieve the session and previous messages
    stmt = select(FraudSession).where(FraudSession.id == session_id)
    result = await db.execute(stmt)
    fraud_session = result.scalar_one_or_none()
    
    if not fraud_session:
        raise ValueError("Session not found")
        
    msg_stmt = select(SessionMessage).where(SessionMessage.session_id == session_id).order_by(SessionMessage.created_at)
    msg_result = await db.execute(msg_stmt)
    past_messages = msg_result.scalars().all()
    
    # 2. Save the user's new message
    user_msg = SessionMessage(
        session_id=session_id,
        role="user",
        content=message_data.content
    )
    db.add(user_msg)
    
    # 3. Format history for LLM
    chat_history = [{"role": m.role, "content": m.content} for m in past_messages]
    
    # 4. Call LLM for answer
    ai_reply_text = await answer_followup(
        transcript=fraud_session.transcript_text,
        risk_score=fraud_session.risk_score,
        explanation=fraud_session.ai_explanation,
        chat_history=chat_history,
        new_message=message_data.content
    )
    
    # 5. Save assistant's reply
    ai_msg = SessionMessage(
        session_id=session_id,
        role="assistant",
        content=ai_reply_text
    )
    db.add(ai_msg)
    await db.flush()
    
    return ai_msg
