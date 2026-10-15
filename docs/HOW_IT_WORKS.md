# How it works (study guide)

Read this before putting the project on a CV. Be able to answer these without looking.

## Questions you must be able to answer
1. What is RAG and why not just ask an LLM about the law directly?
2. Why chunk by legal section instead of fixed windows? What did the evaluation say, and how much do you trust it?
3. How does BM25 score a passage? What do k1 and b do?
4. Why does reciprocal-rank fusion combine rankings instead of adding scores?
5. TF-IDF "vectors" are not embeddings. What would real embeddings fix, and what would they not?
6. What is the coverage score and how does it drive refusal? What does it fail to detect?
7. Walk through the threshold trade-off table: what happens when you raise it?
8. Why is hit@5 = 100% meaningless here? When does it become meaningful?
9. What is a Wilson interval and why is it used instead of a normal approximation?
10. Why do the 24 configurations score so similarly, and why did the app default stay unchanged?
11. In LLM mode, what stops the model from inventing law? What does not?
12. What failures can the extractive mode never have, and which can it never avoid?

## Reading order
`ingest.py` -> `chunking.py` -> `index.py` -> `retrieve.py` -> `generate.py` -> `pipeline.py` -> `evaluate.py` -> `api.py` -> `frontend/src/App.tsx`.

## Make it yours (do all of these)
- [ ] Replace the demo Act with a **real** document you have read (an Act, a university rulebook, a company policy).
- [ ] Write 40-60 questions yourself, including paraphrases and near-miss unanswerable ones. No AI for this step.
- [ ] Run the full grid, then read every failure in `results.md` and write what you think caused each.
- [ ] Try `EMBEDDER=st` and report honestly whether paraphrase questions improve.
- [ ] Run LLM mode (`--generator llm`) and compare against extractive on the same questions.
- [ ] Change one design decision (threshold, rerank weights, chunk size) and explain the evaluation change.
- [ ] Rewrite the README "Results" section with your own numbers and your own words.
