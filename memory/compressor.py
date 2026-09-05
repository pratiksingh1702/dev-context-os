"""Token Budget Compressor for Context Injection.

Lifted and adapted from Context Gateway gateway/core/ranker/compressor.py.
Enforces hard tiktoken constraints so recalled memory fits into AI tools' prompts.
"""

from __future__ import annotations

import tiktoken


class ContextCompressor:
    def __init__(self, encoding_name: str = "cl100k_base"):
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        if self.encoding:
            return len(self.encoding.encode(text))
        return len(text.split()) * 2

    def pack_memories(
        self,
        memories: list[dict],
        token_budget: int = 1000,
    ) -> tuple[list[dict], int, int]:
        included = []
        tokens_used = 0
        total_tokens = 0

        for m in memories:
            text = f"[{m.get('category', '').upper()}] {m.get('title', '')}: {m.get('content', '')}"
            t_count = self.count_tokens(text)
            total_tokens += t_count

            if tokens_used + t_count <= token_budget:
                included.append(m)
                tokens_used += t_count

        tokens_saved = max(0, total_tokens - tokens_used)
        return included, tokens_used, tokens_saved
