"""Step 1: collect candidate PRs with a fixed, mechanical rule (no hand picking).

Rules (decided before any agent run):
  - fastapi, requests, httpx (flask from the old eval dropped: almost no line-level reviews)
  - merged PRs only
  - at least one substantive human review comment on a code line of a code file
    (bots, the PR author, and "LGTM"/"thanks"-style comments do not count)
  - not docs-only
  - at most 5 changed files
  - newest first

Writes data/candidates.json. Step 2 (build_ground_truth.py) turns candidates into the final sample.

Run from repo root:  python -m experiments.context_ablation.select_prs
"""

import re
import sys

from github import Github

from app.core.config import settings
from .common import DATA_DIR, REPOS, save_json

CANDIDATES_FILE = DATA_DIR / "candidates.json"
PER_REPO = 14          # more than the quota, because some will have no extractable issue
MAX_SCAN = 1500        # closed PRs to look at per repo (qualifying PRs are rare)
MAX_FILES = 5

DOC_EXT = (".md", ".rst", ".txt")
DOC_DIRS = ("docs/", "docs_src/", "doc/")
TRIVIAL = re.compile(
    r"^\s*(lgtm|looks good( to me)?|thanks?( you)?|thx|\+1|nice|great|done|fixed|ok(ay)?|👍|🎉|🚀|✅)[\s!.:)]*$",
    re.IGNORECASE,
)


def is_doc(path: str) -> bool:
    return path.endswith(DOC_EXT) or path.startswith(DOC_DIRS)


def is_bot(user) -> bool:
    return user is None or user.type == "Bot" or user.login.endswith("[bot]")


def substantive_comments(pr) -> list[dict]:
    out = []
    author = pr.user.login if pr.user else None
    for c in pr.get_review_comments():
        body = (c.body or "").strip()
        if is_bot(c.user) or c.user.login == author:
            continue
        if len(body) < 15 or TRIVIAL.match(body):
            continue
        if is_doc(c.path):
            continue
        out.append({
            "author": c.user.login,
            "path": c.path,
            "line": c.line or c.original_line,
            "body": body[:1500],
            "diff_hunk": "\n".join((c.diff_hunk or "").splitlines()[-12:]),
        })
    return out


def collect(repo_name: str, g: Github) -> list[dict]:
    repo = g.get_repo(repo_name)
    found, scanned = [], 0
    for pr in repo.get_pulls(state="closed", sort="created", direction="desc"):
        if len(found) >= PER_REPO or scanned >= MAX_SCAN:
            break
        scanned += 1
        if pr.merged_at is None:
            continue
        if pr.review_comments == 0 or pr.changed_files > MAX_FILES:
            continue
        files = [{"filename": f.filename, "status": f.status, "patch": f.patch or ""} for f in pr.get_files()]
        code_files = [f for f in files if not is_doc(f["filename"]) and f["patch"]]
        if not code_files:
            continue
        comments = substantive_comments(pr)
        if not comments:
            continue
        found.append({
            "key": f"{repo_name}#{pr.number}",
            "repo": repo_name,
            "number": pr.number,
            "title": pr.title,
            "created_at": pr.created_at.isoformat(),
            "head_sha": pr.head.sha,
            "files": files,
            "human_comments": comments,
        })
        print(f"  + {repo_name}#{pr.number} ({len(files)} files, {len(comments)} comments)", flush=True)
    print(f"{repo_name}: scanned {scanned}, kept {len(found)}")
    return found


def main():
    g = Github(settings.github_token)
    candidates = []
    for r in REPOS:
        candidates.extend(collect(r, g))
    save_json(CANDIDATES_FILE, candidates)
    print(f"\n{len(candidates)} candidates -> {CANDIDATES_FILE}")


if __name__ == "__main__":
    sys.exit(main())
