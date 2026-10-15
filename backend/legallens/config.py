"""Settings. Everything is overridable by environment variable; defaults run fully offline."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DISCLAIMER = (
    "Educational software. Answers are extracted or generated from the loaded documents and can be wrong "
    "or out of date. This is not legal advice."
)


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    eval_dir: Path
    results_dir: Path
    chunk_strategy: str      # "section" or "window"
    window_words: int
    retrieval: str           # "bm25" | "vector" | "hybrid"
    rerank: bool
    top_k: int
    abstain_threshold: float
    generator: str           # "auto" | "extractive" | "llm"
    llm_provider: str        # "anthropic" | "openai" (any OpenAI-compatible server, e.g. Ollama)
    llm_model: str
    llm_base_url: str
    llm_api_key: str
    embedder: str            # "tfidf" | "st" (sentence-transformers, optional)
    st_model: str


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def get_settings() -> Settings:
    provider = _env("LLM_PROVIDER", "anthropic").lower()
    key = _env("LLM_API_KEY", "") or (_env("ANTHROPIC_API_KEY", "") if provider == "anthropic" else "")
    default_base = "https://api.anthropic.com" if provider == "anthropic" else "http://localhost:11434/v1"
    return Settings(
        data_dir=Path(_env("DATA_DIR", str(BACKEND_DIR / "data" / "raw"))),
        eval_dir=Path(_env("EVAL_DIR", str(BACKEND_DIR / "data" / "eval"))),
        results_dir=Path(_env("RESULTS_DIR", str(BACKEND_DIR / "eval_results"))),
        chunk_strategy=_env("CHUNK_STRATEGY", "section"),
        window_words=int(_env("WINDOW_WORDS", "120")),
        retrieval=_env("RETRIEVAL", "hybrid"),
        rerank=_env("RERANK", "1") not in ("0", "false", "False"),
        top_k=int(_env("TOP_K", "5")),
        abstain_threshold=float(_env("ABSTAIN_THRESHOLD", "0.35")),
        generator=_env("GENERATOR", "auto").lower(),
        llm_provider=provider,
        llm_model=_env("LLM_MODEL", "claude-sonnet-5-5"),
        llm_base_url=_env("LLM_BASE_URL", default_base).rstrip("/"),
        llm_api_key=key,
        embedder=_env("EMBEDDER", "tfidf").lower(),
        st_model=_env("ST_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
    )
