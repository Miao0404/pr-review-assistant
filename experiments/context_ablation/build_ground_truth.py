"""Step 2: turn human review comments into a list of concrete issues per PR, and fix the final sample.

An "issue" = something a human reviewer said was wrong or should change in the code.
Questions that only ask for clarification, praise, and pure style nits about wording are dropped.

The first PRs per repo (newest first) that yield >= 1 issue are kept, up to the quota.
Also writes data/ground_truth_review.md so a human can spot-check the extraction.

Run from repo root:  python -m experiments.context_ablation.build_ground_truth
"""

import json

import openai

from app.core.config import settings
from .common import DATA_DIR, GT_FILE, PRS_FILE, REPOS, cost_usd, load_json, save_json

CANDIDATES_FILE = DATA_DIR / "candidates_snapshot.json"  # reviewer-version snapshots (build_snapshots.py)
GT_MODEL = "gpt-4.1"
QUOTA = {"fastapi/fastapi": 10, "psf/requests": 10, "encode/httpx": 10}
TARGET = 30  # if a repo cannot fill its quota, top up from the other repos' remaining candidates, same order

PROMPT = """Below are human code review comments on a GitHub pull request, each with the code hunk it was attached to.

List the distinct ISSUES the reviewers raised. An issue is a concrete problem in the code or a concrete change the reviewer asked for (bug, missing case, wrong behaviour, missing test, API/design concern, performance, security, naming that affects correctness or clarity of the API).
Do NOT list: pure questions that ask for explanation only, praise, agreement, discussion about process (rebase, CI, changelog), or the PR author's own replies.
Merge comments that describe the same issue. Write each issue as one self-contained sentence a third party could check against another review.

PR title: {title}

Comments:
{comments}

Respond with JSON only: {{"issues": [{{"file": "<path>", "description": "<one sentence>"}}]}}
If there is no qualifying issue, return {{"issues": []}}."""


def format_comments(cands: dict) -> str:
    parts = []
    for i, c in enumerate(cands["human_comments"], 1):
        parts.append(f"[{i}] {c['path']} line {c['line']} by {c['author']}\nHunk:\n{c['diff_hunk']}\nComment: {c['body']}")
    return "\n\n".join(parts)


def extract(client, cand: dict) -> tuple[list[dict], float]:
    resp = client.chat.completions.create(
        model=GT_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": PROMPT.format(title=cand["title"], comments=format_comments(cand))}],
    )
    usage = resp.usage
    cost = cost_usd(GT_MODEL, usage.prompt_tokens, usage.completion_tokens)
    issues = json.loads(resp.choices[0].message.content).get("issues", [])
    for i, it in enumerate(issues, 1):
        it["id"] = i
    return issues, cost


def main():
    client = openai.OpenAI(api_key=settings.openai_api_key)
    candidates = [c for c in load_json(CANDIDATES_FILE) if c["repo"] in QUOTA]
    # Rule added before any agent run: the reviewer is for Python code, so only review comments on .py files
    # count as ground truth, and a PR needs at least one changed .py file and one such comment.
    # (Drops dependency bumps and CI/config-only PRs, whose "issues" cannot be found from the diff.)
    kept_c = []
    for c in candidates:
        c["human_comments"] = [h for h in c["human_comments"] if h["path"].endswith(".py")]
        if c["human_comments"] and any(f["filename"].endswith(".py") and f["patch"] for f in c["files"]):
            kept_c.append(c)
    candidates = kept_c
    kept, gt, total_cost = [], {}, 0.0
    counts = {r: 0 for r in REPOS}

    tried = {}

    def consider(cand):
        nonlocal total_cost
        if cand["key"] not in tried:
            issues, cost = extract(client, cand)
            total_cost += cost
            tried[cand["key"]] = issues
            status = f"{len(issues)} issues" if issues else "no issue -> skipped"
            print(f"{cand['key']}: {status}  (spent ${total_cost:.3f})", flush=True)
        issues = tried[cand["key"]]
        if issues:
            kept.append(cand)
            gt[cand["key"]] = issues
            counts[cand["repo"]] += 1

    # pass 1: per-repo quota
    for cand in candidates:
        if counts[cand["repo"]] < QUOTA[cand["repo"]]:
            consider(cand)
    # pass 2: top up to TARGET from leftovers (candidates are newest-first within each repo)
    for cand in candidates:
        if len(kept) >= TARGET:
            break
        if cand["key"] not in gt and (cand["key"] not in tried or tried[cand["key"]]):
            consider(cand)

    save_json(PRS_FILE, kept)
    save_json(GT_FILE, gt)

    lines = ["# Ground truth spot-check", "", "For each PR: do the issues match what the humans actually said?", ""]
    for cand in kept:
        lines.append(f"## {cand['key']}  {cand['title']}")
        lines.append("")
        lines.append("Human comments:")
        for c in cand["human_comments"]:
            lines.append(f"- `{c['path']}` ({c['author']}): {c['body'][:400].replace(chr(10), ' ')}")
        lines.append("")
        lines.append("Extracted issues:")
        for it in gt[cand["key"]]:
            lines.append(f"{it['id']}. `{it['file']}`: {it['description']}")
        lines.append("")
    (DATA_DIR / "ground_truth_review.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\nKept {len(kept)} PRs {counts}. Cost ${total_cost:.3f}")
    print(f"Spot-check file: {DATA_DIR / 'ground_truth_review.md'}")


if __name__ == "__main__":
    main()
