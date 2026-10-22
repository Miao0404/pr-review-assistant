"""The reviewer agent with a configurable tool set. Same loop, prompt and output schema for every condition.

C0: no exploration tools (diff only, one shot + submit)
C1: search_code   (semantic search over the PR's diff chunks: a way to look, but no new information)
C2: get_file_content   (real files at the reviewed commit: new information, no search)

Differences from app/agent/reviewer.py, applied identically to all conditions:
  - get_file_content gets the repo + head sha, so it returns real file content (the old eval never passed them)
  - an invalid submit_review gets a tool error back and the agent may retry, instead of crashing the run
  - if the model stops without submitting, it gets one nudge
  - token usage, tool calls and iterations are recorded
"""

import time

import anthropic
from github import Github
from pydantic import ValidationError

from app.core.config import settings
from app.rag.chunker import chunk_pr_files
from app.rag.embedder import embed_chunks
from app.rag.retriever import search_chunks, store_chunks
from app.schemas.review import ReviewResult
from .common import cost_usd

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
_gh = Github(settings.github_token)
_repo_cache: dict = {}

MAX_ITERATIONS = 10
DIFF_CHARS_PER_FILE = 20000  # no truncation: every setup sees the full diff (longest in sample ~6.6k)
FILE_CHARS = 6000

TOOL_DEFS = {
    "search_code": {
        "name": "search_code",
        "description": "Semantic search over the PR's changed code chunks. Use to find relevant patterns, related logic, or context.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for, e.g. 'error handling'"}},
            "required": ["query"],
        },
    },
    "get_file_content": {
        "name": "get_file_content",
        "description": "Get the full current content of a file from the repository at the PR's head commit. Use when you need more context than the diff provides.",
        "input_schema": {
            "type": "object",
            "properties": {"filename": {"type": "string", "description": "File path, e.g. 'app/main.py'"}},
            "required": ["filename"],
        },
    },
    "submit_review": {
        "name": "submit_review",
        "description": "Submit the final structured PR review. Each category must be a JSON array of finding objects. Call this when you have enough information.",
        "input_schema": ReviewResult.model_json_schema(),
    },
}

TOOL_LINES = {
    "search_code": "- search_code(query): semantic search over the PR's changed files",
    "get_file_content": "- get_file_content(filename): get the full file content from the repo (not just the diff)",
    "submit_review": "- submit_review(...): submit your final structured review. Call this when done",
}

CONDITION_TOOLS = {
    "C0": ["submit_review"],
    "C1": ["search_code", "submit_review"],
    "C2": ["get_file_content", "submit_review"],  # one factor vs baseline: real extra context, no search
}


def system_prompt(tools: list[str]) -> str:
    lines = ["You are an expert code reviewer. You have these tools:", ""]
    lines += [TOOL_LINES[t] for t in tools]
    lines += ["", "Read the PR diff in the user message, use the available tools if they help, then call submit_review with your complete findings."]
    return "\n".join(lines)


def _repo(name: str):
    if name not in _repo_cache:
        _repo_cache[name] = _gh.get_repo(name)
    return _repo_cache[name]


def _get_file(filename: str, pr: dict) -> str:
    try:
        content = _repo(pr["repo"]).get_contents(filename, ref=pr["head_sha"])
        return content.decoded_content.decode("utf-8", errors="replace")[:FILE_CHARS]
    except Exception:
        for f in pr["files"]:
            if f["filename"] == filename:
                return f"(diff only)\n{f['patch']}" if f["patch"] else "(no content available)"
        return f"File '{filename}' not found."


def _search(query: str) -> str:
    chunks = search_chunks(query, top_k=5)
    if not chunks:
        return "No relevant code found."
    return "\n\n---\n\n".join(f"File: {c['filename']}\n{c['content']}" for c in chunks)


def _flatten(review: ReviewResult) -> list[dict]:
    out = []
    for cat in ["logic_issues", "security_issues", "code_quality", "performance_issues", "test_coverage"]:
        for f in getattr(review, cat):
            out.append({"category": cat, "file": f.file, "severity": f.severity.value,
                        "description": f.description, "suggestion": f.suggestion})
    for i, f in enumerate(out, 1):
        f["id"] = i
    return out


def _strip_trailing_thinking(content: list) -> list:
    blocks = list(content)
    while blocks and blocks[-1].type in ("thinking", "redacted_thinking"):
        blocks.pop()
    return blocks


def review(pr: dict, condition: str) -> dict:
    tools = CONDITION_TOOLS[condition]
    model = settings.review_model
    rec = {"status": "ok", "error": "", "iterations": 0, "tool_calls": {}, "input_tokens": 0,
           "output_tokens": 0, "invalid_submits": 0, "nudges": 0, "findings": [], "summary": ""}
    t0 = time.time()

    try:
        if "search_code" in tools:
            store_chunks(embed_chunks(chunk_pr_files(pr["files"])))

        diff_text = "\n\n".join(
            f"### {f['filename']} ({f['status']})\n{f['patch'][:DIFF_CHARS_PER_FILE]}" for f in pr["files"]
        )
        messages = [{"role": "user", "content": f"Please review this PR:\n\n{diff_text}\n\nThen call submit_review with your findings."}]

        result = None
        for _ in range(MAX_ITERATIONS):
            rec["iterations"] += 1
            resp = client.messages.create(
                model=model, max_tokens=8192, system=system_prompt(tools),
                messages=messages, tools=[TOOL_DEFS[t] for t in tools],
            )
            u = resp.usage
            rec["input_tokens"] += u.input_tokens + (getattr(u, "cache_creation_input_tokens", 0) or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
            rec["output_tokens"] += u.output_tokens

            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                if resp.stop_reason == "max_tokens":
                    raise RuntimeError("hit max_tokens without a tool call")
                if rec["nudges"] >= 1:
                    raise RuntimeError("ended without calling submit_review (after nudge)")
                rec["nudges"] += 1
                kept = _strip_trailing_thinking(resp.content) or [{"type": "text", "text": "(no output)"}]
                messages.append({"role": "assistant", "content": kept})
                messages.append({"role": "user", "content": "Please call submit_review now with your findings."})
                continue

            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in tool_uses:
                rec["tool_calls"][b.name] = rec["tool_calls"].get(b.name, 0) + 1
                if b.name == "submit_review":
                    data = b.input.get("review", b.input) if isinstance(b.input, dict) else b.input
                    try:
                        r = ReviewResult(**data)
                        if not r.summary.strip():
                            raise ValueError("summary is empty")
                        result = r
                        results.append({"type": "tool_result", "tool_use_id": b.id, "content": "Review received."})
                    except (ValidationError, ValueError, TypeError) as e:
                        rec["invalid_submits"] += 1
                        results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                                        "content": f"Invalid review: {str(e)[:800]}. Each category must be a JSON array of objects. Submit again."})
                elif b.name == "search_code":
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": _search(b.input.get("query", ""))})
                elif b.name == "get_file_content":
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": _get_file(b.input.get("filename", ""), pr)})
                else:
                    results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True, "content": f"Unknown tool {b.name}"})

            if result is not None:
                break
            messages.append({"role": "user", "content": results})

        if result is None:
            raise RuntimeError("no valid review within max iterations")
        rec["findings"] = _flatten(result)
        rec["summary"] = result.summary

    except Exception as e:
        rec["status"] = "error"
        rec["error"] = f"{type(e).__name__}: {str(e)[:500]}"

    rec["latency_s"] = round(time.time() - t0, 1)
    rec["model"] = model
    rec["cost_usd"] = round(cost_usd(model, rec["input_tokens"], rec["output_tokens"]), 5)
    return rec
