import json

import pytest
from fastapi.testclient import TestClient

from conftest import DEMO
from legallens.api import create_app
from legallens.pipeline import Pipeline


@pytest.fixture
def client(make_cfg):
    cfg = make_cfg(data_dir=DEMO)
    return TestClient(create_app(Pipeline(cfg), cfg))


def test_health_and_config(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["sections"] == 32 and h["generator"] == "extractive"
    assert client.get("/api/config").json()["abstain_threshold"] == 0.35


def test_documents(client):
    d = client.get("/api/documents").json()["documents"][0]
    assert d["name"] == "demo_tenancy_act.txt" and d["sections"][0]["label"] == "Preamble"


def test_ask_returns_sources_and_highlights(client):
    r = client.post("/api/ask", json={"question": "How much does it cost to file a dispute?"}).json()
    assert r["sources"] and r["sources"][0]["highlight"] and r["disclaimer"]
    assert set(r["timing_ms"]) == {"retrieval", "generation"}


def test_ask_abstains_off_topic(client):
    r = client.post("/api/ask", json={"question": "What is the speed limit on highways?"}).json()
    assert r["abstained"] and r["citations"] == []


@pytest.mark.parametrize("body", [{"question": "hi"}, {"question": "x" * 501}, {"question": "valid question",
                                  "retrieval": "magic"}, {"question": "valid question", "top_k": 99}, {}])
def test_ask_validation(client, body):
    assert client.post("/api/ask", json=body).status_code == 422


def test_no_documents_gives_503(make_cfg):
    cfg = make_cfg()
    c = TestClient(create_app(Pipeline(cfg), cfg))
    assert c.post("/api/ask", json={"question": "anything here"}).status_code == 503


def test_eval_results_404_then_200(make_cfg):
    cfg = make_cfg(data_dir=DEMO)
    c = TestClient(create_app(Pipeline(cfg), cfg))
    assert c.get("/api/eval/results").status_code == 404
    cfg.results_dir.mkdir(parents=True)
    (cfg.results_dir / "results.json").write_text(json.dumps({"ok": 1}))
    assert c.get("/api/eval/results").json() == {"ok": 1}


def test_reindex(client):
    assert client.post("/api/reindex").json()["chunks"] == 32


def test_llm_failure_is_502(make_cfg, monkeypatch):
    import httpx
    from legallens import generate
    monkeypatch.setattr(generate.time, "sleep", lambda s: None)
    cfg = make_cfg(data_dir=DEMO, generator="llm", llm_api_key="k")
    pipe = Pipeline(cfg, client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))))
    r = TestClient(create_app(pipe, cfg)).post("/api/ask", json={"question": "How long must the landlord keep receipts?"})
    assert r.status_code == 502 and "failed after" in r.json()["detail"]
