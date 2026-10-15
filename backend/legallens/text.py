"""Tokenising, stop-words and a deliberately small stemmer (no downloads needed)."""
from __future__ import annotations

import re

STOPWORDS = frozenset("""
a an the and or but if of to in on at by for with from as into than that this these those it its
is are was were be been being am do does did done have has had having can could should would will shall may might
what which who whom whose when where why how there their they them he she his her you your i we our me my
not no any each per also such so very just about over under after before within without upon
tell please explain whats much many long time""".split())

_WORD = re.compile(r"[a-z0-9]+")


def stem(w: str) -> str:
    """Tiny suffix stripper: rents->rent, noticed/notices->notic, returning->return."""
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    for suf in ("ing", "ed", "ly"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    return w


def normalise(text: str) -> str:
    return text.lower().replace("’", "'").replace("'s", "")


def tokens(text: str, keep_stop: bool = False) -> list[str]:
    """Stemmed tokens; stop-words removed unless keep_stop."""
    out = []
    for w in _WORD.findall(normalise(text)):
        if not keep_stop and w in STOPWORDS:
            continue
        out.append(stem(w))
    return out


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.;:])\s+(?=[A-Z\"(])", text.strip())
    return [p.strip() for p in parts if p.strip()]
