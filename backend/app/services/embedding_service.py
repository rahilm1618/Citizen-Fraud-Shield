"""
Embedding service using Hugging Face Inference API.
Avoids local PyTorch dependencies and memory overhead.
"""

import logging
from huggingface_hub import AsyncInferenceClient
from app.config import settings

logger = logging.getLogger(__name__)

# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Initialize the async client
client = AsyncInferenceClient(
    model=MODEL_NAME,
    token=settings.hf_api_key if settings.hf_api_key else None
)

async def get_embedding(text: str) -> list[float]:
    """
    Generate an embedding for the given text using Hugging Face Inference API.
    """
    try:
        response = await client.feature_extraction(text)
        
        # HuggingFace API returns nested lists for 1D inputs (e.g., [[float, float, ...]])
        # or numpy arrays if numpy is installed.
        if hasattr(response, "tolist"):
            response = response.tolist()
            
        if isinstance(response, list) and len(response) > 0:
            if isinstance(response[0], list):
                return response[0]
        return response
    except Exception as e:
        logger.error(f"Hugging Face API failed for embedding generation: {e}")
        # Re-raise so the caller handles it, avoiding inserting zero-vectors into the DB
        raise RuntimeError(f"Failed to generate embedding via Hugging Face: {e}") from e
