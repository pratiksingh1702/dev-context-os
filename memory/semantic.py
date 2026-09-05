"""Semantic Search Engine for Project Memories and Past Bug Fixes.

Uses lightweight embedding similarity to recall relevant ADRs and past decisions.
"""

from __future__ import annotations

import math
from typing import Any


class SemanticMemorySearch:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("BAAI/bge-small-en-v1.5")
            except Exception:
                self._model = None
        return self._model

    def search(
        self,
        query: str,
        memories: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        if not memories:
            return []

        query_terms = set(query.lower().split())

        # If sentence-transformers is available, compute cosine similarity
        if self.model is not None:
            doc_texts = [f"{m['title']} {m['content']} {m['category']}" for m in memories]
            embeddings = self.model.encode([query] + doc_texts, show_progress_bar=False)
            q_emb = embeddings[0]

            scored = []
            for idx, m in enumerate(memories):
                doc_emb = embeddings[idx + 1]
                dot = sum(a * b for a, b in zip(q_emb, doc_emb))
                norm_q = math.sqrt(sum(a * a for a in q_emb))
                norm_d = math.sqrt(sum(b * b for b in doc_emb))
                sim = dot / max(1e-9, norm_q * norm_d)
                scored.append((sim, m))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [item[1] for item in scored[:top_k]]

        # Jaccard + lexical fallback
        scored = []
        for m in memories:
            text = f"{m.get('title', '')} {m.get('content', '')} {m.get('category', '')}".lower()
            text_terms = set(text.split())
            overlap = len(query_terms & text_terms)
            scored.append((overlap, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]
