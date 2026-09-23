#!/usr/bin/env python3
"""
Evaluation script for PR Review Assistant (baseline).
Finds PRs with human reviews, runs the agent, uses Claude as judge.
Results saved to eval_results_<timestamp>.csv
"""

import csv
import json
import time
from datetime import datetime

import anthropic
import openai
from github import Github

from app.core.config import settings
from app.github.client import get_pr_files
from app.agent.reviewer import review_pr

TARGET_REPOS = [
    "fastapi/fastapi",
    "psf/requests",
    "encode/httpx",
    "pallets/flask",
]

JUDGE_PROMPT = """You are evaluating an AI code review agent's output quality.

## PR Diff (changed files)
{diff}

## Human Review Comments
{human_review}

## Agent Review Output
{agent_review}

Score on three dimensions (1-5):
- coverage: How well did the agent cover issues the human reviewers mentioned? (1=missed most, 5=covered all)
- false_positives: How many of the agent's findings seem irrelevant or wrong? (1=many wrong, 5=all valid)
- added_value: Did the agent find real issues the humans missed? (1=nothing useful added, 5=caught important issues)

Respond with JSON only, no explanation:
{{"coverage": <1-5>, "false_positives": <1-5>, "added_value": <1-5>, "notes": "<one sentence observation>"}}
"""


def find_prs_with_reviews(repo_full_name: str, max_prs: int = 7) -> list[int]:
    g = Github(settings.github_token)
    repo = g.get_repo(repo_full_name)
    found = []
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if len(found) >= max_prs:
            break
        if pr.changed_files > 0 and (pr.review_comments > 0 or pr.comments > 0):
            found.append(pr.number)
    return found


def get_human_reviews(repo_full_name: str, pr_number: int) -> str:
    g = Github(settings.github_token)
    repo = g.get_repo(repo_full_name)
    pr = repo.get_pull(pr_number)
    comments = []
    for c in pr.get_issue_comments():
        if c.body.strip():
            comments.append(f"[{c.user.login}]: {c.body[:500]}")
    for c in pr.get_review_comments():
        if c.body.strip():
            comments.append(f"[review on {c.path}]: {c.body[:500]}")
    return "\n\n".join(comments[:10])


def format_diff(files: list[dict]) -> str:
    parts = []
    for f in files[:5]:
        parts.append(f"### {f['filename']} ({f['status']})\n{f['patch'][:1500] if f['patch'] else '(no diff)'}")
    return "\n\n".join(parts)


def format_agent_review(review) -> str:
    parts = []
    for label, findings in [
        ("Logic", review.logic_issues),
        ("Security", review.security_issues),
        ("Code Quality", review.code_quality),
        ("Performance", review.performance_issues),
        ("Test Coverage", review.test_coverage),
    ]:
        for f in findings:
            parts.append(f"[{f.severity.upper()}] {label} | {f.file}: {f.description}")
    parts.append(f"Summary: {review.summary}")
    return "\n".join(parts)


def judge(diff: str, human_review: str, agent_review: str) -> dict:
    client = openai.OpenAI(api_key=settings.openai_api_key)
    prompt = JUDGE_PROMPT.format(
        diff=diff[:3000],
        human_review=human_review[:2000] if human_review else "(no human comments)",
        agent_review=agent_review,
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"coverage": 0, "false_positives": 0, "added_value": 0, "notes": "parse error"}


def evaluate_one(repo: str, pr_number: int) -> dict:
    result = {
        "repo": repo,
        "pr_number": pr_number,
        "status": "ok",
        "latency_s": 0,
        "total_findings": 0,
        "high_findings": 0,
        "coverage": 0,
        "false_positives": 0,
        "added_value": 0,
        "notes": "",
        "error": "",
    }
    try:
        t0 = time.time()
        files = get_pr_files(repo, pr_number)
        review = review_pr(files)
        result["latency_s"] = round(time.time() - t0, 1)

        all_findings = (
            review.logic_issues + review.security_issues +
            review.code_quality + review.performance_issues +
            review.test_coverage
        )
        result["total_findings"] = len(all_findings)
        result["high_findings"] = sum(1 for f in all_findings if f.severity.value == "high")

        human_review = get_human_reviews(repo, pr_number)
        scores = judge(format_diff(files), human_review, format_agent_review(review))

        result["coverage"] = scores.get("coverage", 0)
        result["false_positives"] = scores.get("false_positives", 0)
        result["added_value"] = scores.get("added_value", 0)
        result["notes"] = scores.get("notes", "")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def main():
    print("PR Review Assistant — Baseline Evaluation")
    print("=" * 45)

    pr_list = []
    print("\nCollecting PRs...")
    for repo in TARGET_REPOS:
        prs = find_prs_with_reviews(repo, max_prs=7)
        pr_list.extend((repo, n) for n in prs)
        print(f"  {repo}: {len(prs)} PRs")

    print(f"\nTotal: {len(pr_list)} PRs\n")

    results = []
    for i, (repo, pr_num) in enumerate(pr_list, 1):
        print(f"[{i}/{len(pr_list)}] {repo}#{pr_num} ...", end=" ", flush=True)
        r = evaluate_one(repo, pr_num)
        results.append(r)
        if r["status"] == "ok":
            print(f"latency={r['latency_s']}s findings={r['total_findings']} coverage={r['coverage']}/5")
        else:
            print(f"ERROR: {r['error']}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outfile = f"eval_results_{timestamp}.csv"
    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    ok = [r for r in results if r["status"] == "ok"]
    if ok:
        print(f"\n{'='*45}")
        print(f"Completed {len(ok)}/{len(results)} PRs successfully")
        print(f"  Avg latency:       {sum(r['latency_s'] for r in ok)/len(ok):.1f}s")
        print(f"  Avg coverage:      {sum(r['coverage'] for r in ok)/len(ok):.1f}/5")
        print(f"  Avg false pos:     {sum(r['false_positives'] for r in ok)/len(ok):.1f}/5")
        print(f"  Avg added value:   {sum(r['added_value'] for r in ok)/len(ok):.1f}/5")
    print(f"\nResults saved to: {outfile}")


if __name__ == "__main__":
    main()
