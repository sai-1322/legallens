# LegalLens

Ask questions about legal documents in plain English and get a **cited answer**, or an honest "I couldn't find this".
Full stack (FastAPI + React) with a built-in **evaluation harness** that measures how often it is right, how often it
wrongly refuses, and where it fails.

> **Built with AI assistance (Claude).** I used it to write the first version and am studying it with
> [`docs/HOW_IT_WORKS.md`](docs/HOW_IT_WORKS.md). The bundled law and test questions are **fictional demo data**
> (see "Status").

## Why this exists

Most RAG demos show one good answer. This one is built around the question hiring managers actually ask: *how do you
know it works?* Every retrieval and chunking choice is compared on a question set, with confidence intervals,
failure categories, and a refusal threshold you can see the trade-off of.

## What it does

- **Ingest** `.txt`, `.md`, `.pdf`; split at headings like "Section 9." so every passage knows its section.
- **Chunk** by legal section, or by fixed word windows (compared in the evaluation).
- **Retrieve** with BM25, TF-IDF vectors, or both fused (reciprocal-rank fusion), then an optional lexical rerank.
- **Refuse** when the best passage covers too little of the question's key terms (a tunable threshold).
- **Answer** two ways: *extractive* (quotes the best sentences, no model, works offline) or *LLM* (Anthropic or any
  OpenAI-compatible server such as Ollama), told to cite sources or reply NOT_FOUND.
- **Evaluate**: 24 configurations (4 chunkings x 3 retrievers x rerank on/off) on your question file.

## Status (read before putting this on a CV)

| Part | State |
|---|---|
| Backend, evaluation harness, React UI | Built. **48 tests pass**; I broke the abstention logic on purpose to confirm the tests catch it. UI checked in a headless browser (desktop + mobile) |
| Demo corpus | **A fictional "Demo Residential Tenancy Act"**, written for testing. It is not real law |
| Demo questions (40) | Written with AI help *alongside* the fictional Act, so the numbers below are **optimistic**. Replace with your own questions on real documents |
| LLM mode (Anthropic / OpenAI-compatible) | Request/response handling, retries and error paths are **tested against a mocked server**. It has **never been run against a real LLM API** |
| Neural embeddings (`EMBEDDER=st`) | Optional code path, **not run** (no model download in the build environment) |

## Results on the demo set (extractive answers, default config)

Default config: section chunks, hybrid retrieval, rerank on. 31 answerable + 9 unanswerable questions.

| Metric | Result | 95% CI |
|---|---|---|
| Correct answers (answered and contains every gold fact) | 71% | 53-84% |
| Unanswerable questions correctly refused | 78% | 45-94% |
| Answerable questions wrongly refused | 16% | |
| Right section ranked #1 | 81% | |
| Right section in top 5 | 100% | 89-100% |

What this does and does not tell you:

- **All 24 configurations land within a narrow band** (correct 61-71%, refused-ok 78-89%). With 40 questions one question
  is about 3 points, so the ranking between configs is mostly noise. I deliberately did *not* switch the default to
  whichever config scored best, because that would be tuning on the test set.
- **Hit@5 is 100% everywhere because the corpus has only 32 chunks.** It becomes meaningful only on a real corpus.
- **Paraphrases are the weak spot** (4 of 7 correct vs 18 of 23 for direct wording): keyword and TF-IDF search miss
  "flat" vs "dwelling" and "cost" vs "fee". Neural embeddings are the natural next experiment.
- **Near-miss unanswerable questions** (related topic, answer absent) sometimes get a confident wrong answer. That is
  the hardest failure for a legal tool and the evaluation tab lists each one.
- **Faithfulness is 100% by construction** in extractive mode (it only quotes). It matters in LLM mode.
- The refusal threshold (35%) was picked by hand after glancing at a few examples, not fitted to the whole set. The
  evaluation tab shows the full trade-off table.

## Run it

```bash
# backend (offline, no API key needed)
cd backend
pip install -r requirements.txt
python -m uvicorn legallens.api:app --port 8000

# frontend: build once and FastAPI serves it at http://localhost:8000
cd ../frontend && npm install && npm run build
# or for development:  npm run dev   (http://localhost:5173, proxies /api to :8000)

# evaluation (writes backend/eval_results/results.json and results.md, shown in the UI's Evaluation tab)
cd ../backend && python -m legallens.evaluate            # full 24-config grid
python -m legallens.evaluate --quick                     # default config only

# tests
python -m pytest
```

Docker: `docker build -t legallens . && docker run -p 8000:8000 legallens`

### Use your own documents
1. Put `.txt`, `.md` or `.pdf` files in `backend/data/raw/` (remove the demo Act). Headings must look like
   `Section 12. Title` (also `Article`, `Rule`, `Regulation`).
2. Write **your own** questions in `backend/data/eval/questions.jsonl` (format in `backend/data/eval/README.md`).
   The harness checks that every `gold_sections` label exists in your documents.
3. Restart the API (or `POST /api/reindex`) and run `python -m legallens.evaluate`.

### Use a language model (optional)
```bash
export ANTHROPIC_API_KEY=...                 # GENERATOR=auto switches to LLM mode when a key is present
# or a local OpenAI-compatible server, e.g. Ollama:
export LLM_PROVIDER=openai LLM_BASE_URL=http://localhost:11434/v1 LLM_MODEL=llama3.2
python -m legallens.evaluate --generator llm  # compare LLM vs extractive on the same questions
```
Retrieved passages are sent to the model provider you configure. Do not load confidential documents unless that is acceptable.

### Neural embeddings (optional)
`pip install sentence-transformers` then `EMBEDDER=st`. Downloads a model on first run.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Loaded documents, generator mode |
| `GET /api/config` | Active defaults |
| `GET /api/documents` | Sections per document |
| `POST /api/ask` | `{question, retrieval?, rerank?, top_k?, chunking?}` returns answer, citations, support score, sources |
| `POST /api/reindex` | Reload documents from disk |
| `GET /api/eval/results` | Last evaluation run |

Input is validated (3-500 characters; enums for options). A failing LLM call returns **502**, never a silent fallback.

## Layout

```
backend/legallens/  ingest.py chunking.py index.py retrieve.py generate.py pipeline.py evaluate.py api.py
backend/tests/      48 tests (retrieval, abstention, mocked LLM, metrics arithmetic, API)
backend/data/       raw/ (documents), eval/ (questions)
frontend/src/       Ask, Evaluation and How-it-works tabs
docs/               METHOD.md, HOW_IT_WORKS.md (study guide)
```

## Limitations

- Lexical retrieval misses paraphrases; the refusal rule is a heuristic, not a guarantee.
- It knows only the loaded text: no amendments, case law or other statutes.
- No authentication or rate limiting: do not expose it publicly as is.
- Not legal advice.

## Roadmap

Real-corpus evaluation with your own questions, neural embeddings and a cross-encoder reranker, an LLM-as-judge
faithfulness check compared against hand labels, upload endpoint, query logging for failure analysis.
