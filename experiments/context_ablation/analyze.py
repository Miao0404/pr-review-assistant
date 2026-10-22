"""Step 5: summary tables, paired comparisons, noise check, judge agreement. Pure Python, no scipy.

Run from repo root:  python -m experiments.context_ablation.analyze
Writes data/summary.md and data/per_run.csv
"""

import csv
import random
import statistics as st

from .common import CONDITIONS, DATA_DIR, JUDGE_FILE, RUNS_FILE, read_jsonl

PRIMARY, SECONDARY = "gpt-4.1", "gpt-4o-mini"
B = 10000
rng = random.Random(0)
out_lines: list[str] = []


def say(s: str = ""):
    print(s)
    out_lines.append(s)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else float("nan")


def bootstrap_ci(diffs):
    n = len(diffs)
    ms = sorted(st.mean(rng.choices(diffs, k=n)) for _ in range(B))
    return ms[int(0.025 * B)], ms[int(0.975 * B)]


def signflip_p(diffs):
    """Paired permutation test: under H0 each difference is equally likely to be + or -."""
    obs = abs(st.mean(diffs))
    hits = sum(abs(st.mean([d if rng.random() < 0.5 else -d for d in diffs])) >= obs - 1e-12 for _ in range(B))
    return (hits + 1) / (B + 1)


def kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    labels = set(a) | set(b)
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    runs = read_jsonl(RUNS_FILE)
    judg = read_jsonl(JUDGE_FILE)
    # Sanitize: a judge sometimes returns issue ids that do not exist (e.g. finding ids). Drop them.
    n_bad = 0
    for r in judg:
        ids = [i for i in r["matched_issue_ids"] if 1 <= i <= r["n_issues"]]
        n_bad += len(r["matched_issue_ids"]) != len(ids)
        r["matched_issue_ids"] = ids
        r["recall"] = len(ids) / r["n_issues"]
    J = {(r["key"], r["condition"], r["rep"], r["judge"]): r for r in judg}

    # ---------- per-run table ----------
    rows = []
    for r in runs:
        jp = J.get((r["key"], r["condition"], r["rep"], PRIMARY))
        rows.append({
            "key": r["key"], "condition": r["condition"], "rep": r["rep"], "status": r["status"],
            "n_findings": len(r["findings"]), "iterations": r["iterations"],
            "used_get_file": r["tool_calls"].get("get_file_content", 0), "used_search": r["tool_calls"].get("search_code", 0),
            "input_tokens": r["input_tokens"], "output_tokens": r["output_tokens"], "cost_usd": r["cost_usd"],
            "latency_s": r["latency_s"], "invalid_submits": r["invalid_submits"],
            "recall": jp["recall"] if jp else None, "precision": jp["precision"] if jp else None,
            "unverifiable": jp["unverifiable"] if jp else None,
        })
    with open(DATA_DIR / "per_run.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    rep0 = [x for x in rows if x["rep"] == 0]

    say("# Context ablation results")
    say()
    say(f"Primary judge: {PRIMARY}. Rep 0 runs only unless stated. Judgements with invalid issue ids fixed: {n_bad}")
    say()
    say("## 1. Per condition")
    say()
    say("| Cond | runs | fail % | recall | precision | findings | used get_file % | input tok | output tok | cost $ | latency s |")
    say("|---|---|---|---|---|---|---|---|---|---|---|")
    for c in CONDITIONS:
        xs = [x for x in rep0 if x["condition"] == c]
        ok = [x for x in xs if x["status"] == "ok"]
        if not xs:
            continue
        say(f"| {c} | {len(xs)} | {100*(1-len(ok)/len(xs)):.0f} | {mean([x['recall'] for x in ok]):.2f} | "
            f"{mean([x['precision'] for x in ok]):.2f} | {mean([x['n_findings'] for x in ok]):.1f} | "
            f"{100*mean([1 if x['used_get_file'] else 0 for x in ok]):.0f} | {mean([x['input_tokens'] for x in ok]):.0f} | "
            f"{mean([x['output_tokens'] for x in ok]):.0f} | {mean([x['cost_usd'] for x in ok]):.3f} | {mean([x['latency_s'] for x in ok]):.1f} |")

    # ---------- paired comparisons ----------
    say()
    say("## 2. Paired differences (same PR, rep 0)")
    say()
    say("| Comparison | metric | n pairs | mean diff | 95% bootstrap CI | permutation p | better / worse / tie |")
    say("|---|---|---|---|---|---|---|")
    by = {(x["key"], x["condition"]): x for x in rep0 if x["status"] == "ok"}
    for a, b in [("C1", "C0"), ("C2", "C0"), ("C2", "C1")]:
        for m in ["recall", "precision", "n_findings", "cost_usd", "latency_s"]:
            diffs = []
            for (k, c), x in by.items():
                if c != a or (k, b) not in by:
                    continue
                va, vb = x[m], by[(k, b)][m]
                if va is None or vb is None:
                    continue
                diffs.append(va - vb)
            if len(diffs) < 3:
                continue
            lo, hi = bootstrap_ci(diffs)
            p = signflip_p(diffs)
            wins = sum(d > 0 for d in diffs); loss = sum(d < 0 for d in diffs); tie = len(diffs) - wins - loss
            say(f"| {a} - {b} | {m} | {len(diffs)} | {st.mean(diffs):+.3f} | [{lo:+.3f}, {hi:+.3f}] | {p:.3f} | {wins} / {loss} / {tie} |")

    # ---------- noise: same condition vs itself ----------
    say()
    say("## 3. Run-to-run noise (repeat subset, 3 runs per condition)")
    say()
    say("| Cond | PRs with 3 runs | mean within-PR SD of recall | mean abs diff between two runs of the same condition |")
    say("|---|---|---|---|")
    for c in CONDITIONS:
        sds, absd = [], []
        keys = {x["key"] for x in rows if x["condition"] == c and x["rep"] > 0}
        for k in keys:
            vals = [x["recall"] for x in rows if x["key"] == k and x["condition"] == c and x["status"] == "ok" and x["recall"] is not None]
            if len(vals) == 3:
                sds.append(st.stdev(vals))
                absd += [abs(vals[0] - vals[1]), abs(vals[0] - vals[2]), abs(vals[1] - vals[2])]
        if sds:
            say(f"| {c} | {len(sds)} | {st.mean(sds):.3f} | {st.mean(absd):.3f} |")
    say()
    say("Read: if the paired difference between conditions is not clearly larger than the difference between two runs of the same condition, it is not evidence.")

    # ---------- judge agreement ----------
    say()
    say("## 4. Judge agreement")
    say()
    ia, ib, fa, fb = [], [], [], []
    for (k, c, rep, j), r in J.items():
        if j != PRIMARY or (k, c, rep, SECONDARY) not in J:
            continue
        s = J[(k, c, rep, SECONDARY)]
        for iid in range(1, r["n_issues"] + 1):
            ia.append(iid in r["matched_issue_ids"]); ib.append(iid in s["matched_issue_ids"])
        for fid, v in r["verdicts"].items():
            if fid in s["verdicts"]:
                fa.append(v); fb.append(s["verdicts"][fid])
    if ia:
        say(f"Issue matched yes/no: {len(ia)} items, agreement {100*sum(x==y for x,y in zip(ia,ib))/len(ia):.0f}%, Cohen's kappa {kappa(ia, ib):.2f}")
    if fa:
        say(f"Finding verdict: {len(fa)} items, agreement {100*sum(x==y for x,y in zip(fa,fb))/len(fa):.0f}%, Cohen's kappa {kappa(fa, fb):.2f}")

    say()
    say("Does the recall conclusion hold under the second judge?")
    say()
    for a, b in [("C1", "C0"), ("C2", "C0"), ("C2", "C1")]:
        diffs = []
        for (k, c, rep, j), r in J.items():
            if j == SECONDARY and c == a and rep == 0 and (k, b, 0, SECONDARY) in J:
                diffs.append(r["recall"] - J[(k, b, 0, SECONDARY)]["recall"])
        if len(diffs) >= 3:
            lo, hi = bootstrap_ci(diffs)
            say(f"- {a} - {b} recall ({SECONDARY}): {st.mean(diffs):+.3f}  CI [{lo:+.3f}, {hi:+.3f}]  n={len(diffs)}")

    say()
    say(f"Total spend: Anthropic ${sum(r['cost_usd'] for r in runs):.2f}, OpenAI judging ${sum(r['cost_usd'] for r in judg):.2f}")
    (DATA_DIR / "summary.md").write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nWritten {DATA_DIR / 'summary.md'} and per_run.csv")


if __name__ == "__main__":
    main()
