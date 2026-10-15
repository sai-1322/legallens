"""Ties ingestion, chunking, indexing, retrieval, abstention and generation together."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from .chunking import chunk_sections
from .config import Settings
from .generate import ABSTAIN_TEXT, Answer, extractive_answer, llm_answer, resolve_mode
from .index import Index
from .ingest import load_sections
from .retrieve import Hit, Retriever
from .text import tokens


@dataclass
class Result:
    question: str
    answer: Answer
    hits: list[Hit]
    support: float
    threshold: float
    retrieval_ms: float
    generation_ms: float
    config: dict[str, Any]


class Pipeline:
    def __init__(self, cfg: Settings, client=None):
        self.cfg = cfg
        self.client = client            # injectable httpx client (tests)
        self.sections = load_sections(cfg.data_dir)
        self._indexes: dict[tuple, Retriever] = {}

    @property
    def documents(self) -> list[str]:
        return sorted({s.doc for s in self.sections})

    def retriever(self, strategy: str | None = None, window: int | None = None) -> Retriever:
        strategy = strategy or self.cfg.chunk_strategy
        window = window or self.cfg.window_words
        key = (strategy, window if strategy == "window" else 0)
        if key not in self._indexes:
            chunks = chunk_sections(self.sections, strategy, window)
            self._indexes[key] = Retriever(Index(chunks, self.cfg.embedder, self.cfg.st_model))
        return self._indexes[key]

    def reload(self) -> None:
        self.sections = load_sections(self.cfg.data_dir)
        self._indexes.clear()

    def n_chunks(self) -> int:
        return len(self.retriever().index.chunks) if self.sections else 0

    def ask(self, question: str, mode: str | None = None, rerank: bool | None = None, top_k: int | None = None,
            strategy: str | None = None, window: int | None = None, generator: str | None = None,
            threshold: float | None = None) -> Result:
        mode = mode or self.cfg.retrieval
        rerank = self.cfg.rerank if rerank is None else rerank
        top_k = top_k or self.cfg.top_k
        threshold = self.cfg.abstain_threshold if threshold is None else threshold
        gen_mode = generator or resolve_mode(self.cfg)
        conf = {"retrieval": mode, "rerank": rerank, "top_k": top_k, "chunking": strategy or self.cfg.chunk_strategy,
                "generator": gen_mode}

        t0 = time.perf_counter()
        if not self.sections or not tokens(question):
            ans = Answer(ABSTAIN_TEXT, [], True, gen_mode)
            return Result(question, ans, [], 0.0, threshold, 0.0, 0.0, conf)
        r = self.retriever(strategy, window)
        hits = r.retrieve(question, mode, rerank, top_k)
        support = r.support(hits)
        t1 = time.perf_counter()

        if support < threshold:
            ans = Answer(ABSTAIN_TEXT, [], True, gen_mode)
        elif gen_mode == "llm":
            ans = llm_answer(question, hits, self.cfg, self.client)
        else:
            ans = extractive_answer(question, hits, r)
        t2 = time.perf_counter()
        return Result(question, ans, hits, support, threshold, (t1 - t0) * 1000, (t2 - t1) * 1000, conf)
