import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import FraudSession, ScamPattern
from app.schemas import MatchedPattern

def calculate_similarity_score(distance: float) -> float:
    """
    Clamps the similarity score between 0.0 and 1.0 based on cosine distance.
    Distance 0.0 -> Score 1.0
    Distance 1.0 -> Score 0.0
    Distance 2.0 -> Score 0.0
    """
    return max(0.0, min(1.0, 1.0 - distance))

async def get_matched_patterns_for_session(db: AsyncSession, session: FraudSession) -> List[MatchedPattern]:
    """
    Reads the stored matched_patterns_data JSON from the session, fetches the 
    corresponding ScamPattern models, and rebuilds the ordered list with clamped scores.
    """
    if not session.matched_patterns_data:
        return []
        
    # matched_patterns_data is expected to be a list of dicts: [{"id": "...", "distance": float}, ...]
    data = session.matched_patterns_data
    if not isinstance(data, list):
        return []
        
    pattern_ids = []
    distance_map = {}
    
    for item in data:
        try:
            pid = uuid.UUID(item["id"])
            pattern_ids.append(pid)
            distance_map[pid] = item["distance"]
        except (KeyError, ValueError, TypeError):
            continue
            
    if not pattern_ids:
        return []
        
    stmt = select(ScamPattern).where(ScamPattern.id.in_(pattern_ids))
    result = await db.execute(stmt)
    patterns = result.scalars().all()
    
    # Create a map for quick lookup
    pattern_map = {p.id: p for p in patterns}
    
    matched_patterns = []
    # Re-iterate over pattern_ids to preserve the original sorted order from JSON
    for pid in pattern_ids:
        p = pattern_map.get(pid)
        if p:
            dist = distance_map.get(pid, 1.0)
            score = calculate_similarity_score(dist)
            matched_patterns.append(
                MatchedPattern(
                    id=p.id,
                    title=p.title,
                    category=p.category,
                    similarity_score=score
                )
            )
            
    return matched_patterns
