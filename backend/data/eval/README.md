# Evaluation questions

`questions.jsonl` has one JSON object per line:

| field | meaning |
|---|---|
| `id` | unique number |
| `question` | the question as a user would ask it |
| `answerable` | `true` if the documents contain the answer, `false` if they do not |
| `gold_sections` | sections that contain the answer (any one retrieved counts as a hit). `[]` if unanswerable |
| `gold_answer_points` | facts the answer must contain. Use `a\|b` for alternatives. `[]` if unanswerable |
| `type` | `direct`, `paraphrase`, `multi`, `unanswerable` (far off-topic) or `near_miss` (related topic, but not in the documents) |

**The questions in this folder were written (with AI help) for the fictional demo Act.** They are only there to
prove the harness works. For your real documents, write your own 40-60 questions after reading the law yourself,
including paraphrases and near-miss unanswerable ones. That test set is the most valuable part of the project.
