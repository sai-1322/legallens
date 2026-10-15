"""Chunking strategies. 'section' keeps legal sections whole; 'window' slides a fixed word window.

Every chunk records which sections it really covers so retrieval can be scored against gold sections.
A section counts as covered when the chunk contains at least half of the smaller of (section, chunk).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .ingest import Section

MAX_SECTION_WORDS = 250


@dataclass
class Chunk:
    id: int
    doc: str
    text: str                     # what gets indexed and shown (includes heading for section chunks)
    body: str                     # text without the heading (used for answer sentences)
    sections: list[str]           # labels covered, most-covered first
    heading: str = ""
    words: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return self.sections[0] if self.sections else "?"


def _windows(n: int, size: int, overlap: int) -> list[tuple[int, int]]:
    step = max(1, size - overlap)
    spans, start = [], 0
    while start < n:
        spans.append((start, min(n, start + size)))
        if start + size >= n:
            break
        start += step
    return spans


def chunk_sections(sections: list[Section], strategy: str = "section", window_words: int = 120) -> list[Chunk]:
    if strategy == "section":
        return _by_section(sections)
    if strategy == "window":
        return _by_window(sections, window_words)
    raise ValueError(f"unknown chunk strategy: {strategy}")


def _by_section(sections: list[Section]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for s in sections:
        words = s.body.split()
        pieces = [words] if len(words) <= MAX_SECTION_WORDS else [words[a:b] for a, b in _windows(len(words), MAX_SECTION_WORDS, 40)]
        for piece in pieces:
            body = " ".join(piece)
            chunks.append(Chunk(len(chunks), s.doc, f"{s.heading}. {body}", body, [s.label], s.heading, len(piece)))
    return chunks


def _by_window(sections: list[Section], size: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    by_doc: dict[str, list[Section]] = {}
    for s in sections:
        by_doc.setdefault(s.doc, []).append(s)
    for doc, secs in by_doc.items():
        words: list[str] = []
        owner: list[str] = []
        spans: dict[str, int] = {}
        for s in secs:
            w = f"{s.heading}. {s.body}".split()
            words.extend(w)
            owner.extend([s.label] * len(w))
            spans[s.label] = spans.get(s.label, 0) + len(w)
        for a, b in _windows(len(words), size, size // 4):
            counts: dict[str, int] = {}
            for lab in owner[a:b]:
                counts[lab] = counts.get(lab, 0) + 1
            n = b - a
            covered = [lab for lab, c in counts.items() if c >= 0.5 * min(spans[lab], n)]
            covered.sort(key=lambda lab: -counts[lab])
            if not covered:
                covered = [max(counts, key=counts.get)]
            text = " ".join(words[a:b])
            chunks.append(Chunk(len(chunks), doc, text, text, covered, "", n))
    return chunks
