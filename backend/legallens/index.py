"""Search indexes: BM25, a vector index (TF-IDF by default, sentence-transformers optional) and hybrid fusion."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np

from .chunking import Chunk
from .text import tokens


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.lens = np.array([len(d) for d in docs], dtype=float)
        self.avg = float(self.lens.mean()) if self.n else 0.0
        self.tf: list[Counter] = [Counter(d) for d in docs]
        df: Counter = Counter()
        for c in self.tf:
            df.update(c.keys())
        self.idf = {t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.post: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.tf):
            for t in c:
                self.post[t].append(i)

    def scores(self, query: list[str]) -> np.ndarray:
        s = np.zeros(self.n)
        for t in set(query):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i in self.post[t]:
                f = self.tf[i][t]
                s[i] += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg))
        return s


class TfidfVectors:
    """Sparse TF-IDF with word bigrams. Lexical, not semantic: see README for the honest comparison."""
    name = "tfidf"

    def __init__(self, texts: list[str]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vec = TfidfVectorizer(tokenizer=tokens, lowercase=False, token_pattern=None,
                                   ngram_range=(1, 2), sublinear_tf=True)
        self.mat = self.vec.fit_transform(texts)

    def scores(self, query: str) -> np.ndarray:
        q = self.vec.transform([query])
        return np.asarray((self.mat @ q.T).todense()).ravel()


class SentenceTransformerVectors:
    """Optional dense embeddings (pip install sentence-transformers). Downloads the model on first use."""
    name = "st"

    def __init__(self, texts: list[str], model: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model)
        self.mat = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def scores(self, query: str) -> np.ndarray:
        q = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return self.mat @ q


def _top(scores: np.ndarray, k: int) -> list[tuple[int, float]]:
    order = np.argsort(-scores, kind="stable")[:k]
    return [(int(i), float(scores[i])) for i in order if scores[i] > 0]


class Index:
    RRF_K = 60

    def __init__(self, chunks: list[Chunk], embedder: str = "tfidf", st_model: str = ""):
        self.chunks = chunks
        self.chunk_tokens = [tokens(c.text) for c in chunks]
        self.chunk_sets = [set(t) for t in self.chunk_tokens]
        self.chunk_bigrams = [set(zip(t, t[1:])) for t in self.chunk_tokens]
        self.bm25 = BM25(self.chunk_tokens)
        texts = [c.text for c in chunks]
        self.vectors = SentenceTransformerVectors(texts, st_model) if embedder == "st" else TfidfVectors(texts)
        self.max_idf = max(self.bm25.idf.values(), default=1.0)

    def search(self, query: str, mode: str, k: int = 20) -> list[tuple[int, float]]:
        if not self.chunks:
            return []
        if mode == "bm25":
            return _top(self.bm25.scores(tokens(query)), k)
        if mode == "vector":
            return _top(self.vectors.scores(query), k)
        if mode == "hybrid":
            fused: dict[int, float] = defaultdict(float)
            for ranked in (_top(self.bm25.scores(tokens(query)), 30), _top(self.vectors.scores(query), 30)):
                for rank, (i, _) in enumerate(ranked):
                    fused[i] += 1.0 / (self.RRF_K + rank + 1)
            return sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        raise ValueError(f"unknown retrieval mode: {mode}")
