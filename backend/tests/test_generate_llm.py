import httpx
import pytest

from legallens import generate
from legallens.generate import GenerationError
from legallens.pipeline import Pipeline


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(generate.time, "sleep", lambda s: None)


def llm_pipe(make_cfg, handler, **kw):
    from conftest import DEMO
    cfg = make_cfg(data_dir=DEMO, generator="llm", llm_api_key="test-key", **kw)
    return Pipeline(cfg, client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_anthropic_request_shape_and_citation_parsing(make_cfg):
    seen = {}

    def handler(req: httpx.Request):
        seen["url"], seen["key"] = str(req.url), req.headers["x-api-key"]
        import json
        body = json.loads(req.content)
        seen["system"], seen["user"] = body["system"], body["messages"][0]["content"]
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Ninety days' notice is required [S1]."}]})

    p = llm_pipe(make_cfg, handler)
    r = p.ask("How much notice is needed to increase the rent?")
    assert seen["url"].endswith("/v1/messages") and seen["key"] == "test-key"
    assert "ONLY the numbered sources" in seen["system"] and "[S1]" in seen["user"]
    assert not r.answer.abstained and r.answer.mode == "llm" and len(r.answer.citations) == 1


def test_not_found_becomes_abstention(make_cfg):
    p = llm_pipe(make_cfg, lambda req: httpx.Response(200, json={"content": [{"type": "text", "text": "NOT_FOUND"}]}))
    r = p.ask("How much notice is needed to increase the rent?")
    assert r.answer.abstained


def test_invalid_citation_numbers_are_ignored(make_cfg):
    p = llm_pipe(make_cfg, lambda req: httpx.Response(200, json={"content": [{"type": "text", "text": "Yes [S99] [S1]."}]}))
    r = p.ask("How much notice is needed to increase the rent?")
    assert len(r.answer.citations) == 1


def test_retries_then_succeeds(make_cfg):
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(529, json={"error": "overloaded"})
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok [S1]"}]})

    r = llm_pipe(make_cfg, handler).ask("How much notice is needed to increase the rent?")
    assert calls["n"] == 3 and r.answer.text.startswith("ok")


def test_gives_up_with_clear_error(make_cfg):
    p = llm_pipe(make_cfg, lambda req: httpx.Response(500, json={}))
    with pytest.raises(GenerationError, match="failed after 3 attempts"):
        p.ask("How much notice is needed to increase the rent?")


def test_openai_compatible_shape(make_cfg):
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Thirty days [S1]"}}]})

    p = llm_pipe(make_cfg, handler, llm_provider="openai", llm_base_url="http://localhost:11434/v1")
    r = p.ask("Within how many days must the deposit be returned?")
    assert seen["url"] == "http://localhost:11434/v1/chat/completions" and "Thirty" in r.answer.text


def test_resolve_mode(make_cfg, monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    assert generate.resolve_mode(make_cfg(generator="auto", llm_api_key="")) == "extractive"
    assert generate.resolve_mode(make_cfg(generator="auto", llm_api_key="k")) == "llm"
    assert generate.resolve_mode(make_cfg(generator="extractive", llm_api_key="k")) == "extractive"
