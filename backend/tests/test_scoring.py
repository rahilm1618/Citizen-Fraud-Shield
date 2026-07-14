import pytest
import uuid
from unittest.mock import patch
from app.utils.scoring import calculate_similarity_score, get_matched_patterns_for_session
from app.services.session_service import update_session_score
from app.services.llm_service import score_transcript
from app.models import ScamPattern, FraudSession
from app.config import settings

@pytest.mark.asyncio
async def test_threshold_filtering_and_boundary(db_session):
    # Setup test patterns with known embedding values
    # all-MiniLM-L6-v2 outputs 384 dimensions
    
    zero_emb = [0.0] * 384
    # Pattern 1: Exact match (distance 0.0) -> Should be kept
    p1 = ScamPattern(title="P1", script_text="T1", embedding=zero_emb)
    # Pattern 2: Boundary (distance exactly settings.rag_similarity_threshold) -> Should be kept
    p2 = ScamPattern(title="P2", script_text="T2", embedding=zero_emb)
    # Pattern 3: Excluded (distance > threshold) -> Should be filtered
    p3 = ScamPattern(title="P3", script_text="T3", embedding=zero_emb)
    
    db_session.add_all([p1, p2, p3])
    await db_session.flush()
    
    # We will mock the DB query response inside update_session_score 
    # to return predefined distances instead of calling real HuggingFace API.
    # We just need to mock the `db.execute(stmt)` result, but a simpler way is to mock 
    # the HuggingFace `get_embedding` to return a known vector, and use DB math.
    # However, mocking the DB return is even safer since we want exact distances.
    
    with patch("app.services.session_service.get_embedding", return_value=zero_emb):
        with patch("app.services.session_service.score_transcript", return_value={"risk_score": 50, "explanation": "", "red_flags": []}):
            session = FraudSession(transcript_text="Test", risk_score=0, ai_explanation="", status="pending")
            db_session.add(session)
            await db_session.flush()
            
            # Since mocking sqlalchemy result is hard, let's mock the db.execute just for that query
            original_execute = db_session.execute
            
            async def mock_execute(stmt):
                # Return predefined (pattern, distance)
                class MockResult:
                    def all(self):
                        return [
                            (p1, 0.0),
                            (p2, settings.rag_similarity_threshold),
                            (p3, settings.rag_similarity_threshold + 0.1)
                        ]
                return MockResult()
                
            db_session.execute = mock_execute
            try:
                updated_session = await update_session_score(session, db_session)
                
                # Check results
                data = updated_session.matched_patterns_data
                assert len(data) == 2, "Should keep exactly two patterns (exact and boundary)"
                
                kept_ids = [d["id"] for d in data]
                assert str(p1.id) in kept_ids
                assert str(p2.id) in kept_ids
                assert str(p3.id) not in kept_ids, "Pattern > threshold should be excluded"
            finally:
                db_session.execute = original_execute


@pytest.mark.asyncio
async def test_empty_matched_patterns_llm_prompt():
    transcript = "I went to buy milk."
    
    with patch("app.services.llm_service._get_openai_client") as MockClient:
        # We simulate what the prompt string is
        # The easiest way is to mock the actual AI call and inspect the prompt sent to it
        with patch("app.services.llm_service._score_transcript_openai") as mock_openai:
            mock_openai.return_value = {"risk_score": 0, "explanation": "ok", "red_flags": []}
            
            # Temporarily set to openai to ensure we hit the mocked path
            original_provider = settings.llm_provider
            settings.llm_provider = "openai"
            
            try:
                # Call with empty matched patterns
                await score_transcript(transcript, [])
                
                # Verify prompt
                args, _ = mock_openai.call_args
                system_prompt = args[0]
                
                assert "No close reference pattern was found." in system_prompt
                assert "Rely on general fraud-detection reasoning rather than a fabricated pattern match." in system_prompt
            finally:
                settings.llm_provider = original_provider

def test_clamping_function():
    # distance = 0.0 -> score = 1.0
    assert calculate_similarity_score(0.0) == 1.0
    
    # distance = 1.0 -> score = 0.0
    assert calculate_similarity_score(1.0) == 0.0
    
    # distance = 2.0 -> score = 0.0
    assert calculate_similarity_score(2.0) == 0.0
    
    # distance = 0.35 -> score = 0.65
    assert abs(calculate_similarity_score(0.35) - 0.65) < 1e-5
