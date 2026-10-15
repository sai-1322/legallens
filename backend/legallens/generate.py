"""Answer generation. 'extractive' needs no model: it quotes the best-matching sentences.
'llm' sends the retrieved passages to a language model and asks for a cited answer (needs an API key or a local server)."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import httpx

from .config import Settings
from .retrieve import Hit, Retriever
from .text import sentences, tokens

ABSTAIN_TEXT = "I couldn't find this in the loaded documents, so I won't guess."
SYSTEM_PROMPT = (
    "You answer questions about legal documents using ONLY the numbered sources provided. "
    "Rules: 1) Use only facts stated in the sources. 2) Cite every claim with its source number like [S1]. "
    "3) If the sources do not contain the answer, reply with exactly NOT_FOUND. 4) Be concise (at most 3 sentences). "
    "5) Never add legal advice or facts from memory."
)


class GenerationError(RuntimeError):
    pass


@dataclass
class Answer:
    text: str
    citations: list[str] = field(default_factory=list)
    abstained: bool = False
    mode: str = "extractive"


def extractive_answer(question: str, hits: list[Hit], retriever: Retriever) -> Answer:
    terms = retriever.query_terms(question)
    idf = retriever.index.bm25.idf
    max_idf = retriever.index.max_idf
    cands = []
    for h in hits[:3]:
        for pos, sent in enumerate(sentences(h.chunk.body)):
            toks = set(tokens(sent))
            if not toks:
                continue
            got = sum(idf.get(t, max_idf) for t in terms if t in toks)
            tot = sum(idf.get(t, max_idf) for t in terms) or 1.0
            score = got / tot + 0.15 * h.coverage - 0.02 * h.rank
            cands.append((score, h.rank, pos, sent, h))
    if not cands:
        return Answer(ABSTAIN_TEXT, [], True, "extractive")
    cands.sort(key=lambda c: -c[0])
    best = cands[0][0]
    top = cands[0]
    # extra sentences come only from the same passage as the best one: pulling them from other
    # sections adds text that shares a few words with the question but answers something else
    chosen = [top] + [c for c in cands[1:] if c[4] is top[4] and c[0] >= 0.6 * best]
    chosen = chosen[:2]
    chosen.sort(key=lambda c: (c[1], c[2]))
    text = " ".join(c[3] for c in chosen)
    cites = []
    for c in chosen:
        if c[4].chunk.label not in cites:
            cites.append(c[4].chunk.label)
    return Answer(text, cites, False, "extractive")


def llm_answer(question: str, hits: list[Hit], cfg: Settings, client: httpx.Client | None = None) -> Answer:
    sources = "\n\n".join(f"[S{i}] ({h.chunk.label}) {h.chunk.text}" for i, h in enumerate(hits, 1))
    user = f"Sources:\n{sources}\n\nQuestion: {question}"
    own = client is None
    client = client or httpx.Client(timeout=30)
    try:
        raw = _call_llm(client, cfg, user)
    finally:
        if own:
            client.close()
    if raw.strip().upper().startswith("NOT_FOUND"):
        return Answer(ABSTAIN_TEXT, [], True, "llm")
    nums = []
    for m in re.finditer(r"\[S(\d+)\]", raw):
        n = int(m.group(1))
        if 1 <= n <= len(hits) and n not in nums:
            nums.append(n)
    return Answer(raw.strip(), [hits[n - 1].chunk.label for n in nums], False, "llm")


def _call_llm(client: httpx.Client, cfg: Settings, user: str, retries: int = 3) -> str:
    if cfg.llm_provider == "anthropic":
        url = f"{cfg.llm_base_url}/v1/messages"
        headers = {"x-api-key": cfg.llm_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {"model": cfg.llm_model, "max_tokens": 500, "temperature": 0, "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user}]}
    else:
        url = f"{cfg.llm_base_url}/chat/completions"
        headers = {"content-type": "application/json"}
        if cfg.llm_api_key:
            headers["authorization"] = f"Bearer {cfg.llm_api_key}"
        body = {"model": cfg.llm_model, "temperature": 0,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]}
    last = ""
    for attempt in range(retries):
        try:
            r = client.post(url, headers=headers, json=body)
            if r.status_code in (429, 500, 502, 503, 529):
                last = f"HTTP {r.status_code}"
                time.sleep(min(2 ** attempt, 8))
                continue
            r.raise_for_status()
            data = r.json()
            if cfg.llm_provider == "anthropic":
                return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            return data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            last = f"{type(e).__name__}: {e}"
            time.sleep(min(2 ** attempt, 8))
    raise GenerationError(f"LLM call failed after {retries} attempts ({last})")


def resolve_mode(cfg: Settings) -> str:
    if cfg.generator == "llm":
        return "llm"
    if cfg.generator == "extractive":
        return "extractive"
    # auto: use an LLM only when one is clearly configured
    if cfg.llm_provider == "anthropic":
        return "llm" if cfg.llm_api_key else "extractive"
    return "llm" if cfg.llm_base_url and _is_set("LLM_BASE_URL") else "extractive"


def _is_set(name: str) -> bool:
    import os
    return bool(os.environ.get(name))
