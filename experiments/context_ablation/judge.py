"""Step 4: judge every successful run, per issue and per finding, with two OpenAI models.

The judge is blind: it never sees which condition produced the review.
  recall    = human issues matched by at least one finding / human issues
  precision = valid findings / (valid + invalid)   ("unverifiable" reported separately)

Run from repo root:  python -m experiments.context_ablation.judge --budget 3.5
"""

import argparse
import json

import openai

from app.core.config import settings
from .common import GT_FILE, JUDGE_FILE, PRS_FILE, RUNS_FILE, append_jsonl, cost_usd, load_json, read_jsonl

JUDGES = ["gpt-4.1", "gpt-4o-mini"]
DIFF_CHARS = 20000  # judge sees the full diff

PROMPT = """You are checking an automated code review of a GitHub pull request against issues that human reviewers raised.

## PR diff
{diff}

## Human issues (ground truth)
{issues}

## Automated review findings
{findings}

Task A. For EACH human issue, decide if at least one finding raises substantially the same problem (same location or mechanism; a vaguer finding that clearly points at the same problem counts). List the matching finding ids.
Task B. For EACH finding, judge whether it is:
  "valid": a real problem or a reasonable, specific improvement for this change (it does not need to match a human issue),
  "invalid": wrong, irrelevant to this change, or generic advice with no concrete basis in the code,
  "unverifiable": it depends on code outside the diff that you cannot see.

Respond with JSON only:
{{"issues": [{{"issue_id": <int>, "matched": <bool>, "finding_ids": [<int>]}}],
  "findings": [{{"finding_id": <int>, "verdict": "valid"|"invalid"|"unverifiable"}}]}}"""


def fmt_diff(pr: dict) -> str:
    text = "\n\n".join(f"### {f['filename']}\n{f['patch']}" for f in pr["files"])
    return text[:DIFF_CHARS]


def fmt_issues(issues: list[dict]) -> str:
    return "\n".join(f"{i['id']}. [{i['file']}] {i['description']}" for i in issues)


def fmt_findings(findings: list[dict]) -> str:
    if not findings:
        return "(no findings)"
    return "\n".join(f"{f['id']}. [{f['file']}] {f['description']} Suggestion: {f['suggestion']}" for f in findings)


def judge_one(client, model: str, pr: dict, issues: list[dict], run: dict) -> dict:
    resp = client.chat.completions.create(
        model=model, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PROMPT.format(
            diff=fmt_diff(pr), issues=fmt_issues(issues), findings=fmt_findings(run["findings"]))}],
    )
    data = json.loads(resp.choices[0].message.content)
    n_issues = len(issues)
    matched = {int(d["issue_id"]) for d in data.get("issues", []) if d.get("matched")}
    verdicts = {d["finding_id"]: d["verdict"] for d in data.get("findings", [])}
    valid = sum(v == "valid" for v in verdicts.values())
    invalid = sum(v == "invalid" for v in verdicts.values())
    unver = sum(v == "unverifiable" for v in verdicts.values())
    return {
        "key": run["key"], "condition": run["condition"], "rep": run["rep"], "judge": model,
        "n_issues": n_issues, "n_findings": len(run["findings"]),
        "matched_issue_ids": sorted(matched), "verdicts": verdicts,
        "recall": len(matched) / n_issues,
        "precision": valid / (valid + invalid) if valid + invalid else None,
        "valid": valid, "invalid": invalid, "unverifiable": unver,
        "cost_usd": round(cost_usd(model, resp.usage.prompt_tokens, resp.usage.completion_tokens), 5),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, required=True, help="max total OpenAI USD for judging")
    args = ap.parse_args()

    client = openai.OpenAI(api_key=settings.openai_api_key)
    prs = {p["key"]: p for p in load_json(PRS_FILE)}
    gt = load_json(GT_FILE)
    runs = [r for r in read_jsonl(RUNS_FILE) if r["status"] == "ok"]
    done_rows = read_jsonl(JUDGE_FILE)
    done = {(r["key"], r["condition"], r["rep"], r["judge"]) for r in done_rows}
    spent = sum(r["cost_usd"] for r in done_rows)

    todo = [(r, j) for r in runs for j in JUDGES if (r["key"], r["condition"], r["rep"], j) not in done]
    print(f"{len(todo)} judgements to do, spent so far ${spent:.2f}")
    for i, (run, j) in enumerate(todo, 1):
        if spent >= args.budget:
            print("Budget reached, stopping.")
            break
        try:
            row = judge_one(client, j, prs[run["key"]], gt[run["key"]], run)
        except Exception as e:
            print(f"[{i}] {run['key']} {run['condition']} {j}: ERROR {e}")
            continue
        append_jsonl(JUDGE_FILE, row)
        spent += row["cost_usd"]
        p = "-" if row["precision"] is None else f"{row['precision']:.2f}"
        print(f"[{i}/{len(todo)}] {run['key']} {run['condition']} rep{run['rep']} {j}: recall={row['recall']:.2f} precision={p}  (total ${spent:.2f})", flush=True)


if __name__ == "__main__":
    main()
