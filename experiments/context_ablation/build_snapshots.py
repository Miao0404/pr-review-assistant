"""Step 1b: review each PR at the version the human reviewer actually saw.

For each candidate PR:
  - collect substantive human review comments on .py files (same rules as before:
    no bots, no PR author, no "LGTM"-style, length >= 15)
  - group them by the commit they were written on (original_commit_id)
  - snapshot = the commit with the most such comments (ties: the earliest)
  - diff = base ... snapshot (what the reviewer saw), via GitHub compare
  - answer key comments = only the comments written on the snapshot
Keeps the PR if the snapshot diff has <= 5 files, at least one .py patch,
and every answer-key comment's file appears in the diff.

Writes data/candidates_snapshot.json (same format as candidates.json).
Run from repo root:  python -m experiments.context_ablation.build_snapshots
"""

from collections import defaultdict

from github import Github

from app.core.config import settings
from .common import DATA_DIR, REPOS, load_json, save_json
from .select_prs import TRIVIAL, is_bot

SRC = DATA_DIR / "candidates.json"
OUT = DATA_DIR / "candidates_snapshot.json"
MAX_FILES = 5


def main():
    g = Github(settings.github_token)
    cands = [c for c in load_json(SRC) if c["repo"] in REPOS]
    out, dropped = [], []
    for c in cands:
        repo = g.get_repo(c["repo"])
        pr = repo.get_pull(c["number"])
        author = pr.user.login if pr.user else None
        by_commit = defaultdict(list)
        for rc in pr.get_review_comments():
            body = (rc.body or "").strip()
            if is_bot(rc.user) or rc.user.login == author or len(body) < 15 or TRIVIAL.match(body):
                continue
            if not rc.path.endswith(".py"):
                continue
            by_commit[rc.original_commit_id].append({
                "author": rc.user.login, "path": rc.path,
                "line": rc.original_line, "body": body[:1500],
                "diff_hunk": "\n".join((rc.diff_hunk or "").splitlines()[-12:]),
                "created_at": rc.created_at.isoformat(),
            })
        if not by_commit:
            dropped.append((c["key"], "no .py comments")); continue
        snap = sorted(by_commit, key=lambda s: (-len(by_commit[s]), min(x["created_at"] for x in by_commit[s])))[0]
        try:
            cmp = repo.compare(pr.base.sha, snap)
        except Exception as e:
            dropped.append((c["key"], f"compare failed: {e}")); continue
        files = [{"filename": f.filename, "status": f.status, "patch": f.patch or ""} for f in cmp.files]
        names = {f["filename"] for f in files}
        comments = by_commit[snap]
        if len(files) > MAX_FILES:
            dropped.append((c["key"], f"{len(files)} files at snapshot")); continue
        if not any(f["filename"].endswith(".py") and f["patch"] for f in files):
            dropped.append((c["key"], "no .py patch")); continue
        if not all(x["path"] in names for x in comments):
            dropped.append((c["key"], "comment file not in snapshot diff")); continue
        out.append({**c, "head_sha": snap, "files": files, "human_comments": comments,
                    "final_sha": pr.head.sha, "snapshot_is_final": snap == pr.head.sha})
        print(f"  + {c['key']}: {len(comments)} comments on {snap[:7]} ({len(files)} files)"
              f"{' [final]' if snap == pr.head.sha else ''}", flush=True)
    save_json(OUT, out)
    print(f"\nKept {len(out)}, dropped {len(dropped)}")
    for k, why in dropped:
        print(f"  - {k}: {why}")


if __name__ == "__main__":
    main()
