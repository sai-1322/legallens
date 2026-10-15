import json

import pytest

from legallens import evaluate as ev
from conftest import ROOT


def test_wilson_interval_known_values():
    lo, hi = ev.wilson(8, 10)
    assert 0.49 < lo < 0.50 and 0.94 < hi < 0.95
    assert ev.wilson(0, 0) == (0.0, 0.0)
    lo, hi = ev.wilson(10, 10)
    assert hi == 1.0 and lo > 0.7


def test_points_present_with_alternatives_and_stemming():
    assert ev.points_present("Rents are due monthly.", ["rent", "monthly"]) == (2, 2)
    assert ev.points_present("Punished for it", ["punish|retaliation"]) == (1, 1)
    assert ev.points_present("nothing relevant", ["thirty days"]) == (0, 1)


def test_load_questions_validation(tmp_path):
    f = tmp_path / "q.jsonl"
    f.write_text('{"id":1,"question":"q","answerable":true,"gold_sections":["Section 1"]}\n'
                 '{"id":1,"question":"q2","answerable":false}\n')
    with pytest.raises(ValueError, match="duplicate id"):
        ev.load_questions(f)
    f.write_text('{"id":1,"question":"q","answerable":true}\n')
    with pytest.raises(ValueError, match="needs gold_sections"):
        ev.load_questions(f)
    f.write_text('{"id":1,"question":"q","answerable":true,"gold_sections":["Section 99"]}\n')
    with pytest.raises(ValueError, match="not found"):
        ev.load_questions(f, {"Section 1"})
    f.write_text('{"id":1,"question":"q"}\n')
    with pytest.raises(ValueError, match="missing field"):
        ev.load_questions(f)


def test_categorise():
    base = dict(answerable=True, abstained=False, correct=False, first_hit_rank=None)
    assert ev.categorise({**base, "abstained": True}) == "false_abstain"
    assert ev.categorise({**base}) == "retrieval_miss"
    assert ev.categorise({**base, "first_hit_rank": 1}) == "answer_incomplete"
    assert ev.categorise({**base, "first_hit_rank": 3}) == "ranked_below_top1"
    assert ev.categorise({**base, "correct": True}) is None
    assert ev.categorise({"answerable": False, "abstained": False}) == "false_answer"
    assert ev.categorise({"answerable": False, "abstained": True}) is None


def test_aggregate_arithmetic():
    recs = [
        dict(answerable=True, abstained=False, correct=True, first_hit_rank=1, faithful=1.0, ms=1.0),
        dict(answerable=True, abstained=False, correct=False, first_hit_rank=2, faithful=1.0, ms=3.0),
        dict(answerable=True, abstained=True, correct=False, first_hit_rank=None, faithful=None, ms=2.0),
        dict(answerable=False, abstained=True, correct=None, first_hit_rank=None, faithful=None, ms=2.0),
    ]
    m = ev.aggregate(recs)
    assert m["hit@1"] == pytest.approx(1 / 3) and m["hit@3"] == pytest.approx(2 / 3)
    assert m["mrr@5"] == pytest.approx((1 + 0.5 + 0) / 3)
    assert m["correct"] == pytest.approx(1 / 3) and m["abstain_ok"] == 1.0
    assert m["false_abstain"] == pytest.approx(1 / 3)
    assert m["balanced"] == pytest.approx((1 / 3 + 1.0) / 2)


def test_full_grid_on_demo_and_floor(pipe):
    qs = ev.load_questions(ROOT / "data" / "eval" / "questions.jsonl", {s.label for s in pipe.sections})
    rep = ev.run_grid(pipe, qs, pipe.cfg.abstain_threshold, "extractive")
    assert len(rep["configs"]) == 24 and rep["best_id"] in {c["id"] for c in rep["configs"]}
    json.dumps(rep)  # must be serialisable
    best = next(c for c in rep["configs"] if c["id"] == rep["best_id"])["metrics"]
    # regression floor on the demo set (guards against breaking retrieval, not a claim about real law)
    assert best["correct"] >= 0.6 and best["abstain_ok"] >= 0.6 and best["hit@5"] >= 0.9
    assert rep["threshold_sweep"][0]["false_abstain"] == 0.0  # threshold 0 never abstains
    assert "Failures" in ev.to_markdown(rep)
