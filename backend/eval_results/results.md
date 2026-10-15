# LegalLens evaluation (2026-10-15)

Documents: demo_tenancy_act.txt  
Questions: 40 (31 answerable, 9 unanswerable). Generator: extractive. Abstain threshold: 0.35.

> Selecting the best config on the same questions inflates its score. Treat differences under ~10 points as noise on a set this small.

| config | hit@1 | hit@5 | MRR@5 | correct | abstain ok | false abstain | faithful | ms |
|---|---|---|---|---|---|---|---|---|
| window120-vector-norerank **(best)** | 87% | 100% | 0.93 | 71% | 89% | 16% | 100% | 1 |
| window120-bm25-norerank | 84% | 100% | 0.91 | 68% | 89% | 16% | 100% | 0 |
| window120-bm25-rerank | 84% | 100% | 0.91 | 68% | 89% | 16% | 100% | 0 |
| window120-vector-rerank | 84% | 100% | 0.91 | 68% | 89% | 16% | 100% | 1 |
| window120-hybrid-norerank | 84% | 100% | 0.91 | 68% | 89% | 16% | 100% | 1 |
| window120-hybrid-rerank | 84% | 100% | 0.91 | 68% | 89% | 16% | 100% | 1 |
| window250-bm25-norerank | 90% | 100% | 0.95 | 68% | 89% | 13% | 100% | 1 |
| window250-bm25-rerank | 90% | 100% | 0.95 | 68% | 89% | 13% | 100% | 0 |
| window250-vector-norerank | 97% | 100% | 0.98 | 68% | 89% | 13% | 100% | 1 |
| window250-vector-rerank | 97% | 100% | 0.98 | 68% | 89% | 13% | 100% | 1 |
| window250-hybrid-norerank | 94% | 100% | 0.97 | 68% | 89% | 13% | 100% | 1 |
| window250-hybrid-rerank | 90% | 100% | 0.95 | 68% | 89% | 13% | 100% | 1 |
| window60-bm25-norerank | 77% | 100% | 0.86 | 65% | 89% | 16% | 100% | 0 |
| window60-bm25-rerank | 77% | 100% | 0.86 | 65% | 89% | 16% | 100% | 0 |
| window60-hybrid-norerank | 77% | 100% | 0.87 | 65% | 89% | 16% | 100% | 1 |
| window60-hybrid-rerank | 77% | 100% | 0.87 | 65% | 89% | 16% | 100% | 1 |
| window60-vector-norerank | 71% | 100% | 0.84 | 61% | 89% | 16% | 100% | 1 |
| window60-vector-rerank | 71% | 100% | 0.84 | 61% | 89% | 16% | 100% | 1 |
| section-bm25-norerank | 77% | 100% | 0.86 | 71% | 78% | 16% | 100% | 22 |
| section-bm25-rerank | 77% | 100% | 0.87 | 71% | 78% | 16% | 100% | 0 |
| section-hybrid-norerank | 74% | 100% | 0.85 | 71% | 78% | 16% | 100% | 1 |
| section-hybrid-rerank | 81% | 100% | 0.89 | 71% | 78% | 16% | 100% | 1 |
| section-vector-norerank | 71% | 100% | 0.83 | 68% | 78% | 16% | 100% | 1 |
| section-vector-rerank | 74% | 100% | 0.85 | 68% | 78% | 16% | 100% | 1 |

## Best configuration by question type

| type | ok / n |
|---|---|
| direct | 18 / 23 |
| multi | 0 / 1 |
| near_miss | 4 / 5 |
| paraphrase | 4 / 7 |
| unanswerable | 4 / 4 |

## Failures of the best configuration

| id | type | category | question |
|---|---|---|---|
| 4 | direct | false_abstain | Within how many days must the deposit be returned after the tenant moves out? |
| 8 | direct | false_abstain | How often can the rent be raised? |
| 20 | direct | answer_incomplete | What compensation can a tenant get if the landlord changes the locks without a tribunal order? |
| 21 | paraphrase | false_abstain | What happens to the tenancy when the tenant dies? |
| 23 | direct | answer_incomplete | How much does it cost to file a dispute? |
| 24 | direct | ranked_below_top1 | How long does the Tribunal take to decide a dispute? |
| 26 | multi | answer_incomplete | What is the fine for a landlord who demands an excessive deposit? |
| 27 | paraphrase | false_abstain | My landlord raised my rent by 25 percent. Is that allowed? |
| 31 | paraphrase | false_abstain | Can the landlord come into my flat without telling me? |
| 37 | near_miss | false_answer | What is the maximum rent a landlord can charge in this state? |
