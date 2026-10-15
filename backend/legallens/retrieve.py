"""Retrieve -> (optional) lexical rerank -> support score used for abstention."""
from __future__ import annotations

from dataclasses import dataclass

from .chunking import Chunk
from .index import Index
from .text import tokens

CANDIDATES = 20


@dataclass
class Hit:
    chunk: Chunk
    retrieval_score: float
    coverage: float      # 0..1: share of the question's (idf-weighted) terms this chunk contains
    final_score: float
    rank: int = 0


class Retriever:
    def __init__(self, index: Index):
        self.index = index

    def query_terms(self, question: str) -> list[str]:
        seen: list[str] = []
        for t in tokens(question):
            if t not in seen:
                seen.append(t)
        return seen

    def coverage(self, terms: list[str], chunk_idx: int) -> float:
        """IDF-weighted share of question terms present in the chunk. Terms the corpus has never seen
        count with the maximum weight, so a question about something absent from the corpus scores low."""
        if not terms:
            return 0.0
        idx = self.index
        weights = [idx.bm25.idf.get(t, idx.max_idf) for t in terms]
        present = idx.chunk_sets[chunk_idx]
        uni = sum(w for t, w in zip(terms, weights) if t in present) / sum(weights)
        bigrams = list(zip(terms, terms[1:]))
        bi = (sum(1 for b in bigrams if b in idx.chunk_bigrams[chunk_idx]) / len(bigrams)) if bigrams else uni
        return 0.8 * uni + 0.2 * bi

    def retrieve(self, question: str, mode: str = "hybrid", rerank: bool = True, top_k: int = 5) -> list[Hit]:
        raw = self.index.search(question, mode, CANDIDATES)
        if not raw:
            return []
        terms = self.query_terms(question)
        top = raw[0][1] or 1.0
        hits = []
        for i, score in raw:
            cov = self.coverage(terms, i)
            final = 0.5 * (score / top) + 0.5 * cov if rerank else score
            hits.append(Hit(self.index.chunks[i], score, cov, final))
        if rerank:
            hits.sort(key=lambda h: -h.final_score)
        hits = hits[:top_k]
        for r, h in enumerate(hits, 1):
            h.rank = r
        return hits

    @staticmethod
    def support(hits: list[Hit]) -> float:
        """Best coverage among returned chunks; low means the documents probably do not contain the answer."""
        return max((h.coverage for h in hits), default=0.0)
