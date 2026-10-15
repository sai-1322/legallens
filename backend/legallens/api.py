"""FastAPI app: /api/* endpoints, plus the built React app served from frontend/dist."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .config import BACKEND_DIR, DISCLAIMER, Settings, get_settings
from .generate import GenerationError, resolve_mode
from .pipeline import Pipeline
from .text import stem

FRONTEND_DIST = BACKEND_DIR.parent / "frontend" / "dist"


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    retrieval: Literal["bm25", "vector", "hybrid"] | None = None
    rerank: bool | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)
    chunking: Literal["section", "window"] | None = None


def _highlight_words(text: str, terms: set[str]) -> list[str]:
    seen: list[str] = []
    for w in re.findall(r"[A-Za-z0-9]+", text):
        if stem(w.lower()) in terms and w.lower() not in seen:
            seen.append(w.lower())
    return seen


def create_app(pipeline: Pipeline | None = None, cfg: Settings | None = None) -> FastAPI:
    cfg = cfg or get_settings()
    pipe = pipeline or Pipeline(cfg)
    if pipe.sections:
        pipe.retriever()  # build the default index now so the first question is fast
    app = FastAPI(title="LegalLens", version=__version__)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET", "POST"],
                       allow_headers=["*"])

    @app.exception_handler(GenerationError)
    async def _gen_error(_req, exc: GenerationError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": __version__, "documents": pipe.documents,
                "sections": len(pipe.sections), "generator": resolve_mode(pipe.cfg), "embedder": pipe.cfg.embedder,
                "disclaimer": DISCLAIMER}

    @app.get("/api/config")
    def config():
        c = pipe.cfg
        return {"retrieval": c.retrieval, "rerank": c.rerank, "top_k": c.top_k, "chunking": c.chunk_strategy,
                "window_words": c.window_words, "abstain_threshold": c.abstain_threshold,
                "generator": resolve_mode(c), "llm_model": c.llm_model if resolve_mode(c) == "llm" else None}

    @app.get("/api/documents")
    def documents():
        out: dict[str, list[dict]] = {}
        for s in pipe.sections:
            out.setdefault(s.doc, []).append({"label": s.label, "heading": s.heading, "words": len(s.body.split())})
        return {"documents": [{"name": k, "sections": v} for k, v in out.items()]}

    @app.post("/api/ask")
    def ask(req: AskRequest):
        if not pipe.sections:
            raise HTTPException(503, f"No documents loaded. Put .txt/.md/.pdf files in {pipe.cfg.data_dir}")
        res = pipe.ask(req.question, mode=req.retrieval, rerank=req.rerank, top_k=req.top_k, strategy=req.chunking)
        r = pipe.retriever(req.chunking)
        terms = set(r.query_terms(req.question))
        return {
            "question": req.question,
            "answer": res.answer.text,
            "abstained": res.answer.abstained,
            "citations": res.answer.citations,
            "support": round(res.support, 3),
            "threshold": res.threshold,
            "generator": res.answer.mode,
            "config": res.config,
            "timing_ms": {"retrieval": round(res.retrieval_ms, 1), "generation": round(res.generation_ms, 1)},
            "sources": [{"rank": h.rank, "label": h.chunk.label, "sections": h.chunk.sections, "doc": h.chunk.doc,
                         "text": h.chunk.text, "retrieval_score": round(h.retrieval_score, 4),
                         "coverage": round(h.coverage, 3), "final_score": round(h.final_score, 4),
                         "highlight": _highlight_words(h.chunk.text, terms)} for h in res.hits],
            "disclaimer": DISCLAIMER,
        }

    @app.post("/api/reindex")
    def reindex():
        pipe.reload()
        if pipe.sections:
            pipe.retriever()
        return {"documents": pipe.documents, "sections": len(pipe.sections), "chunks": pipe.n_chunks()}

    @app.get("/api/eval/results")
    def eval_results():
        path = Path(pipe.cfg.results_dir) / "results.json"
        if not path.exists():
            raise HTTPException(404, "No evaluation results yet. Run: python -m legallens.evaluate")
        return json.loads(path.read_text(encoding="utf-8"))

    if FRONTEND_DIST.exists():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="web")
    return app


app = create_app()
