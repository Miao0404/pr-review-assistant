# Context ablation results

Primary judge: gpt-4.1. Rep 0 runs only unless stated. Judgements with invalid issue ids fixed: 12

## 1. Per condition

| Cond | runs | fail % | recall | precision | findings | used get_file % | input tok | output tok | cost $ | latency s |
|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 27 | 0 | 0.62 | 0.96 | 4.6 | 0 | 4057 | 4701 | 0.055 | 49.8 |
| C1 | 27 | 0 | 0.54 | 0.99 | 4.1 | 0 | 21695 | 4279 | 0.086 | 46.7 |
| C2 | 27 | 0 | 0.49 | 1.00 | 4.0 | 96 | 31912 | 4817 | 0.112 | 54.2 |

PRs where at least one human issue was found, per judge (rep 0, successful runs only):

- gpt-4.1: C0 18/27, C1 15/27, C2 14/27
- gpt-4o-mini: C0 25/27, C1 27/27, C2 27/27
- claude-opus-5-5: C0 14/27, C1 13/27, C2 14/27

## 2. Paired differences (same PR, rep 0)

| Comparison | metric | n pairs | mean diff | 95% bootstrap CI | permutation p | better / worse / tie |
|---|---|---|---|---|---|---|
| C1 - C0 | recall | 27 | -0.086 | [-0.198, +0.000] | 0.255 | 0 / 3 / 24 |
| C1 - C0 | precision | 26 | +0.032 | [-0.019, +0.115] | 1.000 | 1 / 1 / 24 |
| C1 - C0 | n_findings | 27 | -0.407 | [-1.296, +0.333] | 0.446 | 7 / 10 / 10 |
| C1 - C0 | cost_usd | 27 | +0.031 | [+0.011, +0.056] | 0.003 | 21 / 6 / 0 |
| C1 - C0 | latency_s | 27 | -3.130 | [-10.822, +4.293] | 0.445 | 14 / 13 / 0 |
| C2 - C0 | recall | 27 | -0.136 | [-0.296, -0.012] | 0.123 | 1 / 4 / 22 |
| C2 - C0 | precision | 27 | +0.037 | [+0.000, +0.111] | 1.000 | 1 / 0 / 26 |
| C2 - C0 | n_findings | 27 | -0.593 | [-1.111, -0.111] | 0.035 | 5 / 11 / 11 |
| C2 - C0 | cost_usd | 27 | +0.057 | [+0.034, +0.083] | 0.000 | 24 / 3 / 0 |
| C2 - C0 | latency_s | 27 | +4.330 | [-2.663, +12.144] | 0.292 | 17 / 10 / 0 |
| C2 - C1 | recall | 27 | -0.049 | [-0.173, +0.049] | 0.502 | 1 / 2 / 24 |
| C2 - C1 | precision | 26 | +0.006 | [+0.000, +0.019] | 1.000 | 1 / 0 / 25 |
| C2 - C1 | n_findings | 27 | -0.185 | [-0.926, +0.704] | 0.752 | 8 / 13 / 6 |
| C2 - C1 | cost_usd | 27 | +0.026 | [-0.001, +0.054] | 0.085 | 19 / 8 / 0 |
| C2 - C1 | latency_s | 27 | +7.459 | [-0.119, +15.963] | 0.081 | 16 / 11 / 0 |

## 3. Run-to-run noise (repeat subset, 3 runs per condition)

| Cond | PRs with 3 runs | mean within-PR SD of recall | mean abs diff between two runs of the same condition |
|---|---|---|---|
| C0 | 5 | 0.115 | 0.133 |
| C1 | 5 | 0.231 | 0.267 |
| C2 | 5 | 0.115 | 0.133 |

Read: if the paired difference between conditions is not clearly larger than the difference between two runs of the same condition, it is not evidence.

## 4. Judge agreement

### gpt-4.1 vs gpt-4o-mini

Issue matched yes/no: 131 items, agreement 60%, Cohen's kappa 0.03
Finding verdict: 459 items, agreement 93%, Cohen's kappa 0.25

Does the recall conclusion hold under gpt-4o-mini?

- C1 - C0 recall (gpt-4o-mini): +0.074  CI [+0.000, +0.185]  permutation p 0.494  n=27
- C2 - C0 recall (gpt-4o-mini): +0.074  CI [+0.000, +0.185]  permutation p 0.500  n=27
- C2 - C1 recall (gpt-4o-mini): +0.000  CI [+0.000, +0.000]  permutation p 1.000  n=27

### gpt-4.1 vs claude-opus-5-5

Issue matched yes/no: 129 items, agreement 87%, Cohen's kappa 0.73
Finding verdict: 454 items, agreement 64%, Cohen's kappa 0.17

Does the recall conclusion hold under claude-opus-5-5?

- C1 - C0 recall (claude-opus-5-5): -0.012  CI [-0.123, +0.099]  permutation p 1.000  n=27
- C2 - C0 recall (claude-opus-5-5): +0.012  CI [-0.099, +0.123]  permutation p 1.000  n=27
- C2 - C1 recall (claude-opus-5-5): +0.025  CI [-0.123, +0.185]  permutation p 1.000  n=27


Total spend: Anthropic $8.34, judging $2.91