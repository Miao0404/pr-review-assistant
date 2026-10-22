# Context ablation experiment

Question: does giving the review agent more context (search, full files) find more of the issues human reviewers found, and at what cost?

| Condition | Tools |
|---|---|
| C0 | diff only |
| C1 | diff + `search_code` (semantic search over the diff chunks) |
| C2 | diff + `search_code` + `get_file_content` (real file at PR head) |

Same model, prompt template, output schema and PR sample in all conditions.

## Run (Windows, from the repo root, with the project venv)

```powershell
.venv\Scripts\activate

# 1. candidate PRs (GitHub only, free)
python -m experiments.context_ablation.select_prs

# 2. ground truth + final PR sample (target 30, 27 PRs in the final sample; OpenAI, ~$0.2)
python -m experiments.context_ablation.build_ground_truth
#    -> open experiments/context_ablation/data/ground_truth_review.md and spot-check a few PRs

# 3. pilot: 3 PRs x 3 conditions, prints projected full cost
python -m experiments.context_ablation.run_agents --pilot 3 --budget 3

# 4. full run (pilot runs are reused, finished runs are skipped; safe to re-run after a crash)
python -m experiments.context_ablation.run_agents --budget 22

# 5. judging (OpenAI)
python -m experiments.context_ablation.judge --budget 3.5

# 6. analysis
python -m experiments.context_ablation.analyze
```

Outputs are in `experiments/context_ablation/data/`: `summary.md`, `per_run.csv`, raw `runs.jsonl` and `judgements.jsonl`.

## Known limitations (by design)
- Ground truth = issues human reviewers raised. Humans miss things, so "invalid" and recall are relative to them.
- Judge is an LLM. Checked by a second judge model and by human spot-checks, not eliminated.
- The judge sees only the diff, so C2 findings about code outside the diff may be "unverifiable".
- Three Python web libraries only (fastapi, requests, httpx), PRs with at most 5 files.
