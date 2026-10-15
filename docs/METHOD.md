# Method

## Chunking
- `section`: one chunk per legal section (sections over 250 words are split with overlap).
- `window`: fixed word windows (60/120/250) with 25% overlap, ignoring section boundaries.
A chunk "covers" a section if it holds at least half of the smaller of (the section, the chunk). Evaluation counts a
retrieval hit when a covered section matches a gold section. Larger windows cover more sections, so they get easier
hits; this bias is why hit@k alone is not trusted.

## Retrieval
- **BM25** (k1 1.5, b 0.75) on stemmed tokens with stop-words removed.
- **Vector**: TF-IDF with word bigrams and cosine similarity. This is lexical, not semantic. `EMBEDDER=st` swaps in
  sentence-transformers.
- **Hybrid**: reciprocal-rank fusion of the top 30 of each, score = sum 1/(60 + rank).
- **Rerank** (top 20 candidates): final = 0.5 x (retrieval score / best) + 0.5 x coverage.

## Coverage and refusal
coverage = 0.8 x idf-weighted share of question terms present + 0.2 x share of question bigrams present. Terms the corpus has never
seen count with the maximum weight, so a question about something absent scores low. The pipeline refuses when the best
coverage among the returned passages is below the threshold (default 0.35). Coverage is a support signal, not a probability.

## Answers
- **Extractive**: scores sentences in the top 3 passages by idf-weighted overlap with the question, returns the best one
  (plus a second only from the same passage).
- **LLM**: sends numbered passages with a system prompt that allows only those sources, requires [S#] citations and the
  literal NOT_FOUND when unsupported, temperature 0. Citations are parsed and invalid numbers dropped. 3 attempts with
  backoff on 429/5xx.

## Evaluation metrics
| Metric | Definition |
|---|---|
| hit@k, MRR@5 | gold section among top k retrieved chunks / mean reciprocal rank of the first one |
| correct | answered, and every gold answer point present (bag of stems; `a|b` = alternatives) |
| abstain_ok | unanswerable questions that were refused |
| false_abstain | answerable questions that were refused |
| faithful | share of answer sentences with at least 80% of their words in one retrieved chunk |
| CI | 95% Wilson interval |
Failures are classified: false_abstain, retrieval_miss, ranked_below_top1, answer_incomplete, false_answer.

## Known weaknesses of the evaluation itself
- Gold-point matching is lexical: a correct paraphrased LLM answer can be marked wrong ("twenty-four" vs "24").
- The best configuration is chosen on the same questions it is scored on.
- 40 questions give wide intervals. Differences under about 10 points are noise.
