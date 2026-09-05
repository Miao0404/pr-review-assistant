from fastapi import FastAPI
from app.webhook.router import router as webhook_router

app = FastAPI(title="PR Review Assistant")

app.include_router(webhook_router, prefix="/webhook")


@app.get("/health")
async def health():
    return {"status": "ok"}