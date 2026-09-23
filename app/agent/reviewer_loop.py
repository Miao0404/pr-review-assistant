import anthropic
from github import Github
from app.core.config import settings
from app.schemas.review import ReviewResult
from app.rag.chunker import chunk_pr_files
from app.rag.embedder import embed_chunks
from app.rag.retriever import store_chunks, search_chunks

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

SYSTEM_PROMPT = """You are an expert code reviewer. You have tools to explore the codebase:

- search_code(query): semantic search over the PR's changed files
- get_file_content(filename): get the full file content from the repo (not just the diff)
- submit_review(...): submit your final structured review — call this when done

Workflow:
1. Read the PR diff in the user message
2. Use search_code to find related patterns or logic
3. Use get_file_content when you need full context for a specific file
4. Call submit_review with your complete findings"""

TOOLS = [
    {
        "name": "search_code",
        "description": "Semantic search over the PR's changed code chunks. Use to find relevant patterns, related logic, or context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, e.g. 'authentication logic' or 'error handling'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_file_content",
        "description": "Get the full current content of a file from the repository. Use when you need more context than the diff provides.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "File path, e.g. 'app/main.py' or 'tests/test_auth.py'"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "submit_review",
        "description": "Submit the final structured PR review. Call this when you have enough information.",
        "input_schema": ReviewResult.model_json_schema(),
    }
]


def _handle_search_code(query: str) -> str:
    chunks = search_chunks(query, top_k=5)
    if not chunks:
        return "No relevant code found."
    parts = [f"File: {c['filename']}\n{c['content']}" for c in chunks]
    return "\n\n---\n\n".join(parts)


def _handle_get_file_content(filename: str, files: list[dict], repo=None, pr=None) -> str:
    if repo is not None and pr is not None:
        try:
            content = repo.get_contents(filename, ref=pr.head.sha)
            text = content.decoded_content.decode("utf-8")
            return text[:6000]
        except Exception:
            pass
    for f in files:
        if f["filename"] == filename:
            return f"(diff only)\n{f['patch']}" if f["patch"] else "(no content available)"
    return f"File '{filename}' not found in this PR."


def review_pr(files: list[dict], repo_full_name: str = None, pr_number: int = None) -> ReviewResult:
    # 1. Chunk, embed, store
    chunks = chunk_pr_files(files)
    chunks = embed_chunks(chunks)
    store_chunks(chunks)

    # 2. Set up GitHub client if credentials provided
    github_repo = None
    github_pr = None
    if repo_full_name and pr_number:
        g = Github(settings.github_token)
        github_repo = g.get_repo(repo_full_name)
        github_pr = github_repo.get_pull(pr_number)

    # 3. Build initial diff message
    diff_parts = []
    for f in files:
        diff_parts.append(f"### {f['filename']} ({f['status']})\n{f['patch'][:2000]}")
    diff_text = "\n\n".join(diff_parts)

    messages = [
        {
            "role": "user",
            "content": (
                f"Please review this PR:\n\n{diff_text}\n\n"
                "Use your tools to explore the code, then call submit_review with your findings."
            )
        }
    ]

    # 4. Agent loop
    max_iterations = 10
    for _ in range(max_iterations):
        response = client.messages.create(
            model=settings.review_model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=TOOLS,
        )

        messages.append({"role": "assistant", "content": response.content})

        submit_call = None
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "submit_review":
                submit_call = block
                continue

            if block.name == "search_code":
                result = _handle_search_code(block.input["query"])
            elif block.name == "get_file_content":
                result = _handle_get_file_content(
                    block.input["filename"], files, github_repo, github_pr
                )
            else:
                result = f"Unknown tool: {block.name}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        # Claude submitted the review — return it
        if submit_call is not None:
            data = submit_call.input
            if "review" in data:
                data = data["review"]
            result = ReviewResult(**data)
            if not result.summary.strip():
                raise ValueError("Agent submitted empty review (no summary)")
            return result

        if response.stop_reason == "end_turn":
            raise ValueError("Agent ended without calling submit_review")

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    raise ValueError("Agent loop exceeded max iterations without submitting review")
