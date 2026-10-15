import pytest

from legallens.pipeline import Pipeline


@pytest.mark.parametrize("mode", ["bm25", "vector", "hybrid"])
@pytest.mark.parametrize("rerank", [False, True])
def test_direct_question_retrieves_right_section(pipe, mode, rerank):
    r = pipe.ask("How much notice is needed to increase the rent?", mode=mode, rerank=rerank)
    assert "Section 9" in [h.chunk.label for h in r.hits[:3]]


def test_answer_has_fact_and_citation(pipe):
    r = pipe.ask("How long must the landlord keep rent receipts?")
    assert not r.answer.abstained and "three years" in r.answer.text and r.answer.citations == ["Section 11"]


@pytest.mark.parametrize("q", ["What is the tax rate on cryptocurrency gains?", "How do I register a new company?"])
def test_out_of_scope_questions_abstain(pipe, q):
    r = pipe.ask(q)
    assert r.answer.abstained and r.answer.citations == []


def test_unseen_terms_lower_support(pipe):
    covered = pipe.ask("deposit return days").support
    unseen = pipe.ask("deposit cryptocurrency blockchain").support
    assert unseen < covered


def test_stopword_only_question_abstains(pipe):
    assert pipe.ask("what is the").answer.abstained


def test_empty_corpus_does_not_crash(make_cfg):
    p = Pipeline(make_cfg())
    r = p.ask("anything at all")
    assert r.answer.abstained and r.hits == []


def test_threshold_controls_abstention(pipe):
    q = "How much notice is needed to increase the rent?"
    assert pipe.ask(q, threshold=0.0).answer.abstained is False
    assert pipe.ask(q, threshold=1.01).answer.abstained is True


def test_window_strategy_works(pipe):
    r = pipe.ask("What is the filing fee for a dispute?", strategy="window", window=120)
    assert r.hits and not r.answer.abstained


def test_reload_picks_up_new_files(make_cfg, tmp_path):
    p = Pipeline(make_cfg())
    assert p.documents == []
    (tmp_path / "x.txt").write_text("Section 1. Pets\nPets are allowed with a deposit of ten dollars.")
    p.reload()
    assert p.documents == ["x.txt"] and "ten dollars" in p.ask("What deposit for pets?").answer.text
