"""
Embedding service using SentenceTransformers.
Loads the model once in memory and provides async generation.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

from sentence_transformers import SentenceTransformer

# Load the model synchronously at module import so it's ready.
# all-MiniLM-L6-v2 produces 384-dimensional embeddings.
MODEL_NAME = "all-MiniLM-L6-v2"
print(f"Loading embedding model {MODEL_NAME}...")
model = SentenceTransformer(MODEL_NAME)
print("Embedding model loaded.")

# Thread pool for CPU-bound embedding generation
executor = ThreadPoolExecutor(max_workers=4)

async def get_embedding(text: str) -> list[float]:
    """
    Generate an embedding for the given text.
    Runs in a thread pool to avoid blocking the async event loop.
    """
    loop = asyncio.get_running_loop()
    # SentenceTransformer.encode returns a numpy array. We convert to a list of floats.
    embedding = await loop.run_in_executor(
        executor, 
        lambda: model.encode(text).tolist()
    )
    return embedding
