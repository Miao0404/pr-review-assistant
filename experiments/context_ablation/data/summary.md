# Context ablation results

Primary judge: gpt-4.1. Rep 0 runs only unless stated. Judgements with invalid issue ids fixed: 8

## 1. Per condition

| Cond | runs | fail % | recall | precision | findings | used get_file % | input tok | output tok | cost $ | latency s |
|---|---|---|---|---|---|---|---|---|---|---|
| C0 | 27 | 7 | 0.59 | 0.96 | 4.4 | 0 | 4136 | 4378 | 0.052 | 46.4 |
| C1 | 27 | 4 | 0.52 | 0.99 | 4.0 | 0 | 21646 | 4044 | 0.084 | 44.2 |
| C2 | 27 | 15 | 0.49 | 1.00 | 3.6 | 96 | 28369 | 3826 | 0.095 | 43.5 |

## 2. Paired differences (same PR, rep 0)

| Comparison | metric | n pairs | mean diff | 95% bootstrap CI | permutation p | better / worse / tie |
|---|---|---|---|---|---|---|
| C1 - C0 | recall | 25 | -0.093 | [-0.213, +0.000] | 0.245 | 0 / 3 / 22 |
| C1 - C0 | precision | 24 | +0.035 | [-0.021, +0.125] | 1.000 | 1 / 1 / 22 |
| C1 - C0 | n_findings | 25 | -0.400 | [-1.360, +0.400] | 0.506 | 7 / 9 / 9 |
| C1 - C0 | cost_usd | 25 | +0.032 | [+0.011, +0.058] | 0.006 | 19 / 6 / 0 |
| C1 - C0 | latency_s | 25 | -2.560 | [-10.632, +5.256] | 0.547 | 14 / 11 / 0 |
| C2 - C0 | recall | 23 | -0.159 | [-0.333, -0.014] | 0.123 | 1 / 4 / 18 |
| C2 - C0 | precision | 23 | +0.043 | [+0.000, +0.130] | 1.000 | 1 / 0 / 22 |
| C2 - C0 | n_findings | 23 | -0.435 | [-0.957, +0.043] | 0.158 | 5 / 8 / 10 |
| C2 - C0 | cost_usd | 23 | +0.050 | [+0.028, +0.075] | 0.000 | 20 / 3 / 0 |
| C2 - C0 | latency_s | 23 | +1.687 | [-4.326, +7.791] | 0.603 | 14 / 9 / 0 |
| C2 - C1 | recall | 23 | -0.058 | [-0.188, +0.058] | 0.496 | 1 / 2 / 20 |
| C2 - C1 | precision | 23 | +0.007 | [+0.000, +0.022] | 1.000 | 1 / 0 / 22 |
| C2 - C1 | n_findings | 23 | -0.522 | [-1.130, +0.043] | 0.138 | 6 / 12 / 5 |
| C2 - C1 | cost_usd | 23 | +0.021 | [-0.007, +0.046] | 0.152 | 16 / 7 / 0 |
| C2 - C1 | latency_s | 23 | +4.809 | [-2.126, +11.952] | 0.212 | 13 / 10 / 0 |

## 3. Run-to-run noise (repeat subset, 3 runs per condition)

| Cond | PRs with 3 runs | mean within-PR SD of recall | mean abs diff between two runs of the same condition |
|---|---|---|---|
| C0 | 5 | 0.115 | 0.133 |
| C1 | 5 | 0.231 | 0.267 |
| C2 | 4 | 0.000 | 0.000 |

Read: if the paired difference between conditions is not clearly larger than the difference between two runs of the same condition, it is not evidence.

## 4. Judge agreement

Issue matched yes/no: 118 items, agreement 58%, Cohen's kappa 0.03
Finding verdict: 403 items, agreement 93%, Cohen's kappa 0.28

Does the recall conclusion hold under the second judge?

- C1 - C0 recall (gpt-4o-mini): +0.080  CI [+0.000, +0.200]  n=25
- C2 - C0 recall (gpt-4o-mini): +0.087  CI [+0.000, +0.217]  n=23
- C2 - C1 recall (gpt-4o-mini): +0.000  CI [+0.000, +0.000]  n=23

Total spend: Anthropic $8.40, OpenAI judging $0.40