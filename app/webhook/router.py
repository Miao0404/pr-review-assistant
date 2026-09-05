import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request

from app.core.config import settings

router = APIRouter()


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


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

    # 后续接入 review 逻辑
    return {"status": "received", "pr": pr_number, "repo": repo_full_name}