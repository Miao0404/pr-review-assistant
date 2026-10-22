"""Step 3: run the agent under C0 / C1 / C2 on every PR (rep 0), plus reps 1-2 on the repeat subset.

- Run order is shuffled with a fixed seed, so no condition systematically runs earlier or later.
- Every run is appended to data/runs.jsonl immediately; re-running the script skips finished runs.
- Stops before starting a run if the Anthropic spend recorded in runs.jsonl has reached --budget.

Run from repo root:
  python -m experiments.context_ablation.run_agents --pilot 3 --budget 3     # pilot: 3 PRs x 3 conditions
  python -m experiments.context_ablation.run_agents --budget 22              # full run
"""

import argparse
import random
import statistics
from datetime import datetime

from .agent import review
from .common import CONDITIONS, PRS_FILE, RUNS_FILE, SEED, append_jsonl, load_json, read_jsonl, repeat_subset


def plan(prs: list[dict], pilot: int | None, repeats: int = 10) -> list[tuple[str, str, int]]:
    if pilot:
        keys = [p["key"] for p in prs]
        rng = random.Random(SEED + 1)
        chosen = rng.sample(keys, min(pilot, len(keys)))
        runs = [(k, c, 0) for k in chosen for c in CONDITIONS]
    else:
        rep_keys = repeat_subset(prs, repeats)
        runs = [(p["key"], c, 0) for p in prs for c in CONDITIONS]
        runs += [(k, c, r) for k in rep_keys for c in CONDITIONS for r in (1, 2)]
    random.Random(SEED).shuffle(runs)
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, required=True, help="max total Anthropic USD across all runs in runs.jsonl")
    ap.add_argument("--pilot", type=int, default=None, help="only run N PRs x 3 conditions")
    ap.add_argument("--repeats", type=int, default=10, help="number of PRs in the noise check (3 runs each)")
    args = ap.parse_args()

    prs = {p["key"]: p for p in load_json(PRS_FILE)}
    done_rows = read_jsonl(RUNS_FILE)
    done = {(r["key"], r["condition"], r["rep"]) for r in done_rows}
    spent = sum(r["cost_usd"] for r in done_rows)

    todo = [r for r in plan(list(prs.values()), args.pilot, args.repeats) if r not in done]
    print(f"{len(todo)} runs to do, {len(done)} already done, spent so far ${spent:.2f}, budget ${args.budget:.2f}\n")

    for i, (key, cond, rep) in enumerate(todo, 1):
        if spent >= args.budget:
            print(f"\nBudget reached (${spent:.2f}). Stopping. Re-run with a higher --budget to continue.")
            break
        print(f"[{i}/{len(todo)}] {key} {cond} rep{rep} ...", end=" ", flush=True)
        rec = review(prs[key], cond)
        rec.update({"key": key, "condition": cond, "rep": rep, "timestamp": datetime.now().isoformat(timespec="seconds")})
        append_jsonl(RUNS_FILE, rec)
        spent += rec["cost_usd"]
        msg = f"{rec['status']} findings={len(rec['findings'])} iters={rec['iterations']} ${rec['cost_usd']:.3f} {rec['latency_s']}s"
        print(msg + (f"  ERR {rec['error'][:120]}" if rec["error"] else "") + f"  (total ${spent:.2f})", flush=True)

    rows = read_jsonl(RUNS_FILE)
    print("\nCost per run by condition (all runs so far):")
    for c in CONDITIONS:
        costs = [r["cost_usd"] for r in rows if r["condition"] == c]
        if costs:
            print(f"  {c}: n={len(costs)} mean ${statistics.mean(costs):.3f}  max ${max(costs):.3f}")
    if args.pilot:
        per_pr = sum(statistics.mean([r["cost_usd"] for r in rows if r["condition"] == c] or [0]) for c in CONDITIONS)
        n_prs = len(prs)
        full = per_pr * n_prs + per_pr * 2 * min(10, n_prs)
        print(f"\nEstimated cost per PR (all 3 conditions): ${per_pr:.3f}")
        print(f"Projected full run ({n_prs} PRs + repeats): ${full:.2f}")


if __name__ == "__main__":
    main()
