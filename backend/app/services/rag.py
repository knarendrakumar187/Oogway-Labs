import os
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from backend.app.config import settings

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings_matrix: Optional[np.ndarray] = None
        self._is_ready = False

    def initialize(self):
        if self._is_ready:
            return

        logger.info("Initializing RAG Service...")
        # 1. Load SentenceTransformer model
        logger.info("Loading embedding model '%s'...", settings.EMBEDDING_MODEL)
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # 2. Load chunk corpus
        if not os.path.exists(settings.CHUNKS_FILE):
            logger.warning("Chunks file not found at %s. Running ingestion...", settings.CHUNKS_FILE)
            from scripts.ingest import build_knowledge_base
            self.chunks = build_knowledge_base()
        else:
            with open(settings.CHUNKS_FILE, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)

        logger.info("Loaded %d knowledge base chunks.", len(self.chunks))

        # 3. Build numpy matrix for fast cosine similarity
        if self.chunks and "embedding" in self.chunks[0]:
            vectors = [c["embedding"] for c in self.chunks]
            self.embeddings_matrix = np.array(vectors, dtype=np.float32)
            # Ensure normalized
            norms = np.linalg.norm(self.embeddings_matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            self.embeddings_matrix = self.embeddings_matrix / norms
            logger.info("Embeddings matrix ready: shape %s", self.embeddings_matrix.shape)
        
        self._is_ready = True

    def search(self, query: str, top_k: Optional[int] = None) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Perform vector similarity search over chunk index.
        Returns:
            Tuple of (retrieved_chunks, is_grounded)
            is_grounded is False if highest similarity < SIMILARITY_THRESHOLD.
        """
        if not self._is_ready:
            self.initialize()

        k = top_k or settings.TOP_K_CHUNKS

        if self.embeddings_matrix is None or len(self.chunks) == 0:
            return [], False

        # Encode query
        query_vec = self.model.encode(query, normalize_embeddings=True)
        # Dot product against normalized vectors gives cosine similarity [-1, 1]
        scores = np.dot(self.embeddings_matrix, query_vec)

        # Top indices
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        max_score = float(scores[top_indices[0]]) if len(top_indices) > 0 else 0.0

        is_grounded = max_score >= settings.SIMILARITY_THRESHOLD

        if not is_grounded:
            logger.info(
                "Query '%s' top score %.3f below threshold %.3f -> Marked ungrounded",
                query, max_score, settings.SIMILARITY_THRESHOLD
            )

        for idx in top_indices:
            score = float(scores[idx])
            chunk = dict(self.chunks[idx])
            chunk["score"] = round(score, 4)
            # Do not carry raw embedding vector in response
            if "embedding" in chunk:
                del chunk["embedding"]
            results.append(chunk)

        return results, is_grounded

    def get_stats(self) -> Dict[str, Any]:
        if not self._is_ready:
            self.initialize()
        unique_episodes = len(set(c.get("episode_slug", "") for c in self.chunks))
        return {
            "indexed_chunks": len(self.chunks),
            "episodes_indexed": unique_episodes,
            "embedding_dim": 384
        }

rag_service = RAGService()
