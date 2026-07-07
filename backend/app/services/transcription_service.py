import logging
import io
from app.config import settings
from app.services.llm_service import _get_groq_client

logger = logging.getLogger(__name__)

async def transcribe_audio_chunk(audio_bytes: bytes, filename: str = "chunk.webm") -> str:
    """
    Transcribes an audio chunk using Groq's Whisper endpoint.
    """
    client = _get_groq_client()
    try:
        # We need a file-like object with a name for the SDK
        file_tuple = (filename, audio_bytes)
        
        response = await client.audio.transcriptions.create(
            file=file_tuple,
            model="whisper-large-v3",
            response_format="text",
            language="en" # Force English for consistent fraud analysis, or remove for auto-detect
        )
        return response
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return ""
