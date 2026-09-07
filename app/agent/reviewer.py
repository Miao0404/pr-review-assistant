import json
import anthropic
from app.core.config import settings
from app.schemas.review import ReviewResult
from app.rag.chunker import chunk_pr_files
from app.rag.embedder import embed_chunks
from app.rag.retriever import store_chunks, search_chunks

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

DIMENSIONS = {
    "logic_issues": "logic errors, incorrect conditions, wrong control flow",
    "security_issues": "security vulnerabilities, injection, authentication, authorization",
    "code_quality": "code duplication, naming, readability, maintainability",
    "performance_issues": "performance, slow query, memory leak, inefficient algorithm",
    "test_coverage": "missing tests, edge cases, error handling not tested",
}


def build_context(dimension_query: str) -> str:
    chunks = search_chunks(dimension_query, top_k=5)
    parts = []
    for chunk in chunks:
        parts.append(f"File: {chunk['filename']}\n{chunk['content']}")
    return "\n\n---\n\n".join(parts)


def review_pr(files: list[dict]) -> ReviewResult:
    # 1. 切块、编码、存入 Qdrant
    chunks = chunk_pr_files(files)
    chunks = embed_chunks(chunks)
    store_chunks(chunks)

    # 2. 按维度搜索，拼成上下文
    contexts = {}
    for dimension, query in DIMENSIONS.items():
        contexts[dimension] = build_context(query)

    # 3. 把所有上下文合并，发给 Claude
    context_text = ""
    for dimension, context in contexts.items():
        context_text += f"\n\n=== {dimension} ===\n{context}"

    prompt = f"""You are an expert code reviewer. Analyze the following PR diff for issues.

{context_text}

Return a thorough review covering logic issues, security issues, code quality, 
performance issues, and test coverage. For each finding include the filename, 
description, severity (high/medium/low), and a concrete suggestion.
"""

    response = client.messages.create(
        model=settings.review_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "submit_review",
                "description": "Submit the structured PR review",
                "input_schema": ReviewResult.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": "submit_review"},
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return ReviewResult(**tool_use.input)