"""Evaluation harness: runs a grid of configurations over a hand-written question set and reports honest metrics.

    python -m legallens.evaluate                # full grid, writes eval_results/results.json + results.md
    python -m legallens.evaluate --quick        # only the default configuration

Metrics (all on the question file you provide):
  hit@k / MRR@5   was a gold section among the top-k retrieved chunks (answerable questions)
  correct         answered (did not abstain) AND the answer contains every gold point
  abstain_ok      unanswerable questions correctly refused
  false_abstain   answerable questions wrongly refused
  faithful        share of answer sentences whose words are found in a single retrieved chunk
  latency         retrieval + generation time
Proportions come with 95% Wilson intervals. With ~40 questions, differences under ~10 points are noise.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import statistics
import time
from datetime import date
from pathlib import Path

from .config import Settings, get_settings
from .pipeline import Pipeline, Result
from .text import sentences, tokens

GRID_CHUNKING = [("section", 0), ("window", 60), ("window", 120), ("window", 250)]
GRID_MODES = ["bm25", "vector", "hybrid"]


# ---------- helpers ----------
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def load_questions(path: Path, known_labels: set[str] | None = None) -> list[dict]:
    qs, seen = [], set()
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        q = json.loads(line)
        for f in ("id", "question", "answerable"):
            if f not in q:
                raise ValueError(f"{path}:{ln} missing field '{f}'")
        if q["id"] in seen:
            raise ValueError(f"{path}:{ln} duplicate id {q['id']}")
        seen.add(q["id"])
        q.setdefault("gold_sections", [])
        q.setdefault("gold_answer_points", [])
        q.setdefault("type", "direct" if q["answerable"] else "unanswerable")
        if q["answerable"] and not q["gold_sections"]:
            raise ValueError(f"{path}:{ln} answerable question needs gold_sections")
        if known_labels is not None:
            bad = [g for g in q["gold_sections"] if g not in known_labels]
            if bad:
                raise ValueError(f"{path}:{ln} gold section(s) {bad} not found in the loaded documents")
        qs.append(q)
    return qs


def points_present(answer: str, points: list[str]) -> tuple[int, int]:
    """How many gold points appear in the answer (bag-of-stems; 'a|b' means either)."""
    atoks = set(tokens(answer))
    got = 0
    for p in points:
        if any(set(tokens(alt)) <= atoks for alt in p.split("|")):
            got += 1
    return got, len(points)


def faithfulness(answer: str, res: Result) -> float | None:
    if res.answer.abstained:
        return None
    clean = re.sub(r"\[S\d+\]", "", answer)
    sents = sentences(clean) or [clean]
    chunk_sets = [set(tokens(h.chunk.text)) for h in res.hits]
    scored = []
    for s in sents:
        st = set(tokens(s))
        if not st:
            continue
        best = max((len(st & cs) / len(st) for cs in chunk_sets), default=0.0)
        scored.append(1.0 if best >= 0.8 else 0.0)
    return sum(scored) / len(scored) if scored else None


# ---------- one configuration ----------
def run_config(pipe: Pipeline, qs: list[dict], chunking: str, window: int, mode: str, rerank: bool,
               threshold: float, generator: str | None = None, top_k: int = 5) -> dict:
    recs = []
    for q in qs:
        res = pipe.ask(q["question"], mode=mode, rerank=rerank, top_k=top_k, strategy=chunking,
                       window=window or None, generator=generator, threshold=threshold)
        rec = {"id": q["id"], "type": q["type"], "answerable": q["answerable"], "question": q["question"],
               "abstained": res.answer.abstained, "support": round(res.support, 3), "answer": res.answer.text,
               "citations": res.answer.citations, "ms": res.retrieval_ms + res.generation_ms}
        gold = set(q["gold_sections"])
        ranks = [h.rank for h in res.hits if gold & set(h.chunk.sections)]
        rec["first_hit_rank"] = min(ranks) if ranks else None
        if q["answerable"]:
            got, tot = points_present(res.answer.text, q["gold_answer_points"])
            rec["points"] = [got, tot]
            rec["correct"] = (not res.answer.abstained) and got == tot
            rec["cited_gold"] = bool(gold & set(res.answer.citations))
        rec["faithful"] = faithfulness(res.answer.text, res)
        recs.append(rec)
    return {"records": recs, "metrics": aggregate(recs)}


def aggregate(recs: list[dict]) -> dict:
    ans = [r for r in recs if r["answerable"]]
    un = [r for r in recs if not r["answerable"]]
    n, m = len(ans), len(un)

    def hit_at(k: int) -> int:
        return sum(1 for r in ans if r["first_hit_rank"] is not None and r["first_hit_rank"] <= k)

    correct = sum(1 for r in ans if r["correct"])
    abst_ok = sum(1 for r in un if r["abstained"])
    false_abs = sum(1 for r in ans if r["abstained"])
    mrr = statistics.fmean([1 / r["first_hit_rank"] if r["first_hit_rank"] else 0.0 for r in ans]) if ans else 0.0
    faith = [r["faithful"] for r in recs if r["faithful"] is not None]
    ms = sorted(r["ms"] for r in recs)
    out = {
        "n_answerable": n, "n_unanswerable": m,
        "hit@1": hit_at(1) / n if n else 0, "hit@3": hit_at(3) / n if n else 0, "hit@5": hit_at(5) / n if n else 0,
        "mrr@5": mrr,
        "correct": correct / n if n else 0,
        "abstain_ok": abst_ok / m if m else None,
        "false_abstain": false_abs / n if n else 0,
        "faithful": statistics.fmean(faith) if faith else None,
        "latency_ms_mean": statistics.fmean(ms) if ms else 0.0,
        "latency_ms_p95": ms[min(len(ms) - 1, int(0.95 * len(ms)))] if ms else 0.0,
        "ci": {"hit@5": wilson(hit_at(5), n), "correct": wilson(correct, n),
               "abstain_ok": wilson(abst_ok, m) if m else None},
    }
    parts = [out["correct"]] + ([out["abstain_ok"]] if out["abstain_ok"] is not None else [])
    out["balanced"] = sum(parts) / len(parts)
    return out


def categorise(rec: dict) -> str | None:
    """Why did this question go wrong? None if it did not."""
    if rec["answerable"]:
        if rec["abstained"]:
            return "false_abstain"
        if rec["correct"]:
            return None
        if rec["first_hit_rank"] is None:
            return "retrieval_miss"
        return "answer_incomplete" if rec["first_hit_rank"] == 1 else "ranked_below_top1"
    return None if rec["abstained"] else "false_answer"


def by_type(recs: list[dict]) -> dict:
    out = {}
    for t in sorted({r["type"] for r in recs}):
        rs = [r for r in recs if r["type"] == t]
        ok = [(r["correct"] if r["answerable"] else r["abstained"]) for r in rs]
        out[t] = {"n": len(rs), "ok": sum(ok), "rate": sum(ok) / len(rs)}
    return out


def threshold_sweep(pipe: Pipeline, qs: list[dict], cfg: dict, generator: str | None) -> list[dict]:
    base = run_config(pipe, qs, cfg["chunking"], cfg["window"], cfg["retrieval"], cfg["rerank"], 0.0, generator)
    rows = []
    for t in [x / 20 for x in range(0, 17)]:
        ans = [r for r in base["records"] if r["answerable"]]
        un = [r for r in base["records"] if not r["answerable"]]
        rows.append({"threshold": t,
                     "false_abstain": sum(1 for r in ans if r["support"] < t) / len(ans) if ans else 0,
                     "correct": sum(1 for r in ans if r["support"] >= t and r["correct"]) / len(ans) if ans else 0,
                     "abstain_ok": sum(1 for r in un if r["support"] < t) / len(un) if un else None})
    return rows


# ---------- full run ----------
def run_grid(pipe: Pipeline, qs: list[dict], threshold: float, generator: str | None, quick: bool = False) -> dict:
    cfg0 = pipe.cfg
    if quick:
        combos = [(cfg0.chunk_strategy, cfg0.window_words if cfg0.chunk_strategy == "window" else 0, cfg0.retrieval, cfg0.rerank)]
    else:
        combos = [(c, w, m, r) for (c, w), m, r in itertools.product(GRID_CHUNKING, GRID_MODES, [False, True])]
    configs = []
    for chunking, window, mode, rerank in combos:
        t0 = time.perf_counter()
        res = run_config(pipe, qs, chunking, window, mode, rerank, threshold, generator)
        cid = f"{chunking}{window or ''}-{mode}-{'rerank' if rerank else 'norerank'}"
        configs.append({"id": cid, "chunking": chunking, "window": window, "retrieval": mode, "rerank": rerank,
                        "metrics": res["metrics"], "records": res["records"],
                        "seconds": round(time.perf_counter() - t0, 2)})
    best = max(configs, key=lambda c: (c["metrics"]["balanced"], c["metrics"]["mrr@5"]))
    failures = []
    for r in best["records"]:
        cat = categorise(r)
        if cat:
            failures.append({"id": r["id"], "type": r["type"], "category": cat, "question": r["question"],
                             "answer": r["answer"], "support": r["support"], "first_hit_rank": r["first_hit_rank"]})
    return {
        "meta": {"date": date.today().isoformat(), "documents": pipe.documents,
                 "n_questions": len(qs), "n_answerable": sum(q["answerable"] for q in qs),
                 "n_unanswerable": sum(not q["answerable"] for q in qs), "threshold": threshold,
                 "generator": generator or "extractive", "embedder": cfg0.embedder, "quick": quick,
                 "note": "Selecting the best config on the same questions inflates its score. Treat differences "
                         "under ~10 points as noise on a set this small."},
        "best_id": best["id"],
        "configs": [{k: v for k, v in c.items() if k != "records"} for c in configs],
        "best_by_type": by_type(best["records"]),
        "best_records": best["records"],
        "failures": failures,
        "threshold_sweep": threshold_sweep(pipe, qs, best, generator),
    }


def to_markdown(rep: dict) -> str:
    m = rep["meta"]
    L = [f"# LegalLens evaluation ({m['date']})", "",
         f"Documents: {', '.join(m['documents'])}  ", f"Questions: {m['n_questions']} "
         f"({m['n_answerable']} answerable, {m['n_unanswerable']} unanswerable). Generator: {m['generator']}. "
         f"Abstain threshold: {m['threshold']}.", "", f"> {m['note']}", "",
         "| config | hit@1 | hit@5 | MRR@5 | correct | abstain ok | false abstain | faithful | ms |",
         "|---|---|---|---|---|---|---|---|---|"]
    pc = lambda v: "n/a" if v is None else f"{v * 100:.0f}%"
    for c in sorted(rep["configs"], key=lambda c: -c["metrics"]["balanced"]):
        x = c["metrics"]
        star = " **(best)**" if c["id"] == rep["best_id"] else ""
        L.append(f"| {c['id']}{star} | {pc(x['hit@1'])} | {pc(x['hit@5'])} | {x['mrr@5']:.2f} | {pc(x['correct'])} | "
                 f"{pc(x['abstain_ok'])} | {pc(x['false_abstain'])} | {pc(x['faithful'])} | {x['latency_ms_mean']:.0f} |")
    L += ["", "## Best configuration by question type", "", "| type | ok / n |", "|---|---|"]
    for t, v in rep["best_by_type"].items():
        L.append(f"| {t} | {v['ok']} / {v['n']} |")
    L += ["", "## Failures of the best configuration", "", "| id | type | category | question |", "|---|---|---|---|"]
    for f in rep["failures"]:
        L.append(f"| {f['id']} | {f['type']} | {f['category']} | {f['question']} |")
    if not rep["failures"]:
        L.append("| | | none | |")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the LegalLens evaluation grid")
    ap.add_argument("--questions", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--generator", choices=["extractive", "llm"], default="extractive")
    ap.add_argument("--threshold", type=float, default=None)
    a = ap.parse_args()
    cfg: Settings = get_settings()
    pipe = Pipeline(cfg)
    if not pipe.sections:
        raise SystemExit(f"No documents found in {cfg.data_dir}. Put .txt/.md/.pdf files there first.")
    labels = {s.label for s in pipe.sections}
    qs = load_questions(a.questions or cfg.eval_dir / "questions.jsonl", labels)
    thr = cfg.abstain_threshold if a.threshold is None else a.threshold
    rep = run_grid(pipe, qs, thr, a.generator, a.quick)
    out = a.out or cfg.results_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    (out / "results.md").write_text(to_markdown(rep), encoding="utf-8")
    print(to_markdown(rep))
    print(f"Wrote {out / 'results.json'}")


if __name__ == "__main__":
    main()
