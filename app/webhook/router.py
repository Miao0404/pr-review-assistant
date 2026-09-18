import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings
from app.github.client import get_pr_files, post_review_comment
from app.agent.reviewer import review_pr

router = APIRouter()


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

def format_review(review) -> str:
    lines = ["## AI PR Review\n"]
    sections = {
        "Logic Issues": review.logic_issues,
        "Security Issues": review.security_issues,
        "Code Quality": review.code_quality,
        "Performance Issues": review.performance_issues,
        "Test Coverage": review.test_coverage,
    }
    for title, findings in sections.items():
        if not findings:
            continue
        lines.append(f"### {title}")
        for f in findings:
            lines.append(f"**[{f.severity.upper()}]** `{f.file}`")
            lines.append(f"{f.description}")
            lines.append(f"{f.suggestion}\n")
    lines.append(f"---\n**Summary:** {review.summary}")
    return "\n".join(lines)


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: str = Header(...),
):
    payload = await request.body()

    if not verify_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    if x_github_event != "pull_request":
        return {"status": "ignored"}

    data = json.loads(payload)
    action = data.get("action")

    if action not in ("opened", "synchronize"):
        return {"status": "ignored"}

    pr_number = data["pull_request"]["number"]
    repo_full_name = data["repository"]["full_name"]

    files = get_pr_files(repo_full_name, pr_number)
    review = review_pr(files)
    comment = format_review(review)
    post_review_comment(repo_full_name, pr_number, comment)

    return {"status": "reviewed", "pr": pr_number}